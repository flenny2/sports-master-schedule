# Sports Master Schedule

Personal sports schedule tracker — shows upcoming games filtered by interest level and availability. Visual direction is editorial/broadsheet: cream newsprint in light mode, warm coffee-black in dark mode, bold sport-colour accents.

## Tech Stack
- Python 3 / Flask backend
- In-memory cache with TTL (no database)
- Vanilla HTML/CSS/JS frontend (no build step, no bundler, no framework)
- ESPN public API (no auth required)
- Google Fonts via CDN: **Archivo Black** (display), **Archivo** (body/UI), **Fraunces** opsz 900 (scores + kickoff times), **JetBrains Mono** (records, datelines, fixture chips)

## Running
```
pip install --user --break-system-packages -r requirements.txt
python app.py
```
Server runs on http://localhost:5000 with debug/auto-reload enabled.

## API Routes
- `GET /api/schedule?month=YYYY-MM&refresh=true` — returns games for a full calendar month (padded Mon-Sun)
- `GET /api/standings?refresh=true` — returns standings + title race data for all tracked leagues
- `GET /api/storylines` — active storylines for the frontend filter chips (includes optional `logo_url` per storyline)
- `POST /api/games/<id>/watched` — toggle watched status (`{"watched": true}`)
- `POST /api/games/<id>/notes` — save user notes (`{"notes": "..."}`)
- Legacy `?week=prev|this|next` still supported for backward compat

## Key Design Decisions
- **Fetchers**: NFL/NBA use per-day scoreboard calls via `_parallel_fetch_days`; soccer uses one date-range scoreboard call per watched league (the scoreboard endpoint accepts `dates=YYYYMMDD-YYYYMMDD` and returns every event in the window in a single response)
- **NFL primetime detection**: converts ESPN's UTC times to Pacific, then checks local hour + broadcast network (no explicit "primetime" flag)
- **Soccer**: requires separate API calls per league for the same team (eng.1, uefa.champions, eng.fa, etc.); Bayern / Real Madrid / Barcelona stay in `WATCHED_TEAMS` specifically so their UCL games surface
- **Importance tiers**: `must_watch` / `notable` / `major_event` — set by `app/importance.py`
- **NBA coverage**: only playoff and play-in games are shown — regular season is completely excluded
- **Availability** is simple: Mon-Fri 8am-6pm PT = unavailable, everything else = available
- **Title races** are configured in `config.TITLE_RACES` and rendered as a widget on the Tables view. Contenders sorted by standings rank ascending (not points), so tiebreakers hold. Widget header uses context-aware gap strings — `"MNC LEAD BY 5 PTS"` / `"LEVEL ON POINTS"` / `" · ARS HAVE 1 GAME IN HAND"` — with team abbreviations for scannability
- **Storylines** are configured in `config.STORYLINES` and filter the Calendar view (chip row above grid + gold pills on matching cards). Each entry can carry an optional `logo_url` — frontend renders the logo inside a cream disc holder on the ochre pill, or falls back to text-only. Separate from `TITLE_RACES`, which stays as the Tables-view widget
- **Series context**: `app/series_context.py` adds `series_summary` + `series_detail` to every playoff game (NBA series score, UCL leg + aggregate). Runs after `tag_playoff` and short-circuits on non-playoff games
- **CALENDAR_EXCLUDED_LEAGUES** (in `config.py`): set of league slugs hidden from Calendar/Playoffs fetches. Standings endpoint is unaffected so the league stays visible on the Tables tab. Currently seeded `{"ger.1", "esp.1"}` — Bundesliga and La Liga. Watched teams in those leagues still surface via their UEFA competitions
- **Month view cold load**: ~22 soccer API calls (one scoreboard range query per watched league + per-team schedules for past games); cache makes repeat visits instant
- **Desktop vs mobile calendar**: desktop renders `calendar-grid` (month grid with dots), mobile renders `mobile-calendar` (7-day rolling window starting from today; nav arrows shift ±7 days on mobile, paginate whole months on desktop) — same DOM element, JS switches the className
- **Day-boundary separators**: each mobile day block carries a 2px ink rule above it; desktop detail panel gets the same treatment. Within a single day, `appendGamesWithDayDivider` injects a centred italic "Coming Up" / "Live & Coming Up" divider once per day when the status transitions from `post` → `live`/`pre`
- **Theme toggle**: light + dark, resolved in the `<head>` via an inline script BEFORE first paint (no FOUC). Precedence: `localStorage.theme` override → `prefers-color-scheme` → light default. Clicking the header toggle flips and persists to `localStorage`
- **Today tab removed** (April 2026): Calendar is the default view and already lands on today via rolling-week + desktop scroll-to-today, so Today was duplicating itself. The "today strip" (top banner showing live / next game) stays but is PASSIVE — no `role="button"`, no `tabindex`, no click handler, no `cursor: pointer`
- **Sticky tab bar**: `.tab-bar` sticks at `top: 0` across Calendar / Playoffs / Tables. Masthead + month-nav scroll away
- **User data** (watched, notes) stored in `data/userdata.json` — not gitignored contents, but the directory is needed at runtime. Watched toggle lives in the expanded-card view (moved off the default meta row)
- **Interactive elements inside game cards** (watched button, notes textarea) must call `stopPropagation()` to prevent toggling the card's expand/collapse

## ESPN API Gotchas
- **Team schedule endpoint** (`/teams/{id}/schedule`) only returns PAST games — use scoreboard with a date range for future fixtures. Also strips `competition.series` / `competition.leg` / `notes` — past UCL games fetched via this path lose their round/leg metadata
- **Scoreboard** accepts `dates=YYYYMMDD-YYYYMMDD` for ranges and `dates=YYYYMM` for whole months — one call returns every event in the window, works for both domestic leagues and cups (use this instead of per-day scanning)
- Soccer season years use the start year: PL 2025-26 = `season=2025`
- **Standings endpoint** is `site.api.espn.com/apis/v2/...` (v2 path), NOT `site.web.espn.com`
- Score values for soccer come back as floats (`"2.0"`) — must cast via `int(float(val))`
- **NBA season_type**: 2=regular, 3=playoffs, 5=play-in. Play-in games have `competition.series = {}` (empty — short-circuit in series tagger)
- **NBA series data** lives at `competition.series` — has `summary` (pre-formatted "LAL lead series 2-1"), `totalCompetitions` (best-of-N), `competitors: [{id, wins}]`. Game 1 pre-game has `wins: 0` on both; treat as "Game 1 of N"
- **UCL/Europa/Conference two-leg ties** expose `competition.leg = {value: 1|2}` and `competition.series.title` (round name). For 2nd-leg aggregate-going-in, the reliable source is fetching the 1st leg directly (via `fetch_first_leg`) — ESPN's `aggregateScore` field only populates after the 2nd leg completes
- `note` field on standings entries contains zone info (Champions League, Relegation, etc.)
- **Broadcaster names** are truncated ("USA Net", "Tele") — cleaned via `BROADCAST_DISPLAY` mapping in `espn.py`
- **Competitor records** (`records[].summary`) must be extracted per-team from the competitor object, not the event
- **Playoff detection** uses three belt-and-suspenders triggers — league in `KNOCKOUT_CUP_LEAGUES` (FA Cup etc.), notes keyword (`"quarterfinal"`, `"final"` etc.), OR `raw_series.title` in `KNOWN_KNOCKOUT_ROUND_TITLES` (`"Round of 16"`, `"Quarterfinals"`, `"Semifinals"`, `"Final"`, `"Knockout Round Playoffs"`). Any one is sufficient; structured-title is preferred when present

## Code Style
- **Beginner-friendly**: clear variable names, comments on non-obvious logic
- **No unnecessary abstractions**
- **Frontend uses safe DOM methods** (`createElement` / `textContent`) — no `innerHTML` (security hook blocks it)
- **Frontend uses `var`** (not `let`/`const`) and function declarations — keep consistent
- **`el(tag, cls, txt)`** helper builds all DOM nodes; **`appendIf(parent, child)`** for nullable nodes like logos
- **Theme** switches via `data-theme` attribute on `<html>`; every themed token lives in `:root[data-theme="light"]` and `:root[data-theme="dark"]` blocks. Add a new themed token in BOTH or it breaks
- **Sport accents are the singular bold element per card** — tier / post-season / availability / series / league / storyline all stay grayscale-ish so the sport rail + winner-score tint pop. Any new pill or tag should follow this rule
- **WCAG AA** (≥4.5:1 for body text, ≥3:1 for UI components) must pass in both themes before shipping any colour addition

## Project Layout
- `app.py` — Flask entry point, creates and runs the app on port 5000
- `config.py` — all user preferences: teams, work schedule, title races, storylines, league exclusions, NFL network list
- `app/espn.py` — ESPN API client with in-memory cache; `fetch_first_leg` helper for 2nd-leg UCL aggregate lookup
- `app/importance.py` — tier classification (`must_watch` / `notable` / `major_event`)
- `app/availability.py` — work-hours tagging (`can_watch` / `will_miss`)
- `app/playoff.py` — `is_playoff` + `playoff_round` tagging; three-trigger detection (league list / notes keyword / structured title)
- `app/series_context.py` — `series_summary` + `series_detail` per playoff game (NBA score, UCL leg + aggregate)
- `app/storylines.py` — narrative tagging (`storylines: [{id, label, logo_url?}]` per game) driven by `config.STORYLINES`
- `app/routes.py` — Flask routes: `/api/schedule`, `/api/standings`, `/api/storylines`, `/api/games/<id>/watched|notes`
- `app/userdata.py` — watched flags + notes persistence (JSON file in `data/userdata.json`)
- `templates/index.html` — single-page HTML shell; inline FOUC-safe theme script in `<head>`, theme-toggle button in header
- `static/app.js` — all frontend rendering (calendar grid, detail panel, standings tables, title race widget, cards with the broadsheet DOM pattern)
- `static/style.css` — full broadsheet style system: per-theme tokens, typography, cards, tables, responsive rules

## Testing
Pytest suite in `tests/` covers availability, importance, userdata, playoff tagging, series context, storylines, auth, and ESPN parsing helpers (no network). Run: `python3 -m pytest tests/ -v`

For anything touching the UI or live ESPN responses, still verify manually by running the app and exercising the feature in a browser.

## Known TODOs / deferred features
Flagged by the user across sessions — not currently scheduled:
- **Team detail view**: click a team (logo/name) → dedicated page for that team's recent results, upcoming fixtures, current form, standings position. Needs investigation of ESPN's team-summary endpoints
- **NFL draft pick tracker**: follow the draft live and log my team's picks. Needs investigation of ESPN's draft feed
- **Phase 3 broadsheet polish**: any real-phone rendering issues found after the Render deploy (font loading, sticky-tab quirks on iOS Safari, viewport math on notched devices, etc.) will be triaged in a separate session
- Past UCL games fetched via team-schedule lose their `series`/`leg`/`notes` metadata (noted inline in `fetch_first_leg` docstring); score still visible on the card so it's an acceptable trade-off, but a future fetch-path rework could recover the round label and aggregate
