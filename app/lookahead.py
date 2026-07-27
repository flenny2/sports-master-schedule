"""
Next-fixture lookahead for the Front Page.

The problem this solves, found by screenshotting the running app on a
390px viewport on 2026-07-26:

    Today's Slate → "No games in this window — browse the calendar."

That line is the LAST resort in `renderFrontPage`, reached only when the
"next up" fallback finds nothing. It was reached because the Front Page
builds from `/api/schedule?month=...`, which returns one padded month —
and the padded July 2026 range (Jun 29 → Aug 2) holds no game after the
World Cup final on Jul 19. The next real fixture is Aug 7, one day past
the end of the window, so the page had the answer just out of reach and
degraded to a dead sentence instead. Between seasons that is what Dylan
sees on the front page every day for weeks.

So `/api/schedule` now scans forward when, and only when, its own window
has nothing left, and returns the single next fixture as `next_upcoming`.

The functions here are PURE — they take games and dates and return games
and dates, and never touch the network. The ESPN fetch is injected by the
caller. That is the same shape as `app/myteams.py` and for the same
reason: it makes the interesting logic reachable from pytest without a
network stub.
"""

from datetime import timedelta

# How far past the end of the loaded window to look, in days. 45 covers
# the longest real gap in Dylan's calendar -- the ~5 weeks between a
# World Cup final and the NFL opener -- without turning one quiet request
# into an unbounded crawl. If nothing turns up inside 45 days the Front
# Page keeps its existing "browse the calendar" line, which is honest.
LOOKAHEAD_DAYS = 45


def find_next_upcoming(games, now_iso):
    """
    The earliest game in `games` that has not started yet, or None.

    "Not started" means status `pre` AND a kickoff strictly after
    `now_iso`. Both conditions are load-bearing: ESPN leaves a game at
    `pre` for a while after kickoff on quiet feeds, and a game that has
    gone `in` or `post` is not something to advertise as next up.

    `now_iso` and every game date are UTC ISO-8601 strings, so plain
    string comparison is chronological -- no parsing, no timezone.
    """
    upcoming = [
        g for g in games
        if g.get("status") == "pre" and (g.get("date") or "") > now_iso
    ]
    if not upcoming:
        return None
    return min(upcoming, key=lambda g: g["date"])


def lookahead_range(window_end, days=LOOKAHEAD_DAYS):
    """
    The (start, end) dates to scan after a window that ended `window_end`.

    Starts the day AFTER the window ends so the scan never re-fetches a
    day the caller already has.
    """
    start = window_end + timedelta(days=1)
    return start, start + timedelta(days=days - 1)


def next_game_beyond_window(games, window_end, now_iso, fetch_games):
    """
    The next fixture that lies OUTSIDE the loaded window, or None.

    Returns None whenever `games` still holds an upcoming fixture of its
    own — the caller already has that one, and handing it back would put
    a duplicate in the response for the Front Page to prefer over
    nothing. So the returned value means exactly one thing: "here is a
    fixture your window does not contain". In an ordinary week this
    returns None without fetching anything.

    `fetch_games` is injected rather than imported so this module stays
    pure and testable; the route passes `get_all_games`.
    """
    if find_next_upcoming(games, now_iso) is not None:
        return None

    start, end = lookahead_range(window_end)
    try:
        ahead = fetch_games(start, end)
    except Exception:
        # A quiet front page is a cosmetic loss; a 500 is not. The Front
        # Page already renders correctly when this returns None, so an
        # ESPN wobble degrades to the old behaviour instead of an error.
        return None
    return find_next_upcoming(ahead or [], now_iso)
