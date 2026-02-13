from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from cfp_reminders.cache import Cache
from cfp_reminders.display import render
from cfp_reminders.fetcher import fetch_cfps, filter_cfps

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "cfp-reminders"
DEFAULT_TTL = 3600


@click.command()
@click.option("--country", default="France", help="Country to filter CFPs by.")
@click.option("--refresh", is_flag=True, help="Ignore cache and fetch fresh data.")
def main(country: str, refresh: bool) -> None:
    """Show upcoming CFP deadlines from developers.events."""
    console = Console()
    cache = Cache(cache_dir=DEFAULT_CACHE_DIR, ttl_seconds=DEFAULT_TTL)

    cfps = None
    if not refresh:
        cfps = cache.read()

    if cfps is None:
        try:
            cfps = fetch_cfps()
            cache.write(cfps)
        except Exception as e:
            # Try stale cache as fallback
            cfps = cache.read(allow_stale=True)
            if cfps is not None:
                console.print(
                    f"[yellow]Warning: fetch failed ({e}), using cached data.[/yellow]"
                )
            else:
                console.print(f"[red]Error: could not fetch CFP data: {e}[/red]")
                return

    filtered = filter_cfps(cfps, country=country)
    if not filtered:
        console.print(f"\nNo open CFPs found for {country}.")
        return

    render(filtered, console=console)
