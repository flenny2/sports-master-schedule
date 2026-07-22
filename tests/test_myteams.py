"""
Tests for app.myteams — the Front Page "Your Teams" strip (brief §D8).

No network: build_team_card and its helpers are pure, so every case here
hands them literal ESPN-shaped dicts. The route test patches
`app.routes.get_my_teams` (not `app.myteams`) because routes.py does
`from app.myteams import get_my_teams`, which binds the name locally.
"""

import pytest

import config
from app import create_app
from app.myteams import (
    _soccer_fallback,
    build_team_card,
    get_favorite_teams,
)

CITY = {
    "name": "Manchester City",
    "espn_id": "382",
    "sport": "soccer",
    "leagues": ["eng.1", "uefa.champions"],
    "tier": "must_watch",
    "favorite": True,
}

STEELERS = {
    "name": "Pittsburgh Steelers",
    "espn_id": "23",
    "sport": "football",
    "leagues": ["nfl"],
    "tier": "must_watch",
    "favorite": True,
}


def _game(sport="soccer", league="eng.1", league_name="Premier League",
          home_id="382", away_id="359", status="post",
          date_str="2026-05-16T15:00Z", score=None, notes="",
          home_abbr="MNC", away_abbr="ARS", color="6CABDD"):
    return {
        "id": "g-" + date_str,
        "sport": sport,
        "league": league,
        "league_name": league_name,
        "status": status,
        "date": date_str,
        "notes": notes,
        "score": score or {},
        "home_team": {"id": home_id, "abbreviation": home_abbr,
                      "name": "Home Team", "logo": "home.png",
                      "color": color, "alt_color": "FFFFFF"},
        "away_team": {"id": away_id, "abbreviation": away_abbr,
                      "name": "Away Team", "logo": "away.png",
                      "color": "EF0107", "alt_color": "063672"},
    }


def _standings(league_id="eng.1", sport="soccer", name="Premier League",
               group_name="", team_id="382", abbr="MNC",
               logo="crest.png", rank="3", stats=None):
    return [{
        "id": league_id,
        "name": name,
        "sport": sport,
        "groups": [{
            "name": group_name,
            "teams": [{
                "rank": rank,
                "team": {"id": team_id, "name": "Manchester City",
                         "abbr": abbr, "logo": logo},
                "stats": stats if stats is not None else {
                    "gp": "38", "w": "28", "d": "5", "l": "5", "pts": "89",
                },
                "zone": "Champions League",
            }],
        }],
    }]


NOW = "2026-07-22T12:00Z"


# ── config flag ───────────────────────────────────────────────────

def test_favorites_are_steelers_and_city():
    """Pins Dylan's Jul-22 answer: favorites drive the strip, tier doesn't."""
    names = {t["name"] for t in get_favorite_teams()}
    assert names == {"Pittsburgh Steelers", "Manchester City"}


def test_arsenal_stays_must_watch_without_being_a_favorite():
    """
    Arsenal is followed for the PL title race, not as a favorite team, and
    its race already has its own Front Page card. Demoting its tier would
    quietly change which games win the marquee, so the two must stay
    independent.
    """
    arsenal = [t for t in config.WATCHED_TEAMS if t["espn_id"] == "359"][0]
    assert arsenal["tier"] == "must_watch"
    assert not arsenal.get("favorite")


# ── sport-scoped matching ─────────────────────────────────────────

def test_football_id_does_not_match_same_id_in_soccer():
    """
    ESPN ids are unique only within a sport. A soccer game between teams
    "23" and "99" must not become the Steelers' next fixture.
    """
    soccer_game = _game(sport="soccer", home_id="23", away_id="99",
                        status="pre", date_str="2026-08-01T15:00Z")
    card = build_team_card(STEELERS, [soccer_game], [], now_iso=NOW)
    assert card["next"] is None
    assert card["last"] is None


# ── next / last selection ─────────────────────────────────────────

def test_next_is_the_earliest_upcoming_game():
    games = [
        _game(status="pre", date_str="2026-09-27T20:00Z", away_abbr="CIN"),
        _game(status="pre", date_str="2026-09-13T17:00Z", away_abbr="ATL"),
        _game(status="pre", date_str="2026-09-20T17:00Z", away_abbr="NE"),
    ]
    card = build_team_card(CITY, games, [], now_iso=NOW)
    assert card["next"]["date"] == "2026-09-13T17:00Z"
    assert card["next"]["opponent"] == "ATL"


def test_stale_pre_game_in_the_past_is_not_next():
    """ESPN sometimes leaves an old fixture stuck in `pre` — ignore it."""
    games = [
        _game(status="pre", date_str="2025-11-02T15:00Z", away_abbr="OLD"),
        _game(status="pre", date_str="2026-08-23T13:00Z", away_abbr="BOU"),
    ]
    card = build_team_card(CITY, games, [], now_iso=NOW)
    assert card["next"]["opponent"] == "BOU"


def test_last_is_the_most_recent_finished_game():
    games = [
        _game(status="post", date_str="2026-04-04T15:00Z",
              score={"home": "4", "away": "0"}, away_abbr="LIV"),
        _game(status="post", date_str="2026-05-16T15:00Z",
              score={"home": "0", "away": "1"}, home_id="363",
              away_id="382", away_abbr="MNC", home_abbr="CHE"),
    ]
    card = build_team_card(CITY, games, [], now_iso=NOW)
    assert card["last"]["date"] == "2026-05-16T15:00Z"


# ── result derivation ─────────────────────────────────────────────

def test_win_as_the_away_team():
    """City won the FA Cup final 1-0 at Chelsea — away side, higher score."""
    game = _game(status="post", date_str="2026-05-16T15:00Z",
                 league="eng.fa", league_name="FA Cup",
                 home_id="363", home_abbr="CHE",
                 away_id="382", away_abbr="MNC",
                 score={"home": "0", "away": "1"})
    card = build_team_card(CITY, [game], [], now_iso=NOW)
    assert card["last"]["outcome"] == "W"
    assert card["last"]["score"] == "1-0"
    assert card["last"]["home"] is False
    assert card["last"]["opponent"] == "CHE"
    assert card["last"]["league_name"] == "FA Cup"


def test_loss_as_the_home_team_with_float_scores():
    """Soccer scores arrive as floats ("2.0") — they must render as ints."""
    game = _game(status="post", score={"home": "1.0", "away": "2.0"})
    card = build_team_card(CITY, [game], [], now_iso=NOW)
    assert card["last"]["outcome"] == "L"
    assert card["last"]["score"] == "1-2"


def test_draw_carries_the_shootout_note():
    """
    A drawn knockout tie is not really a draw. ESPN puts the decider in
    `notes`, and without it the card would claim a result that never was.
    """
    game = _game(status="post", score={"home": "1", "away": "1"},
                 notes="Paris Saint-Germain win 4-3 on penalties")
    card = build_team_card(CITY, [game], [], now_iso=NOW)
    assert card["last"]["outcome"] == "D"
    assert "penalties" in card["last"]["note"]


def test_unscored_finished_game_yields_no_last_row():
    game = _game(status="post", score={})
    card = build_team_card(CITY, [game], [], now_iso=NOW)
    assert card["last"] is None


# ── standings: the pre-season suppression ─────────────────────────

def test_standing_suppressed_before_the_soccer_season_starts():
    """
    ESPN zeroes the table in the off-season and sorts it ALPHABETICALLY
    (probed Jul-22: Arsenal "2nd" on 0 points). Showing that rank would
    invent a standing, so 0 games played means no row.
    """
    standings = _standings(rank="2", stats={
        "gp": "0", "w": "0", "d": "0", "l": "0", "pts": "0",
    })
    card = build_team_card(CITY, [], standings, now_iso=NOW)
    assert card["standing"] is None


def test_standing_suppressed_before_the_nfl_season_starts():
    standings = _standings(league_id="nfl", sport="football", name="NFL",
                           group_name="American Football Conference",
                           team_id="23", abbr="PIT", rank="0",
                           stats={"w": "0", "l": "0", "t": "0"})
    card = build_team_card(STEELERS, [], standings, now_iso=NOW)
    assert card["standing"] is None


def test_standing_shows_once_games_are_played():
    standings = _standings(rank="3")
    card = build_team_card(CITY, [], standings, now_iso=NOW)
    assert card["standing"]["rank"] == "3"
    assert card["standing"]["record"] == "89 pts"
    assert card["standing"]["league_name"] == "Premier League"


def test_nfl_standing_record_includes_ties_only_when_they_exist():
    standings = _standings(league_id="nfl", sport="football", name="NFL",
                           group_name="American Football Conference",
                           team_id="23", abbr="PIT", rank="2",
                           stats={"w": "11", "l": "6", "t": "0"})
    card = build_team_card(STEELERS, [], standings, now_iso=NOW)
    assert card["standing"]["record"] == "11-6"
    assert card["standing"]["group"] == "American Football Conference"

    tied = _standings(league_id="nfl", sport="football", name="NFL",
                      team_id="23", abbr="PIT", rank="2",
                      stats={"w": "10", "l": "6", "t": "1"})
    assert build_team_card(STEELERS, [], tied,
                           now_iso=NOW)["standing"]["record"] == "10-6-1"


def test_standing_prefers_the_teams_domestic_league():
    """
    City sit in both the PL and Champions League tables. The config league
    order decides, so the card reads "Premier League", not a UCL group.
    """
    standings = _standings(league_id="uefa.champions",
                           name="Champions League", rank="1")
    standings += _standings(league_id="eng.1", name="Premier League",
                            rank="3")
    card = build_team_card(CITY, [], standings, now_iso=NOW)
    assert card["standing"]["league_name"] == "Premier League"


# ── identity + empty states ───────────────────────────────────────

def test_identity_takes_crest_from_standings_and_color_from_games():
    """Config has neither; standings carry a crest year-round, games the kit."""
    card = build_team_card(CITY, [_game()], _standings(), now_iso=NOW)
    assert card["logo"] == "crest.png"
    assert card["abbr"] == "MNC"
    assert card["color"] == "6CABDD"


def test_team_with_no_data_still_renders_a_card():
    """Off-season with nothing published must not raise or 500."""
    card = build_team_card(STEELERS, [], [], now_iso=NOW)
    assert card["name"] == "Pittsburgh Steelers"
    assert card["next"] is None
    assert card["last"] is None
    assert card["standing"] is None


def test_fallback_fixture_fills_an_empty_next_row():
    fallback = [{
        "opponent": "BOU", "opponent_name": "AFC Bournemouth",
        "home": True, "date": "2026-08-23T13:00Z",
        "league_name": "Premier League",
    }]
    card = build_team_card(CITY, [], [], fallback_fixtures=fallback,
                           now_iso=NOW)
    assert card["next"]["opponent"] == "BOU"


def test_schedule_upcoming_beats_the_fallback():
    """Only reach for the calendar scan when the schedule has nothing."""
    games = [_game(status="pre", date_str="2026-08-01T15:00Z",
                   away_abbr="SCH")]
    fallback = [{"opponent": "BOU", "home": True,
                 "date": "2026-08-23T13:00Z", "league_name": "PL"}]
    card = build_team_card(CITY, games, [], fallback_fixtures=fallback,
                           now_iso=NOW)
    assert card["next"]["opponent"] == "SCH"


# ── the soccer-only fallback path ─────────────────────────────────

def test_soccer_fallback_skipped_for_nfl(monkeypatch):
    """The NFL team schedule already carries the season ahead."""
    def _boom(*_args):
        raise AssertionError("NFL must not hit the calendar scan")
    monkeypatch.setattr("app.myteams.fetch_upcoming_fixtures", _boom)
    assert _soccer_fallback(STEELERS, [], NOW, {}) == []


def test_soccer_fallback_skipped_when_schedule_has_an_upcoming_game(
        monkeypatch):
    def _boom(*_args):
        raise AssertionError("should not scan when the schedule has one")
    monkeypatch.setattr("app.myteams.fetch_upcoming_fixtures", _boom)
    games = [_game(status="pre", date_str="2026-08-01T15:00Z")]
    assert _soccer_fallback(CITY, games, NOW, {}) == []


def test_soccer_fallback_labels_fixtures_with_the_league_name(monkeypatch):
    monkeypatch.setattr("app.myteams.fetch_upcoming_fixtures",
                        lambda slug, team_id: [{"opponent": "BOU",
                                                "home": True,
                                                "date": "2026-08-23T13:00Z"}])
    out = _soccer_fallback(CITY, [], NOW, {"eng.1": "Premier League"})
    assert out[0]["league_name"] == "Premier League"


# ── route ─────────────────────────────────────────────────────────

@pytest.fixture
def client(monkeypatch):
    import app.routes
    monkeypatch.setattr(app.routes, "get_my_teams",
                        lambda: [build_team_card(CITY, [], _standings())])
    return create_app().test_client()


def test_myteams_route_returns_cards(client):
    resp = client.get("/api/myteams")
    assert resp.status_code == 200
    teams = resp.get_json()["teams"]
    assert len(teams) == 1
    assert teams[0]["name"] == "Manchester City"
