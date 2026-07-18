# Sports Master Schedule

what: Dylan's meta sports tracker / fan-experience hub — Front Page (marquee + slate + storylines + tables), calendar, playoffs, standings, and ON-DEMAND Claude tactical previews; Flask + vanilla HTML/CSS/JS, ESPN public API, in-memory cache, no DB and no build step
rules: docs describe `master` only; NEVER `git push` (push = Render auto-deploy — shipping is Dylan's call); run `./tools/validate` before shipping; SINGLE LIGHT THEME — one `:root` token block, no dark mode, no toggle (Dylan Jul-15 ruling); preview generation is on-demand ONLY (spend = button press, never automatic)
links: product truth `PRODUCT_BRIEF.md` (D1–D8, interview-converged Jul-17) · deploy config `render.yaml` (Render free tier) · idea/task inbox `TODOS.md` · cross-project style rulings `personal-style-tracker/`
updated: 2026-07-18

Dylan's fan hub — phone-first (deployed Render URL). Visual identity: **"broadcast graphics, in daylight"** — bright cool-white surfaces, near-monochrome ink chrome, ALL vivid color from teams/sports, ink "lower-third" section tags with a gold lead, and the signature **team-color duel seam** across each game card's top edge.

## Tech Stack
- Python 3 / Flask backend; in-memory cache with TTL (no database)
- Vanilla HTML/CSS/JS frontend (no build step, no bundler, no framework)
- ESPN public API (no auth) + Anthropic API (tactical reads only, only on button press)
- `anthropic` SDK pinned in requirements.txt
- Google Fonts via CDN: **Saira Condensed** (display/scores/tabs — 700 italic = section tags), **Instrument Sans** (body/UI), **JetBrains Mono** (records, datelines, facts labels)

## Running
```
pip install --user --break-system-packages -r requirements.txt
python app.py
```
Server on http://localhost:5000 with debug/auto-reload. Tactical reads run in **dry-run mode** (canned sections, $0) until `ANTHROPIC_API_KEY` is set in the environment; `PREVIEW_MODEL` optionally overrides the default `claude-opus-4-8` (e.g. `claude-sonnet-5` for cheaper presses). Both are env vars — set in the Render dashboard for prod, never committed.

## API Routes
- `GET /api/schedule?month=YYYY-MM&refresh=true` — games for a padded calendar month (legacy `?week=` still supported)
- `GET /api/standings?refresh=true` — standings + title races (NFL first, then soccer; NBA unplugged per brief A1)
- `GET /api/storylines` — active storyline chips (optional `logo_url` each)
- `GET /api/games/<id>/facts?sport=&league=` — FREE facts panel (odds, form, H2H, lineups near kickoff; NFL injuries/leaders); public read, one cached ESPN summary call
- `GET /api/games/<id>/preview` — tactical-read state: `none | pending | ready | error`
- `POST /api/games/<id>/preview` — start generation (body: sport/league/league_name/home/away/date/venue). **Auth-gated** (spend protection); 202 + background thread; frontend polls the GET every 3s
- `POST /api/games/<id>/watched` · `POST /api/games/<id>/notes` — user data (auth-gated)
- Write auth: `SCHEDULE_TOKEN` env → visit `/?token=<value>` once → cookie gates all POSTs

## Key Design Decisions
- **Front Page (Home tab, landing view)**: dateline → MAIN EVENT marquee (highest `scoreMarquee()`: live > upcoming, must-watch/major/playoff boosted) → Today's Slate → storyline cards → mini standings (PL + NFL top-5 + watched rows). Desktop: 7/5 two-column grid (slate left, stories+tables rail). All blocks build from data already fetched — no front-page-specific endpoints
- **Duel seam (the design signature)**: every game card's `.rail` is a top strip where the away team's kit color meets the home team's at an angled gradient cut. `_parse_game` extracts `color`/`alt_color` per team; JS `seamColor()` rejects too-light colors (luma > 0.82 — white kits) in favor of the alternate, else the sport fallback pair. Sport color still drives dots/pills; team color is the bold element, chrome stays quiet
- **Single light theme**: one `:root` token block in style.css; dark mode was DELETED (not hidden) per the Jul-15 ruling. Every token pair WCAG-AA verified numerically (≥4.5:1 text, ≥3:1 UI) — keep it that way when adding tokens
- **Tactical previews (brief D3)**: hybrid. Facts panel = free ESPN summary parse (`app/facts.py`). Read = `POST /preview` → `previews.mark_pending` → daemon thread (`app/tactical.py`) → Claude with server-side `web_search_20260209` (`max_uses=4` = cost cap), adaptive thinking, effort medium, `pause_turn` continuation (max 3) → sections stored in `data/previews.json` (`app/previews.py`, userdata pattern, gitignored, ephemeral-on-Render accepted). Background thread exists because gunicorn runs `--timeout 60`; the store is on disk so both workers see it. Output = plain text with `## ` section headings; `parse_sections` splits; frontend renders via `el()` (bullets + paragraphs, no markdown lib)
- **Preview scope**: soccer + NFL only (`PREVIEW_SPORTS` in facts.py). Button on `pre` games; cached reads stay viewable after kickoff; "Refresh read" deliberately re-spends
- **NFL pillar (brief D5)**: Steelers in `WATCHED_TEAMS` (id 23, must_watch) → `fetch_nfl_games` has THREE inclusion paths: watched team (slot "My Team", outranks Primetime label) / primetime / RedZone window. NFL standings = AFC/NFC conference tables with `playoffSeed` as rank (seed zones: 1 = bye, 2–7 playoff) — ESPN's v2 `level=3` division split returns empty entries, so conference view is the honest v1. `FANTASY_ROSTER` in config (name → NFL abbrev, hand-maintained post-draft) drives `app/fantasy.py` → `my_guys` on NFL games → dashed-gold "YOUR GUYS" chip
- **Watched-row highlight is sport-scoped** in `fetch_standings` — ESPN team ids are only unique per sport (Steelers "23" ≠ NBA/soccer "23"); a flat set false-highlights other leagues
- **Deep links**: `#front/#week/#playoffs/#tables` select a tab on load (tab clicks sync the hash); `#game-<espn id>` auto-expands that game's card — also how headless-Chrome screenshot verification reaches interactive states
- **Importance tiers** (`app/importance.py`): must_watch / notable / major_event — all fetched NFL games are must_watch (every path implies it); soccer must-watch teams upgrade; NBA tier logic retained but dormant
- **NBA unplugged + NFL-first order (brief A1, Dylan post-deploy Jul-18)**: NBA is out of the fetchers list, standings list, and filter chips — `fetch_nba_games`/taggers/table builders remain for a one-line restore (comments mark the spots in `get_all_games` + `get_all_standings`). Sport order everywhere is NFL → Soccer (chips, Tables order = standings list order, `MINI_TABLE_LEAGUES`). Filter chips use recolorable CSS-mask glyph icons (`.pill-ico`), not color dots
- **Storylines** (`config.STORYLINES`) filter the Calendar and render as Front Page story cards; **TITLE_RACES** render as the Tables widget AND as richer Front Page race cards (gap headline via `buildGapString`). Front Page dedupes: a storyline whose games live in a league already covered by a race card is skipped
- **Soccer fetch**: pass 1 per-team schedule (past games), pass 2 one date-range scoreboard call per league, pass 3 `FOLLOWED_COMPETITIONS` full-tournament follows (fifa.world). `CALENDAR_EXCLUDED_LEAGUES` hides ger.1/esp.1 from Calendar, standings unaffected
- **Availability**: Mon–Fri 8am–6pm PT = will_miss, else can_watch
- **Desktop vs mobile calendar**: desktop month grid + detail panel; mobile rolling 7-day window (arrows ±7 days). Mobile day blocks separated by a hairline; `appendGamesWithDayDivider` injects the "Coming Up" divider once per day
- **User data**: `data/userdata.json` + `data/previews.json` (both gitignored) via `DATA_DIR`-resolvable paths; ephemeral on Render free tier by design
- **Interactive elements inside cards** (watched, notes, read buttons) must call `stopPropagation()` — the card body click toggles expand/collapse

## ESPN API Gotchas
- **Summary endpoint** (`/{sport}/{league}/summary?event=`) powers the facts panel. Soccer: form lives at `boxscore.form`, prior meetings at **`headToHeadGames`** (not `headToHead`), `rosters[].roster` is EMPTY until near kickoff (formation + starters appear late). NFL: `injuries` (per team, athlete + status), `leaders` (nested three levels), `lastFiveGames` often null. Parse defensively — facts are garnish, never a 500
- **NFL v2 standings**: children = 2 conferences; entries carry `playoffSeed` (no plain `rank`), `wins/losses/ties/winPercent/streak/divisionRecord`; `?level=3` (divisions) returns children with EMPTY entries — don't chase it
- **Team scoreboard colors**: competitor `team.color`/`alternateColor` are bare hex WITHOUT `#`, missing on some events, and can be white (e.g. England `FFFFFF`) — hence the frontend luma guard
- **Team schedule endpoint** only returns PAST games — use scoreboard `dates=YYYYMMDD-YYYYMMDD` ranges for futures; team-schedule path strips `series`/`leg`/`notes`
- Soccer season years use the start year (PL 2025-26 = `season=2025`); soccer scores arrive as floats (`"2.0"` → `int(float(v))`)
- **Standings** use the `site.api.espn.com/apis/v2/...` path; `note` on entries = zone info
- **NBA**: season_type 2/3/5 = regular/playoffs/play-in; play-in has empty `competition.series`; series data at `competition.series` (summary, totalCompetitions, competitors[].wins)
- **UCL two-leg ties**: `competition.leg.value` + `series.title`; 2nd-leg aggregate via `fetch_first_leg` (ESPN's aggregateScore only populates post-match)
- **Broadcaster names** truncated → `BROADCAST_DISPLAY` map; competitor records at `records[].summary` per competitor
- **Playoff detection**: league in `KNOCKOUT_CUP_LEAGUES` OR notes keyword OR `raw_series.title` in known round titles — any one suffices

## Code Style
- **Beginner-friendly**: clear names, comments on non-obvious logic; no unnecessary abstractions
- **Frontend uses safe DOM methods** (`createElement`/`textContent`) — no `innerHTML` (security hook blocks it); `el(tag, cls, txt)` builds nodes, `appendIf` for nullables
- **Frontend uses `var`** and function declarations — keep consistent
- **Single-theme tokens**: add new CSS custom properties to the ONE `:root` block; verify contrast (≥4.5:1 text / ≥3:1 UI on the surface it sits on) before shipping — the palette is documented as numerically AA-verified
- **Color POV**: chrome near-monochrome ink; vivid color belongs to teams (seam) and sports (dots/rails). New chips/tags stay quiet (ink, outline, or gold fill)
- **Editing app.js with tools**: the file mixes literal `\uXXXX` escapes with real Unicode in adjacent lines — exact-match string editors can fail there; a small Python splice on unambiguous anchor lines is the reliable fallback

## Project Layout
- `app.py` — Flask entry point (port 5000)
- `config.py` — teams (soccer + Steelers), work schedule, title races, storylines, league exclusions, `FOLLOWED_COMPETITIONS`, `FANTASY_ROSTER`, NFL networks
- `PRODUCT_BRIEF.md` — converged product decisions D1–D8; if code contradicts it, the brief wins or gets amended first
- `tools/validate` — uniform validation entrypoint (pytest + `VALIDATE PASS`)
- `TODOS.md` — repo-native idea/task inbox
- `app/espn.py` — ESPN client + cache; fetchers (incl. NFL 3-path), standings (incl. NFL), `fetch_first_leg`
- `app/facts.py` — summary fetch + per-sport facts parsing (`PREVIEW_SPORTS`)
- `app/previews.py` — tactical-read JSON store (pending/ready/error)
- `app/tactical.py` — prompt builder, Claude call (web search, cost caps), dry-run mode, background thread
- `app/fantasy.py` — `my_guys` tagger from `FANTASY_ROSTER`
- `app/importance.py` · `app/availability.py` · `app/playoff.py` · `app/series_context.py` · `app/storylines.py` — game taggers
- `app/routes.py` — all routes; tagging chain ends `tag_storylines` → `tag_my_guys`
- `app/userdata.py` — watched/notes JSON store (defines the shared `_resolve_data_dir`)
- `templates/index.html` — single-page shell: masthead, sticky tab bar (Home/Calendar/Playoffs/Tables), view containers
- `static/app.js` — all rendering: front page (marquee/slate/stories/minis), calendar, playoffs, tables (soccer/NBA/NFL builders), cards + duel seam, match intel (facts + read), deep links
- `static/style.css` — the light design system: tokens, section tags, cards/seam, front page, calendar, tables, intel, responsive

## Testing
Pytest suite in `tests/` — 123 tests: availability, importance, userdata, playoff tagging, series context, storylines, auth (incl. preview spend gate), ESPN parsing, NFL inclusion + standings mapping, fantasy tagger, facts parsing (fixtures from live-probed shapes), preview store + dry-run pipeline. Run `./tools/validate`.

UI or live-ESPN work still needs a manual run: `python app.py`, browse, and screenshot (headless Chrome + `#hash` deep links reach every state, including expanded cards via `#game-<id>`).

## Known TODOs / deferred features
- **Deferred by the revamp interview (brief §D8)**: milestone watch · your-teams strip · NBA tactical previews · NFL draft/offseason tracker · ESPN-fantasy roster auto-pull · MLB/NHL
- **Dylan's future steps**: set `ANTHROPIC_API_KEY` (+ optional `PREVIEW_MODEL`) on Render + locally when he wants live reads; fill `FANTASY_ROSTER` after the LPPC draft (late Aug); real-phone pass after deploy (fonts, sticky tabs on iOS, notch viewport)
- **Team detail view** (click team → results/fixtures/form page) — needs ESPN team-summary endpoint investigation
- NFL mini table on Home currently shows the FIRST conference group (AFC — the Steelers' conference); NFC visible on Tables
- Past UCL games via team-schedule lose series/leg metadata (accepted; noted in `fetch_first_leg` docstring)
