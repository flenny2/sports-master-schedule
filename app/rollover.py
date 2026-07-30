"""
Season-rollover staleness checks.

CLAUDE.md carries a "do every August" checklist of config artifacts that go
stale silently — nothing crashes, the app just quietly shows the wrong thing:
a dead filter chip, last season's title race, a primetime game that vanishes
from the schedule with no error. The only defence was the prose checklist,
and a prose checklist is a thing nobody runs. This module is the thing that
runs.

Every check returns the same shape so `tools/rollover-check` can print them
uniformly and `tools/validate` can summarise them in one line:

    {"item": short name,
     "state": "ok" | "stale" | "needs-you",
     "detail": one plain sentence}

The three states are deliberately different kinds of thing:

  ok         nothing to do.
  stale      MECHANICALLY detected — a date has passed, a value is empty.
             No judgement involved, so a session can act on it.
  needs-you  a judgement only Dylan can make (who is contending this season,
             which networks carry Friday games). The checker's job here is
             to ASK the question at the right time of year, not answer it —
             so these never count as failures.

Pure: every check takes the config module (injected, so tests can pass a
stand-in) and touches no network and no disk beyond one repo grep.
"""

from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

OK = "ok"
STALE = "stale"
NEEDS_YOU = "needs-you"


def _result(item, state, detail):
    return {"item": item, "state": state, "detail": detail}


def check_storylines(cfg, today=None):
    """Storylines carry an `end_date` and `get_active_storylines` drops any
    that have passed — correctly, so an expired one stops shipping a chip.
    Nothing replaces it though, and the Calendar loses its storyline filter
    entirely until a new entry is added. That is the silent part."""
    today = today or date.today()
    entries = [s for s in getattr(cfg, "STORYLINES", []) if s.get("active")]
    if not entries:
        return _result("STORYLINES", STALE,
                       "no active storyline is configured, so the Calendar "
                       "has no storyline filter at all")

    expired = []
    for s in entries:
        end = s.get("end_date")
        if end and date.fromisoformat(end) < today:
            expired.append(f"{s.get('label', s.get('id'))} (ended {end})")

    if len(expired) == len(entries):
        return _result("STORYLINES", STALE,
                       "every active storyline has expired — "
                       + ", ".join(expired)
                       + " — so the Calendar has no storyline filter")
    if expired:
        return _result("STORYLINES", STALE,
                       "expired but still marked active: " + ", ".join(expired))
    return _result("STORYLINES", OK,
                   f"{len(entries)} active, none past its end date")


def check_title_races(cfg):
    """Contenders are hand-picked, so last season's two-horse race persists
    into the new season until somebody edits it. Not detectable — the config
    looks identical whether it is current or a year out of date."""
    races = getattr(cfg, "TITLE_RACES", [])
    if not races:
        return _result("TITLE_RACES", OK, "no title race configured")
    described = "; ".join(
        f"{r.get('label')} → {len(r.get('team_ids', []))} teams"
        for r in races
    )
    return _result("TITLE_RACES", NEEDS_YOU,
                   f"check these are THIS season's contenders: {described}")


def check_primetime_networks(cfg):
    """A game is included if it is primetime by weekday+hour OR airs on a
    network in this set. There is no Friday branch in the weekday logic, so
    a Friday game is included SOLELY via this set — which is why Netflix is
    in it (Christmas 2026 is a Friday). If a rights deal moves and this is
    not updated, those games vanish from the schedule with no error."""
    nets = sorted(getattr(cfg, "NFL_PRIMETIME_NETWORKS", set()))
    return _result("NFL_PRIMETIME_NETWORKS", NEEDS_YOU,
                   "Friday games are included ONLY via this set — re-verify "
                   "against the new slate's rights deals: " + ", ".join(nets))


def check_fantasy_roster(cfg):
    """Empty is correct until the draft, and wrong the moment it happens —
    the YOUR GUYS tag simply never appears and nothing says why."""
    roster = getattr(cfg, "FANTASY_ROSTER", {})
    if roster:
        return _result("FANTASY_ROSTER", OK, f"{len(roster)} players listed")
    return _result("FANTASY_ROSTER", NEEDS_YOU,
                   "empty — fill it after the LPPC draft (late Aug) or NFL "
                   "cards will never show the YOUR GUYS tag")


def check_dead_nba_networks(cfg, repo=None):
    """`NBA_NATIONAL_NETWORKS` is defined and referenced nowhere, and its
    comment claims coverage no code path provides — NBA is unplugged
    entirely. The checklist says "decide, then act"; this at least stops the
    decision from being invisible. Re-greps rather than trusting the note,
    so restoring NBA silently flips this to ok."""
    name = "NBA_NATIONAL_NETWORKS"
    if not hasattr(cfg, name):
        return _result(name, OK, "gone")

    # Application code only — the repo root and app/. A mention in tools/ or
    # tests/ does not make a setting live, and counting one would let this
    # check clear itself the moment somebody wrote a test for the dead value.
    repo = Path(repo) if repo else REPO
    users = []
    for path in list(repo.glob("*.py")) + list((repo / "app").glob("*.py")):
        if path.name in ("config.py", "rollover.py"):
            continue
        if name in path.read_text(encoding="utf-8"):
            users.append(path.name)
    if users:
        return _result(name, OK, "used by " + ", ".join(sorted(users)))
    return _result(name, STALE,
                   "defined but used by nothing, and its comment describes "
                   "regular-season coverage no code path provides — delete "
                   "it or re-wire it deliberately")


CHECKS = (
    check_storylines,
    check_title_races,
    check_primetime_networks,
    check_fantasy_roster,
    check_dead_nba_networks,
)


def run_all(cfg, today=None):
    """Every check, in checklist order. `today` is threaded only into the
    dated one so tests can move the calendar."""
    results = []
    for check in CHECKS:
        if check is check_storylines:
            results.append(check(cfg, today=today))
        else:
            results.append(check(cfg))
    return results


def summary(results):
    """One line of facts, no call to action — the caller adds the pointer,
    because the checker printing "run the checker" reads as a bug."""
    stale = [r["item"] for r in results if r["state"] == STALE]
    asks = [r["item"] for r in results if r["state"] == NEEDS_YOU]
    if not stale and not asks:
        return "ROLLOVER: nothing stale"
    parts = []
    if stale:
        parts.append(f"{len(stale)} STALE ({', '.join(stale)})")
    if asks:
        parts.append(f"{len(asks)} need Dylan ({', '.join(asks)})")
    return "ROLLOVER: " + " · ".join(parts)
