"""
On-demand tactical read — the Claude layer of the preview (brief D3).

Flow: the routes layer marks the game "pending" in the previews store and
calls start_generation(); a background thread gathers ESPN facts, calls
the Claude API with server-side web search, and writes the finished
sections back to the store. The frontend polls GET /preview until ready.

Why a background thread: Render runs gunicorn with --timeout 60 and a
web-research generation can exceed that. The POST returns 202 instantly;
the thread writes to the on-disk store, which both gunicorn workers see.

DRY-RUN MODE: with no ANTHROPIC_API_KEY in the environment, the button
still works end-to-end but returns canned sections at $0 — that's how
the pipeline is built and tested keyless. Dylan flips it live by setting
the env var (Render dashboard + local shell); the key is never read by
this code beyond passing it implicitly to the SDK, never logged, never
committed.

Cost per press (approximate, verified against current pricing Jul-18):
default model claude-opus-4-8 ≈ 15–30¢ with research; PREVIEW_MODEL can
be set to claude-sonnet-5 for ≈ 10–15¢. Spend happens ONLY on button
press — nothing generates automatically, ever (brief D3 hard rule).
"""

import os
import threading

from app import previews
from app.facts import get_game_facts

# Model default per Anthropic guidance; override with PREVIEW_MODEL.
DEFAULT_MODEL = "claude-opus-4-8"

# Fixed section headings — the prompt demands them and parse_sections()
# splits on them, so prompt + parser + frontend stay in lockstep.
SECTION_HEADINGS = [
    "The Stakes",
    "Styles & Tactics",
    "Key Matchups",
    "Availability & Selection",
    "The Read",
]

_SPORT_ANGLE = {
    "soccer": (
        "Expected formations and each coach's tactical identity "
        "(pressing triggers, build-up style, where they overload). "
        "Name the key men and the one duel that decides the match."
    ),
    "football": (
        "Offensive and defensive scheme identities, coordinator "
        "tendencies (personnel groupings, blitz rates, coverage "
        "shells), the QB-vs-coverage chess match, and the trenches."
    ),
}


def build_prompt(ctx, facts):
    """Compose the user prompt for one game. ctx keys: sport, league_name,
    home, away, date, venue (all strings, sanitized by the routes layer)."""
    sport_word = "soccer" if ctx["sport"] == "soccer" else "American football"
    lines = [
        "You are writing a pre-match tactical preview for one "
        "knowledgeable fan who is deciding how to watch this game.",
        "",
        "MATCH: " + ctx["away"] + " at " + ctx["home"],
        "COMPETITION: " + ctx.get("league_name", ""),
        "KICKOFF (UTC): " + ctx.get("date", ""),
        "VENUE: " + (ctx.get("venue") or "unknown"),
        "SPORT: " + sport_word,
        "",
        "Verified facts from ESPN (treat as current):",
        repr(facts) if facts else "(none available)",
        "",
        "Research the matchup first: latest team news, expected "
        "lineups/inactives, coach press-conference notes, current "
        "tactical writing. Then write EXACTLY these five sections, each "
        "starting with its literal heading line:",
    ]
    for h in SECTION_HEADINGS:
        lines.append("## " + h)
    lines += [
        "",
        "Focus for this sport: " + _SPORT_ANGLE[ctx["sport"]],
        "",
        "Style: tight, vivid, fan-facing. Short paragraphs and \"- \" "
        "bullets. No tables, no links, no citations, no hedging "
        "boilerplate. 450–650 words total. Write nothing before the "
        "first heading and nothing after the last section.",
    ]
    return "\n".join(lines)


def parse_sections(text):
    """Split model output on '## ' heading lines into section dicts.
    Falls back to one section if the model ignored the format."""
    sections = []
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                current["body"] = current["body"].strip()
                sections.append(current)
            current = {"heading": line[3:].strip(), "body": ""}
        elif current:
            current["body"] += line + "\n"
    if current:
        current["body"] = current["body"].strip()
        sections.append(current)
    if not sections and text.strip():
        sections = [{"heading": "Tactical Read", "body": text.strip()}]
    return [s for s in sections if s["body"]]


def dry_run_sections(ctx):
    """Canned preview used when no API key is configured — keeps the
    whole pipeline testable at $0 and shows the real layout."""
    away, home = ctx["away"], ctx["home"]
    return [
        {"heading": "The Stakes",
         "body": "DRY RUN — no ANTHROPIC_API_KEY is set, so this is "
                 "canned text showing the preview layout. Set the key in "
                 "the environment (Render dashboard or local shell) and "
                 "press Refresh to generate a real tactical read.\n\n"
                 + away + " visit " + home + " with plenty on the line — "
                 "this section will frame what the match means for both."},
        {"heading": "Styles & Tactics",
         "body": "- How " + home + " want the game to look\n"
                 "- How " + away + " counter it\n"
                 "- Expected shapes and pressing pictures"},
        {"heading": "Key Matchups",
         "body": "- The individual duel that tilts the game\n"
                 "- The zone where it will be won or lost"},
        {"heading": "Availability & Selection",
         "body": "Injuries, suspensions, and expected selections land "
                 "here, cross-checked against the ESPN facts panel."},
        {"heading": "The Read",
         "body": "A two-sentence verdict on what to watch for."},
    ]


def _call_claude(prompt):
    """One generation round-trip. Returns (sections, model_id)."""
    import anthropic  # deferred so keyless test envs never need it wired

    model = os.environ.get("PREVIEW_MODEL", DEFAULT_MODEL)
    client = anthropic.Anthropic(timeout=180.0, max_retries=1)

    messages = [{"role": "user", "content": prompt}]
    response = None
    # Server-side web search can pause long turns (stop_reason
    # "pause_turn"); re-send to let it resume, max 3 rounds.
    for _ in range(3):
        response = client.messages.create(
            model=model,
            max_tokens=6000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            tools=[{
                "type": "web_search_20260209",
                "name": "web_search",
                "max_uses": 4,  # cost cap per press
            }],
            messages=messages,
        )
        if response.stop_reason == "pause_turn":
            messages = [
                messages[0],
                {"role": "assistant", "content": response.content},
            ]
            continue
        break

    text = "".join(
        block.text for block in response.content if block.type == "text"
    )
    if response.stop_reason == "refusal" or not text.strip():
        raise RuntimeError(
            "generation returned no text (stop_reason="
            + str(response.stop_reason) + ")"
        )
    return parse_sections(text), model


def _run(game_id, ctx):
    """Thread body: gather facts, generate, persist. Never raises —
    failures land in the store as status=error for the UI to show."""
    try:
        facts = get_game_facts(ctx["sport"], ctx.get("league", ""), game_id)
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sections, model = dry_run_sections(ctx), "dry-run"
        else:
            sections, model = _call_claude(build_prompt(ctx, facts))
        previews.mark_ready(game_id, sections, model)
    except Exception as exc:  # noqa: BLE001 — thread edge, must not die silently
        previews.mark_error(game_id, exc)


def start_generation(game_id, ctx):
    """Fire-and-forget generation thread (daemon: a dying server should
    not be held open by a preview; the pending record just goes stale
    and the next press regenerates)."""
    thread = threading.Thread(
        target=_run, args=(game_id, ctx), daemon=True,
        name="preview-" + str(game_id),
    )
    thread.start()
    return thread
