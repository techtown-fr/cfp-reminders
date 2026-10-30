from __future__ import annotations

import time
from datetime import UTC, datetime

import httpx

from cfp_reminders.display import group_by_urgency

DAY_MS = 24 * 3600 * 1000

SECTIONS = [
    ("this_week", "🔴 Cette semaine"),
    ("this_month", "🟡 D'ici 30 jours"),
    ("later", "🟢 Plus tard"),
]


class ChatPostError(Exception):
    """Webhook call failed. The message never contains the webhook URL."""


def _format_line(cfp: dict) -> str:
    conf = cfp["conf"]
    name = conf["name"]
    link = cfp.get("link") or conf.get("hyperlink")
    title = f"<{link}|{name}>" if link else name
    city = conf.get("location", "").split(" (")[0]
    deadline = datetime.fromtimestamp(cfp["untilDate"] / 1000, tz=UTC)
    return f"• {title} · {city} · clôture le {deadline:%d/%m}"


def build_message(cfps: list[dict], *, country: str, days: int) -> str | None:
    """Google Chat text for CFPs closing within `days`, or None if there are none."""
    limit_ms = time.time() * 1000 + days * DAY_MS
    upcoming = [c for c in cfps if c["untilDate"] <= limit_ms]
    if not upcoming:
        return None

    groups = group_by_urgency(upcoming)
    lines = [f"*📣 CFP ouverts ({country}), clôture dans les {days} prochains jours*"]
    for key, label in SECTIONS:
        if groups[key]:
            lines += ["", f"*{label}*"]
            lines += [_format_line(c) for c in groups[key]]
    lines += ["", "_Source : developers.events_"]
    return "\n".join(lines)


def post_message(webhook_url: str, text: str) -> None:
    try:
        response = httpx.post(webhook_url, json={"text": text}, timeout=10)
    except httpx.HTTPError as e:
        # str(e) can embed the URL, which carries the webhook key and token
        raise ChatPostError(f"network error ({type(e).__name__})") from None
    if response.is_error:
        raise ChatPostError(f"webhook answered HTTP {response.status_code}")
