# REVAMP build plan — ws/revamp-v1

## Context

Dylan is expanding sports-master-schedule from a check-the-calendar app into his **meta
sports tracker / fan hub**. The product is converged and committed: **PRODUCT_BRIEF.md**
(`605df65`, decisions D1–D8 from a 3-round interview). This plan is the implementation of
that brief on branch `ws/revamp-v1`. Build order is Dylan's pick (D7): design + Front Page
first, then tactical previews, then NFL. **Never push — push = Render deploy.** All 93
tests stay green; new features bring tests.

Repo facts the plan builds on: Flask + vanilla JS, no build step; `app.js` 1728 lines /
`style.css` 1497 / `espn.py` 815; auth = `SCHEDULE_TOKEN` env → cookie → `_write_allowed()`
(routes.py:31); storage pattern = `userdata.py` (DATA_DIR-resolvable JSON, ephemeral-OK);
gunicorn `--timeout 60`, 2 workers (render.yaml) — so preview generation must not block a
request; ESPN fetchers per sport in `espn.py` with NFL currently primetime-only.

## Phase 1 — Light-only modern design system + Front Page (ships first)

**1a. `templates/index.html`** — restructure the shell:
- Remove: inline theme script, `#btn-theme`, `color-scheme` meta, dark `theme-color` meta.
- New tab set: **Front Page (home) / Calendar / Playoffs / Tables**. `data-view="front"` first + active.
- Move month-nav (`.week-nav`) INSIDE `#week-view` (it's calendar-only now); delete the
  today-strip markup (its job moves into the Front Page slate).
- Add `<div id="front-view">`; new Google Fonts link (final faces picked at build with the
  frontend-design skill loaded — modern sports-app stack, tabular numerals for scores).

**1b. `static/style.css`** — full rewrite, single light theme:
- One `:root` token block (no `[data-theme]` selectors). Bright surface, vivid sport +
  team-color accents, bigger logos, chip/card geometry, tight spacing/alignment grid —
  the Jul-12 verdict (wasted space, misalignment) is a first-class requirement.
- Keep existing class names where the component survives (`.game-card`, `.tab-bar`,
  `.standings-*`) so app.js churn stays low; delete broadsheet-only styles.
- WCAG AA verified for every token pair before commit (contrast-check pass; ≥4.5:1 text,
  ≥3:1 UI).

**1c. `static/app.js`**:
- Delete theme-toggle handler + `btnTheme`; delete today-strip renderer.
- Add `currentView === "front"` to `render()` dispatch + tab wiring; nav label/refresh
  scoped per view.
- New `renderFrontPage()` building three blocks from data already fetched
  (`allGames`, `standingsData`, `titleRacesData`, `storylinesData` — no new endpoints):
  1. **Today/Tonight slate** — today's (+ tonight's) games, must-watch first, live scores;
     reuses `buildCard()` unchanged.
  2. **Storyline cards** — per active storyline + title race: standings context (from
     `findTeamStanding`-style lookup), next fixture + stakes line; WC knockout state from
     playoff-tagged games.
  3. **Mini standings** — compact PL top-5 + watched-team rows (NFL joins in Phase 3).
- Front Page is the mobile-first surface: blocks stack; desktop gets a 2-column editorial grid.

Verify: `./tools/validate` (93 ✓ — backend untouched) + local run + screenshots (mobile
390px, desktop 1280px) of all four tabs.

## Phase 2 — Tactical previews (hybrid: facts panel + Claude read)

**2a. Facts panel (free, instant)** — new `app/facts.py`:
- `fetch_event_summary(sport, league, event_id)` → ESPN `summary?event=` endpoint via the
  existing `_cached_get` (1h TTL) — one call per game, parsed per sport:
  soccer = form, head-to-head, probable/confirmed lineups when present; NFL = injuries,
  leaders, records. Defensive parsing throughout (parse-bomb test style already in repo);
  panel hides empty rows. **Live-verify endpoint shapes with curl during build.**
- Route `GET /api/games/<id>/facts?sport&league` (public read, like other GETs).
- Frontend: facts panel auto-loads into the expanded card view for soccer + NFL games.

**2b. Preview store** — new `app/previews.py`, mirroring `userdata.py`:
- `DATA_DIR/previews.json` keyed by game id: `{status: pending|ready|error, sections/text,
  model, generated_at, error}`. Ephemeral-on-Render accepted (brief D3).

**2c. Claude generation** — new `app/tactical.py`:
- **`anthropic` SDK** (one new dependency — see Approval notes), zero-arg client reads
  `ANTHROPIC_API_KEY` from env; the key is never logged or committed.
- `messages.create` with server-side **`web_search_20260209`** tool, `max_uses=4` (cost
  cap), `thinking={"type":"adaptive"}`, `output_config={"effort":"medium"}`,
  `max_tokens≈6000`, client timeout ≈180s, `pause_turn` continuation loop (max 3).
- Sport-aware prompts: soccer = philosophies, expected formations, key men, absences;
  NFL = scheme/coordinator matchups, key injuries. Output = plain text with fixed section
  headers; frontend splits on them (no structured-outputs/citations conflict).
- Model: default **`claude-opus-4-8`** (Anthropic guidance), `PREVIEW_MODEL` env override
  (e.g. `claude-sonnet-5`). Honest cost: ~15–30¢/press on default, ~10–15¢ on Sonnet —
  brief's cost line gets amended to match (it said "estimate, pinned at build").
- **Dry-run mode**: no `ANTHROPIC_API_KEY` → canned realistic preview, $0 — whole pipeline
  works keyless (that's how I build + test it).
- Runs in a **background thread**; writes status to the JSON store (disk-shared across
  gunicorn workers; POST returns immediately → no 60s-timeout risk).

**2d. Routes** — `POST /api/games/<id>/preview` (behind `_write_allowed()` — spend
protection, brief D3; body carries game context: teams/league/sport/date; returns 202) +
`GET /api/games/<id>/preview` (status/result; frontend polls every 3s while pending).

**2e. Frontend** — expanded card (soccer + NFL, `pre` status): "Generate tactical read"
button → pending state → sections rendered via `el()` line-based renderer (headers/bullets,
no innerHTML); cached read stays viewable after kickoff; "Refresh" link re-spends
deliberately. Buttons call `stopPropagation()` (card-expand rule).

**2f. `render.yaml` + `requirements.txt`** — document `ANTHROPIC_API_KEY` + `PREVIEW_MODEL`
env vars (set in Render dashboard, never in repo); add `anthropic` pin.

## Phase 3 — NFL pillar

**3a. `config.py`** — Steelers in `WATCHED_TEAMS` (`sport:"football"`, must_watch; ESPN id
verified live at build, expected `23`); `FANTASY_ROSTER = {}` — documented
`"Player Name": "NFL team abbrev"` map Dylan fills after the late-Aug LPPC draft.

**3b. `app/espn.py`**:
- `fetch_nfl_games`: add watched-team inclusion path (any game featuring a watched
  football team id; `nfl_slot = "My Team"`), alongside primetime/RedZone.
- `get_all_standings` += `("football", "nfl")`; NFL stats mapping in `fetch_standings`
  (W/L/T, pct, streak, `playoffSeed`-style rank) — conference tables + divisions if the
  v2 endpoint's level/groups data supports it cleanly (**live-verify at build**).

**3c. My-guys tagger** — small `tag_my_guys` step in the routes pipeline: NFL games get
`my_guys: [names]` where the roster map's team abbrev matches home/away. Frontend chip
("YOUR GUYS: Jacobs, St. Brown") on cards + slate.

**3d. Frontend** — `buildNflTable` (conference/division standings on Tables), NFL mini on
Front Page, my-guys chips. `importance.py` comment updated (football = must_watch holds:
primetime, RedZone, and now my-team games all qualify).

## Phase 4 — Docs + wrap

- `CLAUDE.md` rewritten for the new reality (tabs, preview architecture + env vars, NFL
  coverage, single light theme, new tokens rule replacing the light+dark rule).
- TODOS sweep; final `./tools/validate`; screenshots bundle; wrap-session → CLOSE-OUT
  ferry (with screenshot paths), per kickoff.

## Tests (new, alongside the existing 93)

- `test_previews.py` — store CRUD + status transitions (tmp `DATA_DIR`); dry-run generator
  returns canned sections without a key; prompt builder contains teams/sport template.
- `test_facts.py` — soccer + NFL summary parsing on fixture JSON (incl. empty/missing
  branches, parse-bomb style).
- `test_espn.py` additions — NFL watched-team inclusion; NFL standings mapping fixture.
- `test_my_guys.py` — tagger matches abbrevs, empty roster = no-op.
- `test_auth.py` addition — preview POST 401s without cookie when token set.

## Verification

- `./tools/validate` green after every phase.
- Local run (`python app.py`) + browser screenshots per phase (mobile 390px + desktop):
  Front Page, Calendar, Tables, expanded card with facts panel + dry-run tactical read.
  Screenshot mechanism: headless chromium if present on the system (checked at build;
  no installs without asking — fallback is curl/DOM checks + Dylan's eyeball on localhost).
- Live ESPN endpoint spot-checks (summary shapes, NFL standings shape, PIT team id) with
  curl before wiring parsers.

## Approval notes (what saying "go" green-lights)

1. **One new dependency**: `anthropic` SDK added to `requirements.txt` + installed locally
   via `pip install --user --break-system-packages anthropic` (the repo's documented
   install pattern). Render installs it automatically from requirements.txt at next deploy.
   Everything else uses existing deps.
2. Branch-only commits on `ws/revamp-v1` as phases land; **no push, ever** — deploy stays
   your explicit call.
3. Dark mode is deleted (not hidden) per the brief; the broadsheet CSS system is replaced.
4. Your future (not-now) steps stay as in the brief: API key + Render env var when Phase 2
   lands; `FANTASY_ROSTER` fill after the LPPC draft.
