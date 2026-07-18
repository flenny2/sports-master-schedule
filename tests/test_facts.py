"""
Tests for app/facts.py — ESPN summary parsing for the facts panel.

Fixtures are trimmed copies of REAL response shapes probed live on
2026-07-18 (soccer: fifa.world summary; NFL: playoff summary). No
network: fetch_event_summary is monkeypatched everywhere.
"""

from app import facts


SOCCER_SUMMARY = {
    "gameInfo": {"venue": {"fullName": "Hard Rock Stadium"}},
    "odds": [{"details": "FRA -115", "overUnder": 3.5}],
    "boxscore": {
        "form": [
            {
                "team": {"abbreviation": "FRA"},
                "events": [
                    {"gameResult": "L"}, {"gameResult": "W"},
                    {"gameResult": "W"}, {"gameResult": "D"},
                    {"gameResult": "W"}, {"gameResult": "W"},
                ],
            },
            {
                "team": {"abbreviation": "ENG"},
                "events": [{"gameResult": "W"}, {"gameResult": "W"}],
            },
        ],
    },
    "headToHeadGames": [
        {
            "team": {"abbreviation": "FRA"},
            "events": [
                {"gameDate": "2022-12-10T19:00Z", "score": "2-1"},
                {"gameDate": "2017-06-13T19:00Z", "score": "3-2"},
            ],
        }
    ],
    "rosters": [
        {
            "homeAway": "home",
            "team": {"abbreviation": "FRA"},
            "formation": "4-2-3-1",
            "roster": [
                {"starter": True, "athlete": {"displayName": "M. Maignan"}},
                {"starter": True, "athlete": {"displayName": "K. Mbappé"}},
                {"starter": False, "athlete": {"displayName": "Sub Guy"}},
            ],
        },
        {
            "homeAway": "away",
            "team": {"abbreviation": "ENG"},
            "roster": [],  # lineup not announced yet
        },
    ],
}

NFL_SUMMARY = {
    "gameInfo": {"venue": {"fullName": "EverBank Stadium"}},
    "injuries": [
        {
            "team": {"abbreviation": "JAX"},
            "injuries": [
                {
                    "status": "Questionable",
                    "athlete": {
                        "displayName": "Travis Hunter",
                        "position": {"abbreviation": "WR"},
                    },
                },
                {
                    "status": "Out",
                    "athlete": {"displayName": "Some Guard"},  # no position
                },
            ],
        },
        {"team": {"abbreviation": "BUF"}, "injuries": []},  # clean sheet
    ],
    "leaders": [
        {
            "team": {"abbreviation": "JAX"},
            "leaders": [
                {
                    "displayName": "Passing Leader",
                    "leaders": [
                        {
                            "displayValue": "18/30, 207 YDS, 3 TD, 2 INT",
                            "athlete": {"displayName": "Trevor Lawrence"},
                        }
                    ],
                },
                {"displayName": "Empty Category", "leaders": []},
            ],
        }
    ],
}


def test_soccer_facts_full(monkeypatch):
    monkeypatch.setattr(facts, "fetch_event_summary",
                        lambda *a: SOCCER_SUMMARY)
    f = facts.get_game_facts("soccer", "fifa.world", "760516")
    assert f["venue"] == "Hard Rock Stadium"
    assert f["odds"] == "FRA -115 · O/U 3.5"
    # Form capped at 5 results, space-joined
    fra = [s for s in f["form"] if s["team"] == "FRA"][0]
    assert fra["results"] == "L W W D W"
    assert f["h2h"] == ["2022-12 · 2-1", "2017-06 · 3-2"]
    # Only FRA announced a lineup; only starters included
    assert len(f["lineups"]) == 1
    xi = f["lineups"][0]
    assert xi["team"] == "FRA"
    assert xi["formation"] == "4-2-3-1"
    assert xi["starters"] == ["M. Maignan", "K. Mbappé"]


def test_soccer_facts_sparse_summary_is_none(monkeypatch):
    monkeypatch.setattr(facts, "fetch_event_summary", lambda *a: {})
    assert facts.get_game_facts("soccer", "eng.1", "1") is None


def test_nfl_facts_full(monkeypatch):
    monkeypatch.setattr(facts, "fetch_event_summary", lambda *a: NFL_SUMMARY)
    f = facts.get_game_facts("football", "nfl", "401772977")
    assert f["venue"] == "EverBank Stadium"
    # BUF had no listed injuries -> only JAX present
    assert len(f["injuries"]) == 1
    jax = f["injuries"][0]
    assert jax["team"] == "JAX"
    assert "Travis Hunter (WR) — Questionable" in jax["players"]
    assert "Some Guard — Out" in jax["players"]  # position optional
    # Leaders: empty categories skipped
    assert f["leaders"][0]["lines"] == [
        "Passing Leader: Trevor Lawrence — 18/30, 207 YDS, 3 TD, 2 INT"
    ]


def test_fetch_failure_returns_none(monkeypatch):
    monkeypatch.setattr(facts, "fetch_event_summary", lambda *a: None)
    assert facts.get_game_facts("soccer", "eng.1", "1") is None


def test_unsupported_sport_returns_none(monkeypatch):
    called = []
    monkeypatch.setattr(facts, "fetch_event_summary",
                        lambda *a: called.append(a))
    assert facts.get_game_facts("basketball", "nba", "1") is None
    assert called == []  # never even fetches


def test_malformed_shape_returns_none(monkeypatch):
    # Parse-bomb style: plausible keys, hostile value types
    bomb = {"boxscore": "not-a-dict-surprise"}
    monkeypatch.setattr(facts, "fetch_event_summary", lambda *a: bomb)
    assert facts.get_game_facts("soccer", "eng.1", "1") is None
