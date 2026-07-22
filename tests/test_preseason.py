"""
Tests for the pre-season standings gate (`preseason` flag).

Between seasons ESPN zeroes every stat and then sorts the table
ALPHABETICALLY — probed 2026-07-22, the Premier League read Bournemouth
1st / Arsenal 2nd / Man City 15th on 0 points, and every NFL team sat at
rank 0. The numbers are honest; the ORDER is not a standing. These pin
the flag that lets the render sites decline to draw one.

No network — `_cached_get` is monkeypatched, the same way
tests/test_nfl.py and tests/test_standings_fragility.py do it.
"""

import config
from app import espn


def _entry(team_id, name, stats):
    return {
        "team": {"id": team_id, "displayName": name,
                 "abbreviation": name[:3].upper()},
        "stats": [{"name": k, "displayValue": v} for k, v in stats.items()],
    }


def _payload(entries, group_name="Group A", league_name="Test League"):
    return {
        "name": league_name,
        "children": [{"name": group_name,
                      "standings": {"entries": entries}}],
    }


ZEROED_SOCCER = _payload([
    _entry("349", "Bournemouth", {"gamesPlayed": "0", "points": "0",
                                  "rank": "1"}),
    _entry("359", "Arsenal", {"gamesPlayed": "0", "points": "0",
                              "rank": "2"}),
    _entry("382", "Manchester City", {"gamesPlayed": "0", "points": "0",
                                      "rank": "15"}),
])

PLAYED_SOCCER = _payload([
    _entry("382", "Manchester City", {"gamesPlayed": "38", "points": "89",
                                      "rank": "1"}),
    _entry("359", "Arsenal", {"gamesPlayed": "38", "points": "84",
                              "rank": "2"}),
])


# ── games_played ──────────────────────────────────────────────────

def test_games_played_reads_gp_for_soccer():
    assert espn.games_played("soccer", {"gp": "38"}) == 38
    assert espn.games_played("soccer", {"gp": "0"}) == 0


def test_games_played_sums_the_record_for_football():
    assert espn.games_played("football", {"w": "11", "l": "6", "t": "0"}) == 17
    assert espn.games_played("football", {"w": "0", "l": "0", "t": "0"}) == 0


def test_games_played_treats_missing_or_junk_stats_as_zero():
    """
    ESPN's off-season shape drops stats entirely, which _stat_val turns
    into "" (see tests/test_standings_fragility.py). Reading that as
    zero games is the safe direction: the table renders an honest
    "not started" note rather than a fabricated ranking.
    """
    assert espn.games_played("soccer", {}) == 0
    assert espn.games_played("soccer", {"gp": ""}) == 0
    assert espn.games_played("football", {"w": "", "l": None}) == 0


# ── the flag on fetch_standings ───────────────────────────────────

def test_zeroed_table_is_flagged_preseason(monkeypatch):
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **kw: ZEROED_SOCCER)
    espn.clear_cache()
    standing = espn.fetch_standings("soccer", "eng.1")
    assert standing["preseason"] is True


def test_alphabetical_zero_point_order_is_what_gets_suppressed(monkeypatch):
    """
    Documents the exact live shape: ESPN really does hand back Man City
    at "15" on 0 points. The rows are still returned — the flag is what
    tells the frontend not to present them as a ranking.
    """
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **kw: ZEROED_SOCCER)
    espn.clear_cache()
    standing = espn.fetch_standings("soccer", "eng.1")
    city = [t for t in standing["groups"][0]["teams"]
            if t["team"]["id"] == "382"][0]
    assert city["rank"] == "15"
    assert city["stats"]["pts"] == "0"
    assert standing["preseason"] is True


def test_table_with_games_played_is_not_preseason(monkeypatch):
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **kw: PLAYED_SOCCER)
    espn.clear_cache()
    standing = espn.fetch_standings("soccer", "eng.1")
    assert standing["preseason"] is False


def test_one_played_game_ends_the_preseason(monkeypatch):
    """Opening weekend: a single played fixture must restore the table."""
    mixed = _payload([
        _entry("349", "Bournemouth", {"gamesPlayed": "0", "points": "0"}),
        _entry("382", "Manchester City", {"gamesPlayed": "1", "points": "3"}),
    ])
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **kw: mixed)
    espn.clear_cache()
    assert espn.fetch_standings("soccer", "eng.1")["preseason"] is False


def test_empty_standings_are_not_flagged_preseason(monkeypatch):
    """No entries is a broken/absent table, not an unplayed season."""
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **kw: _payload([]))
    espn.clear_cache()
    assert espn.fetch_standings("soccer", "eng.1")["preseason"] is False


def test_nfl_zero_records_are_flagged_preseason(monkeypatch):
    zeroed_nfl = _payload([
        _entry("23", "Pittsburgh Steelers",
               {"wins": "0", "losses": "0", "ties": "0", "playoffSeed": "0"}),
        _entry("2", "Buffalo Bills",
               {"wins": "0", "losses": "0", "ties": "0", "playoffSeed": "0"}),
    ], group_name="American Football Conference", league_name="NFL")
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **kw: zeroed_nfl)
    espn.clear_cache()
    assert espn.fetch_standings("football", "nfl")["preseason"] is True


# ── the flag reaching the title race ──────────────────────────────

def test_title_race_carries_the_preseason_flag(monkeypatch):
    """
    The race is NOT dropped pre-season — its upcoming fixtures are real
    and worth showing. Only the gap headline and the rank are fiction,
    and the frontend gates those on this flag.
    """
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **kw: ZEROED_SOCCER)
    monkeypatch.setattr(espn, "fetch_upcoming_fixtures",
                        lambda slug, tid: [{"opponent": "COV", "home": True,
                                            "date": "2026-08-21T19:00Z",
                                            "opponent_name": "Coventry"}])
    monkeypatch.setattr(config, "TITLE_RACES", [{
        "league": "eng.1",
        "label": "Premier League Title Race",
        "team_ids": ["359", "382"],
    }])
    espn.clear_cache()
    races = espn.get_title_races()
    assert len(races) == 1
    assert races[0]["preseason"] is True
    # the real part survives
    assert races[0]["contenders"][0]["upcoming"][0]["opponent"] == "COV"


def test_played_title_race_is_not_flagged(monkeypatch):
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **kw: PLAYED_SOCCER)
    monkeypatch.setattr(espn, "fetch_upcoming_fixtures", lambda slug, tid: [])
    monkeypatch.setattr(config, "TITLE_RACES", [{
        "league": "eng.1",
        "label": "Premier League Title Race",
        "team_ids": ["359", "382"],
    }])
    espn.clear_cache()
    races = espn.get_title_races()
    assert races[0]["preseason"] is False
    assert races[0]["gap"] == 5
