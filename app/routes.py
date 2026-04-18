"""
Flask routes — serves the dashboard page and the schedule API.
"""

import calendar
import os
from datetime import date, timedelta
from flask import (
    Blueprint, render_template, jsonify, request, make_response,
)

from app.espn import get_all_games, get_all_standings, get_title_races, clear_cache
from app.importance import tag_importance
from app.availability import tag_availability
from app.playoff import tag_playoff
from app.userdata import get_all_userdata, set_watched, set_notes

main = Blueprint("main", __name__)

# Optional write-auth token. When SCHEDULE_TOKEN is set, POST endpoints
# require a matching cookie. Read endpoints stay public.
# Flow: user hits /?token=<value> once; the server sets a long-lived
# cookie and redirects. Subsequent POSTs are accepted.
# If the env var isn't set, writes are open (fine for local dev).
_WRITE_TOKEN = os.environ.get("SCHEDULE_TOKEN", "").strip()
_TOKEN_COOKIE = "schedule_token"


def _write_allowed():
    if not _WRITE_TOKEN:
        return True
    return request.cookies.get(_TOKEN_COOKIE) == _WRITE_TOKEN


def _get_week_range(offset=0):
    """
    Get the Monday–Sunday date range for a week.
    offset=0 is this week, offset=1 is next week, offset=-1 is last week.
    """
    today = date.today()
    # Monday of this week
    monday = today - timedelta(days=today.weekday())
    # Apply offset
    monday += timedelta(weeks=offset)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _get_month_range(year, month):
    """
    Get the Monday–Sunday padded display range for a calendar month.
    E.g., April 2026 starts on Wednesday, so we include Mon Mar 30.
    """
    first_day = date(year, month, 1)
    start = first_day - timedelta(days=first_day.weekday())
    _, last_day_num = calendar.monthrange(year, month)
    last_day = date(year, month, last_day_num)
    end = last_day + timedelta(days=(6 - last_day.weekday()))
    return start, end


@main.route("/")
def dashboard():
    """
    Serve the main dashboard page.

    If SCHEDULE_TOKEN is configured and the request carries a matching
    ?token=<value>, remember it in a cookie so future POSTs are
    authenticated without the token in the URL.
    """
    resp = make_response(render_template("index.html"))
    if _WRITE_TOKEN:
        provided = request.args.get("token", "").strip()
        if provided == _WRITE_TOKEN:
            # 1-year, SameSite=Lax, HttpOnly. Secure when served over HTTPS.
            resp.set_cookie(
                _TOKEN_COOKIE, provided,
                max_age=365 * 24 * 3600,
                httponly=False,  # readable by JS (useful for client checks)
                samesite="Lax",
                secure=request.is_secure,
            )
    return resp


@main.route("/api/schedule")
def api_schedule():
    """
    Return games for a given week as JSON.

    Query params:
      week: "this" (default), "next", or "prev"
      refresh: "true" to clear cache and re-fetch
    """
    # Handle cache refresh
    if request.args.get("refresh") == "true":
        clear_cache()

    # Month-based range (e.g. ?month=2026-04) or legacy week param
    month_param = request.args.get("month")
    if month_param:
        try:
            year_str, month_str = month_param.split("-", 1)
            year, month = int(year_str), int(month_str)
            if not (1 <= month <= 12) or not (1900 <= year <= 2999):
                raise ValueError("out of range")
        except (ValueError, IndexError):
            return jsonify({
                "error": "invalid month — use YYYY-MM (e.g. 2026-04)",
            }), 400
        start_date, end_date = _get_month_range(year, month)
    else:
        week_param = request.args.get("week", "this")
        offset = {"prev": -1, "this": 0, "next": 1}.get(week_param, 0)
        start_date, end_date = _get_week_range(offset)

    # Fetch games from ESPN
    games = get_all_games(start_date, end_date)

    # Tag each game with importance tier, availability, and playoff status
    games = tag_importance(games)
    games = tag_availability(games)
    games = tag_playoff(games)

    # Merge in user data (watched flags, notes)
    user_data = get_all_userdata()
    for game in games:
        gid = game.get("id", "")
        ud = user_data.get(gid, {})
        game["watched"] = ud.get("watched", False)
        game["user_notes"] = ud.get("notes", "")

    return jsonify({
        "games": games,
        "range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
    })


@main.route("/api/games/<game_id>/watched", methods=["POST"])
def api_set_watched(game_id):
    """Toggle watched status for a game."""
    if not _write_allowed():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    set_watched(game_id, bool(data.get("watched", False)))
    return jsonify({"ok": True})


@main.route("/api/games/<game_id>/notes", methods=["POST"])
def api_save_notes(game_id):
    """Save user notes for a game."""
    if not _write_allowed():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "")
    if not isinstance(notes, str):
        return jsonify({"error": "notes must be a string"}), 400
    # Keep notes bounded so a misbehaving client can't balloon the JSON file
    set_notes(game_id, notes[:2000])
    return jsonify({"ok": True})


@main.route("/api/standings")
def api_standings():
    """
    Return current standings for all tracked leagues.
    """
    if request.args.get("refresh") == "true":
        clear_cache()

    standings = get_all_standings()
    title_races = get_title_races()
    return jsonify({"leagues": standings, "title_races": title_races})
