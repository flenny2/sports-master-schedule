"""
Tactical-preview persistence — one JSON file keyed by game ID.

Same DATA_DIR convention as userdata.py (env-resolvable; ./data default).
On Render's ephemeral free tier the file resets on restart — accepted by
design (PRODUCT_BRIEF.md D3): previews are pre-match ephemera and
regenerating one costs cents.

Record shape per game id:
  {
    "status":       "pending" | "ready" | "error",
    "sections":     [{"heading": str, "body": str}, ...]   (ready only)
    "model":        model id string, or "dry-run"          (ready only)
    "error":        short message                          (error only)
    "generated_at": ISO timestamp                          (ready only)
    "started_at":   ISO timestamp                          (pending only)
    "game":         small context dict (teams/league) for display
  }
"""

import json
import os
import threading
from datetime import datetime, timezone

from app.userdata import _resolve_data_dir  # single source of DATA_DIR logic

PREVIEWS_FILE = os.path.join(_resolve_data_dir(), "previews.json")

# Guards read-modify-write races between the generation thread and
# request threads in one process. gunicorn runs 2 worker processes that
# this lock can't see — a cross-process race just means last-write-wins
# on the file, which for a single-user app is an acceptable worst case.
_lock = threading.Lock()


def _load():
    if not os.path.exists(PREVIEWS_FILE):
        return {}
    try:
        with open(PREVIEWS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Corrupt/half-written file — start fresh rather than crash
        return {}


def _save(data):
    os.makedirs(os.path.dirname(PREVIEWS_FILE), exist_ok=True)
    with open(PREVIEWS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_preview(game_id):
    """Return the stored record for a game, or None."""
    return _load().get(game_id)


def _put(game_id, record):
    with _lock:
        data = _load()
        data[game_id] = record
        _save(data)


def mark_pending(game_id, game_ctx):
    _put(game_id, {
        "status": "pending",
        "started_at": _now(),
        "game": game_ctx,
    })


def mark_ready(game_id, sections, model):
    existing = get_preview(game_id) or {}
    _put(game_id, {
        "status": "ready",
        "sections": sections,
        "model": model,
        "generated_at": _now(),
        "game": existing.get("game", {}),
    })


def mark_error(game_id, message):
    existing = get_preview(game_id) or {}
    _put(game_id, {
        "status": "error",
        "error": str(message)[:300],
        "game": existing.get("game", {}),
    })
