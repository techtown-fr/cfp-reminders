from __future__ import annotations

import json
from pathlib import Path

import click
import httpx
from rich.console import Console

from cfp_reminders.cache import Cache
from cfp_reminders.chat import ChatPostError, build_message, post_message
from cfp_reminders.display import render
from cfp_reminders.fetcher import fetch_cfps, filter_cfps
from cfp_reminders.meetown import MeetownPostError, build_snapshot, post_snapshot

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "cfp-reminders"
DEFAULT_TTL = 3600


@click.command()
@click.option("--country", default="France", help="Country to filter CFPs by.")
@click.option("--refresh", is_flag=True, help="Ignore cache and fetch fresh data.")
@click.option("--chat", is_flag=True, help="Post a reminder to Google Chat.")
@click.option(
    "--webhook-url",
    envvar="GOOGLE_CHAT_WEBHOOK_URL",
    default=None,
    help="Google Chat incoming webhook (env: GOOGLE_CHAT_WEBHOOK_URL).",
)
@click.option(
    "--days",
    type=click.IntRange(min=1),
    default=30,
    show_default=True,
    help="Chat reminder window, in days.",
)
@click.option("--meetown", is_flag=True, help="Push all open CFPs to Meetown.")
@click.option(
    "--meetown-url",
    envvar="MEETOWN_WEBHOOK_URL",
    default=None,
    help="Meetown endpoint (env: MEETOWN_WEBHOOK_URL).",
)
@click.option(
    "--meetown-token",
    envvar="MEETOWN_TOKEN",
    default=None,
    help="Meetown bearer token (env: MEETOWN_TOKEN).",
)
@click.option("--dry-run", is_flag=True, help="Print what would be sent, do not post.")
def main(
    country: str,
    refresh: bool,
    chat: bool,
    webhook_url: str | None,
    days: int,
    meetown: bool,
    meetown_url: str | None,
    meetown_token: str | None,
    dry_run: bool,
) -> None:
    """Show upcoming CFP deadlines from developers.events."""
    console = Console()
    if chat and meetown:
        raise click.UsageError("use --chat or --meetown, not both.")
    if chat and not dry_run and not webhook_url:
        raise click.UsageError("--chat needs GOOGLE_CHAT_WEBHOOK_URL or --dry-run.")
    if meetown and not dry_run and not (meetown_url and meetown_token):
        raise click.UsageError(
            "--meetown needs MEETOWN_WEBHOOK_URL and MEETOWN_TOKEN, or --dry-run."
        )
    push = chat or meetown

    cache = Cache(cache_dir=DEFAULT_CACHE_DIR, ttl_seconds=DEFAULT_TTL)

    cfps = None
    if not refresh and not push:
        cfps = cache.read()

    if cfps is None:
        try:
            cfps = fetch_cfps()
            cache.write(cfps)
        except httpx.HTTPError as e:
            # A push must never be built from stale data
            if push:
                raise click.ClickException(f"could not fetch CFP data: {e}") from None
            cfps = cache.read(allow_stale=True)
            if cfps is not None:
                console.print(
                    f"[yellow]Warning: fetch failed ({e}), using cached data.[/yellow]"
                )
            else:
                console.print(f"[red]Error: could not fetch CFP data: {e}[/red]")
                return

    filtered = filter_cfps(cfps, country=country)

    if chat:
        _send_chat(filtered, country, days, webhook_url, dry_run)
        return
    if meetown:
        _send_meetown(filtered, country, meetown_url, meetown_token, dry_run)
        return

    if not filtered:
        console.print(f"\nNo open CFPs found for {country}.")
        return

    render(filtered, console=console)


def _send_chat(
    cfps: list[dict], country: str, days: int, webhook_url: str | None, dry_run: bool
) -> None:
    message = build_message(cfps, country=country, days=days)
    if message is None:
        click.echo(f"No CFP closing within {days} days, nothing posted.")
    elif dry_run:
        click.echo(message)
    else:
        try:
            post_message(webhook_url, message)
        except ChatPostError as e:
            raise click.ClickException(f"Google Chat post failed: {e}") from None
        click.echo("Reminder posted to Google Chat.")


def _send_meetown(
    cfps: list[dict], country: str, url: str | None, token: str | None, dry_run: bool
) -> None:
    snapshot = build_snapshot(cfps, country=country)
    skipped = len(cfps) - len(snapshot["cfps"])
    if skipped:
        click.echo(f"{skipped} CFP skipped (no event date or CFP link).", err=True)
    if dry_run:
        click.echo(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return
    # Meetown replaces its list with each snapshot: an empty one would wipe it
    if not snapshot["cfps"]:
        raise click.ClickException("no CFP to push, Meetown left unchanged.")
    try:
        post_snapshot(url, token, snapshot)
    except MeetownPostError as e:
        raise click.ClickException(f"Meetown push failed: {e}") from None
    click.echo(f"{len(snapshot['cfps'])} CFP pushed to Meetown.")
