"""
User data persistence — watched flags and personal notes per game.
Stored as a simple JSON file under DATA_DIR/userdata.json.

The data directory is configurable via the DATA_DIR env var so the
same code works both for local dev (./data) and for a production host
with a persistent disk mounted elsewhere (e.g. Render Disk at
/var/data). On a platform with an ephemeral filesystem the file will
be rebuilt empty on every restart — that's expected.
"""

import json
import os


def _resolve_data_dir():
    env_dir = os.environ.get("DATA_DIR")
    if env_dir:
        return env_dir
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


DATA_FILE = os.path.join(_resolve_data_dir(), "userdata.json")


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
