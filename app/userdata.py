"""
User data persistence — watched flags and personal notes per game.
Stored as a simple JSON file in data/userdata.json.
"""

import json
import os

DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "userdata.json"
)


def _load():
    """Read the user data file, or return empty dict if it doesn't exist."""
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def _save(data):
    """Write user data to disk."""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_all_userdata():
    """Return all user data (watched flags + notes), keyed by game ID."""
    return _load()


def set_watched(game_id, watched):
    """Set or clear the watched flag for a game."""
    data = _load()
    if game_id not in data:
        data[game_id] = {}
    data[game_id]["watched"] = watched
    _save(data)


def set_notes(game_id, notes):
    """Save user notes for a game."""
    data = _load()
    if game_id not in data:
        data[game_id] = {}
    data[game_id]["notes"] = notes
    _save(data)
