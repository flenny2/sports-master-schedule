"""
Tests for FIFA World Cup 2026 support — pure functions, no network.

Ground truth (ESPN, verified live 2026-07-09; see spec 120): WC round labels
live in event.season.slug ("group-stage", "round-of-16", "final", ...), NOT in
competition.notes (empty []) or competition.series (None). These tests build
synthetic ESPN shapes inline and never hit the network.
"""

import config
from app import espn
from app.playoff import tag_playoff


def _wc_event(season_slug):
    """A minimal synthetic ESPN World Cup event with the round in season.slug.
    WC season.type is a large opaque id (e.g. 13803), not the 1/2/3 convention."""
    return {
        "id": "wc-1",
        "date": "2026-07-11T19:00Z",
        "name": "Country A at Country B",
        "shortName": "A @ B",
        "season": {"type": 13803, "slug": season_slug},
        "competitions": [{
            "competitors": [
                {"homeAway": "home",
                 "team": {"id": 1, "displayName": "Country B",
                          "abbreviation": "B", "logo": "http://x/b.png"},
                 "score": {"value": 1},
                 "records": [{"type": "total", "summary": "1-0-0"}]},
                {"homeAway": "away",
                 "team": {"id": 2, "displayName": "Country A",
                          "abbreviation": "A", "logo": "http://x/a.png"},
                 "score": {"value": 0},
                 "records": [{"type": "total", "summary": "0-1-0"}]},
            ],
            "broadcasts": [{"market": "national", "names": ["FOX"]}],
            "geoBroadcasts": [],
            "status": {"type": {"state": "post"}},
            "venue": {"fullName": "Test Stadium"},
            "notes": [],          # WC: notes empty (ground truth)
            # no "series" key -> raw_series parses to None (ground truth)
        }],
    }


def _wc_game(season_slug):
    """A parsed-game dict shaped as _parse_game would produce it, for the tagger."""
    return {
        "sport": "soccer",
        "league": "fifa.world",
        "season_type": 13803,
        "season_slug": season_slug,
        "notes": "",
        "raw_series": None,
    }


# ── config wiring ───────────────────────────────────────────────────
def test_league_name_registered():
    assert config.LEAGUE_NAMES["fifa.world"] == "FIFA World Cup"


def test_followed_competition_registered():
    assert "fifa.world" in config.FOLLOWED_COMPETITIONS


# ── parser captures the stage slug ─────────────────────────────────
def test_parse_game_captures_season_slug():
    game = espn._parse_game(_wc_event("round-of-16"), "soccer", "fifa.world")
    assert game is not None
    assert game["season_slug"] == "round-of-16"


# ── playoff tagging off season.slug ────────────────────────────────
def test_group_stage_is_not_playoff():
    # group-stage is round-robin — must NOT be tagged knockout
    games = tag_playoff([_wc_game("group-stage")])
    assert games[0]["is_playoff"] is False
    assert games[0]["playoff_round"] == ""


def test_round_of_16_is_playoff_with_label():
    games = tag_playoff([_wc_game("round-of-16")])
    assert games[0]["is_playoff"] is True
    assert games[0]["playoff_round"] == "Round of 16"


def test_quarterfinals_label():
    games = tag_playoff([_wc_game("quarterfinals")])
    assert games[0]["is_playoff"] is True
    assert games[0]["playoff_round"] == "Quarterfinals"


def test_final_is_playoff_with_label():
    games = tag_playoff([_wc_game("final")])
    assert games[0]["is_playoff"] is True
    assert games[0]["playoff_round"] == "Final"
