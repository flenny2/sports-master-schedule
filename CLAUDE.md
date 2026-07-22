# Sports Master Schedule

what: Dylan's meta sports tracker / fan-experience hub — Front Page (marquee + slate + storylines + tables), calendar, playoffs, standings, and ON-DEMAND Claude tactical previews; Flask + vanilla HTML/CSS/JS, ESPN public API, in-memory cache, no DB and no build step
rules: docs describe `master` only; NEVER `git push` (push = Render auto-deploy — shipping is Dylan's call); run `./tools/validate` before shipping; SINGLE LIGHT THEME — one `:root` token block, no dark mode, no toggle (Dylan Jul-15 ruling); preview generation is on-demand ONLY (spend = button press, never automatic)
links: product truth `PRODUCT_BRIEF.md` (D1–D8, interview-converged Jul-17) · deploy config `render.yaml` (Render free tier) · idea/task inbox `TODOS.md` · cross-project style rulings `personal-style-tracker/`
updated: 2026-07-22

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
- `GET /api/myteams?refresh=true` — "Your Teams" strip cards (one per config `favorite` team): next fixture, last result, table position. Public read, no spend
- `GET /api/games/<id>/facts?sport=&league=` — FREE facts panel (odds, form, H2H, lineups near kickoff; NFL injuries/leaders); public read, one cached ESPN summary call
- `GET /api/games/<id>/preview` — tactical-read state: `none | pending | ready | error`
- `POST /api/games/<id>/preview` — start generation (body: sport/league/league_name/home/away/date/venue). **Auth-gated** (spend protection); 202 + background thread; frontend polls the GET every 3s
- `POST /api/games/<id>/watched` · `POST /api/games/<id>/notes` — user data (auth-gated)
- Write auth: `SCHEDULE_TOKEN` env → visit `/?token=<value>` once → cookie gates all POSTs

## Key Design Decisions
- **Front Page (Home tab, landing view)**: dateline → YOUR TEAMS strip → MAIN EVENT marquee (highest `scoreMarquee()`: live > upcoming, must-watch/major/playoff boosted) → Today's Slate → storyline cards → mini standings (PL + NFL top-5 + watched rows). Desktop: 7/5 two-column grid (slate left, stories+tables rail). Every block EXCEPT the strip builds from data already fetched; the strip is the one front-page-specific endpoint (see below)
- **"Your Teams" strip (brief §D8, built Jul-22)**: `app/myteams.py` + `GET /api/myteams` → one card per config `favorite` team (Steelers, Man City) with next fixture + countdown, last result, table position. Four decisions worth keeping:
  - **`favorite` is a separate config key from `tier`.** `tier` drives `app/importance.py` and the marquee scorer; bending it to mean "my team" would silently change which games headline the page. Arsenal is `must_watch` (Dylan follows the PL title race) but NOT `favorite` — its race already has a Front Page story card, so a strip entry would be a third Arsenal surface
  - **It gets its own endpoint** because the strip needs games ∩ standings and no existing endpoint carries both. This is a deliberate exception to the "no front-page-specific endpoints" rule above, not an oversight
  - **A table position is suppressed at 0 games played.** ESPN zeroes every stat in the off-season and then sorts ALPHABETICALLY — probed Jul-22, the PL read "Bournemouth 1st / Arsenal 2nd / Man City 15th" on 0 pts and every NFL team sat at rank 0. Printing that rank would state a standing that doesn't exist. (The Home **mini-tables and title-race card still show it** — pre-existing, logged in TODOS)
  - **Assembly is server-side and pure** so the sport-scoped id matching and last/next selection are pytest-reachable; `static/app.js` only renders
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
- **Team schedule endpoint is SPORT-SPLIT** (re-probed Jul-22, corrects the old blanket "only returns PAST games"): `soccer/*` returns finished matches only — use scoreboard `dates=YYYYMMDD-YYYYMMDD` ranges, or `fetch_upcoming_fixtures()`, for futures. `football/nfl` returns the **whole upcoming season** (17 events, all `pre`, months ahead) and no past games by default; add `?season=YYYY` for a prior year. The team-schedule path also strips `series`/`leg`/`notes` **and `color`/`alternateColor`** — so kit colors are unavailable from it (the strip falls back to sport colors)
- **Standings reset to zeros between seasons** and then sort ALPHABETICALLY. Probed Jul-22: PL = Bournemouth 1st / Arsenal 2nd / Man City 15th, all on 0 pts; every NFL team at `rank 0, 0-0-0`. Any feature that prints a rank must gate on games-played (`app/myteams.py:_games_played`) or it will state a standing that doesn't exist
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
- `app/myteams.py` — "Your Teams" strip assembly (pure helpers + `get_my_teams()`)
- `app/importance.py` · `app/availability.py` · `app/playoff.py` · `app/series_context.py` · `app/storylines.py` — game taggers
- `app/routes.py` — all routes; tagging chain ends `tag_storylines` → `tag_my_guys`
- `app/userdata.py` — watched/notes JSON store (defines the shared `_resolve_data_dir`)
- `templates/index.html` — single-page shell: masthead, sticky tab bar (Home/Calendar/Playoffs/Tables), view containers
- `static/app.js` — all rendering: front page (marquee/slate/stories/minis), calendar, playoffs, tables (soccer/NBA/NFL builders), cards + duel seam, match intel (facts + read), deep links
- `static/style.css` — the light design system: tokens, section tags, cards/seam, front page, calendar, tables, intel, responsive

## Testing
Pytest suite in `tests/` — 167 tests: availability, importance, userdata, playoff tagging, series context, storylines, auth (incl. preview spend gate), ESPN parsing, NFL inclusion + standings mapping, fantasy tagger, facts parsing (fixtures from live-probed shapes), preview store + dry-run pipeline, schedule-route param edges, standings fragility, my-teams strip. Run `./tools/validate`.

UI or live-ESPN work still needs a manual run: `python app.py`, browse, and screenshot (headless Chrome + `#hash` deep links reach every state, including expanded cards via `#game-<id>`).

## Known TODOs / deferred features
- **Deferred by the revamp interview (brief §D8)**: milestone watch (needs a curated chase list from Dylan) · NBA tactical previews · NFL draft/offseason tracker · ESPN-fantasy roster auto-pull · MLB/NHL. ~~your-teams strip~~ BUILT Jul-22 (brief amendment A2)
- **Dylan's future steps**: set `ANTHROPIC_API_KEY` (+ optional `PREVIEW_MODEL`) on Render + locally when he wants live reads; fill `FANTASY_ROSTER` after the LPPC draft (late Aug); real-phone pass after deploy (fonts, sticky tabs on iOS, notch viewport)
- **Team detail view** (click team → results/fixtures/form page) — needs ESPN team-summary endpoint investigation
- NFL mini table on Home currently shows the FIRST conference group (AFC — the Steelers' conference); NFC visible on Tables
- Past UCL games via team-schedule lose series/leg metadata (accepted; noted in `fetch_first_leg` docstring)

## Season rollover checklist (do every August)
Several config artifacts are pinned to a specific season and go stale silently — nothing
crashes, the app just quietly shows the wrong thing (a dead filter chip, last season's title
race, a missing primetime game). Walk this list when the new season's fixtures drop, usually
early-to-mid August. Line numbers are current as of the 2026-07-20 salvage but drift — `grep`
the token if a pointer misses.

- **`STORYLINES` — retire the expired entry, add the new season's** (`config.py:113`; schema
  comment above it `config.py:91-112`; gate in `app/storylines.py:get_active_storylines`,
  line 92). Entries carry an `end_date` (`config.py:124` — currently `"2026-05-31"` on
  `pl_title_race_25_26`, label "PL Title Race"). `get_active_storylines` drops any storyline
  past its `end_date`, so an expired one correctly stops shipping a chip — but nothing replaces
  it, and the Calendar loses its storyline filter entirely until a new entry is added. Bump the
  `id`/`label`/`description` to the new season and set a fresh `end_date`. **As of the 2026-07-20
  salvage this is still pending** — the 25-26 entry expired May 31 and no live storyline exists.
  (Leaving an entry `active` past its `end_date` was the dead-PL-chip bug; the date gate is the
  fix, not a reason to skip this.)
- **`TITLE_RACES` — re-pick the contenders and relabel** (`config.py:83`). Currently Arsenal +
  Man City (`team_ids: ["359", "382"]`) under label `"Premier League Title Race"`. Consumed by
  `get_title_races()` (`app/espn.py:787`; loop `for race_cfg in config.TITLE_RACES` at 794).
  Contenders are hand-picked, so last season's two-horse race persists into the new season until
  edited.
- **`NFL_PRIMETIME_NETWORKS` — re-verify against the new slate's rights deals** (`config.py:157`;
  consumed at `app/espn.py:407`). A game is included if it's primetime by weekday+hour **or** airs
  on a network in this set. The weekday branches (`app/espn.py:388-411`) cover Thu/Sun/Mon/Sat
  **only — there is no Friday branch**, so a Friday game is included *solely* via this network set.
  That's why `"Netflix"` is in it: Christmas 2026 falls on a Friday and the NFL Christmas games
  stream on Netflix, so both inclusion paths fail without it. Pinned by `tests/test_nfl_primetime.py`
  (Netflix Friday included; CBS Friday excluded — the fix stays specific, it doesn't blanket-include
  every Friday evening). If a streaming rights deal moves, update this set or those games vanish
  from the schedule with no error.
- **The `38 - gp` max-points assumption is Premier-League-only** (`app/espn.py:815`, inside
  `get_title_races()`). `remaining = 38 - gp` hardcodes a 38-match season, but the loop runs over
  **every** `TITLE_RACES` entry (`app/espn.py:794`), not just `eng.1`. La Liga and Serie A are also
  38 so they'd happen to work; **Bundesliga and Ligue 1 play 34**, so a title race in either would
  over-count remaining matches by 4 (12 points) — silently wrong output, no exception. Add a
  per-league match-count lookup before configuring a non-38-match race.
- **`NBA_NATIONAL_NETWORKS` is dead code, and NBA is unplugged — decide, then act** (`config.py:161`).
  Defined once and referenced nowhere else (verified 2026-07-20). Its comment (`config.py:159-160`)
  still claims "playoff games ... and nationally televised regular season", which is doubly wrong now:
  the live NBA rule is playoff/play-in only (`fetch_nba_games`, `app/espn.py:524`), AND since the
  brief-A1 revamp NBA is **unplugged entirely** — out of the fetchers, standings, and filter chips,
  kept only for a one-line restore (see the `get_all_games`/`get_all_standings` restore comments and
  the "NBA unplugged" notes in Key Design Decisions). So this set backs nothing. Either delete it, or
  if NBA is ever restored re-wire it deliberately — don't leave a comment implying regular-season
  national-TV coverage that no code path provides.
