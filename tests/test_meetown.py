import json
import time
from pathlib import Path

import httpx
import jsonschema
import pytest

from cfp_reminders.display import DAY_SECONDS
from cfp_reminders.meetown import MeetownPostError, build_snapshot, post_snapshot

SCHEMA = json.loads(
    (Path(__file__).parent.parent / "schemas" / "cfp-snapshot.schema.json").read_text()
)
URL = "https://meetown.example/api/cfps?trace=SECRETURL"
TOKEN = "SECRETTOKEN"


def _ms(in_days: float) -> int:
    return int((time.time() + in_days * DAY_SECONDS) * 1000)


def _cfp(name: str, *, event_days: tuple[float, ...] = (40,)) -> dict:
    return {
        "link": f"https://cfp.example/{name}",
        "untilDate": _ms(10),
        "conf": {
            "name": name,
            "date": [_ms(d) for d in event_days],
            "hyperlink": f"https://{name.lower()}.example",
            "location": "Nantes (France)",
        },
    }


def _validate(snapshot: dict) -> None:
    jsonschema.Draft202012Validator(
        SCHEMA, format_checker=jsonschema.FormatChecker()
    ).validate(snapshot)


def test_snapshot_matches_schema():
    multi_day = _cfp("DevFest", event_days=(40, 41, 42))
    no_site = _cfp("NoSite")
    no_site["conf"].pop("hyperlink")
    snapshot = build_snapshot([multi_day, no_site], country="France")
    _validate(snapshot)
    first, second = snapshot["cfps"]
    assert first["id"] == first["cfpUrl"] == "https://cfp.example/DevFest"
    assert first["city"] == "Nantes"
    assert first["eventEndDate"] > first["eventStartDate"]
    assert second["eventUrl"] is None


def test_one_day_event_has_null_end_date():
    same_day = _cfp("SameDay", event_days=(40, 40))
    snapshot = build_snapshot([_cfp("OneDay"), same_day], country="France")
    assert [c["eventEndDate"] for c in snapshot["cfps"]] == [None, None]


def test_skips_entries_without_event_date_or_safe_link():
    no_date = _cfp("NoDate")
    no_date["conf"]["date"] = []
    bad_date = _cfp("BadDate")
    bad_date["conf"]["date"] = ["soon"]
    no_link = _cfp("NoLink")
    no_link.pop("link")
    ftp = _cfp("Ftp")
    ftp["link"] = "ftp://cfp.example/x"
    pipe = _cfp("Pipe")
    pipe["link"] = "https://cfp.example/a|b"
    cfps = [no_date, bad_date, no_link, ftp, pipe, _cfp("Kept")]
    snapshot = build_snapshot(cfps, country="France")
    _validate(snapshot)
    assert [c["name"] for c in snapshot["cfps"]] == ["Kept"]


def test_deduplicates_on_cfp_url():
    snapshot = build_snapshot([_cfp("Twice"), _cfp("Twice")], country="France")
    assert len(snapshot["cfps"]) == 1


def test_empty_snapshot_is_still_valid():
    snapshot = build_snapshot([], country="France")
    _validate(snapshot)
    assert snapshot["cfps"] == []


def test_post_sends_bearer_token_and_json(httpx_mock):
    httpx_mock.add_response(
        url=URL,
        method="POST",
        match_headers={"Authorization": f"Bearer {TOKEN}"},
        status_code=204,
    )
    snapshot = build_snapshot([_cfp("A")], country="France")
    post_snapshot(URL, TOKEN, snapshot)
    assert json.loads(httpx_mock.get_request().read()) == snapshot


@pytest.mark.parametrize("status", [302, 401, 500])
def test_non_2xx_is_an_error_without_secrets(httpx_mock, status):
    httpx_mock.add_response(url=URL, method="POST", status_code=status)
    with pytest.raises(MeetownPostError) as exc:
        post_snapshot(URL, TOKEN, {})
    assert str(status) in str(exc.value)
    assert "SECRET" not in str(exc.value)


def test_network_error_hides_url_and_token(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError(f"cannot reach {URL} with {TOKEN}"))
    with pytest.raises(MeetownPostError) as exc:
        post_snapshot(URL, TOKEN, {})
    assert "SECRET" not in str(exc.value)
    assert exc.value.__cause__ is None


def test_refuses_plain_http_before_sending_the_token():
    with pytest.raises(MeetownPostError, match="https"):
        post_snapshot("http://meetown.example/api", TOKEN, {})


def test_bad_until_date_skips_the_entry():
    broken = _cfp("Broken")
    broken["untilDate"] = 10**20
    snapshot = build_snapshot([broken, _cfp("Kept")], country="France")
    assert [c["name"] for c in snapshot["cfps"]] == ["Kept"]


def test_strips_whitespace_from_url_and_token(httpx_mock):
    httpx_mock.add_response(
        url=URL, method="POST", match_headers={"Authorization": f"Bearer {TOKEN}"}
    )
    post_snapshot(f"  {URL}\n", f"{TOKEN}\n", {})


def test_non_ascii_token_is_wrapped_without_secret():
    with pytest.raises(MeetownPostError) as exc:
        post_snapshot(URL, "SECRETtoké", {})
    assert "SECRET" not in str(exc.value)
