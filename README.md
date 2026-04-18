# Sports Master Schedule

A personal dashboard that shows upcoming games you care about, filtered by
importance and your work availability. Built as a single-user Flask app with
a vanilla-JS dark UI.

## What it shows

| Tier | What |
|---|---|
| **Must Watch** | NFL primetime (TNF/SNF/MNF), RedZone Sundays, all Manchester City & Arsenal matches |
| **Notable**    | Champions League, Real Madrid, Barcelona, Bayern Munich, top-6 Premier League matchups |
| **Major Event**| NBA playoffs and play-in tournament |

Games also carry a **Post-Season** tag when they're knockout-stage (NBA
playoffs, NFL postseason, FA Cup, League Cup, Copa del Rey, DFB-Pokal,
Conference League, and UCL/Europa knockouts).

Games are color-coded by whether you can watch them based on your work
schedule (Mon–Fri, 8 AM – 6 PM PT by default).

## Tabs

- **Calendar** — full month grid with per-day game dots (desktop) or a
  2-week vertical list (mobile). Swipe left/right on mobile to navigate
  months.
- **Today** — live / upcoming / completed sections for today's games,
  with countdown timers for upcoming kickoffs.
- **Playoffs** — knockout / postseason games only, grouped by date with
  Today + Tomorrow auto-expanded and all further dates collapsed.
- **Tables** — league standings for the Premier League, La Liga,
  Bundesliga, and the Champions League, plus NBA conference standings
  and the Premier League title-race widget.

A persistent "Today" strip at the top of every view shows the live game
count and next kickoff, and links to the Today tab.

## Setup

Install dependencies and run the dev server:

```bash
pip install --user --break-system-packages -r requirements.txt
python3 app.py
# → http://localhost:5000
```

Edit `config.py` to change:
- **Your teams** — entries in `WATCHED_TEAMS`
- **Work schedule** — `WORK_SCHEDULE`
- **Timezone** — `TIMEZONE`
- **Title races** — `TITLE_RACES`

## Tests

```bash
python3 -m pytest tests/ -v
```

Covers the importance / availability / playoff taggers, userdata
persistence, ESPN parse helpers, and the write-auth flow. No network
required — ESPN is mocked at the `_cached_get` boundary where needed.

## Deployment (Render)

The repo ships with `render.yaml` for one-click Blueprint deploys.
Manual setup is also fine — pick **Web Service**, point it at this
repo, and use:

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60 "app:create_app()"`

Netlify won't work — this is a Flask server, not a static site.

### Environment variables

| Var | Purpose |
|---|---|
| `SCHEDULE_TOKEN` | Optional. When set, POST endpoints (watched / notes) require a matching cookie. Visit `/?token=<value>` once to install the cookie; reads stay public. Leave unset for local dev or behind a VPN. |
| `DATA_DIR` | Optional. Directory for `userdata.json`. Defaults to `./data`. Set to a mounted disk path (e.g. `/var/data`) when you add a Render Disk. |

### Persistent userdata

Render's free tier has an ephemeral filesystem, so `data/userdata.json`
resets on every restart. To keep your watched flags and notes around,
upgrade past free and uncomment the `disk:` block in `render.yaml`,
then set `DATA_DIR=/var/data` in the dashboard.

## Data source

Uses ESPN's undocumented public API. No authentication or API key
required. These endpoints are widely used but unofficial — they could
change without notice. If something breaks, the API response format may
have changed. Responses are cached in memory for 1 hour; the Refresh
button force-clears the cache.
