"""
Flask routes — serves the dashboard page and the schedule API.
"""

import calendar
from datetime import date, timedelta
from flask import Blueprint, render_template, jsonify, request

from app.espn import get_all_games, get_all_standings, get_title_races, clear_cache
from app.importance import tag_importance
from app.availability import tag_availability
from app.playoff import tag_playoff
from app.userdata import get_all_userdata, set_watched, set_notes

main = Blueprint("main", __name__)


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
    """Serve the main dashboard page."""
    return render_template("index.html")


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
        parts = month_param.split("-")
        year, month = int(parts[0]), int(parts[1])
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
    data = request.get_json()
    set_watched(game_id, data.get("watched", False))
    return jsonify({"ok": True})


@main.route("/api/games/<game_id>/notes", methods=["POST"])
def api_save_notes(game_id):
    """Save user notes for a game."""
    data = request.get_json()
    set_notes(game_id, data.get("notes", ""))
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
