from __future__ import annotations

from datetime import UTC, datetime

import httpx

from cfp_reminders.chat import safe_link
from cfp_reminders.display import format_deadline

SOURCE = "developers.events"
_DAY = "%Y-%m-%d"


class MeetownPostError(Exception):
    """Meetown call failed. The message never contains the URL or the token."""


def _to_entry(cfp: dict) -> dict | None:
    conf = cfp["conf"]
    link = safe_link(cfp.get("link"))
    dates = conf.get("date")
    if not link or not dates or not conf.get("name"):
        return None
    try:
        deadline = format_deadline(cfp["untilDate"], _DAY)
        start = format_deadline(min(dates), _DAY)
        end = format_deadline(max(dates), _DAY)
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    return {
        "id": link,
        "name": conf["name"],
        "cfpUrl": link,
        "cfpDeadline": deadline,
        "eventUrl": safe_link(conf.get("hyperlink")),
        "eventStartDate": start,
        "eventEndDate": end if end != start else None,
        "city": conf["location"].split(" (")[0],
    }


def build_snapshot(cfps: list[dict], *, country: str) -> dict:
    """Full snapshot of the given open CFPs, in the shape of cfp-snapshot.schema.json."""
    entries: list[dict] = []
    seen: set[str] = set()
    for cfp in cfps:
        entry = _to_entry(cfp)
        if entry and entry["id"] not in seen:
            seen.add(entry["id"])
            entries.append(entry)
    return {
        "source": SOURCE,
        "generatedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "country": country,
        "cfps": entries,
    }


def post_snapshot(url: str, token: str, snapshot: dict) -> None:
    url, token = url.strip(), token.strip()
    if not url.startswith("https://"):
        raise MeetownPostError("URL must use https")
    try:
        response = httpx.post(
            url,
            json=snapshot,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except (httpx.HTTPError, httpx.InvalidURL, ValueError) as e:
        # str(e) can embed the URL or the request headers; ValueError: non-ASCII token
        raise MeetownPostError(f"request failed ({type(e).__name__})") from None
    if not response.is_success:
        raise MeetownPostError(f"Meetown answered HTTP {response.status_code}")
