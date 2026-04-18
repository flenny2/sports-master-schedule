"""
Tests for app.espn — focused on pure functions that don't hit the network.
"""

from datetime import date

from app import espn


SAMPLE_EVENT = {
    "id": "999",
    "date": "2026-04-15T19:00Z",
    "name": "Home FC at Away FC",
    "shortName": "AWY @ HOM",
    "season": {"type": 2},
    "competitions": [{
        "competitors": [
            {
                "homeAway": "home",
                "team": {
                    "id": 100, "displayName": "Home FC",
                    "abbreviation": "HOM", "logo": "http://x/h.png",
                },
                "score": {"value": 2},
                "records": [{"type": "total", "summary": "10-5-3"}],
            },
            {
                "homeAway": "away",
                "team": {
                    "id": 200, "displayName": "Away FC",
                    "abbreviation": "AWY", "logo": "http://x/a.png",
                },
                "score": {"value": 1},
                "records": [{"type": "total", "summary": "8-7-2"}],
            },
        ],
        "broadcasts": [{"market": "national", "names": ["ESPN"]}],
        "geoBroadcasts": [],
        "status": {"type": {"state": "post"}},
        "venue": {"fullName": "Test Stadium"},
        "notes": [{"headline": "Quarterfinal"}],
    }],
}


def test_parse_game_extracts_score():
    game = espn._parse_game(SAMPLE_EVENT, "soccer", "eng.1")
    assert game is not None
    assert game["score"] == {"home": "2", "away": "1"}
    assert game["home_team"]["name"] == "Home FC"
    assert game["away_team"]["name"] == "Away FC"


def test_parse_game_flags_national_broadcast():
    game = espn._parse_game(SAMPLE_EVENT, "soccer", "eng.1")
    assert game["is_national"] is True
    assert "ESPN" in game["broadcasts"]


def test_parse_game_returns_none_for_missing_teams():
    broken = {"id": "1", "competitions": [{"competitors": []}]}
    assert espn._parse_game(broken, "soccer", "eng.1") is None


def test_parse_game_handles_float_score_strings():
    event = {
        **SAMPLE_EVENT,
        "competitions": [{
            **SAMPLE_EVENT["competitions"][0],
            "competitors": [
                {**SAMPLE_EVENT["competitions"][0]["competitors"][0],
                 "score": "2.0"},
                {**SAMPLE_EVENT["competitions"][0]["competitors"][1],
                 "score": "1.0"},
            ],
        }],
    }
    game = espn._parse_game(event, "soccer", "eng.1")
    assert game["score"] == {"home": "2", "away": "1"}


def test_filter_to_date_range():
    games = [
        {"date": "2026-04-14T23:00Z"},  # before range (in Pacific)
        {"date": "2026-04-15T19:00Z"},  # inside range
        {"date": "2026-04-20T06:00Z"},  # outside range
    ]
    out = espn._filter_to_date_range(
        games, date(2026, 4, 15), date(2026, 4, 16))
    assert len(out) == 1
    assert out[0]["date"] == "2026-04-15T19:00Z"


def test_cache_roundtrip(monkeypatch):
    """_cached_get should return cached data without hitting the network."""
    calls = {"n": 0}

    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"hello": "world"}

    def fake_get(url, params=None, timeout=None):
        calls["n"] += 1
        return FakeResp()

    monkeypatch.setattr(espn.requests, "get", fake_get)
    espn.clear_cache()
    a = espn._cached_get("http://example.com/x")
    b = espn._cached_get("http://example.com/x")
    assert a == {"hello": "world"}
    assert a == b
    assert calls["n"] == 1  # second call served from cache
