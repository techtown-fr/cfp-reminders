from __future__ import annotations

from pathlib import Path

import click
import httpx
from rich.console import Console

from cfp_reminders.cache import Cache
from cfp_reminders.chat import ChatPostError, build_message, post_message
from cfp_reminders.display import render
from cfp_reminders.fetcher import fetch_cfps, filter_cfps

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
    "--days", default=30, show_default=True, help="Chat reminder window, in days."
)
@click.option("--dry-run", is_flag=True, help="Print the chat message, do not post.")
def main(
    country: str,
    refresh: bool,
    chat: bool,
    webhook_url: str | None,
    days: int,
    dry_run: bool,
) -> None:
    """Show upcoming CFP deadlines from developers.events."""
    console = Console()
    if chat and not dry_run and not webhook_url:
        raise click.UsageError("--chat needs GOOGLE_CHAT_WEBHOOK_URL or --dry-run.")

    cache = Cache(cache_dir=DEFAULT_CACHE_DIR, ttl_seconds=DEFAULT_TTL)

    cfps = None
    if not refresh:
        cfps = cache.read()

    if cfps is None:
        try:
            cfps = fetch_cfps()
            cache.write(cfps)
        except httpx.HTTPError as e:
            # Try stale cache as fallback
            cfps = cache.read(allow_stale=True)
            if cfps is not None:
                console.print(
                    f"[yellow]Warning: fetch failed ({e}), using cached data.[/yellow]"
                )
            else:
                if chat:
                    raise click.ClickException(
                        f"could not fetch CFP data: {e}"
                    ) from None
                console.print(f"[red]Error: could not fetch CFP data: {e}[/red]")
                return

    filtered = filter_cfps(cfps, country=country)

    if chat:
        _send_chat(filtered, country, days, webhook_url, dry_run)
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
