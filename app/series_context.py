"""
Series context tagger — adds postseason series-state info to playoff games.

Sets two fields on each game:
  series_summary (str): short display string for the card. Empty when
                        we don't have series context (non-playoff, NBA
                        play-in, single-leg cup, 1st-leg fallback failed).
  series_detail  (dict|None): structured data for the expanded view.
                              Sport-specific shape — see below.

NBA detail shape:
  {
    "sport":     "basketball",
    "title":     "Playoff Series",
    "best_of":   7,
    "completed": False,
    "summary":   "LAL lead series 2-1",
    "teams":     [{"id": "13", "abbr": "LAL", "wins": 2},
                  {"id": "10", "abbr": "HOU", "wins": 1}],
  }

Soccer two-leg detail shape:
  {
    "sport":     "soccer",
    "round":     "Quarterfinals",
    "leg":       2,
    "first_leg": {            # None when the 1st leg lookup fails
      "home_abbr":  "ATM",
      "away_abbr":  "BAR",
      "home_score": 2,
      "away_score": 1,
      "date":       "2026-04-08T19:00Z",
    },
  }

Must run AFTER tag_playoff — it short-circuits on is_playoff == False.
"""

from datetime import datetime
import pytz

import config
from app.espn import fetch_first_leg


# ── NBA ──────────────────────────────────────────────────────────

def _nba_context(game):
    """Return (summary, detail) for an NBA playoff game."""
    series = game.get("raw_series") or {}
    competitors = series.get("competitors") or []

    # Play-in games come through with season_type 5 and series={}. Skip.
    if not series or not competitors:
        return "", None

    # Map ESPN team IDs to our parsed abbreviations.
    home = game.get("home_team", {}) or {}
    away = game.get("away_team", {}) or {}
    id_to_abbr = {
        str(home.get("id", "")): home.get("abbreviation", ""),
        str(away.get("id", "")): away.get("abbreviation", ""),
    }

    teams = []
    total_wins = 0
    for c in competitors:
        cid = str(c.get("id", ""))
        wins = int(c.get("wins", 0) or 0)
        total_wins += wins
        teams.append({
            "id":   cid,
            "abbr": id_to_abbr.get(cid, ""),
            "wins": wins,
        })

    best_of = int(series.get("totalCompetitions", 0) or 0)
    espn_summary = (series.get("summary") or "").strip()

    # Game 1 pre-game: no wins recorded yet. ESPN's summary is usually
    # empty or odd here — display "Game 1 of N" using the series length.
    if total_wins == 0:
        summary = f"Game 1 of {best_of}" if best_of else "Game 1"
    else:
        # Trust ESPN's pre-formatted summary ("LAL lead series 2-1",
        # "Series tied 1-1", "OKC win series 4-2").
        summary = espn_summary

    detail = {
        "sport":     "basketball",
        "title":     series.get("title", "Playoff Series"),
        "best_of":   best_of,
        "completed": bool(series.get("completed", False)),
        "summary":   summary,
        "teams":     teams,
    }
    return summary, detail


# ── Two-leg soccer ───────────────────────────────────────────────

def _parse_game_date(iso_str):
    """Parse an ISO-8601 UTC timestamp to a local calendar date."""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        tz = pytz.timezone(config.TIMEZONE)
        return dt.astimezone(tz).date()
    except (ValueError, TypeError):
        return None


def _soccer_context(game):
    """Return (summary, detail) for a two-leg soccer knockout game."""
    leg_obj = game.get("raw_leg") or {}
    leg_value = leg_obj.get("value")

    # No leg metadata → single-leg tie (FA Cup, DFB-Pokal, UCL Final, etc.)
    # Short-circuit — the existing playoff_round label already says enough.
    if leg_value not in (1, 2):
        return "", None

    series = game.get("raw_series") or {}
    round_title = (series.get("title") or "").strip()

    # 1st leg — no aggregate to show yet.
    if leg_value == 1:
        detail = {
            "sport":     "soccer",
            "round":     round_title,
            "leg":       1,
            "first_leg": None,
        }
        return "1st Leg", detail

    # 2nd leg — fetch the 1st leg to compute incoming aggregate.
    game_date = _parse_game_date(game.get("date", ""))
    home = game.get("home_team", {}) or {}
    away = game.get("away_team", {}) or {}
    home_id = str(home.get("id", ""))
    away_id = str(away.get("id", ""))
    league = game.get("league", "")

    first_leg = None
    try:
        first_leg = fetch_first_leg(
            league, home_id, away_id, round_title, game_date,
        )
    except Exception as exc:
        # Never let a fallback failure block rendering.
        print(f"[series_context] first-leg fetch raised for "
              f"{game.get('id','')} ({league}, {round_title}): {exc}")

    if first_leg is None:
        # Silent misses are the thing Dylan asked me to log loudly.
        print(f"[series_context] no 1st leg found for game {game.get('id','')} "
              f"({league}, round={round_title!r}, "
              f"teams={home_id}/{away_id}, 2nd-leg-date={game_date})")
        detail = {
            "sport":     "soccer",
            "round":     round_title,
            "leg":       2,
            "first_leg": None,
        }
        return "2nd Leg", detail

    score = first_leg.get("score") or {}
    try:
        home_leg1 = int(score.get("home"))
        away_leg1 = int(score.get("away"))
    except (TypeError, ValueError):
        # 1st leg hasn't been played or the score is unparseable.
        detail = {
            "sport":     "soccer",
            "round":     round_title,
            "leg":       2,
            "first_leg": None,
        }
        return "2nd Leg", detail

    # Home/away flip between legs in every two-leg tie ESPN reports.
    # Whoever was home in leg 1 is away in leg 2. Map leg-1 scores onto
    # leg-2 teams by team id, not by home/away role.
    first_leg_home = (first_leg.get("home_team") or {})
    if str(first_leg_home.get("id", "")) == home_id:
        # Same home team both legs (unusual, but handle it)
        agg_home = home_leg1
        agg_away = away_leg1
    else:
        # Normal case: roles swap between legs
        agg_home = away_leg1   # leg-2 home team was leg-1 away team
        agg_away = home_leg1

    if agg_home > agg_away:
        summary = (
            f"2nd Leg · {home.get('abbreviation','')} "
            f"lead {agg_home}-{agg_away}"
        )
    elif agg_away > agg_home:
        summary = (
            f"2nd Leg · {away.get('abbreviation','')} "
            f"lead {agg_away}-{agg_home}"
        )
    else:
        summary = f"2nd Leg · agg {agg_home}-{agg_away}"

    detail = {
        "sport":     "soccer",
        "round":     round_title,
        "leg":       2,
        "first_leg": {
            "home_abbr":  first_leg_home.get("abbreviation", ""),
            "away_abbr":  (first_leg.get("away_team") or {}).get("abbreviation", ""),
            "home_score": home_leg1,
            "away_score": away_leg1,
            "date":       first_leg.get("date", ""),
        },
    }
    return summary, detail


# ── Entry point ──────────────────────────────────────────────────

def tag_series_context(games):
    """
    Set series_summary and series_detail on each playoff game.

    Non-playoff games get empty string / None (cheap no-op, no API calls).
    Modifies games in place and returns them.
    """
    for game in games:
        game["series_summary"] = ""
        game["series_detail"] = None

        if not game.get("is_playoff"):
            continue

        sport = game.get("sport", "")
        if sport == "basketball":
            summary, detail = _nba_context(game)
        elif sport == "soccer":
            summary, detail = _soccer_context(game)
        else:
            # NFL playoffs: no series concept (single-elimination).
            summary, detail = "", None

        game["series_summary"] = summary
        game["series_detail"] = detail

    return games
