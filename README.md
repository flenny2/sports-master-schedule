# Sports Master Schedule

A personal dashboard that shows upcoming games you care about, filtered by importance and your availability.

## What it shows

| Tier | What |
|---|---|
| **Must Watch** | NFL primetime (TNF/SNF/MNF), RedZone Sundays, all Manchester City matches |
| **Notable** | Champions League, Real Madrid, Barcelona, top-6 Premier League matchups |
| **Major Event** | NBA playoffs, nationally televised NBA games |

Games are color-coded by whether you can watch them based on your work schedule (Mon–Fri, 8 AM – 6 PM PT).

## Setup

**1. Install dependencies:**

```bash
# If you have python3-venv:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# If not (Ubuntu/Debian):
pip install --user --break-system-packages -r requirements.txt
```

**2. Run the app:**

```bash
python3 app.py
```

**3. Open in your browser:**

```
http://localhost:5000
```

## Customization

Edit `config.py` to change:

- **Your teams** — add/remove entries in `WATCHED_TEAMS`
- **Work schedule** — update `WORK_SCHEDULE` hours and days
- **Timezone** — change `TIMEZONE` (uses pytz timezone names)
- **Top PL teams** — edit `PL_TOP_TEAMS` to change which matchups count as notable

## How it works

- Pulls data from ESPN's public API (no API key needed)
- Data is cached in memory for 1 hour — hit the "Refresh Data" button to force a re-fetch
- Games are tagged with importance tiers and availability automatically
- Week navigation lets you check previous, current, and next week

## Data source

Uses ESPN's undocumented public API. No authentication or API key required. These endpoints are widely used but unofficial — they could change without notice. If something breaks, the API response format may have changed.
