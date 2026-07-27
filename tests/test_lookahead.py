"""
Tests for the Front Page's next-fixture lookahead (app/lookahead.py).

The bug being pinned here is the one seen live on 2026-07-26: the Front
Page showed "No games in this window — browse the calendar." because the
padded July range ended Aug 2 and the next real fixture was Aug 7 — five
days out of reach. These tests are pure; the ESPN fetch is injected.
"""

from datetime import date

import pytest

from app import create_app
from app.lookahead import (
    LOOKAHEAD_DAYS,
    find_next_upcoming,
    lookahead_range,
    next_game_beyond_window,
)


def game(gid, date_iso, status="pre"):
    return {"id": gid, "date": date_iso, "status": status}


NOW = "2026-07-26T18:00Z"


# ── find_next_upcoming ──────────────────────────────────────────────

def test_picks_the_earliest_future_game():
    games = [
        game("c", "2026-08-14T00:00Z"),
        game("a", "2026-08-07T00:00Z"),
        game("b", "2026-08-13T23:00Z"),
    ]
    assert find_next_upcoming(games, NOW)["id"] == "a"


def test_ignores_games_already_played():
    games = [game("done", "2026-07-19T19:00Z", status="post")]
    assert find_next_upcoming(games, NOW) is None


def test_ignores_a_game_in_progress():
    """A live game is not 'next up' — the marquee already covers it."""
    games = [game("live", "2026-07-26T17:00Z", status="in")]
    assert find_next_upcoming(games, NOW) is None


def test_ignores_a_past_kickoff_still_marked_pre():
    """
    ESPN leaves a finished game at `pre` on quiet feeds, so status alone
    is not enough — the kickoff has to be in the future too.
    """
    games = [game("stale", "2026-07-20T19:00Z", status="pre")]
    assert find_next_upcoming(games, NOW) is None


def test_a_kickoff_exactly_now_is_not_upcoming():
    assert find_next_upcoming([game("x", NOW)], NOW) is None


def test_empty_list_is_none():
    assert find_next_upcoming([], NOW) is None


def test_tolerates_a_game_with_no_date():
    """Parsing is defensive everywhere else in this app; be so here too."""
    games = [{"id": "broken", "status": "pre"}, game("ok", "2026-08-07T00:00Z")]
    assert find_next_upcoming(games, NOW)["id"] == "ok"


# ── lookahead_range ─────────────────────────────────────────────────

def test_scan_starts_the_day_after_the_window_ends():
    """No overlap — the caller already has every day up to window_end."""
    start, end = lookahead_range(date(2026, 8, 2))
    assert start == date(2026, 8, 3)


def test_scan_length_matches_the_configured_window():
    start, end = lookahead_range(date(2026, 8, 2))
    assert (end - start).days + 1 == LOOKAHEAD_DAYS


def test_scan_window_covers_the_real_offseason_gap():
    """
    The gap this feature exists for: window ends Aug 2, the next fixture
    is Aug 7. If the scan ever stops covering that, the live symptom is
    back.
    """
    start, end = lookahead_range(date(2026, 8, 2))
    assert start <= date(2026, 8, 7) <= end


# ── next_game_beyond_window ─────────────────────────────────────────

def test_returns_nothing_and_fetches_nothing_when_the_window_has_a_game():
    """
    Two guarantees in one: an ordinary week costs no extra ESPN call, and
    the result is None rather than the in-window game — the caller
    already has that one, and returning it would duplicate it in the
    response.
    """
    calls = []

    def fetch(s, e):
        calls.append((s, e))
        return []

    games = [game("inside", "2026-07-30T19:00Z")]
    assert next_game_beyond_window(games, date(2026, 8, 2), NOW, fetch) is None
    assert calls == []


def test_scans_forward_when_the_window_is_exhausted():
    ahead = [game("aug7", "2026-08-07T00:00Z")]
    calls = []

    def fetch(s, e):
        calls.append((s, e))
        return ahead

    played_out = [game("wcfinal", "2026-07-19T19:00Z", status="post")]
    got = next_game_beyond_window(played_out, date(2026, 8, 2), NOW, fetch)
    assert got["id"] == "aug7"
    assert calls == [(date(2026, 8, 3), date(2026, 9, 16))]


def test_returns_none_when_even_the_scan_finds_nothing():
    """The Front Page's existing message is the correct fallback here."""
    got = next_game_beyond_window([], date(2026, 8, 2), NOW, lambda s, e: [])
    assert got is None


def test_an_espn_failure_degrades_instead_of_raising():
    """
    A quiet front page is cosmetic; a 500 on the app's main endpoint is
    not. The scan must never be able to take /api/schedule down.
    """
    def boom(s, e):
        raise RuntimeError("ESPN timed out")

    assert next_game_beyond_window([], date(2026, 8, 2), NOW, boom) is None


def test_a_none_result_from_the_fetcher_is_survivable():
    assert next_game_beyond_window([], date(2026, 8, 2), NOW,
                                   lambda s, e: None) is None


def test_scan_still_filters_out_stale_and_finished_games():
    """The forward scan gets the same honesty rules as the main window."""
    ahead = [
        game("finished", "2026-08-05T00:00Z", status="post"),
        game("real", "2026-08-13T23:00Z"),
    ]
    got = next_game_beyond_window([], date(2026, 8, 2), NOW, lambda s, e: ahead)
    assert got["id"] == "real"


# ── Route wiring ────────────────────────────────────────────────────
# The pure helpers above were always correct in isolation; the live bug
# was that nothing CALLED them from /api/schedule. These pin the wiring.

def route_game(gid, date_iso, status="pre"):
    """
    A game with enough shape to survive the route's tagging chain.
    The bare `game()` above is fine for the pure helpers but the taggers
    read `sport`, `league` and both teams.
    """
    return {
        "id": gid,
        "date": date_iso,
        "status": status,
        "sport": "soccer",
        "league": "eng.1",
        "league_name": "Premier League",
        "name": "Test A at Test B",
        "notes": "",
        "home_team": {"id": "1", "name": "Test B", "abbreviation": "TSB"},
        "away_team": {"id": "2", "name": "Test A", "abbreviation": "TSA"},
    }


@pytest.fixture
def client(monkeypatch):
    """
    Flask test client with ESPN stubbed. The stub answers as the real
    off-season did: the padded July window is played out, and the next
    fixture sits just past its end.
    """
    import app.routes

    def fake_get_all_games(start, end):
        played = route_game("wcfinal", "2026-07-19T19:00Z", status="post")
        ahead = route_game("aug7", "2126-08-07T00:00Z")  # far future: never stale
        if start <= date(2026, 7, 19) <= end:
            return [played]
        if start > date(2026, 8, 2):
            return [ahead]
        return []

    monkeypatch.setattr(app.routes, "get_all_games", fake_get_all_games)
    monkeypatch.setattr(app.routes, "get_all_userdata", lambda: {})
    return create_app().test_client()


def test_route_reports_the_next_fixture_beyond_an_exhausted_window(client):
    body = client.get("/api/schedule?month=2026-07").get_json()
    assert body["next_upcoming"]["id"] == "aug7"


def test_route_tags_the_lookahead_game_like_any_other(client):
    """
    The Front Page renders it with the ordinary card builder, which reads
    tier/availability — an untagged game would render a broken card.
    """
    nxt = client.get("/api/schedule?month=2026-07").get_json()["next_upcoming"]
    assert "tier" in nxt and "availability" in nxt
    assert nxt["watched"] is False


def test_route_omits_the_key_when_the_window_has_its_own_games(monkeypatch):
    """No key at all, rather than a null — the frontend tests truthiness."""
    import app.routes
    monkeypatch.setattr(app.routes, "get_all_games",
                        lambda s, e: [route_game("soon", "2126-07-30T19:00Z")])
    monkeypatch.setattr(app.routes, "get_all_userdata", lambda: {})
    body = create_app().test_client().get("/api/schedule?month=2026-07").get_json()
    assert body["games"] and "next_upcoming" not in body
