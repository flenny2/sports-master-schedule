"""Tests for app.storylines."""

import pytest

import config
from app.storylines import tag_storylines, get_active_storylines


def _game(
    game_id="g1",
    home_id="359",
    away_id="349",
    league="eng.1",
    date_str="2026-05-01T19:00Z",
):
    return {
        "id": game_id,
        "sport": "soccer",
        "league": league,
        "date": date_str,
        "home_team": {"id": home_id},
        "away_team": {"id": away_id},
    }


@pytest.fixture
def one_storyline(monkeypatch):
    """Replace STORYLINES with a single PL title race storyline."""
    monkeypatch.setattr(config, "STORYLINES", [
        {
            "id": "pl_title",
            "label": "PL Title Race",
            "active": True,
            "team_ids": ["359", "382"],
            "leagues": ["eng.1"],
            "start_date": "2026-04-01",
            "end_date": "2026-05-31",
        },
    ])


def test_matches_when_team_plays(one_storyline):
    games = tag_storylines([_game(home_id="359")])  # Arsenal home
    assert len(games[0]["storylines"]) == 1
    assert games[0]["storylines"][0]["id"] == "pl_title"
    assert games[0]["storylines"][0]["label"] == "PL Title Race"


def test_does_not_match_unrelated_teams(one_storyline):
    # Neither team is Arsenal/Man City
    games = tag_storylines([_game(home_id="1", away_id="2")])
    assert games[0]["storylines"] == []


def test_team_on_team_still_tagged_once(one_storyline):
    # Arsenal vs Man City — both listed. Must appear exactly once.
    games = tag_storylines([_game(home_id="382", away_id="359")])
    assert len(games[0]["storylines"]) == 1


def test_league_filter_excludes_other_competitions(one_storyline):
    # Arsenal in FA Cup — storyline restricted to eng.1
    games = tag_storylines([_game(home_id="359", league="eng.fa")])
    assert games[0]["storylines"] == []


def test_date_window_excludes_outside_games(one_storyline):
    # Before window
    early = tag_storylines([_game(date_str="2026-01-10T19:00Z")])
    assert early[0]["storylines"] == []
    # After window
    late = tag_storylines([_game(date_str="2026-08-10T19:00Z")])
    assert late[0]["storylines"] == []


def test_no_date_window_matches_any_date(monkeypatch):
    """A storyline with neither start_date nor end_date tags any date."""
    monkeypatch.setattr(config, "STORYLINES", [
        {"id": "ucl_run", "label": "UCL Run",
         "active": True, "team_ids": ["359"]},
    ])
    far_past = tag_storylines([_game(date_str="2000-01-01T19:00Z")])
    far_future = tag_storylines([_game(date_str="2099-12-31T19:00Z")])
    assert far_past[0]["storylines"][0]["id"] == "ucl_run"
    assert far_future[0]["storylines"][0]["id"] == "ucl_run"


def test_only_start_date_filters_earlier_games(monkeypatch):
    """Games before start_date are excluded; after is unbounded."""
    monkeypatch.setattr(config, "STORYLINES", [
        {"id": "ko", "label": "KO Run", "active": True,
         "team_ids": ["359"], "start_date": "2026-03-01"},
    ])
    before = tag_storylines([_game(date_str="2026-02-15T19:00Z")])
    after = tag_storylines([_game(date_str="2030-06-01T19:00Z")])
    assert before[0]["storylines"] == []
    assert after[0]["storylines"][0]["id"] == "ko"


def test_only_end_date_filters_later_games(monkeypatch):
    """Games after end_date are excluded; before is unbounded."""
    monkeypatch.setattr(config, "STORYLINES", [
        {"id": "season", "label": "Season", "active": True,
         "team_ids": ["359"], "end_date": "2026-05-31"},
    ])
    before = tag_storylines([_game(date_str="2020-01-01T19:00Z")])
    after = tag_storylines([_game(date_str="2026-06-01T19:00Z")])
    assert before[0]["storylines"][0]["id"] == "season"
    assert after[0]["storylines"] == []


def test_inactive_storyline_is_skipped(monkeypatch):
    monkeypatch.setattr(config, "STORYLINES", [
        {
            "id": "off", "label": "Off", "active": False,
            "team_ids": ["359"],
        },
    ])
    games = tag_storylines([_game(home_id="359")])
    assert games[0]["storylines"] == []


def test_multiple_storylines_all_tagged(monkeypatch):
    monkeypatch.setattr(config, "STORYLINES", [
        {"id": "a", "label": "A", "active": True, "team_ids": ["359"]},
        {"id": "b", "label": "B", "active": True, "team_ids": ["359"]},
    ])
    games = tag_storylines([_game(home_id="359")])
    ids = [s["id"] for s in games[0]["storylines"]]
    assert ids == ["a", "b"]


def test_missing_storylines_config_is_safe(monkeypatch):
    """If config has no STORYLINES, every game gets an empty list."""
    monkeypatch.setattr(config, "STORYLINES", [])
    games = tag_storylines([_game(home_id="359")])
    assert games[0]["storylines"] == []


def test_get_active_storylines_filters_inactive(monkeypatch):
    monkeypatch.setattr(config, "STORYLINES", [
        {"id": "on",  "label": "On",  "active": True,  "team_ids": ["1"]},
        {"id": "off", "label": "Off", "active": False, "team_ids": ["1"]},
    ])
    out = get_active_storylines()
    assert [s["id"] for s in out] == ["on"]


def test_get_active_storylines_shape(monkeypatch):
    """Response shape should expose id, label, description."""
    monkeypatch.setattr(config, "STORYLINES", [
        {
            "id": "pl", "label": "PL Title Race",
            "description": "Arsenal vs Man City",
            "active": True, "team_ids": ["359", "382"],
        },
    ])
    out = get_active_storylines()
    assert out == [{
        "id": "pl",
        "label": "PL Title Race",
        "description": "Arsenal vs Man City",
    }]


def test_get_active_storylines_hides_expired_chip(monkeypatch):
    """An active storyline whose end_date is in the past must be hidden.

    Reproduces the dead-chip bug: the tagger stops matching games past
    end_date, so serving the chip filters the calendar to zero games.
    Far-past date keeps this test from going stale over time.
    """
    monkeypatch.setattr(config, "STORYLINES", [
        {"id": "expired", "label": "Expired", "active": True,
         "team_ids": ["359"], "end_date": "2020-01-01"},
    ])
    assert get_active_storylines() == []


def test_get_active_storylines_includes_future_end_date(monkeypatch):
    """A storyline whose window is still open (far-future end) is served."""
    monkeypatch.setattr(config, "STORYLINES", [
        {"id": "live", "label": "Live", "active": True,
         "team_ids": ["359"], "end_date": "2099-12-31"},
    ])
    assert [s["id"] for s in get_active_storylines()] == ["live"]


def test_get_active_storylines_hides_not_yet_started(monkeypatch):
    """A storyline whose start_date is far in the future is not yet served."""
    monkeypatch.setattr(config, "STORYLINES", [
        {"id": "upcoming", "label": "Upcoming", "active": True,
         "team_ids": ["359"], "start_date": "2099-01-01"},
    ])
    assert get_active_storylines() == []


def test_get_active_storylines_no_window_is_unbounded(monkeypatch):
    """A storyline with no date window is always served while active."""
    monkeypatch.setattr(config, "STORYLINES", [
        {"id": "always", "label": "Always", "active": True,
         "team_ids": ["359"]},
    ])
    assert [s["id"] for s in get_active_storylines()] == ["always"]


# ── The SHIPPED config, not a fixture ─────────────────────────────
# Everything above tests the mechanism against stand-in storylines. These
# two test the entry that actually ships, because the mechanism was never
# the problem: the 25-26 entry sat expired from 31 May to 27 July and the
# Calendar quietly had no storyline filter for two months.

def test_shipped_storylines_are_season_scoped():
    """Every shipped entry needs BOTH ends of its window.

    `end_date` is what lets ./tools/rollover-check notice the entry has gone
    stale — without it a dead storyline is indistinguishable from a live one.
    `start_date` is what stops it reaching backwards: the 25-26 entry left it
    off on the reasoning that earlier fixtures in the same season were part of
    the story, which was true when 25-26 was the only season the app had ever
    seen and false the moment a second one existed.
    """
    for s in config.STORYLINES:
        assert s.get("start_date"), f"{s['id']} has no start_date"
        assert s.get("end_date"), f"{s['id']} has no end_date"


def test_shipped_storyline_does_not_reach_into_a_previous_season():
    """The concrete regression: a title-race chip on last season's games.

    Arsenal played Man City in the 2025-26 season. With the shipped config,
    a game from that season must carry no storyline at all — otherwise
    scrolling the Calendar back would show 26-27 title-race chips on matches
    that decided a different title.
    """
    old = _game(game_id="last-season", home_id="359", away_id="382",
                date_str="2026-03-15T19:00Z")
    assert tag_storylines([old])[0]["storylines"] == []
