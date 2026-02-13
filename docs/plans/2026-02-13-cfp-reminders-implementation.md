# CFP Reminders Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python CLI tool that fetches CFP deadlines from developers.events, filters by country, and displays them in the terminal grouped by urgency.

**Architecture:** A `uv`-managed Python package with four modules: `cache.py` (local JSON cache with TTL), `fetcher.py` (HTTP fetch + filter), `display.py` (rich terminal output), and `cli.py` (click entry point). Data flows: fetch → cache → filter → group → display.

**Tech Stack:** Python 3.12+, uv, httpx, rich, click, pytest

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/cfp_reminders/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Initialize uv project**

Run:
```bash
cd cfp-reminders
uv init --lib --name cfp-reminders
```

This creates `pyproject.toml`, `src/cfp_reminders/__init__.py`, and other scaffolding.

**Step 2: Update pyproject.toml with dependencies and CLI entry point**

Edit `pyproject.toml` to contain:

```toml
[project]
name = "cfp-reminders"
version = "0.1.0"
description = "Track CFP deadlines from developers.events"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "click>=8.1",
    "httpx>=0.27",
    "rich>=13.0",
]

[project.scripts]
cfp-reminders = "cfp_reminders.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-httpx>=0.35",
]
```

**Step 3: Add dev dependencies and sync**

Run:
```bash
uv sync
```

Expected: lock file created, dependencies installed.

**Step 4: Create empty test package**

Create `tests/__init__.py` as an empty file.

**Step 5: Verify setup**

Run:
```bash
uv run pytest --co
```

Expected: "no tests ran" (no test files yet), exit 5 — confirms pytest works.

**Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/ tests/ .python-version
git commit -m "feat: scaffold uv project with dependencies"
```

---

### Task 2: Cache Module

**Files:**
- Create: `src/cfp_reminders/cache.py`
- Create: `tests/test_cache.py`

**Step 1: Write the failing tests**

Create `tests/test_cache.py`:

```python
import json
import time
from pathlib import Path

from cfp_reminders.cache import Cache


def test_read_returns_none_when_no_cache(tmp_path):
    cache = Cache(cache_dir=tmp_path, ttl_seconds=3600)
    assert cache.read() is None


def test_write_and_read_within_ttl(tmp_path):
    cache = Cache(cache_dir=tmp_path, ttl_seconds=3600)
    data = [{"conf": {"name": "Test Conf"}}]
    cache.write(data)
    assert cache.read() == data


def test_read_returns_none_when_expired(tmp_path):
    cache = Cache(cache_dir=tmp_path, ttl_seconds=0)
    data = [{"conf": {"name": "Test Conf"}}]
    cache.write(data)
    time.sleep(0.01)
    assert cache.read() is None


def test_read_expired_returns_data_when_allow_stale(tmp_path):
    cache = Cache(cache_dir=tmp_path, ttl_seconds=0)
    data = [{"conf": {"name": "Test Conf"}}]
    cache.write(data)
    time.sleep(0.01)
    assert cache.read(allow_stale=True) == data


def test_cache_creates_directory(tmp_path):
    cache_dir = tmp_path / "nested" / "dir"
    cache = Cache(cache_dir=cache_dir, ttl_seconds=3600)
    cache.write([{"test": True}])
    assert cache_dir.exists()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cfp_reminders.cache'`

**Step 3: Write minimal implementation**

Create `src/cfp_reminders/cache.py`:

```python
from __future__ import annotations

import json
import time
from pathlib import Path

CACHE_FILENAME = "cfps.json"
META_FILENAME = "meta.json"


class Cache:
    def __init__(self, cache_dir: Path, ttl_seconds: int = 3600) -> None:
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self._data_path = cache_dir / CACHE_FILENAME
        self._meta_path = cache_dir / META_FILENAME

    def read(self, *, allow_stale: bool = False) -> list | None:
        if not self._data_path.exists() or not self._meta_path.exists():
            return None
        meta = json.loads(self._meta_path.read_text())
        age = time.time() - meta["written_at"]
        if age > self.ttl_seconds and not allow_stale:
            return None
        return json.loads(self._data_path.read_text())

    def write(self, data: list) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._data_path.write_text(json.dumps(data))
        self._meta_path.write_text(json.dumps({"written_at": time.time()}))
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cache.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/cfp_reminders/cache.py tests/test_cache.py
git commit -m "feat: add cache module with TTL and stale fallback"
```

---

### Task 3: Fetcher Module

**Files:**
- Create: `src/cfp_reminders/fetcher.py`
- Create: `tests/test_fetcher.py`

**Step 1: Write the failing tests**

Create `tests/test_fetcher.py`:

```python
import time
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from cfp_reminders.fetcher import fetch_cfps, filter_cfps

# Timestamps in milliseconds
FUTURE_TS = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp() * 1000)
PAST_TS = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp() * 1000)

SAMPLE_CFPS = [
    {
        "link": "https://example.com/cfp1",
        "until": "March-15-2026",
        "untilDate": FUTURE_TS,
        "conf": {
            "name": "DevFest Paris",
            "date": [FUTURE_TS],
            "hyperlink": "https://devfest.paris",
            "status": "open",
            "location": "Paris (France)",
        },
    },
    {
        "link": "https://example.com/cfp2",
        "until": "Jan-01-2025",
        "untilDate": PAST_TS,
        "conf": {
            "name": "Old Conf",
            "date": [PAST_TS],
            "hyperlink": "https://old.conf",
            "status": "open",
            "location": "Lyon (France)",
        },
    },
    {
        "link": "https://example.com/cfp3",
        "until": "April-01-2026",
        "untilDate": FUTURE_TS,
        "conf": {
            "name": "JSConf Berlin",
            "date": [FUTURE_TS],
            "hyperlink": "https://jsconf.berlin",
            "status": "open",
            "location": "Berlin (Germany)",
        },
    },
]


def test_filter_by_country():
    result = filter_cfps(SAMPLE_CFPS, country="France")
    names = [c["conf"]["name"] for c in result]
    assert "DevFest Paris" in names
    assert "JSConf Berlin" not in names


def test_filter_excludes_past_deadlines():
    result = filter_cfps(SAMPLE_CFPS, country="France")
    names = [c["conf"]["name"] for c in result]
    assert "Old Conf" not in names


def test_filter_sorted_by_deadline():
    result = filter_cfps(SAMPLE_CFPS, country="France")
    deadlines = [c["untilDate"] for c in result]
    assert deadlines == sorted(deadlines)


def test_filter_skips_malformed_entries():
    bad_data = [{"link": "x"}]  # missing conf, untilDate
    result = filter_cfps(bad_data, country="France")
    assert result == []


def test_fetch_cfps_makes_http_request(httpx_mock):
    httpx_mock.add_response(
        url="https://developers.events/all-cfps.json",
        json=SAMPLE_CFPS,
    )
    result = fetch_cfps()
    assert len(result) == 3
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_fetcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cfp_reminders.fetcher'`

**Step 3: Write minimal implementation**

Create `src/cfp_reminders/fetcher.py`:

```python
from __future__ import annotations

import time

import httpx

CFP_URL = "https://developers.events/all-cfps.json"


def fetch_cfps() -> list[dict]:
    response = httpx.get(CFP_URL, timeout=10)
    response.raise_for_status()
    return response.json()


def filter_cfps(cfps: list[dict], *, country: str) -> list[dict]:
    now_ms = time.time() * 1000
    country_tag = f"({country})"
    filtered = []
    for cfp in cfps:
        try:
            location = cfp["conf"]["location"]
            deadline = cfp["untilDate"]
        except (KeyError, TypeError):
            continue
        if country_tag in location and deadline > now_ms:
            filtered.append(cfp)
    filtered.sort(key=lambda c: c["untilDate"])
    return filtered
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_fetcher.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/cfp_reminders/fetcher.py tests/test_fetcher.py
git commit -m "feat: add fetcher module with country filtering"
```

---

### Task 4: Display Module

**Files:**
- Create: `src/cfp_reminders/display.py`
- Create: `tests/test_display.py`

**Step 1: Write the failing tests**

Create `tests/test_display.py`:

```python
from datetime import datetime, timedelta, timezone

from cfp_reminders.display import group_by_urgency

NOW = datetime.now(timezone.utc)


def _make_cfp(days_until_deadline: int, name: str = "Conf") -> dict:
    deadline = NOW + timedelta(days=days_until_deadline)
    return {
        "link": "https://example.com/cfp",
        "until": "Some-Date",
        "untilDate": int(deadline.timestamp() * 1000),
        "conf": {
            "name": name,
            "date": [int(deadline.timestamp() * 1000)],
            "hyperlink": "https://example.com",
            "status": "open",
            "location": "Paris (France)",
        },
    }


def test_group_this_week():
    cfps = [_make_cfp(3, "Soon Conf")]
    groups = group_by_urgency(cfps)
    assert len(groups["this_week"]) == 1
    assert groups["this_week"][0]["conf"]["name"] == "Soon Conf"


def test_group_this_month():
    cfps = [_make_cfp(15, "Month Conf")]
    groups = group_by_urgency(cfps)
    assert len(groups["this_month"]) == 1


def test_group_later():
    cfps = [_make_cfp(60, "Later Conf")]
    groups = group_by_urgency(cfps)
    assert len(groups["later"]) == 1


def test_group_multiple_buckets():
    cfps = [
        _make_cfp(2, "Week"),
        _make_cfp(20, "Month"),
        _make_cfp(90, "Later"),
    ]
    groups = group_by_urgency(cfps)
    assert len(groups["this_week"]) == 1
    assert len(groups["this_month"]) == 1
    assert len(groups["later"]) == 1


def test_group_empty():
    groups = group_by_urgency([])
    assert groups["this_week"] == []
    assert groups["this_month"] == []
    assert groups["later"] == []
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_display.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cfp_reminders.display'`

**Step 3: Write minimal implementation**

Create `src/cfp_reminders/display.py`:

```python
from __future__ import annotations

import time
from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table

WEEK_SECONDS = 7 * 24 * 3600
MONTH_SECONDS = 30 * 24 * 3600


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


def _format_deadline(until_date_ms: int) -> str:
    dt = datetime.fromtimestamp(until_date_ms / 1000, tz=timezone.utc)
    return dt.strftime("%b %d, %Y")


def _make_table(title: str, cfps: list[dict], style: str) -> Table:
    table = Table(title=title, title_style=style, show_lines=True)
    table.add_column("Conference", style="bold")
    table.add_column("Deadline")
    table.add_column("Location")
    table.add_column("CFP Link", style="dim")
    for cfp in cfps:
        table.add_row(
            cfp["conf"]["name"],
            _format_deadline(cfp["untilDate"]),
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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_display.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/cfp_reminders/display.py tests/test_display.py
git commit -m "feat: add display module with urgency grouping"
```

---

### Task 5: CLI Module

**Files:**
- Create: `src/cfp_reminders/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write the failing tests**

Create `tests/test_cli.py`:

```python
from unittest.mock import patch

from click.testing import CliRunner

from cfp_reminders.cli import main

SAMPLE_CFPS = [
    {
        "link": "https://example.com/cfp1",
        "until": "March-15-2026",
        "untilDate": 1773590400000,  # far future
        "conf": {
            "name": "DevFest Paris",
            "date": [1773590400000],
            "hyperlink": "https://devfest.paris",
            "status": "open",
            "location": "Paris (France)",
        },
    },
]


@patch("cfp_reminders.cli.fetch_cfps", return_value=SAMPLE_CFPS)
def test_default_shows_france(mock_fetch):
    runner = CliRunner()
    result = runner.invoke(main)
    assert result.exit_code == 0
    assert "DevFest Paris" in result.output


@patch("cfp_reminders.cli.fetch_cfps", side_effect=Exception("Network error"))
def test_network_error_shows_message(mock_fetch):
    runner = CliRunner()
    result = runner.invoke(main)
    assert result.exit_code == 0
    assert "error" in result.output.lower() or "Error" in result.output


@patch("cfp_reminders.cli.fetch_cfps", return_value=[])
def test_no_cfps_shows_message(mock_fetch):
    runner = CliRunner()
    result = runner.invoke(main)
    assert result.exit_code == 0
    assert "No" in result.output
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cfp_reminders.cli'`

**Step 3: Write minimal implementation**

Create `src/cfp_reminders/cli.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: 3 passed

**Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All 18 tests pass

**Step 6: Commit**

```bash
git add src/cfp_reminders/cli.py tests/test_cli.py
git commit -m "feat: add CLI entry point with click"
```

---

### Task 6: Integration Test & Final Verification

**Files:**
- None created — just verification

**Step 1: Verify CLI entry point works**

Run:
```bash
uv run cfp-reminders --help
```

Expected: Shows help text with `--country` and `--refresh` options.

**Step 2: Run live test**

Run:
```bash
uv run cfp-reminders
```

Expected: Fetches real data, displays France CFPs grouped by urgency (or "No open CFPs found" if none currently open).

**Step 3: Test with different country**

Run:
```bash
uv run cfp-reminders --country "Germany"
```

Expected: Shows Germany CFPs.

**Step 4: Test refresh flag**

Run:
```bash
uv run cfp-reminders --refresh
```

Expected: Fetches fresh data (ignoring cache).

**Step 5: Run full test suite one final time**

Run: `uv run pytest -v`
Expected: All tests pass.

**Step 6: Final commit if any adjustments were needed**

Only if fixes were required during integration testing.
