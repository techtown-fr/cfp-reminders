import json
import time

import httpx
import pytest

from cfp_reminders.chat import (
    MAX_CFPS,
    ChatPostError,
    build_message,
    post_message,
)
from cfp_reminders.display import DAY_SECONDS

WEBHOOK = (
    "https://chat.googleapis.com/v1/spaces/X/messages?key=SECRETKEY&token=SECRETTOKEN"
)


def _cfp(name: str, in_days: float, location: str = "Tours (France)") -> dict:
    return {
        "link": f"https://cfp.example/{name}",
        "untilDate": int((time.time() + in_days * DAY_SECONDS) * 1000),
        "conf": {"name": name, "location": location},
    }


def test_returns_none_when_window_is_empty():
    assert build_message([_cfp("Far", 45)], country="France", days=30) is None
    assert build_message([], country="France", days=30) is None


def test_keeps_window_and_groups_by_urgency():
    text = build_message(
        [_cfp("Soon", 3), _cfp("Month", 20), _cfp("Far", 31)],
        country="France",
        days=30,
    )
    assert "Far" not in text
    assert "Plus tard" not in text
    assert text.index("Cette semaine") < text.index("Soon")
    assert text.index("Soon") < text.index("D'ici 30 jours") < text.index("Month")


def test_line_has_link_city_and_date():
    cfp = _cfp("Touraine Tech", 3)
    text = build_message([cfp], country="France", days=30)
    assert "|Touraine Tech>" in text
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
    assert "\u2014" not in text
    assert "\u2013" not in text


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


def test_neutralises_chat_markup_in_names_and_cities():
    cfp = _cfp("Foo <users/all> | Bar", 3, location="Paris <x> (France)")
    cfp["link"] = "https://cfp.example/foo"
    text = build_message([cfp], country="France", days=30)
    line = text.splitlines()[3]
    assert "<users/all>" not in line
    assert line.count("<") == 1 and line.count("|") == 1 and line.count(">") == 1


def test_drops_unsafe_links():
    bad = [_cfp(n, 3) for n in ("Pipe", "Js", "Ctl")]
    bad[0]["link"] = "https://x.example/a|b"
    bad[1]["link"] = "javascript:alert(1)"
    bad[2]["link"] = "https://x.example/\x07"
    text = build_message(bad, country="France", days=30)
    for name in ("Pipe", "Js", "Ctl"):
        assert f"• {name} ·" in text


def test_encodes_spaces_in_links():
    text = build_message([_cfp("Touraine Tech", 3)], country="France", days=30)
    assert "<https://cfp.example/Touraine%20Tech|Touraine Tech>" in text


def test_caps_the_number_of_cfps():
    cfps = [_cfp(f"Conf{i:02d}", 1 + i * 0.5) for i in range(25)]
    text = build_message(cfps, country="France", days=30)
    assert text.count("\n• ") == MAX_CFPS
    assert "+ 5 autres CFP" in text
    assert "Conf00" in text and "Conf24" not in text


def test_redirect_is_an_error(httpx_mock):
    httpx_mock.add_response(url=WEBHOOK, method="POST", status_code=302)
    with pytest.raises(ChatPostError):
        post_message(WEBHOOK, "hello")


def test_invalid_url_is_wrapped_without_secret():
    with pytest.raises(ChatPostError) as exc:
        post_message("https://chat.example:99999/x?key=SECRETKEY\n", "hello")
    assert "SECRET" not in str(exc.value)
