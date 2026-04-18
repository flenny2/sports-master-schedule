"""Tests for app.playoff."""

from app.playoff import tag_playoff


def _g(**kwargs):
    base = {
        "sport": "soccer",
        "league": "eng.1",
        "season_type": 2,
        "notes": "",
    }
    base.update(kwargs)
    return base


def test_nba_game_always_playoff():
    games = tag_playoff([_g(sport="basketball", league="nba", season_type=3)])
    assert games[0]["is_playoff"] is True


def test_nba_play_in_flagged():
    games = tag_playoff([_g(sport="basketball", league="nba", season_type=5)])
    assert games[0]["is_playoff"] is True
    assert games[0]["playoff_round"] in ("Play-In Tournament", "")


def test_nfl_regular_season_not_playoff():
    games = tag_playoff([_g(sport="football", league="nfl", season_type=2)])
    assert games[0]["is_playoff"] is False


def test_nfl_postseason_flagged():
    games = tag_playoff([_g(sport="football", league="nfl", season_type=3)])
    assert games[0]["is_playoff"] is True


def test_fa_cup_always_playoff():
    games = tag_playoff([_g(league="eng.fa")])
    assert games[0]["is_playoff"] is True


def test_league_cup_always_playoff():
    games = tag_playoff([_g(league="eng.league_cup")])
    assert games[0]["is_playoff"] is True


def test_dfb_pokal_always_playoff():
    games = tag_playoff([_g(league="ger.dfb_pokal")])
    assert games[0]["is_playoff"] is True


def test_ucl_knockout_flagged_by_notes():
    games = tag_playoff([_g(
        league="uefa.champions",
        notes="Quarterfinal - 2nd Leg"
    )])
    assert games[0]["is_playoff"] is True
    assert games[0]["playoff_round"] == "Quarterfinal - 2nd Leg"


def test_ucl_group_stage_not_playoff():
    games = tag_playoff([_g(
        league="uefa.champions",
        notes="Matchday 3"
    )])
    assert games[0]["is_playoff"] is False


def test_pl_league_game_not_playoff():
    games = tag_playoff([_g(league="eng.1", notes="")])
    assert games[0]["is_playoff"] is False
