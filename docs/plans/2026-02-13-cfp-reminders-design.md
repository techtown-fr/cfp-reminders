# CFP Reminders — Design Document

## Problem

Track Call for Papers (CFP) deadlines for tech conferences in France, using data from [developers.events](https://developers.events), and display them in the terminal grouped by urgency.

## Data Source

- **Endpoint:** `https://developers.events/all-cfps.json`
- **Structure per entry:**
  - `link` — CFP submission URL
  - `until` — Deadline (human-readable, e.g. "March-15-2026")
  - `untilDate` — Deadline as Unix timestamp (milliseconds)
  - `conf.name` — Conference name
  - `conf.date` — Conference date(s) as timestamp array
  - `conf.hyperlink` — Conference homepage
  - `conf.location` — Location string, e.g. "Paris (France)"
- **Filtering:** Match `(France)` in `conf.location` (simple string match on the single CFP endpoint)

## Solution

An installable Python CLI tool managed with `uv`.

### Project Structure

```
cfp-reminders/
├── pyproject.toml          # uv-managed, dependencies, CLI entry point
├── src/
│   └── cfp_reminders/
│       ├── __init__.py
│       ├── cli.py          # CLI entry point (click)
│       ├── fetcher.py      # Fetch + filter CFP data
│       ├── display.py      # Terminal formatting (rich)
│       └── cache.py        # Local JSON cache with TTL
└── tests/
```

### Dependencies

- `httpx` — HTTP client
- `rich` — Terminal tables and color coding
- `click` — CLI framework

### CLI Interface

```bash
# Show all upcoming France CFPs grouped by urgency (default)
cfp-reminders

# Force refresh (ignore cache)
cfp-reminders --refresh

# Filter by a different country
cfp-reminders --country "Germany"
```

### Data Flow

1. **Fetch:** `fetcher.py` GETs `https://developers.events/all-cfps.json`
2. **Cache:** Response cached at `~/.cache/cfp-reminders/cfps.json` with 1-hour TTL
3. **Filter:** Keep entries where `conf.location` contains `(<country>)` AND `untilDate` is in the future
4. **Sort:** By `untilDate` ascending (soonest first)
5. **Group:** Into urgency buckets:
   - **Closing this week** (0–7 days) — red
   - **Closing this month** (8–30 days) — yellow
   - **Later** (31+ days) — green
6. **Display:** Rich table per group: Conference name, Deadline, Location, CFP link

### Error Handling

- **Network failure:** Show error; fall back to expired cache if available (with warning)
- **No matching CFPs:** Print "No open CFPs found for <country>"
- **Malformed entries:** Skip silently, don't crash
- **All expired:** Show "No upcoming CFP deadlines"

## Decisions

- **Single endpoint** (`all-cfps.json`) — simpler than cross-referencing with `all-events.json`
- **String matching for country** — `(France)` in location field; good enough, avoids extra API call
- **1-hour cache TTL** — CFP data doesn't change frequently; avoids hammering the API
- **`uv` for package management** — fast, modern Python tooling
- **`click` for CLI** — mature and well-documented
