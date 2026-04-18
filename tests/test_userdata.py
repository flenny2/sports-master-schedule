"""
Tests for app.userdata.

userdata.py hardcodes the JSON path, so we monkeypatch that module
attribute to point to a temp file per test.
"""

import json

from app import userdata


def test_empty_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(userdata, "DATA_FILE", str(tmp_path / "missing.json"))
    assert userdata.get_all_userdata() == {}


def test_set_and_read_watched(tmp_path, monkeypatch):
    monkeypatch.setattr(userdata, "DATA_FILE", str(tmp_path / "ud.json"))
    userdata.set_watched("game123", True)
    data = userdata.get_all_userdata()
    assert data["game123"]["watched"] is True


def test_set_notes_preserves_watched(tmp_path, monkeypatch):
    path = tmp_path / "ud.json"
    monkeypatch.setattr(userdata, "DATA_FILE", str(path))
    userdata.set_watched("g1", True)
    userdata.set_notes("g1", "great match")
    data = userdata.get_all_userdata()
    assert data["g1"] == {"watched": True, "notes": "great match"}


def test_multiple_games_independent(tmp_path, monkeypatch):
    monkeypatch.setattr(userdata, "DATA_FILE", str(tmp_path / "ud.json"))
    userdata.set_watched("a", True)
    userdata.set_notes("b", "hello")
    data = userdata.get_all_userdata()
    assert data["a"]["watched"] is True
    assert data["b"]["notes"] == "hello"
    assert "watched" not in data["b"]


def test_persists_across_reload(tmp_path, monkeypatch):
    path = tmp_path / "ud.json"
    monkeypatch.setattr(userdata, "DATA_FILE", str(path))
    userdata.set_notes("x", "first")
    # Simulate a process restart by reading the raw file
    with open(path) as f:
        on_disk = json.load(f)
    assert on_disk["x"]["notes"] == "first"
