# Test findings — locked-but-unfixed bugs

This file records bugs that have been **characterized** (locked with a test that asserts
current behavior) but **not yet fixed**. Each entry is the input spec for a future
supervised fix: the linked characterization test is red-to-green bait — it passes today
against the buggy code and is expected to fail once the fix lands, at which point the test
should be rewritten to assert the corrected behavior.

---

## 1. Parse bomb: one malformed score empties an entire sport's batch

- **Status:** locked, NOT fixed (fix is a separate supervised task)
- **Severity:** high — a single postponed/abandoned game silently blanks a whole sport in
  the Calendar/Playoffs views
- **Characterization test:** `tests/test_espn_parse_bomb.py`
- **Source of finding:** `meta-fable-supervisor/reports/fable-review-sports-schedule.md`
  §2 (parse-bomb table row) and §5.3

### What happens

`_parse_game` (`app/espn.py:107`) wraps its whole body in:

```python
except (KeyError, IndexError, TypeError) as e:   # app/espn.py:218
    print(f"[ESPN] Failed to parse event: {e}")
    return None
```

The intent of that guard is "if one event is malformed, return `None` and skip it, but keep
parsing the rest of the batch." It works for the error types listed.

But the score-cleanup cast:

```python
score = {
    "home": str(int(float(home_score))),   # app/espn.py:177
    "away": str(int(float(away_score))),   # app/espn.py:178
}
```

raises **`ValueError`** when a score is non-numeric — e.g. ESPN returns `"PPD"` (postponed),
`"—"`, or any other placeholder in the `score.value` field for a game that entered an
`"in"`/`"post"` status without a real number. `ValueError` is **not** in the except tuple at
line 218, so it is not caught here.

### Why it empties the whole sport

`_parse_game` is called inside a bare loop in the fetch functions, e.g.:

```python
for event in data.get("events", []):      # app/espn.py:273 (fetch_scoreboard)
    game = _parse_game(event, sport, league_slug)
    if game:
        games.append(game)
```

(Same pattern in `fetch_team_schedule` at `app/espn.py:252`.)

Because the `ValueError` escapes `_parse_game` instead of returning `None`, it propagates up
through this `for` loop and aborts it mid-iteration. Every game already appended is
discarded and the caller receives an **exception, not a list**. Since one scoreboard
response covers a whole league/date-range in a single call (see CLAUDE.md, "Scoreboard
accepts `dates=YYYYMMDD-YYYYMMDD`"), a single bad score wipes out every game in that
window — the sport looks empty in the UI.

### Exact references

| What | Location |
|------|----------|
| Cast that raises `ValueError` | `app/espn.py:177` (and `:178`) |
| Except tuple missing `ValueError` | `app/espn.py:218` |
| Loop that aborts (scoreboard) | `app/espn.py:273` |
| Loop that aborts (team schedule) | `app/espn.py:252` |

### Recommended fix (for the future supervised task — NOT done here)

Either is sufficient; both is belt-and-suspenders:

1. Add `ValueError` to the except tuple at `app/espn.py:218` — one malformed event returns
   `None` and is skipped, the rest of the batch survives. Simplest, matches existing intent.
2. Guard the cast at `app/espn.py:177` — only cast when the value is numeric; otherwise
   leave `score = None` (treat as "no score yet"). More targeted, keeps the game visible
   without a score.

When the fix lands, `tests/test_espn_parse_bomb.py` will start failing (the `pytest.raises`
assertions no longer hold). Rewrite it then to assert the fixed behavior: the malformed
event is dropped and the good games in the same batch are still returned.
