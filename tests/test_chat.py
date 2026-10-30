import json
import time

import httpx
import pytest

from cfp_reminders.chat import ChatPostError, build_message, post_message

DAY_MS = 24 * 3600 * 1000
WEBHOOK = (
    "https://chat.googleapis.com/v1/spaces/X/messages?key=SECRETKEY&token=SECRETTOKEN"
)


def _cfp(name: str, in_days: float, location: str = "Tours (France)") -> dict:
    return {
        "link": f"https://cfp.example/{name}",
        "untilDate": int(time.time() * 1000 + in_days * DAY_MS),
        "conf": {"name": name, "location": location},
    }


def test_returns_none_when_window_is_empty():
    assert build_message([_cfp("Far", 45)], country="France", days=30) is None
    assert build_message([], country="France", days=30) is None


def test_keeps_only_cfps_within_window():
    text = build_message(
        [_cfp("Soon", 3), _cfp("Month", 20), _cfp("Far", 31)],
        country="France",
        days=30,
    )
    assert "Soon" in text
    assert "Month" in text
    assert "Far" not in text


def test_groups_by_urgency():
    text = build_message(
        [_cfp("Soon", 3), _cfp("Month", 20)], country="France", days=30
    )
    assert text.index("Cette semaine") < text.index("Soon")
    assert text.index("Soon") < text.index("D'ici 30 jours") < text.index("Month")
    assert "Plus tard" not in text


def test_line_has_link_city_and_date():
    cfp = _cfp("Touraine Tech", 3)
    text = build_message([cfp], country="France", days=30)
    assert "<https://cfp.example/Touraine Tech|Touraine Tech>" in text
    assert "· Tours ·" in text
    assert "clôture le " in text


def test_falls_back_to_conf_hyperlink_then_plain_name():
    with_site = _cfp("SiteOnly", 3)
    with_site.pop("link")
    with_site["conf"]["hyperlink"] = "https://site.example"
    no_link = _cfp("NoLink", 4)
    no_link.pop("link")
    text = build_message([with_site, no_link], country="France", days=30)
    assert "<https://site.example|SiteOnly>" in text
    assert "• NoLink ·" in text


def test_message_has_no_em_or_en_dash():
    text = build_message([_cfp("A", 3), _cfp("B", 20)], country="France", days=30)
    assert "—" not in text
    assert "–" not in text


def test_post_sends_json_text(httpx_mock):
    httpx_mock.add_response(url=WEBHOOK, method="POST", status_code=200)
    post_message(WEBHOOK, "hello")
    request = httpx_mock.get_request()
    assert json.loads(request.read()) == {"text": "hello"}


def test_post_error_hides_webhook_secret(httpx_mock):
    httpx_mock.add_response(url=WEBHOOK, method="POST", status_code=400)
    with pytest.raises(ChatPostError) as exc:
        post_message(WEBHOOK, "hello")
    assert "400" in str(exc.value)
    assert "SECRET" not in str(exc.value)


def test_network_error_hides_webhook_secret(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError(f"cannot reach {WEBHOOK}"))
    with pytest.raises(ChatPostError) as exc:
        post_message(WEBHOOK, "hello")
    assert "SECRET" not in str(exc.value)
    assert exc.value.__cause__ is None
