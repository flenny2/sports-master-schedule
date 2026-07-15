"""
Tests for /api/schedule query-param handling (month + legacy week).

These exercise the route through Flask's test client, with ESPN stubbed
out — no network is touched. `get_all_games` is patched on `app.routes`
(not `app.espn`) because routes.py does `from app.espn import
get_all_games`, which binds the function into the routes namespace at
import time; patching the origin module would not affect the name the
view actually calls.

`get_all_userdata` is stubbed for the same reason plus one more: it
reads a JSON file whose path is fixed at import time, and a sibling test
file reloads that module with a temp DATA_DIR. Stubbing keeps these
tests independent of disk state and of test-file ordering.
"""

from datetime import date, timedelta

import pytest

from app import create_app


@pytest.fixture
def client(monkeypatch):
    """Flask test client with ESPN + user data stubbed to empty."""
    import app.routes
    monkeypatch.setattr(app.routes, "get_all_games", lambda start, end: [])
    monkeypatch.setattr(app.routes, "get_all_userdata", lambda: {})
    return create_app().test_client()


# --- month param: rejection cases -------------------------------------
# All three failure modes funnel into the same 400 at routes.py:109 —
# a bad unpack ("2026" has no "-"), a bad int() ("abc"), and the
# explicit range check (month 13 / month 0 / year 1899).

@pytest.mark.parametrize("bad_month", [
    "2026-13",   # month above 12
    "2026-00",   # month below 1
    "abc",       # not numeric, and no "-" to split on
    "2026",      # missing the month half -> unpack ValueError
    "1899-05",   # year below the 1900 floor
    "2026-",     # empty month half -> int("") ValueError
])
def test_invalid_month_returns_400(client, bad_month):
    r = client.get("/api/schedule?month=" + bad_month)
    assert r.status_code == 400
    assert "error" in r.get_json()


# --- month param: happy path ------------------------------------------

def test_valid_month_returns_padded_monday_sunday_range(client):
    """
    April 2026 starts on a Wednesday and ends on a Thursday, so the
    calendar grid pads out to the surrounding Monday and Sunday.
    """
    r = client.get("/api/schedule?month=2026-04")
    assert r.status_code == 200
    body = r.get_json()
    assert body["range"] == {"start": "2026-03-30", "end": "2026-05-03"}
    assert body["games"] == []


def test_month_range_edges_are_monday_and_sunday(client):
    """The padded range must always span whole Mon-Sun weeks."""
    r = client.get("/api/schedule?month=2026-02")
    body = r.get_json()
    start = date.fromisoformat(body["range"]["start"])
    end = date.fromisoformat(body["range"]["end"])
    assert start.weekday() == 0  # Monday
    assert end.weekday() == 6    # Sunday


# --- legacy week param -------------------------------------------------

def _expected_week(offset):
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return monday.isoformat(), (monday + timedelta(days=6)).isoformat()


def test_unknown_week_value_silently_defaults_to_this_week(client):
    """
    CHARACTERIZATION — locks in current behavior, not desired behavior.

    Unlike the month param, an unrecognized ?week= value is not
    rejected: routes.py:116 uses dict.get(week_param, 0), so anything
    outside prev/this/next falls through to offset 0 ("this week").
    If that is ever tightened to a 400, this test should be updated
    deliberately rather than treated as a regression.
    """
    r = client.get("/api/schedule?week=bogus")
    assert r.status_code == 200
    start, end = _expected_week(0)
    assert r.get_json()["range"] == {"start": start, "end": end}


@pytest.mark.parametrize("week_param,offset", [
    ("prev", -1),
    ("this", 0),
    ("next", 1),
])
def test_known_week_values_map_to_offsets(client, week_param, offset):
    r = client.get("/api/schedule?week=" + week_param)
    assert r.status_code == 200
    start, end = _expected_week(offset)
    assert r.get_json()["range"] == {"start": start, "end": end}


def test_no_params_defaults_to_this_week(client):
    r = client.get("/api/schedule")
    assert r.status_code == 200
    start, end = _expected_week(0)
    assert r.get_json()["range"] == {"start": start, "end": end}


def test_month_param_wins_over_week_param(client):
    """month is checked first, so a stray week= alongside it is ignored."""
    r = client.get("/api/schedule?month=2026-04&week=next")
    assert r.status_code == 200
    assert r.get_json()["range"]["start"] == "2026-03-30"
