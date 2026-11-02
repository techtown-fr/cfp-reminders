import json
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest
from click.testing import CliRunner

from cfp_reminders.chat import ChatPostError
from cfp_reminders.cli import main
from cfp_reminders.display import DAY_SECONDS
from cfp_reminders.meetown import MeetownPostError

FAR_FUTURE_MS = int((time.time() + 365 * DAY_SECONDS) * 1000)

SAMPLE_CFPS = [
    {
        "link": "https://example.com/cfp1",
        "until": "March-15-2026",
        "untilDate": FAR_FUTURE_MS,
        "conf": {
            "name": "DevFest Paris",
            "date": [FAR_FUTURE_MS],
            "hyperlink": "https://devfest.paris",
            "status": "open",
            "location": "Paris (France)",
        },
    },
]

SAMPLE_CFPS_GERMANY = [
    {
        "link": "https://example.com/cfp2",
        "until": "April-01-2026",
        "untilDate": FAR_FUTURE_MS,
        "conf": {
            "name": "JSConf Berlin",
            "date": [FAR_FUTURE_MS],
            "hyperlink": "https://jsconf.berlin",
            "status": "open",
            "location": "Berlin (Germany)",
        },
    },
]


def _mock_cache(read_return=None, stale_return=None):
    """Create a mock Cache whose read() returns the given values."""
    cache = MagicMock()

    def _read(*, allow_stale=False):
        if allow_stale:
            return stale_return
        return read_return

    cache.read.side_effect = _read
    return cache


@patch("cfp_reminders.cli.Cache")
@patch("cfp_reminders.cli.fetch_cfps", return_value=SAMPLE_CFPS)
def test_default_shows_france(mock_fetch, mock_cache_cls):
    mock_cache_cls.return_value = _mock_cache()
    runner = CliRunner()
    result = runner.invoke(main)
    assert result.exit_code == 0
    assert "DevFest Paris" in result.output


@patch("cfp_reminders.cli.Cache")
@patch("cfp_reminders.cli.fetch_cfps", side_effect=httpx.RequestError("Network error"))
def test_network_error_shows_message(mock_fetch, mock_cache_cls):
    mock_cache_cls.return_value = _mock_cache()
    runner = CliRunner()
    result = runner.invoke(main)
    assert result.exit_code == 0
    assert "error" in result.output.lower() or "Error" in result.output


@patch("cfp_reminders.cli.Cache")
@patch("cfp_reminders.cli.fetch_cfps", return_value=[])
def test_no_cfps_shows_message(mock_fetch, mock_cache_cls):
    mock_cache_cls.return_value = _mock_cache()
    runner = CliRunner()
    result = runner.invoke(main)
    assert result.exit_code == 0
    assert "No" in result.output


@patch("cfp_reminders.cli.Cache")
@patch("cfp_reminders.cli.fetch_cfps", return_value=SAMPLE_CFPS)
def test_refresh_bypasses_cache(mock_fetch, mock_cache_cls):
    mock_cache_cls.return_value = _mock_cache(read_return=[{"cached": True}])
    runner = CliRunner()
    result = runner.invoke(main, ["--refresh"])
    assert result.exit_code == 0
    assert "DevFest Paris" in result.output
    mock_cache_cls.return_value.read.assert_not_called()


@patch("cfp_reminders.cli.Cache")
@patch("cfp_reminders.cli.fetch_cfps", return_value=SAMPLE_CFPS_GERMANY)
def test_country_filter(mock_fetch, mock_cache_cls):
    mock_cache_cls.return_value = _mock_cache()
    runner = CliRunner()
    result = runner.invoke(main, ["--country", "Germany"])
    assert result.exit_code == 0
    assert "JSConf Berlin" in result.output
    assert "DevFest Paris" not in result.output


@patch("cfp_reminders.cli.Cache")
@patch("cfp_reminders.cli.fetch_cfps", side_effect=httpx.RequestError("Network error"))
def test_network_error_fallback_to_stale_cache(mock_fetch, mock_cache_cls):
    mock_cache_cls.return_value = _mock_cache(
        read_return=None, stale_return=SAMPLE_CFPS
    )
    runner = CliRunner()
    result = runner.invoke(main)
    assert result.exit_code == 0
    assert "Warning" in result.output
    assert "DevFest Paris" in result.output


SOON_CFPS = [
    {
        "link": "https://example.com/soon",
        "untilDate": int((time.time() + 3 * DAY_SECONDS) * 1000),
        "conf": {"name": "Touraine Tech", "location": "Tours (France)"},
    },
]
WEBHOOK = "https://chat.example/hook?key=SECRETKEY&token=SECRETTOKEN"


@pytest.fixture
def chat_env():
    """Patch Cache, fetch_cfps and post_message; tests set fetch's return."""
    with (
        patch("cfp_reminders.cli.Cache") as cache_cls,
        patch("cfp_reminders.cli.fetch_cfps", return_value=SOON_CFPS) as fetch,
        patch("cfp_reminders.cli.post_message") as post,
    ):
        cache_cls.return_value = _mock_cache()
        yield fetch, post


def test_chat_dry_run_prints_message_without_posting(chat_env):
    _, post = chat_env
    result = CliRunner().invoke(main, ["--chat", "--dry-run"])
    assert result.exit_code == 0
    assert "<https://example.com/soon|Touraine Tech>" in result.output
    post.assert_not_called()


def test_chat_posts_to_webhook_from_env(chat_env):
    _, post = chat_env
    result = CliRunner().invoke(
        main, ["--chat"], env={"GOOGLE_CHAT_WEBHOOK_URL": WEBHOOK}
    )
    assert result.exit_code == 0
    url, text = post.call_args.args
    assert url == WEBHOOK
    assert "Touraine Tech" in text


def test_chat_without_webhook_is_a_usage_error():
    result = CliRunner().invoke(main, ["--chat"], env={"GOOGLE_CHAT_WEBHOOK_URL": ""})
    assert result.exit_code == 2
    assert "GOOGLE_CHAT_WEBHOOK_URL" in result.output


def test_chat_post_failure_exits_1_without_leaking_url(chat_env):
    _, post = chat_env
    post.side_effect = ChatPostError("webhook answered HTTP 400")
    result = CliRunner().invoke(main, ["--chat", "--webhook-url", WEBHOOK])
    assert result.exit_code == 1
    assert "HTTP 400" in result.output
    assert "SECRET" not in result.output


def test_chat_empty_window_posts_nothing(chat_env):
    fetch, post = chat_env
    fetch.return_value = SAMPLE_CFPS
    result = CliRunner().invoke(main, ["--chat", "--webhook-url", WEBHOOK])
    assert result.exit_code == 0
    assert "nothing posted" in result.output
    post.assert_not_called()


def test_chat_fetch_failure_exits_1(chat_env):
    fetch, _ = chat_env
    fetch.side_effect = httpx.RequestError("down")
    result = CliRunner().invoke(main, ["--chat", "--dry-run"])
    assert result.exit_code == 1


def test_env_webhook_without_chat_flag_keeps_terminal_output(chat_env):
    fetch, post = chat_env
    fetch.return_value = SAMPLE_CFPS
    result = CliRunner().invoke(main, env={"GOOGLE_CHAT_WEBHOOK_URL": WEBHOOK})
    assert result.exit_code == 0
    assert "DevFest Paris" in result.output
    post.assert_not_called()


def test_chat_ignores_cache_and_fails_on_fetch_error(chat_env):
    fetch, _ = chat_env
    fetch.side_effect = httpx.RequestError("down")
    with patch("cfp_reminders.cli.Cache") as cache_cls:
        cache_cls.return_value = _mock_cache(
            read_return=SOON_CFPS, stale_return=SOON_CFPS
        )
        result = CliRunner().invoke(main, ["--chat", "--dry-run"])
    assert result.exit_code == 1
    cache_cls.return_value.read.assert_not_called()


def test_days_must_be_positive():
    result = CliRunner().invoke(main, ["--chat", "--dry-run", "--days", "0"])
    assert result.exit_code == 2


MEETOWN_ENV = {
    "MEETOWN_WEBHOOK_URL": "https://meetown.example/api?k=SECRETURL",
    "MEETOWN_TOKEN": "SECRETTOKEN",
}
OPEN_CFPS = [
    {**SAMPLE_CFPS[0], "link": "https://example.com/cfp1"},
    SAMPLE_CFPS_GERMANY[0],
]


@pytest.fixture
def meetown_env():
    """Patch Cache, fetch_cfps and post_snapshot; tests set fetch's return."""
    with (
        patch("cfp_reminders.cli.Cache") as cache_cls,
        patch("cfp_reminders.cli.fetch_cfps", return_value=OPEN_CFPS) as fetch,
        patch("cfp_reminders.cli.post_snapshot") as post,
    ):
        cache_cls.return_value = _mock_cache(read_return=[], stale_return=[])
        yield fetch, post, cache_cls


def test_meetown_dry_run_prints_country_snapshot(meetown_env):
    _, post, cache_cls = meetown_env
    result = CliRunner().invoke(main, ["--meetown", "--dry-run"], env={})
    assert result.exit_code == 0
    snapshot = json.loads(result.output)
    assert snapshot["country"] == "France"
    assert [c["name"] for c in snapshot["cfps"]] == ["DevFest Paris"]
    post.assert_not_called()
    cache_cls.return_value.read.assert_not_called()


def test_meetown_posts_with_url_and_token_from_env(meetown_env):
    _, post, _ = meetown_env
    result = CliRunner().invoke(main, ["--meetown"], env=MEETOWN_ENV)
    assert result.exit_code == 0
    url, token, snapshot = post.call_args.args
    assert (url, token) == (
        MEETOWN_ENV["MEETOWN_WEBHOOK_URL"],
        MEETOWN_ENV["MEETOWN_TOKEN"],
    )
    assert len(snapshot["cfps"]) == 1
    assert "1 CFP pushed" in result.output


@pytest.mark.parametrize("missing", ["MEETOWN_WEBHOOK_URL", "MEETOWN_TOKEN"])
def test_meetown_without_url_or_token_is_a_usage_error(missing):
    env = {**MEETOWN_ENV, missing: ""}
    result = CliRunner().invoke(main, ["--meetown"], env=env)
    assert result.exit_code == 2
    assert "MEETOWN_TOKEN" in result.output


def test_meetown_and_chat_are_exclusive():
    result = CliRunner().invoke(main, ["--meetown", "--chat", "--dry-run"])
    assert result.exit_code == 2


def test_meetown_post_failure_exits_1_without_secrets(meetown_env):
    _, post, _ = meetown_env
    post.side_effect = MeetownPostError("Meetown answered HTTP 401")
    result = CliRunner().invoke(main, ["--meetown"], env=MEETOWN_ENV)
    assert result.exit_code == 1
    assert "HTTP 401" in result.output
    assert "SECRET" not in result.output


def test_meetown_fetch_failure_exits_1(meetown_env):
    fetch, post, _ = meetown_env
    fetch.side_effect = httpx.RequestError("down")
    result = CliRunner().invoke(main, ["--meetown"], env=MEETOWN_ENV)
    assert result.exit_code == 1
    post.assert_not_called()


def test_meetown_refuses_to_push_an_empty_snapshot(meetown_env):
    fetch, post, _ = meetown_env
    fetch.return_value = []
    result = CliRunner().invoke(main, ["--meetown"], env=MEETOWN_ENV)
    assert result.exit_code == 1
    assert "unchanged" in result.output
    post.assert_not_called()


def test_meetown_reports_skipped_entries(meetown_env):
    fetch, _, _ = meetown_env
    no_date = {**OPEN_CFPS[0], "conf": {**OPEN_CFPS[0]["conf"], "date": []}}
    fetch.return_value = [no_date]
    result = CliRunner().invoke(main, ["--meetown", "--dry-run"], env={})
    assert result.exit_code == 0
    assert "1 CFP skipped" in result.stderr
