"""
CHARACTERIZATION tests for the standings fragility tracked as H1
(meta-fable-supervisor/reports/sms-code-review.md, seed S3, 2026-07-07).

These tests LOCK CURRENT BEHAVIOR — they are NOT assertions about desired
behavior. Every assertion here documents a way `/api/standings` can 500 when
ESPN's payload omits a stat, which is likely this offseason (ESPN thins out
standings stats between seasons).

When someone adds the guard that fixes H1, these tests are EXPECTED to fail.
That failure is the signal the guard worked. Update them then — do not treat a
failure here as a regression.

No network, no Flask app: `_stat_val` is pure, and the one test that exercises
`fetch_standings` stubs `_cached_get` via monkeypatch.
"""

from app import espn


# ── (a) The dangerous default ─────────────────────────────────────

def test_stat_val_returns_empty_string_when_stat_has_no_value():
    """
    A stats item that matches by name but carries neither `displayValue` nor
    `value` falls through to the default — `""`, not 0 and not None.

    See app/espn.py:580-585. The `""` default is the root of H1: every caller
    that wraps this in int() inherits a ValueError.
    """
    assert espn._stat_val([{"name": "points"}], "points") == ""


def test_stat_val_returns_empty_string_when_stat_is_absent():
    """A name that appears nowhere in the stats array also yields `""`."""
    assert espn._stat_val([{"name": "wins", "value": 3}], "points") == ""


# ── (b) The ValueError that reaches the route ─────────────────────

def test_int_of_missing_points_raises_value_error():
    """
    The crash itself. `get_title_races` (app/espn.py:771-772) does:

        pts = int(t["stats"].get("pts", 0))
        gp  = int(t["stats"].get("gp", 0))

    NOTE — the task spec for this characterization cited espn.py:752-753 and
    described `int(_stat_val(...))` called directly. That is not what the code
    does; the real call site is 771-772 and it reads a pre-built dict. The
    ValueError is real, but it arrives by the indirect path pinned in
    `test_get_title_races_dict_default_is_dead_code` below. Trust that test
    over the spec's line numbers.
    """
    try:
        int(espn._stat_val([], "points", ""))
    except ValueError:
        pass  # expected today; a guard would make this not raise
    else:
        raise AssertionError("expected int('') to raise ValueError")


# ── (c) The KeyError on a malformed stats item ────────────────────

def test_stat_val_raises_key_error_on_stat_item_without_name():
    """
    `_stat_val` indexes `s["name"]` directly (app/espn.py:583) rather than
    using `.get("name")`, so a single malformed item anywhere in the array
    raises KeyError — even if the stat being looked up appears later.
    """
    stats = [{"displayValue": "42"}, {"name": "points", "displayValue": "42"}]
    try:
        espn._stat_val(stats, "points")
    except KeyError:
        pass  # expected today
    else:
        raise AssertionError("expected KeyError on a stats item missing 'name'")


# ── The indirect path: why the existing default doesn't save us ───

def test_get_title_races_dict_default_is_dead_code(monkeypatch):
    """
    THE LOAD-BEARING ONE. Explains why the `0` default in
    `int(t["stats"].get("pts", 0))` (app/espn.py:771) cannot prevent H1.

    `fetch_standings` builds the stats dict unconditionally (app/espn.py:627):

        "pts": _stat_val(raw_stats, "points"),

    So the "pts" KEY IS ALWAYS PRESENT — set to `""` when ESPN omits the stat.
    `.get("pts", 0)` therefore never returns its `0` fallback; it returns `""`,
    and int("") raises. The default reads like a guard but is dead code.

    A future fix must coerce the VALUE (e.g. in `_stat_val`, or via an
    int-with-fallback helper at the call site). Adding or changing a dict
    default at 771-772 is a no-op — that is the rejected alternative this test
    exists to rule out.
    """
    payload = {
        "name": "Test League",
        "children": [{
            "name": "Group A",
            "standings": {"entries": [{
                "team": {"id": "999", "displayName": "Ghost FC",
                         "abbreviation": "GHO"},
                # ESPN handed us a team with no points/gamesPlayed stats —
                # the offseason shape this whole file is about.
                "stats": [{"name": "rank", "displayValue": "1"}],
            }]},
        }],
    }
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **kw: payload)
    espn.clear_cache()

    standing = espn.fetch_standings("soccer", "eng.1")
    stats = standing["groups"][0]["teams"][0]["stats"]

    # The key exists, so `.get("pts", 0)` returns "" — never the 0 default.
    assert "pts" in stats
    assert stats["pts"] == ""
    assert stats["gp"] == ""
    assert stats.get("pts", 0) == ""  # the dead default, demonstrated

    # ...and that "" is what get_title_races feeds to int().
    try:
        int(stats.get("pts", 0))
    except ValueError:
        pass  # expected today: this is the 500 on /api/standings
    else:
        raise AssertionError("expected int('') to raise ValueError")


def test_rank_is_guarded_twice_while_points_is_guarded_not_at_all(monkeypatch):
    """
    Contrast case — the guard idiom already exists in this file, and `rank`
    gets it TWICE while `pts`/`gp` get it zero times.

    rank (app/espn.py:640 and :666):
        rank = _stat_val(raw_stats, "rank", "0")        # explicit "0" default
        ... int(t["rank"]) if str(t["rank"]).isdigit()  # AND an isdigit check

    pts  (app/espn.py:627):
        "pts": _stat_val(raw_stats, "points"),          # bare "" default
        ... int(t["stats"].get("pts", 0))               # no value check (:771)

    So rank degrades to "0" and sorts fine; pts degrades to "" and raises. The
    author clearly knew to override the "" default on the field they were about
    to int() — that instinct just never reached the soccer stats block. A fix
    for H1 should follow the rank precedent (explicit default at the _stat_val
    call site) rather than invent a new pattern.
    """
    payload = {
        "name": "Test League",
        "children": [{
            "name": "Group A",
            "standings": {"entries": [{
                "team": {"id": "999", "displayName": "Ghost FC",
                         "abbreviation": "GHO"},
                "stats": [],  # no rank at all
            }]},
        }],
    }
    monkeypatch.setattr(espn, "_cached_get", lambda *a, **kw: payload)
    espn.clear_cache()

    # Does not raise: rank falls back to the explicit "0" default, and the
    # isdigit() sort guard would have absorbed a non-numeric value anyway.
    standing = espn.fetch_standings("soccer", "eng.1")
    team = standing["groups"][0]["teams"][0]
    assert team["rank"] == "0"      # explicit default, NOT the bare ""
    assert int(team["rank"]) == 0   # int() is safe here, unlike on "pts"

    # Same entry, same missing-stats payload — pts is the one that raises.
    assert team["stats"]["pts"] == ""
