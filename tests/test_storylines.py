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
