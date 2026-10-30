from __future__ import annotations

import time

import httpx

from cfp_reminders.display import DAY_SECONDS, format_deadline, group_by_urgency

# Keeps the message well under Google Chat's text size limit
MAX_CFPS = 20

SECTIONS = [
    ("this_week", "🔴 Cette semaine"),
    ("this_month", "🟡 D'ici 30 jours"),
    ("later", "🟢 Plus tard"),
]

# Chat markup is <url|text>: neutralise it in third-party names and cities
_MARKUP = str.maketrans({"<": "‹", ">": "›", "|": "¦"})


class ChatPostError(Exception):
    """Webhook call failed. The message never contains the webhook URL."""


def _safe_link(link: str | None) -> str | None:
    if not link:
        return None
    link = link.strip().replace(" ", "%20")
    if not link.startswith(("https://", "http://")):
        return None
    if any(c in "<>|" or not c.isprintable() for c in link):
        return None
    return link


def _format_line(cfp: dict) -> str:
    conf = cfp["conf"]
    name = conf["name"].translate(_MARKUP)
    link = _safe_link(cfp.get("link") or conf.get("hyperlink"))
    title = f"<{link}|{name}>" if link else name
    city = conf.get("location", "").split(" (")[0].translate(_MARKUP)
    deadline = format_deadline(cfp["untilDate"], "%d/%m")
    return f"• {title} · {city} · clôture le {deadline}"


def build_message(cfps: list[dict], *, country: str, days: int) -> str | None:
    """Google Chat text for CFPs closing within `days`, or None if there are none."""
    limit_ms = (time.time() + days * DAY_SECONDS) * 1000
    upcoming = sorted(
        (c for c in cfps if c["untilDate"] <= limit_ms), key=lambda c: c["untilDate"]
    )
    if not upcoming:
        return None

    shown, hidden = upcoming[:MAX_CFPS], len(upcoming) - MAX_CFPS
    groups = group_by_urgency(shown)
    lines = [f"*📣 CFP ouverts ({country}), clôture dans les {days} prochains jours*"]
    for key, label in SECTIONS:
        if groups[key]:
            lines += ["", f"*{label}*"]
            lines += [_format_line(c) for c in groups[key]]
    if hidden > 0:
        lines += ["", f"_+ {hidden} autres CFP sur developers.events_"]
    lines += ["", "_Source : developers.events_"]
    return "\n".join(lines)


def post_message(webhook_url: str, text: str) -> None:
    try:
        response = httpx.post(webhook_url, json={"text": text}, timeout=10)
    except (httpx.HTTPError, httpx.InvalidURL) as e:
        # str(e) can embed the URL, which carries the webhook key and token
        raise ChatPostError(f"request failed ({type(e).__name__})") from None
    if not response.is_success:
        raise ChatPostError(f"webhook answered HTTP {response.status_code}")
