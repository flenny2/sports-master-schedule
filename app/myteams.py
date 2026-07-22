"""
"Your Teams" strip — the Front Page glance at Dylan's own teams.

Brief §D8 deselected this for v1 at the Jul-17 interview; built Jul-22.
Every config.WATCHED_TEAMS entry flagged `favorite` gets one compact card:
the next fixture with a countdown, the last result, and the league
position.

Two things are worth knowing before editing this file.

1. Assembly lives here, not in app.js, so the fiddly parts — sport-scoped
   id matching, picking last/next out of a mixed schedule, refusing to
   print a pre-season table position — are plain functions the pytest
   suite can pin. The frontend only renders what these return.

2. The ESPN team-schedule endpoint is SPORT-SPLIT, which the top-level
   "only returns past games" gotcha only half-captures. Probed Jul-22:
     football/nfl  → the whole upcoming season (17 events, all `pre`)
     soccer/*      → finished matches only
   So NFL cards get their NEXT row straight from the schedule, and soccer
   cards fall back to fetch_upcoming_fixtures(), which scans the league
   calendar instead.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import pytz

import config
from app.espn import (
    _MAX_WORKERS,
    fetch_team_schedule,
    fetch_upcoming_fixtures,
    get_all_standings,
)

# ESPN game dates look like "2026-09-13T17:00Z". Building "now" in the
# same shape lets us compare them as plain strings — ISO-8601 UTC sorts
# lexicographically, so no parsing is needed just to ask "has this
# kicked off yet?".
_NOW_FORMAT = "%Y-%m-%dT%H:%MZ"


def _utc_now():
    return datetime.now(pytz.utc).strftime(_NOW_FORMAT)


def get_favorite_teams():
    """Config entries flagged `favorite` — see the note above WATCHED_TEAMS."""
    return [t for t in getattr(config, "WATCHED_TEAMS", []) or []
            if t.get("favorite")]


# ── Pure helpers ──────────────────────────────────────────────────

def _team_side(game, team):
    """
    Which side of this game the team is on: "home", "away", or None.

    Checks sport BEFORE comparing ids. ESPN team ids are unique only
    within a sport — the Steelers are "23" in the NFL and "23" is also a
    valid soccer id — so an unscoped comparison would hand a club's
    fixtures to an NFL card. fetch_standings scopes its watched-row
    highlight the same way.
    """
    if game.get("sport") != team.get("sport"):
        return None
    team_id = team.get("espn_id")
    if (game.get("home_team") or {}).get("id") == team_id:
        return "home"
    if (game.get("away_team") or {}).get("id") == team_id:
        return "away"
    return None


def _score_int(raw):
    """Scores arrive as ints from the NFL and floats ("2.0") from soccer."""
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _fixture(game, side):
    """The shared shape for a fixture row (used by both NEXT and LAST)."""
    opponent = game["away_team"] if side == "home" else game["home_team"]
    return {
        "opponent": opponent.get("abbreviation", "???"),
        "opponent_name": opponent.get("name", ""),
        "home": side == "home",
        "date": game.get("date", ""),
        "league_name": game.get("league_name", ""),
    }


def _result(game, side):
    """
    The LAST row: outcome + score, or None when the game has no scores.

    `note` carries ESPN's tie-breaker text ("Paris Saint-Germain win 4-3
    on penalties"). Without it a drawn cup final would render as a bare
    "D 1-1", which reads as a result that never happened.
    """
    score = game.get("score") or {}
    own = _score_int(score.get(side))
    other = _score_int(score.get("away" if side == "home" else "home"))
    if own is None or other is None:
        return None

    row = _fixture(game, side)
    row["outcome"] = "W" if own > other else ("L" if own < other else "D")
    row["score"] = f"{own}-{other}"
    row["note"] = (game.get("notes") or "")[:120]
    return row


def _pick_last_next(games, team, now_iso):
    """
    Latest finished game and earliest upcoming one, from a mixed list.

    Returns two (date, game, side) tuples, either of which may be None.
    An upcoming game must be at or after `now_iso`: ESPN occasionally
    leaves an old fixture stuck in `pre`, and without the check one of
    those would headline the card forever.
    """
    last = None
    nxt = None
    for game in games:
        side = _team_side(game, team)
        if side is None:
            continue
        when = game.get("date", "")
        status = game.get("status")
        if status == "post":
            if last is None or when > last[0]:
                last = (when, game, side)
        elif status == "pre" and when >= now_iso:
            if nxt is None or when < nxt[0]:
                nxt = (when, game, side)
    return last, nxt


def _standings_entry(standings, team):
    """
    (league, group, entry) for this team's standings row, or three Nones.

    Walks the team's OWN league list in config order, so a club with both
    a domestic and a European table resolves to the domestic one — City
    should read "Premier League 3rd", not a Champions League group place.
    """
    by_id = {lg.get("id"): lg for lg in (standings or [])}
    for slug in team.get("leagues", []) or []:
        league = by_id.get(slug)
        if not league or league.get("sport") != team.get("sport"):
            continue
        for group in league.get("groups", []):
            for entry in group.get("teams", []):
                if (entry.get("team") or {}).get("id") == team.get("espn_id"):
                    return league, group, entry
    return None, None, None


def _games_played(sport, stats):
    """How many games the table credits this team with."""
    if sport == "soccer":
        return _score_int(stats.get("gp")) or 0
    return sum(_score_int(stats.get(key)) or 0 for key in ("w", "l", "t"))


def _record_string(sport, stats):
    """Matches the mini-table convention: points for soccer, W-L(-T) else."""
    if sport == "soccer":
        return f"{stats.get('pts', '0')} pts"
    record = f"{stats.get('w', '0')}-{stats.get('l', '0')}"
    if stats.get("t") and stats["t"] != "0":
        record += f"-{stats['t']}"
    return record


def _standing_row(standings, team):
    """
    The team's table position — or None before the season starts.

    ESPN zeroes every stat in the off-season and then sorts the table
    ALPHABETICALLY. Probed Jul-22: the Premier League read Bournemouth
    1st and Arsenal 2nd on 0 points, and every NFL team sat at rank 0.
    Rendering that would state a standing that doesn't exist yet, so a
    table showing 0 games played earns no row at all.
    """
    league, group, entry = _standings_entry(standings, team)
    if entry is None:
        return None

    stats = entry.get("stats", {}) or {}
    if _games_played(team.get("sport"), stats) == 0:
        return None

    return {
        "league_name": league.get("name", ""),
        "group": group.get("name", ""),
        "rank": entry.get("rank", ""),
        "record": _record_string(team.get("sport"), stats),
        "zone": entry.get("zone", ""),
    }


def _identity(team, games, standings):
    """
    Crest, abbreviation and kit colors — none of which live in config.

    Standings carry a crest year-round (including the off-season, when
    there are no games to read one from); games carry the kit colors.
    Take whichever source has each piece.

    In practice `color` comes back empty today: the team-schedule endpoint
    strips `color`/`alternateColor` from its competitors (probed Jul-22 —
    the same trimming that already costs us `series`/`leg`/`notes` there),
    and standings never carried them. The frontend's seamColor() falls
    back to the sport palette, so the card still gets an accent. The
    harvest stays because a scoreboard-shaped game would populate it.
    """
    out = {"abbr": "", "logo": "", "color": "", "alt_color": ""}

    _league, _group, entry = _standings_entry(standings, team)
    if entry:
        info = entry.get("team") or {}
        out["abbr"] = info.get("abbr", "")
        out["logo"] = info.get("logo", "")

    for game in games:
        side = _team_side(game, team)
        if side is None:
            continue
        info = game.get(f"{side}_team") or {}
        out["abbr"] = out["abbr"] or info.get("abbreviation", "")
        out["logo"] = out["logo"] or info.get("logo", "")
        if info.get("color"):
            out["color"] = info["color"]
            out["alt_color"] = info.get("alt_color", "")
            break

    return out


def build_team_card(team, games, standings, fallback_fixtures=None,
                    now_iso=None):
    """
    Assemble one strip card. Pure: every input is passed in, so tests
    exercise the whole shape without touching the network.
    """
    now_iso = now_iso or _utc_now()
    last, nxt = _pick_last_next(games, team, now_iso)
    identity = _identity(team, games, standings)

    card = {
        "name": team.get("name", ""),
        "sport": team.get("sport", ""),
        "abbr": identity["abbr"],
        "logo": identity["logo"],
        "color": identity["color"],
        "alt_color": identity["alt_color"],
        "next": None,
        "last": None,
        "standing": _standing_row(standings, team),
    }

    if last:
        card["last"] = _result(last[1], last[2])
    if nxt:
        card["next"] = _fixture(nxt[1], nxt[2])
    elif fallback_fixtures:
        card["next"] = dict(fallback_fixtures[0])

    return card


# ── Fetch + assemble ──────────────────────────────────────────────

def _soccer_fallback(team, games, now_iso, league_names):
    """
    Upcoming soccer fixtures, for when the team schedule has none.

    Only soccer needs this (see the module docstring): the NFL schedule
    already carries the season ahead. fetch_upcoming_fixtures scans the
    league calendar, and get_title_races() already calls it for the PL
    contenders, so it is usually served from cache.
    """
    if team.get("sport") != "soccer":
        return []
    has_upcoming = any(
        _team_side(g, team) and g.get("status") == "pre"
        and g.get("date", "") >= now_iso
        for g in games
    )
    if has_upcoming:
        return []

    slug = (team.get("leagues") or [None])[0]
    if not slug:
        return []

    fixtures = fetch_upcoming_fixtures(slug, team["espn_id"])
    for fixture in fixtures:
        # The calendar scan knows the league slug but not its pretty
        # name; the standings payload we already hold does.
        fixture["league_name"] = league_names.get(slug, "")
    return fixtures


def get_my_teams():
    """
    Fetch and assemble the strip. The only function here that touches the
    network — everything above it is pure.

    Cost is one team-schedule call per (team, league) pair, run in
    parallel. Those are the same calls fetch_soccer_games' pass 1 makes,
    so on a warm cache the strip adds roughly one request (the NFL team's
    schedule) to a normal page load.
    """
    teams = get_favorite_teams()
    if not teams:
        return []

    standings = get_all_standings()
    league_names = {lg.get("id"): lg.get("name", "") for lg in standings}

    pairs = [
        (team, league)
        for team in teams
        for league in team.get("leagues", []) or []
    ]
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        schedules = list(executor.map(
            lambda pair: fetch_team_schedule(
                pair[0]["sport"], pair[1], pair[0]["espn_id"]),
            pairs,
        ))

    games_by_team = {}
    for (team, _league), games in zip(pairs, schedules):
        games_by_team.setdefault(team["espn_id"], []).extend(games)

    now_iso = _utc_now()
    cards = []
    for team in teams:
        games = games_by_team.get(team["espn_id"], [])
        fallback = _soccer_fallback(team, games, now_iso, league_names)
        cards.append(
            build_team_card(team, games, standings, fallback, now_iso)
        )
    return cards
