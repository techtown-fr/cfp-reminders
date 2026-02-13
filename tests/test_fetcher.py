from datetime import UTC, datetime, timedelta

from cfp_reminders.fetcher import fetch_cfps, filter_cfps

# Timestamps in milliseconds
FUTURE_TS = int((datetime.now(UTC) + timedelta(days=30)).timestamp() * 1000)
PAST_TS = int((datetime.now(UTC) - timedelta(days=1)).timestamp() * 1000)

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
