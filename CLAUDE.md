# Sports Master Schedule

Personal sports schedule tracker — shows upcoming games filtered by interest level and availability.

## Tech Stack
- Python 3 / Flask backend
- In-memory cache with TTL (no database)
- Vanilla HTML/CSS/JS frontend
- ESPN public API (no auth required)

## Running
```
pip install --user --break-system-packages -r requirements.txt
python app.py
```
Server runs on http://localhost:5000 with debug/auto-reload enabled.

## API Routes
- `GET /api/schedule?month=YYYY-MM&refresh=true` — returns games for a full calendar month (padded Mon-Sun)
- `GET /api/standings?refresh=true` — returns standings + title race data for all tracked leagues
- `POST /api/games/<id>/watched` — toggle watched status (`{"watched": true}`)
- `POST /api/games/<id>/notes` — save user notes (`{"notes": "..."}`)
- Legacy `?week=prev|this|next` still supported for backward compat

## Key Design Decisions
- ESPN API has no date-range queries for soccer/NBA — we fetch per-day or per-team-season
- NFL primetime detection converts ESPN's UTC times to Pacific, then checks local hour + broadcast network (no explicit "primetime" flag)
- Soccer requires separate API calls per league for the same team (eng.1, uefa.champions, eng.fa, etc.)
- Games are tagged with importance tiers: "must_watch", "notable", "major_event"
- NBA: only playoff and play-in games are shown — regular season is completely excluded
- Availability is simple: Mon-Fri 8am-6pm PT = unavailable, everything else = available
- Title races are configured in config.py TITLE_RACES and rendered as a widget above standings
- Month view fetches ~35 days of data — first load is slow (many per-day API calls), cache makes subsequent loads fast
- Desktop renders `calendar-grid` (month grid with dots), mobile renders `mobile-calendar` (2-week vertical list with inline cards) — same DOM element, JS switches the className
- User data (watched, notes) stored in `data/userdata.json` — not gitignored contents, but the directory is needed at runtime
- Interactive elements inside game cards (watched button, notes textarea) must call `stopPropagation()` to prevent toggling the card's expand/collapse

## ESPN API Gotchas
- Team schedule endpoint (`/teams/{id}/schedule`) only returns PAST games — use scoreboard-by-date + league calendar for future fixtures
- Soccer season years use the start year: PL 2025-26 = `season=2025`
- Standings endpoint is `site.api.espn.com/apis/v2/...` (v2 path), NOT `site.web.espn.com`
- Score values for soccer come back as floats ("2.0") — must cast via `int(float(val))`
- NBA season_type: 2=regular, 3=playoffs, 5=play-in
- The `note` field on standings entries contains zone info (Champions League, Relegation, etc.)
- Broadcaster names are truncated ("USA Net", "Tele") — cleaned via `BROADCAST_DISPLAY` mapping in `espn.py`
- Competitor records (`records[].summary`) must be extracted per-team from the competitor object, not the event

## Code Style
- Beginner-friendly: clear variable names, comments on non-obvious logic
- No unnecessary abstractions
- Frontend uses safe DOM methods (createElement/textContent) — no innerHTML (security hook blocks it)
- Frontend uses `var` (not `let`/`const`) and function declarations — keep consistent
- `el(tag, cls, txt)` helper builds all DOM nodes; `appendIf(parent, child)` for nullable nodes like logos
- Google Fonts (Barlow Condensed) loaded via CDN for broadcast-style typography

## Project Layout
- `app.py` — Flask entry point, creates and runs the app on port 5000
- `config.py` — all user preferences: teams, work schedule, title races, league settings
- `app/espn.py` — ESPN API client with in-memory cache
- `app/importance.py` — tier classification (must_watch / notable / major_event)
- `app/availability.py` — work-hours tagging (can_watch / will_miss)
- `app/routes.py` — Flask routes: `/api/schedule`, `/api/standings`, `/api/games/<id>/watched|notes`
- `app/userdata.py` — watched flags + notes persistence (JSON file in `data/userdata.json`)
- `templates/index.html` — single-page HTML shell (header, tabs, grid containers, footer legend)
- `static/app.js` — all frontend rendering (calendar grid, detail panel, standings tables, title race widget)
- `static/style.css` — all styles (dark theme, responsive, sport-colored accents)

## Testing
No test suite exists. Verify changes by running the app and checking the UI manually.
