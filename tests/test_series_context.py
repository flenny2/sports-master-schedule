"""Tests for app.series_context."""

from unittest.mock import patch

from app.series_context import tag_series_context


def _nba_game(home_abbr, home_id, away_abbr, away_id,
              home_wins, away_wins, espn_summary,
              best_of=7, completed=False, is_playoff=True):
    """Build a parsed NBA playoff game dict."""
    return {
        "id":         f"nba-{home_abbr}-{away_abbr}-{home_wins}-{away_wins}",
        "sport":      "basketball",
        "league":     "nba",
        "date":       "2026-04-22T23:00Z",
        "home_team":  {"id": home_id, "abbreviation": home_abbr},
        "away_team":  {"id": away_id, "abbreviation": away_abbr},
        "is_playoff": is_playoff,
        "raw_series": {
            "type":              "playoff",
            "title":             "Playoff Series",
            "summary":           espn_summary,
            "completed":         completed,
            "totalCompetitions": best_of,
            "competitors": [
                {"id": home_id, "wins": home_wins},
                {"id": away_id, "wins": away_wins},
            ],
        },
        "raw_leg": None,
    }


def _soccer_game(home_abbr, home_id, away_abbr, away_id, leg,
                 round_title="Quarterfinals", league="uefa.champions",
                 is_playoff=True, game_date="2026-04-15T19:00Z"):
    """Build a parsed two-leg soccer game dict."""
    return {
        "id":         f"soc-{home_abbr}-{away_abbr}-L{leg}",
        "sport":      "soccer",
        "league":     league,
        "date":       game_date,
        "home_team":  {"id": home_id, "abbreviation": home_abbr},
        "away_team":  {"id": away_id, "abbreviation": away_abbr},
        "is_playoff": is_playoff,
        "raw_series": {
            "title":             round_title,
            "totalCompetitions": 2,
            "competitors": [
                {"id": home_id},
                {"id": away_id},
            ],
        },
        "raw_leg": {"value": leg, "displayValue": f"{leg}{'st' if leg==1 else 'nd'} Leg"},
    }


def _first_leg_result(home_abbr, home_id, away_abbr, away_id, hs, as_,
                      round_title="Quarterfinals"):
    """Build what fetch_first_leg would return for a completed 1st leg."""
    return {
        "id":        f"leg1-{home_abbr}-{away_abbr}",
        "sport":     "soccer",
        "date":      "2026-04-08T19:00Z",
        "home_team": {"id": home_id, "abbreviation": home_abbr},
        "away_team": {"id": away_id, "abbreviation": away_abbr},
        "score":     {"home": str(hs), "away": str(as_)},
        "status":    "post",
        "raw_series": {"title": round_title},
    }


# ── NBA ──────────────────────────────────────────────────────────

def test_nba_leading_2_1():
    g = _nba_game("LAL", "13", "HOU", "10", 2, 1, "LAL lead series 2-1")
    tag_series_context([g])
    assert g["series_summary"] == "LAL lead series 2-1"
    d = g["series_detail"]
    assert d["sport"] == "basketball"
    assert d["best_of"] == 7
    assert d["completed"] is False
    assert {"id": "13", "abbr": "LAL", "wins": 2} in d["teams"]
    assert {"id": "10", "abbr": "HOU", "wins": 1} in d["teams"]


def test_nba_series_tied_1_1():
    g = _nba_game("ORL", "19", "DET", "8", 1, 1, "Series tied 1-1")
    tag_series_context([g])
    assert g["series_summary"] == "Series tied 1-1"
    assert g["series_detail"]["teams"][0]["wins"] == 1


def test_nba_sweep_3_0():
    g = _nba_game("OKC", "25", "PHX", "21", 3, 0,
                  "OKC lead series 3-0", completed=False)
    tag_series_context([g])
    assert g["series_summary"] == "OKC lead series 3-0"


def test_nba_series_closeout_4_2():
    g = _nba_game("BOS", "2", "PHI", "20", 4, 2,
                  "BOS win series 4-2", completed=True)
    tag_series_context([g])
    assert g["series_summary"] == "BOS win series 4-2"
    assert g["series_detail"]["completed"] is True


def test_nba_game_1_pregame_falls_back_to_game_x_of_n():
    # Before Game 1 tips: both teams have 0 wins. ESPN's summary may be
    # empty or odd. We show "Game 1 of 7".
    g = _nba_game("LAL", "13", "HOU", "10", 0, 0, "", best_of=7)
    tag_series_context([g])
    assert g["series_summary"] == "Game 1 of 7"
    assert g["series_detail"]["best_of"] == 7


def test_nba_game_1_respects_short_best_of_format():
    # Future-proof: if ESPN shortens to best-of-5 we should read the
    # length from totalCompetitions, not assume 7.
    g = _nba_game("LAL", "13", "HOU", "10", 0, 0, "", best_of=5)
    tag_series_context([g])
    assert g["series_summary"] == "Game 1 of 5"


def test_nba_play_in_gets_empty_context():
    # Play-in tournament games come through with series={} from ESPN.
    g = _nba_game("MIA", "14", "CHA", "30", 0, 0, "")
    g["raw_series"] = None  # simulate ESPN's empty series object
    tag_series_context([g])
    assert g["series_summary"] == ""
    assert g["series_detail"] is None


# ── UCL / two-leg soccer ─────────────────────────────────────────

def test_ucl_first_leg():
    g = _soccer_game("MUN", "132", "RMA", "86", leg=1)
    tag_series_context([g])
    assert g["series_summary"] == "1st Leg"
    d = g["series_detail"]
    assert d["sport"] == "soccer"
    assert d["round"] == "Quarterfinals"
    assert d["leg"] == 1
    assert d["first_leg"] is None


def test_ucl_second_leg_tied_aggregate():
    # 2nd leg where 1st leg was a 1-1 draw.
    # Leg 1: MUN (home) 1, RMA (away) 1.
    # Leg 2: RMA (home) vs MUN (away). Entering aggregate: RMA 1, MUN 1.
    g = _soccer_game("RMA", "86", "MUN", "132", leg=2)
    first_leg = _first_leg_result("MUN", "132", "RMA", "86", 1, 1)
    with patch("app.series_context.fetch_first_leg", return_value=first_leg):
        tag_series_context([g])
    assert g["series_summary"] == "2nd Leg · agg 1-1"
    d = g["series_detail"]
    assert d["leg"] == 2
    assert d["first_leg"]["home_score"] == 1
    assert d["first_leg"]["away_score"] == 1


def test_ucl_second_leg_home_team_leading():
    # Leg 1: SCP (home) 0, ARS (away) 1.
    # Leg 2: ARS (home) vs SCP (away). Entering aggregate: ARS 1, SCP 0.
    # Leg-2 home team (ARS) is leading.
    g = _soccer_game("ARS", "359", "SCP", "2250", leg=2)
    first_leg = _first_leg_result("SCP", "2250", "ARS", "359", 0, 1)
    with patch("app.series_context.fetch_first_leg", return_value=first_leg):
        tag_series_context([g])
    assert g["series_summary"] == "2nd Leg · ARS lead 1-0"
    assert g["series_detail"]["first_leg"]["home_score"] == 0
    assert g["series_detail"]["first_leg"]["away_score"] == 1


def test_ucl_second_leg_away_team_leading():
    # Leg 1: BAR (home) 2, ATM (away) 0.
    # Leg 2: ATM (home) vs BAR (away). Entering aggregate: ATM 0, BAR 2.
    # Leg-2 away team (BAR) is leading.
    g = _soccer_game("ATM", "1068", "BAR", "83", leg=2)
    first_leg = _first_leg_result("BAR", "83", "ATM", "1068", 2, 0)
    with patch("app.series_context.fetch_first_leg", return_value=first_leg):
        tag_series_context([g])
    assert g["series_summary"] == "2nd Leg · BAR lead 2-0"


def test_ucl_second_leg_fetch_failure():
    # Fallback returns None (round mismatch, network failure, etc.)
    g = _soccer_game("PSG", "160", "LIV", "364", leg=2)
    with patch("app.series_context.fetch_first_leg", return_value=None):
        tag_series_context([g])
    assert g["series_summary"] == "2nd Leg"
    d = g["series_detail"]
    assert d["leg"] == 2
    assert d["first_leg"] is None


def test_ucl_second_leg_fetch_raises():
    # Network exceptions are swallowed — never block rendering.
    g = _soccer_game("PSG", "160", "LIV", "364", leg=2)
    with patch(
        "app.series_context.fetch_first_leg",
        side_effect=RuntimeError("boom"),
    ):
        tag_series_context([g])
    assert g["series_summary"] == "2nd Leg"
    assert g["series_detail"]["first_leg"] is None


# ── Short-circuits ───────────────────────────────────────────────

def test_non_playoff_game_is_untouched():
    g = {
        "id":         "regular",
        "sport":      "basketball",
        "is_playoff": False,
        "raw_series": {"summary": "junk should not be read"},
    }
    tag_series_context([g])
    assert g["series_summary"] == ""
    assert g["series_detail"] is None


def test_unknown_sport_gets_empty_context():
    g = {
        "id":         "baseball-game",
        "sport":      "baseball",
        "is_playoff": True,
        "home_team":  {"id": "1", "abbreviation": "LAD"},
        "away_team":  {"id": "2", "abbreviation": "NYY"},
    }
    tag_series_context([g])
    assert g["series_summary"] == ""
    assert g["series_detail"] is None


def test_single_leg_cup_final_gets_empty_context():
    # UCL/Europa final is single-leg — no `leg` field. No two-leg logic.
    g = _soccer_game("PSG", "160", "ARS", "359", leg=1)
    g["raw_leg"] = None
    g["raw_series"]["title"] = "Final"
    tag_series_context([g])
    assert g["series_summary"] == ""
    assert g["series_detail"] is None


def test_nfl_playoff_game_gets_empty_context():
    # NFL playoffs are single-elimination — no series concept.
    g = {
        "id":         "nfl-wildcard",
        "sport":      "football",
        "is_playoff": True,
        "home_team":  {"id": "1", "abbreviation": "KC"},
        "away_team":  {"id": "2", "abbreviation": "BUF"},
    }
    tag_series_context([g])
    assert g["series_summary"] == ""
    assert g["series_detail"] is None
