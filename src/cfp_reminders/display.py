from __future__ import annotations

import time
from datetime import UTC, datetime

from rich.console import Console
from rich.table import Table

# Urgency buckets: 0 to 7 days (this week), 8 to 30 days (this month), 31+ days (later)
DAY_SECONDS = 24 * 3600
WEEK_SECONDS = 7 * DAY_SECONDS
MONTH_SECONDS = 30 * DAY_SECONDS


def group_by_urgency(cfps: list[dict]) -> dict[str, list[dict]]:
    now_ms = time.time() * 1000
    groups: dict[str, list[dict]] = {
        "this_week": [],
        "this_month": [],
        "later": [],
    }
    for cfp in cfps:
        remaining_s = (cfp["untilDate"] - now_ms) / 1000
        if remaining_s <= WEEK_SECONDS:
            groups["this_week"].append(cfp)
        elif remaining_s <= MONTH_SECONDS:
            groups["this_month"].append(cfp)
        else:
            groups["later"].append(cfp)
    return groups


def format_deadline(until_date_ms: int, fmt: str = "%b %d, %Y") -> str:
    return datetime.fromtimestamp(until_date_ms / 1000, tz=UTC).strftime(fmt)


def _make_table(title: str, cfps: list[dict], style: str) -> Table:
    table = Table(title=title, title_style=style, show_lines=True)
    table.add_column("Conference", style="bold")
    table.add_column("Deadline")
    table.add_column("Location")
    table.add_column("CFP Link", style="dim")
    for cfp in cfps:
        table.add_row(
            cfp["conf"]["name"],
            format_deadline(cfp["untilDate"]),
            cfp["conf"].get("location", ""),
            cfp.get("link", ""),
        )
    return table


def render(cfps: list[dict], *, console: Console | None = None) -> None:
    console = console or Console()
    groups = group_by_urgency(cfps)

    sections = [
        ("Closing this week", groups["this_week"], "bold red"),
        ("Closing this month", groups["this_month"], "bold yellow"),
        ("Later", groups["later"], "bold green"),
    ]

    any_found = False
    for title, group_cfps, style in sections:
        if group_cfps:
            any_found = True
            console.print()
            console.print(_make_table(title, group_cfps, style))

    if not any_found:
        console.print("\nNo upcoming CFP deadlines found.")
