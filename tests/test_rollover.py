"""
Tests for the season-rollover staleness checks (app/rollover.py).

What these pin is the DISTINCTION the module exists to make: "stale" means a
date has passed or a value is empty, so a session can act on it without
asking; "needs-you" means a judgement only Dylan can make, and the checker's
whole job there is to ask the question at the right time of year rather than
answer it. Blur those two and the output becomes a nag list, which is how the
prose checklist in CLAUDE.md ended up unread for two months.

Every check takes the config module injected, so these pass stand-ins and
touch neither the real config nor the network.
"""

from datetime import date

import pytest

from app import rollover


class Cfg:
    """A stand-in config. Only the attributes a check reads need to exist —
    the checks use getattr with defaults, which is also what makes them
    survive someone deleting a setting outright."""

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


TODAY = date(2026, 7, 27)


def storyline(sid, end=None, active=True, label=None):
    s = {"id": sid, "active": active, "label": label or sid}
    if end:
        s["end_date"] = end
    return s


# ── Storylines: the one that is actually stale today ──────────────

def test_expired_storyline_is_stale_and_says_why_it_matters():
    r = rollover.check_storylines(
        Cfg(STORYLINES=[storyline("pl", end="2026-05-31", label="PL Title Race")]),
        today=TODAY)
    assert r["state"] == rollover.STALE
    # The consequence, not just the fact — an expired storyline stops
    # shipping a chip correctly, and nothing replaces it.
    assert "no storyline filter" in r["detail"]
    assert "2026-05-31" in r["detail"]


def test_no_storylines_at_all_is_stale_too():
    r = rollover.check_storylines(Cfg(STORYLINES=[]), today=TODAY)
    assert r["state"] == rollover.STALE


def test_inactive_entries_do_not_count_as_cover():
    """`active: False` is the documented way to hide one without deleting
    it, so a config holding only inactive entries has no live storyline."""
    r = rollover.check_storylines(
        Cfg(STORYLINES=[storyline("old", end="2027-05-31", active=False)]),
        today=TODAY)
    assert r["state"] == rollover.STALE


def test_a_live_storyline_is_ok():
    r = rollover.check_storylines(
        Cfg(STORYLINES=[storyline("pl2627", end="2027-05-31")]), today=TODAY)
    assert r["state"] == rollover.OK


def test_a_storyline_with_no_end_date_never_expires():
    """`end_date` is optional in the schema; absent means open-ended."""
    r = rollover.check_storylines(
        Cfg(STORYLINES=[storyline("forever")]), today=TODAY)
    assert r["state"] == rollover.OK


def test_one_expired_among_several_is_still_reported():
    r = rollover.check_storylines(Cfg(STORYLINES=[
        storyline("live", end="2027-05-31"),
        storyline("dead", end="2026-01-01", label="Old Race"),
    ]), today=TODAY)
    assert r["state"] == rollover.STALE
    assert "Old Race" in r["detail"]


# ── The judgement calls stay judgement calls ──────────────────────

def test_title_races_never_reports_stale():
    """A year-out-of-date contender list is indistinguishable from a current
    one, so claiming to detect it would be a lie. It asks instead."""
    r = rollover.check_title_races(Cfg(TITLE_RACES=[
        {"league": "eng.1", "label": "Premier League Title Race",
         "team_ids": ["359", "382"]},
    ]))
    assert r["state"] == rollover.NEEDS_YOU
    assert "Premier League Title Race" in r["detail"]


def test_no_title_race_configured_is_fine():
    r = rollover.check_title_races(Cfg(TITLE_RACES=[]))
    assert r["state"] == rollover.OK


def test_primetime_networks_names_the_friday_trap():
    """There is no Friday branch in the weekday logic, so a Friday game is
    included SOLELY via this set — the reason Netflix is in it."""
    r = rollover.check_primetime_networks(
        Cfg(NFL_PRIMETIME_NETWORKS={"NBC", "Netflix"}))
    assert r["state"] == rollover.NEEDS_YOU
    assert "Friday" in r["detail"]
    assert "Netflix" in r["detail"]


def test_empty_fantasy_roster_asks_rather_than_scolds():
    """Empty is correct until the draft, so this is never 'stale'."""
    r = rollover.check_fantasy_roster(Cfg(FANTASY_ROSTER={}))
    assert r["state"] == rollover.NEEDS_YOU


def test_filled_fantasy_roster_is_ok():
    r = rollover.check_fantasy_roster(Cfg(FANTASY_ROSTER={"Josh Jacobs": "GB"}))
    assert r["state"] == rollover.OK


# ── Dead code: re-grepped, not remembered ─────────────────────────

def test_unused_nba_networks_is_stale(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "espn.py").write_text("# nothing here\n")
    r = rollover.check_dead_nba_networks(
        Cfg(NBA_NATIONAL_NETWORKS={"ESPN"}), repo=tmp_path)
    assert r["state"] == rollover.STALE


def test_restoring_nba_flips_it_to_ok_by_itself(tmp_path):
    """The check re-greps rather than trusting a note, so wiring NBA back up
    clears it with no edit here — the failure mode of a hand-maintained
    'known dead code' list is that it outlives the deadness."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "espn.py").write_text(
        "from config import NBA_NATIONAL_NETWORKS\n")
    r = rollover.check_dead_nba_networks(
        Cfg(NBA_NATIONAL_NETWORKS={"ESPN"}), repo=tmp_path)
    assert r["state"] == rollover.OK
    assert "espn.py" in r["detail"]


def test_deleting_the_setting_clears_it(tmp_path):
    (tmp_path / "app").mkdir()
    r = rollover.check_dead_nba_networks(Cfg(), repo=tmp_path)
    assert r["state"] == rollover.OK


# ── The summary line tools/validate prints ────────────────────────

def test_summary_separates_what_a_session_can_fix_from_what_dylan_must():
    results = [
        {"item": "A", "state": rollover.STALE, "detail": ""},
        {"item": "B", "state": rollover.NEEDS_YOU, "detail": ""},
        {"item": "C", "state": rollover.OK, "detail": ""},
    ]
    line = rollover.summary(results)
    assert "1 STALE (A)" in line
    assert "1 need Dylan (B)" in line
    assert "C" not in line


def test_summary_is_quiet_when_there_is_nothing_to_say():
    assert rollover.summary(
        [{"item": "A", "state": rollover.OK, "detail": ""}]
    ) == "ROLLOVER: nothing stale"


def test_summary_carries_no_call_to_action():
    """The pointer belongs to the caller: the checker printing 'run the
    checker' at the bottom of its own output reads as a bug."""
    assert "rollover-check" not in rollover.summary([
        {"item": "A", "state": rollover.STALE, "detail": ""}])


# ── The real config, as it stands ─────────────────────────────────

def test_run_all_covers_every_checklist_item():
    import config
    results = rollover.run_all(config)
    assert len(results) == len(rollover.CHECKS)
    assert {r["state"] for r in results} <= {
        rollover.OK, rollover.STALE, rollover.NEEDS_YOU}
    for r in results:
        assert r["detail"], f"{r['item']} reported nothing useful"


@pytest.mark.parametrize("check", rollover.CHECKS)
def test_every_check_survives_a_config_missing_that_setting(check):
    """Checks read through getattr with defaults on purpose — a rollover
    reporter that crashes because somebody deleted a setting is worse than
    no reporter."""
    r = check(Cfg()) if check is not rollover.check_storylines \
        else check(Cfg(), today=TODAY)
    assert r["state"] in (rollover.OK, rollover.STALE, rollover.NEEDS_YOU)
