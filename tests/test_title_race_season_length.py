"""
Tests for the season length a title race is measured against.

The bug being pinned: `get_title_races()` hardcoded `remaining = 38 - gp`
while looping over EVERY entry in `config.TITLE_RACES`. 38 is right for a
20-team league and wrong for an 18-team one, so a Bundesliga or Ligue 1 race
would have reported four matches — twelve points — of "still reachable" that
do not exist, with no exception and no visible symptom. It was documented in
CLAUDE.md's August rollover checklist as a trap to walk around; this makes it
not a trap.

`season_match_count` is pure, so most of this needs no network. The one test
that exercises `get_title_races()` stubs its two fetches.
"""

import pytest

from app import espn


# ── The pure helper ───────────────────────────────────────────────

@pytest.mark.parametrize("teams,matches", [
    (20, 38),   # Premier League, La Liga, Serie A
    (18, 34),   # Bundesliga, Ligue 1 — the case the old constant broke
    (16, 30),
    (12, 22),
])
def test_double_round_robin_length(teams, matches):
    assert espn.season_match_count(teams) == matches


@pytest.mark.parametrize("bad", [0, 1, 3, -20, None, "20", 20.0])
def test_returns_none_rather_than_guessing(bad):
    """A table too small to be a league — a cup group, an empty pre-season
    fetch — gets None. Guessing there is exactly what the old constant did."""
    assert espn.season_match_count(bad) is None


# ── The race builder ──────────────────────────────────────────────

def _table(n_teams, played_by_contenders):
    """A standings payload of `n_teams`, where the first two are the
    contenders with the given games played."""
    teams = []
    for i in range(n_teams):
        gp = played_by_contenders if i < 2 else 0
        teams.append({
            "rank": str(i + 1),
            "team": {"id": str(i + 1), "name": f"Team {i + 1}",
                     "abbr": f"T{i + 1}", "logo": ""},
            "stats": {"pts": gp * 2, "gp": gp},
        })
    return {"id": "x", "name": "Test League", "sport": "soccer",
            "preseason": False, "groups": [{"name": "", "teams": teams}]}


def _race(monkeypatch, n_teams, gp, league="ger.1"):
    monkeypatch.setattr(espn.config, "TITLE_RACES", [
        {"league": league, "label": "Test Race", "team_ids": ["1", "2"]},
    ])
    monkeypatch.setattr(espn, "fetch_standings",
                        lambda sport, slug: _table(n_teams, gp))
    monkeypatch.setattr(espn, "fetch_upcoming_fixtures",
                        lambda slug, tid: [])
    races = espn.get_title_races()
    assert len(races) == 1
    return races[0]


def test_eighteen_team_league_gets_34_not_38(monkeypatch):
    """The regression itself. Against the old constant this reads 28."""
    race = _race(monkeypatch, 18, gp=10)
    assert race["contenders"][0]["remaining"] == 24


def test_twenty_team_league_still_gets_38(monkeypatch):
    """The leagues that worked by accident must keep working."""
    race = _race(monkeypatch, 20, gp=10, league="eng.1")
    assert race["contenders"][0]["remaining"] == 28


def test_max_points_follows_the_real_season_length(monkeypatch):
    """max_pts is what the title-race widget calls still reachable, so it
    inherits the error directly: 12 phantom points in an 18-team league."""
    race = _race(monkeypatch, 18, gp=10)
    c = race["contenders"][0]
    assert c["max_pts"] == c["pts"] + c["remaining"] * 3
    assert c["max_pts"] == 20 + 72


def test_remaining_never_goes_negative(monkeypatch):
    """A table that grew mid-season, or a gp ESPN over-reports, must not
    render as a negative number of matches left."""
    race = _race(monkeypatch, 18, gp=40)
    assert race["contenders"][0]["remaining"] == 0


def test_unknown_season_length_omits_the_figure_rather_than_inventing_one(
        monkeypatch):
    """A four-team group is not a league. Both the per-team figures and the
    race-level games-in-hand go None, so the frontend can drop them —
    `static/app.js` filters null stat boxes out."""
    race = _race(monkeypatch, 3, gp=2)
    assert race["contenders"][0]["remaining"] is None
    assert race["contenders"][0]["max_pts"] is None
    assert race["games_in_hand"] is None


def test_games_in_hand_still_computed_when_the_length_is_known(monkeypatch):
    race = _race(monkeypatch, 18, gp=10)
    # Both contenders have played 10, so neither has a game in hand.
    assert race["games_in_hand"] == 0
