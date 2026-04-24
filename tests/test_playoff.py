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


# ── Structured-title trigger (3rd belt-and-suspenders path) ──────

def test_ucl_flagged_by_series_title_even_without_notes_keyword():
    # Real-world case: ESPN notes say "1st Leg" (no keyword match) but
    # series.title says "Quarterfinals" — must still flag as playoff.
    games = tag_playoff([_g(
        league="uefa.champions",
        notes="1st Leg",
        raw_series={"title": "Quarterfinals"},
    )])
    assert games[0]["is_playoff"] is True
    assert games[0]["playoff_round"] == "Quarterfinals"


def test_europa_semifinal_flagged_by_series_title():
    games = tag_playoff([_g(
        league="uefa.europa",
        notes="2nd Leg - Team X advance 3-1 on aggregate",
        raw_series={"title": "Semifinals"},
    )])
    assert games[0]["is_playoff"] is True
    # Structured title beats the ugly notes string.
    assert games[0]["playoff_round"] == "Semifinals"


def test_conference_league_round_of_16_flagged_by_title():
    games = tag_playoff([_g(
        league="uefa.europa.conf",
        notes="1st Leg",
        raw_series={"title": "Round of 16"},
    )])
    assert games[0]["is_playoff"] is True
    assert games[0]["playoff_round"] == "Round of 16"


def test_unknown_series_title_does_not_trigger():
    # "Group Stage" is not a knockout round — shouldn't flag.
    games = tag_playoff([_g(
        league="uefa.champions",
        notes="Matchday 5",
        raw_series={"title": "Group Stage"},
    )])
    assert games[0]["is_playoff"] is False


def test_nba_series_title_does_not_pollute_round_label():
    # NBA's title "Playoff Series" is not in the knockout set, so it
    # must fall back to notes — preserves existing NBA behavior.
    games = tag_playoff([_g(
        sport="basketball",
        league="nba",
        season_type=3,
        notes="East 1st Round - Game 2",
        raw_series={"title": "Playoff Series"},
    )])
    assert games[0]["is_playoff"] is True
    assert games[0]["playoff_round"] == "East 1st Round - Game 2"
