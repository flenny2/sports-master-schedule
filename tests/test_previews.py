"""
Tests for the tactical-preview pipeline: the previews store
(app/previews.py) and the generation helpers (app/tactical.py).

No network and no API key anywhere here — generation is exercised via
dry-run mode, which is exactly what runs in a keyless environment.
"""

import json

from app import previews, tactical


GAME_CTX = {
    "sport": "soccer",
    "league": "eng.1",
    "league_name": "Premier League",
    "home": "Arsenal",
    "away": "Manchester City",
    "date": "2026-08-22T16:30Z",
    "venue": "Emirates Stadium",
}


# ── Store ─────────────────────────────────────────────────────────

def test_get_preview_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(previews, "PREVIEWS_FILE", str(tmp_path / "p.json"))
    assert previews.get_preview("g1") is None


def test_pending_then_ready_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(previews, "PREVIEWS_FILE", str(tmp_path / "p.json"))
    previews.mark_pending("g1", GAME_CTX)
    rec = previews.get_preview("g1")
    assert rec["status"] == "pending"
    assert rec["game"]["home"] == "Arsenal"

    sections = [{"heading": "The Stakes", "body": "big"}]
    previews.mark_ready("g1", sections, "dry-run")
    rec = previews.get_preview("g1")
    assert rec["status"] == "ready"
    assert rec["sections"] == sections
    assert rec["model"] == "dry-run"
    assert rec["game"]["home"] == "Arsenal"  # ctx carried through
    assert "generated_at" in rec


def test_error_flow_truncates_message(tmp_path, monkeypatch):
    monkeypatch.setattr(previews, "PREVIEWS_FILE", str(tmp_path / "p.json"))
    previews.mark_pending("g2", GAME_CTX)
    previews.mark_error("g2", "boom " * 200)
    rec = previews.get_preview("g2")
    assert rec["status"] == "error"
    assert len(rec["error"]) <= 300


def test_corrupt_file_returns_empty(tmp_path, monkeypatch):
    path = tmp_path / "p.json"
    path.write_text("{not json")
    monkeypatch.setattr(previews, "PREVIEWS_FILE", str(path))
    assert previews.get_preview("anything") is None
    # And writes recover the file
    previews.mark_pending("g3", GAME_CTX)
    assert previews.get_preview("g3")["status"] == "pending"


# ── Prompt + parsing ──────────────────────────────────────────────

def test_build_prompt_contains_matchup_and_headings():
    prompt = tactical.build_prompt(GAME_CTX, {"odds": "ARS -120"})
    assert "Manchester City at Arsenal" in prompt
    assert "Premier League" in prompt
    assert "ARS -120" in prompt
    for heading in tactical.SECTION_HEADINGS:
        assert "## " + heading in prompt
    # Sport-specific angle present
    assert "formations" in prompt


def test_build_prompt_football_angle():
    ctx = dict(GAME_CTX, sport="football", home="Steelers", away="Ravens")
    prompt = tactical.build_prompt(ctx, None)
    assert "coordinator" in prompt.lower()
    assert "American football" in prompt


def test_parse_sections_standard():
    text = (
        "## The Stakes\nBig game.\n\n"
        "## The Read\n- watch the press\n- watch the flanks\n"
    )
    secs = tactical.parse_sections(text)
    assert [s["heading"] for s in secs] == ["The Stakes", "The Read"]
    assert secs[0]["body"] == "Big game."
    assert "- watch the press" in secs[1]["body"]


def test_parse_sections_fallback_without_headings():
    secs = tactical.parse_sections("just a blob of prose")
    assert len(secs) == 1
    assert secs[0]["heading"] == "Tactical Read"


def test_parse_sections_drops_empty_bodies():
    secs = tactical.parse_sections("## Empty\n\n## Full\ncontent\n")
    assert [s["heading"] for s in secs] == ["Full"]


# ── Dry-run generation (the keyless end-to-end path) ─────────────

def test_run_without_key_produces_dry_run(tmp_path, monkeypatch):
    monkeypatch.setattr(previews, "PREVIEWS_FILE", str(tmp_path / "p.json"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # No network: facts lookup stubbed out
    monkeypatch.setattr(tactical, "get_game_facts", lambda *a: None)

    previews.mark_pending("g9", GAME_CTX)
    tactical._run("g9", GAME_CTX)  # call thread body directly

    rec = previews.get_preview("g9")
    assert rec["status"] == "ready"
    assert rec["model"] == "dry-run"
    headings = [s["heading"] for s in rec["sections"]]
    assert headings == tactical.SECTION_HEADINGS
    joined = json.dumps(rec["sections"])
    assert "Arsenal" in joined and "Manchester City" in joined
    assert "DRY RUN" in joined


def test_run_marks_error_on_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(previews, "PREVIEWS_FILE", str(tmp_path / "p.json"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def explode(*a):
        raise RuntimeError("espn fell over")

    monkeypatch.setattr(tactical, "get_game_facts", explode)
    previews.mark_pending("g10", GAME_CTX)
    tactical._run("g10", GAME_CTX)
    rec = previews.get_preview("g10")
    assert rec["status"] == "error"
    assert "espn fell over" in rec["error"]
