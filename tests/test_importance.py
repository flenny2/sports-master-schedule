"""Tests for app.importance."""

from app.importance import tag_importance


def _soccer_game(home_id, away_id, league="eng.1", extra=None):
    g = {
        "sport": "soccer",
        "league": league,
        "home_team": {"id": home_id},
        "away_team": {"id": away_id},
        "tier": None,
    }
    if extra:
        g.update(extra)
    return g


def test_man_city_is_must_watch():
    # Man City (382) vs anyone → must_watch
    games = tag_importance([_soccer_game("382", "359")])
    assert games[0]["tier"] == "must_watch"


def test_champions_league_is_notable():
    # Random non-watched clubs in UCL
    games = tag_importance([
        _soccer_game("1", "2", league="uefa.champions")
    ])
    assert games[0]["tier"] == "notable"


def test_real_madrid_notable_in_la_liga():
    # Real Madrid (86) in La Liga → notable tier
    games = tag_importance([
        _soccer_game("86", "83", league="esp.1")
    ])
    # Both 86 and 83 are notable-tier watched teams
    assert games[0]["tier"] == "notable"


def test_top6_matchup_is_notable():
    # Liverpool (364) vs Chelsea (363) → top-6 matchup → notable
    games = tag_importance([_soccer_game("364", "363")])
    assert games[0]["tier"] == "notable"


def test_nfl_primetime_is_must_watch():
    games = tag_importance([{
        "sport": "football",
        "league": "nfl",
        "home_team": {"id": "1"},
        "away_team": {"id": "2"},
        "nfl_slot": "Primetime",
        "tier": None,
    }])
    assert games[0]["tier"] == "must_watch"


def test_nba_is_major_event():
    games = tag_importance([{
        "sport": "basketball",
        "league": "nba",
        "home_team": {"id": "1"},
        "away_team": {"id": "2"},
        "tier": None,
    }])
    assert games[0]["tier"] == "major_event"
