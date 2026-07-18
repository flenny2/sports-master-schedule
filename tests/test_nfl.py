"""
NFL pillar tests (brief D5): watched-team game inclusion and the NFL
standings mapping. No network — ESPN calls are monkeypatched.

Assumes config.WATCHED_TEAMS contains the Steelers (espn_id "23",
sport "football") — that's product config, not test fixture.
"""

from datetime import date

from app import espn


def _game(gid, date_iso, home_id, away_id, broadcasts=None):
    return {
        "id": gid,
        "date": date_iso,
        "home_team": {"id": home_id, "abbreviation": "H" + home_id},
        "away_team": {"id": away_id, "abbreviation": "A" + away_id},
        "broadcasts": broadcasts or [],
    }


def test_watched_team_game_included_outside_primetime(monkeypatch):
    # Thursday 10am PT: not primetime, not a RedZone window — only the
    # watched-team path can include it.
    fixtures = [
        _game("steelers", "2026-09-10T17:00Z", "23", "2"),
        _game("nobody", "2026-09-10T17:00Z", "3", "4"),
    ]
    monkeypatch.setattr(espn, "_parallel_fetch_days",
                        lambda *a: fixtures)
    games = espn.fetch_nfl_games(date(2026, 9, 7), date(2026, 9, 14))
    ids = {g["id"] for g in games}
    assert "steelers" in ids
    assert "nobody" not in ids
    steelers = [g for g in games if g["id"] == "steelers"][0]
    assert steelers["nfl_slot"] == "My Team"


def test_watched_beats_primetime_label(monkeypatch):
    # Sunday night Steelers game: watched path wins the label
    fixtures = [_game("snf-pit", "2026-09-14T00:20Z", "2", "23", ["NBC"])]
    monkeypatch.setattr(espn, "_parallel_fetch_days",
                        lambda *a: fixtures)
    games = espn.fetch_nfl_games(date(2026, 9, 7), date(2026, 9, 14))
    assert games[0]["nfl_slot"] == "My Team"


def test_primetime_and_redzone_paths_still_work(monkeypatch):
    fixtures = [
        # Sunday 8:20pm ET (Mon 00:20Z) — SNF
        _game("snf", "2026-09-14T00:20Z", "5", "6", ["NBC"]),
        # Sunday 10am PT (17:00Z) — RedZone window
        _game("rz", "2026-09-13T17:00Z", "7", "8"),
    ]
    monkeypatch.setattr(espn, "_parallel_fetch_days",
                        lambda *a: fixtures)
    games = espn.fetch_nfl_games(date(2026, 9, 7), date(2026, 9, 14))
    slots = {g["id"]: g["nfl_slot"] for g in games}
    assert slots["snf"] == "Primetime"
    assert slots["rz"] == "RedZone Window"


# ── NFL standings mapping ─────────────────────────────────────────

NFL_STANDINGS = {
    "name": "National Football League",
    "children": [
        {
            "name": "American Football Conference",
            "standings": {
                "entries": [
                    {
                        "team": {
                            "id": "23",
                            "displayName": "Pittsburgh Steelers",
                            "abbreviation": "PIT",
                            "logos": [{"href": "http://logo/pit.png"}],
                        },
                        "stats": [
                            {"name": "wins", "displayValue": "10"},
                            {"name": "losses", "displayValue": "7"},
                            {"name": "ties", "displayValue": "0"},
                            {"name": "winPercent", "displayValue": ".588"},
                            {"name": "streak", "displayValue": "W2"},
                            {"name": "divisionRecord", "displayValue": "4-2"},
                            {"name": "playoffSeed", "displayValue": "5"},
                        ],
                    },
                    {
                        "team": {
                            "id": "2",
                            "displayName": "Buffalo Bills",
                            "abbreviation": "BUF",
                            "logos": [{"href": "http://logo/buf.png"}],
                        },
                        "stats": [
                            {"name": "wins", "displayValue": "13"},
                            {"name": "losses", "displayValue": "4"},
                            {"name": "ties", "displayValue": "0"},
                            {"name": "winPercent", "displayValue": ".765"},
                            {"name": "streak", "displayValue": "W5"},
                            {"name": "divisionRecord", "displayValue": "5-1"},
                            {"name": "playoffSeed", "displayValue": "2"},
                        ],
                    },
                ]
            },
        }
    ],
}


def test_nfl_standings_mapping(monkeypatch):
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **k: NFL_STANDINGS)
    result = espn.fetch_standings("football", "nfl")
    assert result["sport"] == "football"
    teams = result["groups"][0]["teams"]
    # Sorted by rank (playoffSeed): BUF seed 2 before PIT seed 5
    assert [t["team"]["abbr"] for t in teams] == ["BUF", "PIT"]
    pit = teams[1]
    assert pit["rank"] == "5"
    assert pit["stats"] == {
        "w": "10", "l": "7", "t": "0",
        "pct": ".588", "streak": "W2", "div": "4-2",
    }
    assert pit["is_watched"] is True
    assert teams[0]["is_watched"] is False


def test_watched_highlight_is_sport_scoped(monkeypatch):
    # A SOCCER team with id "23" must NOT light up because the
    # Steelers (football id "23") are watched.
    soccer = {
        "name": "Premier League",
        "children": [{
            "name": "overall",
            "standings": {"entries": [{
                "team": {"id": "23", "displayName": "Imaginary FC",
                         "abbreviation": "IFC", "logos": []},
                "stats": [
                    {"name": "gamesPlayed", "displayValue": "1"},
                    {"name": "points", "displayValue": "3"},
                    {"name": "rank", "displayValue": "1"},
                ],
            }]},
        }],
    }
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **k: soccer)
    result = espn.fetch_standings("soccer", "eng.1")
    assert result["groups"][0]["teams"][0]["is_watched"] is False
