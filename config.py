"""
Configuration for Sports Master Schedule.
Edit this file to customize your teams, availability, and preferences.
"""

# ── Your timezone ──────────────────────────────────────────────────
TIMEZONE = "US/Pacific"

# ── Work hours (you're unavailable during these times) ─────────────
# Days are 0=Monday through 6=Sunday
WORK_SCHEDULE = {
    "days": [0, 1, 2, 3, 4],   # Mon-Fri
    "start_hour": 8,             # 8 AM (including commute)
    "end_hour": 18,              # 6 PM (including commute)
}

# ── Teams you follow ──────────────────────────────────────────────
# Each team has an ESPN ID, the leagues to check, and an importance tier.
# Tiers: "must_watch", "notable", "major_event"
WATCHED_TEAMS = [
    {
        "name": "Manchester City",
        "espn_id": "382",
        "sport": "soccer",
        "leagues": ["eng.1", "uefa.champions", "eng.fa", "eng.league_cup"],
        "tier": "must_watch",
    },
    {
        "name": "Arsenal",
        "espn_id": "359",
        "sport": "soccer",
        "leagues": [
            "eng.1", "uefa.champions", "uefa.europa",
            "eng.fa", "eng.league_cup",
        ],
        "tier": "must_watch",
    },
    {
        "name": "Real Madrid",
        "espn_id": "86",
        "sport": "soccer",
        "leagues": ["esp.1", "uefa.champions"],
        "tier": "notable",
    },
    {
        "name": "Barcelona",
        "espn_id": "83",
        "sport": "soccer",
        "leagues": ["esp.1", "uefa.champions"],
        "tier": "notable",
    },
    {
        "name": "Bayern Munich",
        "espn_id": "132",
        "sport": "soccer",
        "leagues": ["ger.1", "uefa.champions"],
        "tier": "notable",
    },
]

# ── Title races to track ─────────────────────────────────────────
# Teams competing for a league title. Shown as a comparison widget
# on the Tables view. Set to empty list to disable.
TITLE_RACES = [
    {
        "league": "eng.1",
        "label": "Premier League Title Race",
        "team_ids": ["359", "382"],  # Arsenal, Man City
    },
]

# ── Storylines ───────────────────────────────────────────────────
# Storylines are narrative tags applied to games so you can filter the
# schedule down to one story (e.g., "show only PL title race games").
# This is a superset of the TITLE_RACES widget — title races stay as a
# standings comparison on the Tables view; storylines filter the
# schedule view.
#
# Schema per entry:
#   id          unique string used by the frontend filter
#   label       display name on chips and pills
#   description optional longer note (shown in a tooltip, if you add one)
#   active      bool; set False to hide without deleting
#   team_ids    list of ESPN team IDs — a game matches if ANY listed
#               team plays (home or away)
#   leagues     optional list of league slugs (e.g. ["eng.1"]); if
#               omitted, any league counts
#   start_date  optional ISO date "YYYY-MM-DD" — ignore games before
#   end_date    optional ISO date "YYYY-MM-DD" — ignore games after
#   logo_url    optional competition logo URL; rendered inside a cream
#               disc on the ochre storyline chip. Falls back to text-only
#               pill when omitted. Typical source: ESPN CDN
#               (https://a.espncdn.com/i/leaguelogos/soccer/500/<id>.png).
STORYLINES = [
    {
        "id": "pl_title_race_25_26",
        "label": "PL Title Race",
        "description": "Arsenal vs Man City for the 2025-26 Premier League title",
        "active": True,
        "team_ids": ["359", "382"],  # Arsenal, Man City
        "leagues": ["eng.1"],
        "logo_url": "https://a.espncdn.com/i/leaguelogos/soccer/500/23.png",
        # No start_date — past title-race fixtures are part of the story.
        # end_date stops tagging after the season ends.
        "end_date": "2026-05-31",
    },
]

# ── Leagues hidden from Calendar / Playoffs default views ────────
# Games in these leagues are NOT fetched when building the schedule,
# even if a watched team is in them. Standings (Tables tab) are
# unaffected — the league stays fully visible there. Add a league
# slug here to declutter the Calendar without uninstalling the team
# (e.g., Bayern stays in WATCHED_TEAMS so their UCL games still
# surface via uefa.champions; only the Bundesliga league matches
# are suppressed here).
CALENDAR_EXCLUDED_LEAGUES = {"ger.1", "esp.1"}

# ── Premier League "Big 6" for detecting top matchups ─────────────
# When two of these teams play each other, it's flagged as "notable"
PL_TOP_TEAMS = {
    "382": "Manchester City",
    "359": "Arsenal",
    "364": "Liverpool",
    "360": "Manchester United",
    "363": "Chelsea",
    "367": "Tottenham Hotspur",
}

# ── NFL settings ──────────────────────────────────────────────────
# We show all primetime games (TNF, SNF, MNF) and flag RedZone on Sundays.
# Primetime is detected by game time (evening UTC) + national broadcast.
NFL_PRIMETIME_NETWORKS = {"NBC", "Peacock", "ESPN", "ABC", "Prime Video", "Amazon"}

# ── NBA settings ──────────────────────────────────────────────────
# Show playoff games (season type 3) and nationally televised regular season.
NBA_NATIONAL_NETWORKS = {"ESPN", "TNT", "ABC", "NBA TV", "Prime Video"}

# ── League display names ──────────────────────────────────────────
LEAGUE_NAMES = {
    "eng.1": "Premier League",
    "eng.fa": "FA Cup",
    "eng.league_cup": "League Cup",
    "esp.1": "La Liga",
    "esp.copa_del_rey": "Copa del Rey",
    "ger.1": "Bundesliga",
    "ger.dfb_pokal": "DFB-Pokal",
    "ita.1": "Serie A",
    "fra.1": "Ligue 1",
    "uefa.champions": "Champions League",
    "uefa.europa": "Europa League",
    "uefa.europa.conf": "Conference League",
    "fifa.cwc": "Club World Cup",
    "nfl": "NFL",
    "nba": "NBA",
}

# ── Cache settings ────────────────────────────────────────────────
CACHE_TTL_SECONDS = 3600  # Re-fetch from ESPN after 1 hour
