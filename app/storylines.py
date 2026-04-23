"""
Storylines tagger — tags games with narrative tags for the schedule filter.

Each storyline is configured in config.STORYLINES. A game matches when:
  - the storyline is active
  - at least one of the game's teams is in storyline["team_ids"]
  - if leagues is set, the game's league is in that list
  - if a date window is set, the game's local date is inside it
"""

from datetime import datetime
import pytz

import config


def _game_local_date(game, tz):
    """Return the game's local calendar date, or None if unparseable."""
    try:
        dt = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
        return dt.astimezone(tz).date()
    except (ValueError, KeyError, AttributeError):
        return None


def _parse_iso_date(s):
    """Parse a 'YYYY-MM-DD' string, or return None."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _matches(storyline, game, tz):
    """Return True if this game belongs to this storyline."""
    if not storyline.get("active", True):
        return False

    # League filter — skip unless the game's league is allowed
    leagues = storyline.get("leagues")
    if leagues and game.get("league") not in leagues:
        return False

    # Team filter — at least one listed team must be playing
    team_ids = set(storyline.get("team_ids") or [])
    if not team_ids:
        return False
    home_id = game.get("home_team", {}).get("id", "")
    away_id = game.get("away_team", {}).get("id", "")
    if home_id not in team_ids and away_id not in team_ids:
        return False

    # Date window filter — only applied if start or end is set
    start = _parse_iso_date(storyline.get("start_date"))
    end = _parse_iso_date(storyline.get("end_date"))
    if start or end:
        game_day = _game_local_date(game, tz)
        if game_day is None:
            return False
        if start and game_day < start:
            return False
        if end and game_day > end:
            return False

    return True


def tag_storylines(games):
    """
    Set `storylines` on each game: a list of {"id", "label"} dicts,
    one per matched storyline. Games matching none get an empty list.
    Modifies games in place and returns them.
    """
    tz = pytz.timezone(config.TIMEZONE)
    storylines = getattr(config, "STORYLINES", []) or []
    for game in games:
        matched = []
        for sl in storylines:
            if _matches(sl, game, tz):
                matched.append({"id": sl["id"], "label": sl["label"]})
        game["storylines"] = matched
    return games


def get_active_storylines():
    """Return active storylines in the shape the frontend needs."""
    out = []
    for sl in getattr(config, "STORYLINES", []) or []:
        if not sl.get("active", True):
            continue
        out.append({
            "id": sl["id"],
            "label": sl["label"],
            "description": sl.get("description", ""),
        })
    return out
