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
