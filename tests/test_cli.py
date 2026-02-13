from unittest.mock import MagicMock, patch

import httpx
from click.testing import CliRunner

from cfp_reminders.cli import main

SAMPLE_CFPS = [
    {
        "link": "https://example.com/cfp1",
        "until": "March-15-2026",
        "untilDate": 1773590400000,  # far future
        "conf": {
            "name": "DevFest Paris",
            "date": [1773590400000],
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
        "untilDate": 1773590400000,
        "conf": {
            "name": "JSConf Berlin",
            "date": [1773590400000],
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
