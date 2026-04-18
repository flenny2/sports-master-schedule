"""
Tests for SCHEDULE_TOKEN write auth on POST endpoints.

The token is evaluated at module import time (_WRITE_TOKEN =
os.environ.get(...)). To toggle it per test, we set the env var
before importing app.routes in a fresh module namespace via
importlib.reload — that's what the _reload_with_token helper does.
"""

import importlib
import os

import pytest

from app import create_app


def _client_with_token(token, tmp_path, monkeypatch):
    """Return a Flask test client where SCHEDULE_TOKEN is set to `token`."""
    monkeypatch.setenv("SCHEDULE_TOKEN", token or "")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # Reload routes so the module picks up the env var
    import app.routes
    importlib.reload(app.routes)
    # Also reload userdata so DATA_FILE resolves to the tmp path
    import app.userdata
    importlib.reload(app.userdata)
    return create_app().test_client()


def test_no_token_means_writes_open(tmp_path, monkeypatch):
    client = _client_with_token("", tmp_path, monkeypatch)
    r = client.post("/api/games/123/watched", json={"watched": True})
    assert r.status_code == 200


def test_token_set_writes_rejected_without_cookie(tmp_path, monkeypatch):
    client = _client_with_token("hunter2", tmp_path, monkeypatch)
    r = client.post("/api/games/123/watched", json={"watched": True})
    assert r.status_code == 401


def test_token_via_query_param_installs_cookie(tmp_path, monkeypatch):
    client = _client_with_token("hunter2", tmp_path, monkeypatch)
    r = client.get("/?token=hunter2")
    assert r.status_code == 200
    # The Set-Cookie response header should include schedule_token=hunter2
    cookies = r.headers.get_all("Set-Cookie")
    assert any("schedule_token=hunter2" in c for c in cookies)


def test_writes_allowed_after_token_cookie_set(tmp_path, monkeypatch):
    client = _client_with_token("hunter2", tmp_path, monkeypatch)
    client.set_cookie("schedule_token", "hunter2")
    r = client.post("/api/games/123/watched", json={"watched": True})
    assert r.status_code == 200


def test_writes_rejected_with_wrong_cookie(tmp_path, monkeypatch):
    client = _client_with_token("hunter2", tmp_path, monkeypatch)
    client.set_cookie("schedule_token", "wrong")
    r = client.post("/api/games/123/notes", json={"notes": "x"})
    assert r.status_code == 401


def test_reads_always_public(tmp_path, monkeypatch):
    client = _client_with_token("hunter2", tmp_path, monkeypatch)
    r = client.get("/api/schedule?month=2026-04")
    # Even without a valid token we should be able to read
    # (200 or 502 both mean auth didn't block us; ESPN may be flaky)
    assert r.status_code in (200, 502, 500)


def test_notes_rejects_non_string(tmp_path, monkeypatch):
    client = _client_with_token("", tmp_path, monkeypatch)
    r = client.post("/api/games/123/notes", json={"notes": {"bad": "type"}})
    assert r.status_code == 400


def test_notes_truncated_at_2000_chars(tmp_path, monkeypatch):
    client = _client_with_token("", tmp_path, monkeypatch)
    big = "x" * 5000
    r = client.post("/api/games/123/notes", json={"notes": big})
    assert r.status_code == 200
    # Read it back and confirm it's capped
    from app import userdata
    data = userdata.get_all_userdata()
    assert len(data["123"]["notes"]) == 2000


def test_empty_body_on_watched_defaults_to_false(tmp_path, monkeypatch):
    client = _client_with_token("", tmp_path, monkeypatch)
    r = client.post("/api/games/123/watched")  # no body
    assert r.status_code == 200
    from app import userdata
    data = userdata.get_all_userdata()
    assert data["123"]["watched"] is False


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch):
    # Ensure no stale SCHEDULE_TOKEN / DATA_DIR leaks from one test
    # into the next via the shared app.routes module.
    monkeypatch.delenv("SCHEDULE_TOKEN", raising=False)
    monkeypatch.delenv("DATA_DIR", raising=False)
    yield
    # Reload routes back to unset token so subsequent test files
    # aren't surprised by leftover auth state.
    if "SCHEDULE_TOKEN" in os.environ:
        del os.environ["SCHEDULE_TOKEN"]
    import app.routes
    importlib.reload(app.routes)
