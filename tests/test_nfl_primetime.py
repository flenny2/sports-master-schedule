"""
Regression tests for NFL primetime inclusion — the Netflix / Christmas-Friday case.

Background: `fetch_nfl_games` includes a game when it is primetime by weekday+hour
OR when it airs on a network in `config.NFL_PRIMETIME_NETWORKS`. The weekday
primetime branches cover Thu/Sun/Mon/Sat only — NOT Friday. Christmas 2026 falls
on a Friday and the NFL Christmas games stream on Netflix, so BOTH inclusion paths
fail unless "Netflix" is in the primetime-network set. These tests pin that:

- The Netflix Friday game must be INCLUDED (drives the config fix).
- A CBS Friday game (network NOT in the primetime set) must be EXCLUDED — proving
  the fix does not blanket-include every Friday-evening NFL game.

Network is avoided entirely by monkeypatching `_parallel_fetch_days`.
"""

from datetime import date, datetime

import pytz

from app import espn
import config


# 2026-12-26T01:30Z maps to Fri Dec 25 2026 17:30 US/Pacific (PST, UTC-8).
CHRISTMAS_UTC = "2026-12-26T01:30Z"


def _make_game(broadcasts):
    """Minimal game dict with only the keys fetch_nfl_games reads."""
    return {"date": CHRISTMAS_UTC, "broadcasts": broadcasts}


def test_christmas_utc_maps_to_friday_evening_pacific():
    """Self-check: the fixture date really is a Friday (weekday 4) in Pacific."""
    tz = pytz.timezone(config.TIMEZONE)
    game_dt = datetime.fromisoformat(CHRISTMAS_UTC.replace("Z", "+00:00"))
    game_local = game_dt.astimezone(tz)
    assert game_local.weekday() == 4  # Friday
    assert game_local.hour >= 17      # evening — the weekday branch would fire
                                      # for Thu/Sun/Mon/Sat, but Friday is absent


def test_netflix_friday_game_is_included(monkeypatch):
    """Netflix Christmas (Friday) game must survive as a Primetime slot."""
    game = _make_game(["Netflix"])
    monkeypatch.setattr(
        espn, "_parallel_fetch_days", lambda *a, **kw: [game])

    out = espn.fetch_nfl_games(date(2026, 12, 25), date(2026, 12, 26))

    assert len(out) == 1
    assert out[0]["date"] == CHRISTMAS_UTC
    assert out[0]["nfl_slot"] == "Primetime"


def test_non_primetime_network_friday_game_is_excluded(monkeypatch):
    """Control: a CBS Friday game is NOT primetime and must be dropped.

    CBS is not in NFL_PRIMETIME_NETWORKS and Friday has no weekday primetime
    branch, so neither inclusion path fires — the fix stays specific to
    primetime networks rather than every Friday-evening game.
    """
    game = _make_game(["CBS"])
    monkeypatch.setattr(
        espn, "_parallel_fetch_days", lambda *a, **kw: [game])

    out = espn.fetch_nfl_games(date(2026, 12, 25), date(2026, 12, 26))

    assert out == []
