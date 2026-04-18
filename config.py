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
