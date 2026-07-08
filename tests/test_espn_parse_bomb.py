"""
CHARACTERIZATION TESTS — these LOCK a known bug, they do NOT assert desired behavior.

Bug: a single non-numeric score in an ESPN response empties an entire sport's batch.

`_parse_game` wraps its body in `try/except (KeyError, IndexError, TypeError)`
(app/espn.py:218) so that one malformed event returns None and gets skipped while
the rest of the batch survives. But the score cast `int(float(home_score))`
(app/espn.py:177) raises **ValueError** on non-numeric input like "PPD" (a
postponed game). ValueError is NOT in that except tuple, so it escapes `_parse_game`
and propagates up through the `for event in ...` loop in `fetch_scoreboard`
(app/espn.py:273). The loop aborts, every already-parsed game is discarded, and the
caller gets an exception instead of a list — i.e. one bad score empties the sport.

These tests assert the CURRENT (buggy) outcome so a future supervised fix has a
red-to-green target. When the fix lands (add ValueError to the except tuple at
line 218, or guard the cast at line 177), these tests are EXPECTED to fail and
should be rewritten to assert the fixed behavior (malformed event skipped, good
games returned). See tests/FINDINGS.md.
"""

import pytest

from app import espn


# A well-formed, post-game event that parses cleanly (mirrors test_espn.SAMPLE_EVENT).
def _good_event(event_id, home_score, away_score):
    return {
        "id": event_id,
        "date": "2026-04-15T19:00Z",
        "name": "Home FC at Away FC",
        "shortName": "AWY @ HOM",
        "season": {"type": 2},
        "competitions": [{
            "competitors": [
                {
                    "homeAway": "home",
                    "team": {"id": 100, "displayName": "Home FC",
                             "abbreviation": "HOM", "logo": "http://x/h.png"},
                    "score": {"value": home_score},
                },
                {
                    "homeAway": "away",
                    "team": {"id": 200, "displayName": "Away FC",
                             "abbreviation": "AWY", "logo": "http://x/a.png"},
                    "score": {"value": away_score},
                },
            ],
            "broadcasts": [],
            "geoBroadcasts": [],
            "status": {"type": {"state": "post"}},
            "venue": {"fullName": "Test Stadium"},
            "notes": [],
        }],
    }


def _bad_score_event(event_id, bad_value):
    """A post-game event whose home score is non-numeric (e.g. 'PPD')."""
    event = _good_event(event_id, 2, 1)
    event["competitions"][0]["competitors"][0]["score"] = {"value": bad_value}
    return event


def test_parse_game_raises_valueerror_on_nonnumeric_score():
    """
    LOCKS BUG: int(float("PPD")) at app/espn.py:177 raises ValueError, which is
    NOT caught by the (KeyError, IndexError, TypeError) tuple at app/espn.py:218.
    So _parse_game does NOT gracefully return None — it lets ValueError escape.

    Desired behavior (future fix) would be to return None and skip the event.
    """
    bad = _bad_score_event("500", "PPD")
    with pytest.raises(ValueError):
        espn._parse_game(bad, "soccer", "eng.1")


def test_one_bad_score_empties_whole_scoreboard_batch(monkeypatch):
    """
    LOCKS BUG: because the ValueError escapes _parse_game, it also escapes the
    `for event in data.get("events", [])` loop in fetch_scoreboard (app/espn.py:273).
    The loop aborts mid-iteration, so the two perfectly good games in the same
    response are LOST — the caller gets an exception, not a partial list.

    Mock at the _cached_get boundary per the tests/ no-network convention.
    """
    events = [
        _good_event("1", 3, 0),          # good — parses fine on its own
        _bad_score_event("2", "PPD"),    # malformed — detonates the batch
        _good_event("3", 1, 1),          # good, but never reached
    ]
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **kw: {"events": events})

    # Current behavior: the whole call blows up rather than returning [game1, game3].
    with pytest.raises(ValueError):
        espn.fetch_scoreboard("soccer", "eng.1", "20260415")
