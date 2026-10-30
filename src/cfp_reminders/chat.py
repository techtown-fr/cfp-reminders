from __future__ import annotations

import time

import httpx

from cfp_reminders.display import DAY_SECONDS, format_deadline, group_by_urgency

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
    deadline = format_deadline(cfp["untilDate"], "%d/%m")
    return f"• {title} · {city} · clôture le {deadline}"


def build_message(cfps: list[dict], *, country: str, days: int) -> str | None:
    """Google Chat text for CFPs closing within `days`, or None if there are none."""
    limit_ms = (time.time() + days * DAY_SECONDS) * 1000
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
