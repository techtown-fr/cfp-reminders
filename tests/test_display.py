from datetime import UTC, datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock

from rich.console import Console

from cfp_reminders.display import group_by_urgency, render

NOW = datetime.now(UTC)


def _make_cfp(days_until_deadline: int, name: str = "Conf") -> dict:
    deadline = NOW + timedelta(days=days_until_deadline)
    return {
        "link": "https://example.com/cfp",
        "until": "Some-Date",
        "untilDate": int(deadline.timestamp() * 1000),
        "conf": {
            "name": name,
            "date": [int(deadline.timestamp() * 1000)],
            "hyperlink": "https://example.com",
            "status": "open",
            "location": "Paris (France)",
        },
    }


def test_group_this_week():
    cfps = [_make_cfp(3, "Soon Conf")]
    groups = group_by_urgency(cfps)
    assert len(groups["this_week"]) == 1
    assert groups["this_week"][0]["conf"]["name"] == "Soon Conf"


def test_group_this_month():
    cfps = [_make_cfp(15, "Month Conf")]
    groups = group_by_urgency(cfps)
    assert len(groups["this_month"]) == 1


def test_group_later():
    cfps = [_make_cfp(60, "Later Conf")]
    groups = group_by_urgency(cfps)
    assert len(groups["later"]) == 1


def test_group_multiple_buckets():
    cfps = [
        _make_cfp(2, "Week"),
        _make_cfp(20, "Month"),
        _make_cfp(90, "Later"),
    ]
    groups = group_by_urgency(cfps)
    assert len(groups["this_week"]) == 1
    assert len(groups["this_month"]) == 1
    assert len(groups["later"]) == 1


def test_group_empty():
    groups = group_by_urgency([])
    assert groups["this_week"] == []
    assert groups["this_month"] == []
    assert groups["later"] == []


def test_render_outputs_tables():
    cfps = [
        _make_cfp(3, "Soon Conf"),
        _make_cfp(15, "Month Conf"),
    ]
    buf = StringIO()
    console = Console(file=buf, force_terminal=True)
    render(cfps, console=console)
    output = buf.getvalue()
    assert "Soon Conf" in output
    assert "Month Conf" in output


def test_render_empty_shows_message():
    console = MagicMock()
    render([], console=console)
    console.print.assert_called()
    calls_str = " ".join(str(c) for c in console.print.call_args_list)
    assert "No upcoming" in calls_str
