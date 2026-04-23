"""
ESPN public API client.

Fetches game schedules from ESPN's undocumented public endpoints.
No API key needed. Data is cached in memory to avoid hammering the API.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor
import requests
from datetime import datetime, timedelta
import pytz

import config

# Max parallel HTTP requests — keeps us gentle on ESPN's public endpoints
_MAX_WORKERS = 8

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"

# ESPN returns abbreviated/truncated broadcaster names — clean them up
BROADCAST_DISPLAY = {
    "USA Net": "USA",
    "Tele": "Telemundo",
    "Amazon": "Prime Video",
    "CBSSN": "CBS Sports",
    "NBATV": "NBA TV",
}

# ── In-memory cache ───────────────────────────────────────────────
# Format: { "cache_key": (data, timestamp) }
# Lock protects writes when multiple threads fetch in parallel. Reads of
# a single key are atomic in CPython, but double-writes from two threads
# racing on the same URL would waste API calls.
_cache = {}
_cache_lock = threading.Lock()


def _cached_get(url, params=None):
    """
    GET request with simple time-based caching.
    Returns parsed JSON, or None if the request fails.
    """
    # Build a cache key from the URL + sorted params
    param_str = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    cache_key = f"{url}?{param_str}"

    # Check cache
    cached = _cache.get(cache_key)
    if cached is not None:
        data, fetched_at = cached
        age = time.time() - fetched_at
        if age < config.CACHE_TTL_SECONDS:
            return data

    # Fetch fresh data
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        with _cache_lock:
            _cache[cache_key] = (data, time.time())
        return data
    except requests.RequestException as e:
        print(f"[ESPN] Request failed: {url} — {e}")
        return None


def clear_cache():
    """Clear all cached data (used by the manual refresh button)."""
    with _cache_lock:
        _cache.clear()


def _parallel_fetch_days(sport, league_slug, start_date, end_date):
    """
    Fetch per-day scoreboards for a date range in parallel.
    Returns a deduplicated list of parsed games.
    """
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)

    seen_ids = set()
    games = []

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        results = executor.map(
            lambda d: fetch_scoreboard(sport, league_slug, d),
            dates,
        )
        for day_games in results:
            for game in day_games:
                gid = game["id"]
                if gid not in seen_ids:
                    seen_ids.add(gid)
                    games.append(game)

    return games


# ── Parsing helpers ───────────────────────────────────────────────

def _parse_game(event, sport, league_slug):
    """
    Turn an ESPN event object into a clean game dict.
    Returns None if the event can't be parsed.
    """
    try:
        competition = event["competitions"][0]
        competitors = competition.get("competitors", [])

        # Figure out home vs away
        home = away = None
        for team_info in competitors:
            team = team_info.get("team", {})
            entry = {
                "name": team.get("displayName", "Unknown"),
                "abbreviation": team.get("abbreviation", "???"),
                "id": str(team.get("id", "")),
                "logo": team.get("logo", ""),
            }
            # Extract team record if available (e.g. "25-10-3")
            for rec in team_info.get("records", []):
                if rec.get("type") == "total":
                    entry["record"] = rec.get("summary", "")
                    break
            if team_info.get("homeAway") == "home":
                home = entry
            else:
                away = entry

        if not home or not away:
            return None

        # Broadcast info
        broadcasts = []
        is_national = False
        for b in competition.get("broadcasts", []):
            if b.get("market") == "national":
                is_national = True
            for name in b.get("names", []):
                broadcasts.append(BROADCAST_DISPLAY.get(name, name))

        # Also check geoBroadcasts for US-specific info
        for gb in competition.get("geoBroadcasts", []):
            market = gb.get("market", {})
            if market.get("type") == "National":
                is_national = True

        # Game status
        status_obj = competition.get("status", {}).get("type", {})
        status = status_obj.get("state", "pre")  # pre, in, post

        # Score (only if game started)
        score = None
        if status in ("in", "post"):
            home_score = None
            away_score = None
            for team_info in competitors:
                s = team_info.get("score", {})
                # Score can be a string like "24" or a dict with "value"
                if isinstance(s, dict):
                    val = s.get("value", s.get("displayValue"))
                else:
                    val = s
                if team_info.get("homeAway") == "home":
                    home_score = val
                else:
                    away_score = val
            if home_score is not None:
                # Clean up float scores like "2.0" → "2"
                score = {
                    "home": str(int(float(home_score))),
                    "away": str(int(float(away_score))),
                }

        # Notes (playoff round, leg info, etc.)
        notes_list = competition.get("notes", [])
        notes = notes_list[0].get("headline", "") if notes_list else ""

        # Season type: 1=preseason, 2=regular, 3=postseason, 5=play-in (NBA)
        season_type = event.get("season", {}).get("type", 2)

        return {
            "id": event.get("id", ""),
            "sport": sport,
            "league": league_slug,
            "league_name": config.LEAGUE_NAMES.get(league_slug, league_slug),
            "date": event.get("date", ""),
            "name": event.get("name", f"{away['name']} at {home['name']}"),
            "short_name": event.get("shortName", ""),
            "home_team": home,
            "away_team": away,
            "venue": competition.get("venue", {}).get("fullName", ""),
            "broadcasts": broadcasts,
            "is_national": is_national,
            "status": status,
            "score": score,
            "notes": notes,
            "season_type": season_type,
            # tier and availability get set later by importance.py / availability.py
            "tier": None,
            "availability": None,
        }
    except (KeyError, IndexError, TypeError) as e:
        print(f"[ESPN] Failed to parse event: {e}")
        return None


def _filter_to_date_range(games, start_date, end_date):
    """Keep only games whose date falls within [start_date, end_date]."""
    tz = pytz.timezone(config.TIMEZONE)
    filtered = []
    for game in games:
        try:
            # ESPN dates are ISO 8601 UTC like "2026-04-11T15:00Z"
            game_dt = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
            game_local = game_dt.astimezone(tz)
            if start_date <= game_local.date() <= end_date:
                filtered.append(game)
        except (ValueError, KeyError):
            continue
    return filtered


# ── Fetching functions ────────────────────────────────────────────

def fetch_team_schedule(sport, league_slug, team_id):
    """
    Fetch a team's full season schedule.
    Returns a list of parsed game dicts.
    """
    url = f"{BASE_URL}/{sport}/{league_slug}/teams/{team_id}/schedule"
    data = _cached_get(url)
    if not data:
        return []

    games = []
    for event in data.get("events", []):
        game = _parse_game(event, sport, league_slug)
        if game:
            games.append(game)
    return games


def fetch_scoreboard(sport, league_slug, date_str=None):
    """
    Fetch the scoreboard for a sport/league.
    date_str format: "YYYYMMDD" (optional, for day-specific results).
    Returns a list of parsed game dicts.
    """
    url = f"{BASE_URL}/{sport}/{league_slug}/scoreboard"
    params = {"dates": date_str} if date_str else None

    data = _cached_get(url, params)
    if not data:
        return []

    games = []
    for event in data.get("events", []):
        game = _parse_game(event, sport, league_slug)
        if game:
            games.append(game)
    return games


# ── Sport-specific fetchers ───────────────────────────────────────

def fetch_nfl_games(start_date, end_date):
    """
    Fetch NFL games across the given date range.
    Includes past games (with final scores) + upcoming games,
    filtered to primetime (TNF, SNF, MNF) and RedZone Sundays.
    """
    # Iterate day-by-day so past weeks + future dates are both covered.
    # Without a `dates=` param, ESPN only returns the current week.
    raw_games = _parallel_fetch_days("football", "nfl", start_date, end_date)

    # Filter to date range (scoreboard-by-date is already scoped, but
    # this also handles edge cases around timezone boundaries)
    games = _filter_to_date_range(raw_games, start_date, end_date)

    # Identify primetime and RedZone-relevant games
    tz = pytz.timezone(config.TIMEZONE)
    primetime_games = []

    for game in games:
        try:
            game_dt = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
            game_local = game_dt.astimezone(tz)
            hour = game_local.hour
            weekday = game_local.weekday()  # 0=Mon, 6=Sun

            is_primetime = False

            # Thursday night: Thursday after 5pm local
            if weekday == 3 and hour >= 17:
                is_primetime = True
            # Sunday night: Sunday after 5pm local
            elif weekday == 6 and hour >= 17:
                is_primetime = True
            # Monday night: Monday after 5pm local
            elif weekday == 0 and hour >= 17:
                is_primetime = True
            # Saturday primetime (late season / playoffs)
            elif weekday == 5 and hour >= 17:
                is_primetime = True

            # Check broadcast networks too
            has_primetime_network = bool(
                set(game["broadcasts"]) & config.NFL_PRIMETIME_NETWORKS
            )

            # RedZone window: Sunday 10am-5pm PT (the afternoon games)
            is_redzone_window = weekday == 6 and 10 <= hour < 17

            if is_primetime or has_primetime_network:
                game["nfl_slot"] = "Primetime"
                primetime_games.append(game)
            elif is_redzone_window:
                game["nfl_slot"] = "RedZone Window"
                primetime_games.append(game)

        except (ValueError, KeyError):
            continue

    return primetime_games


def fetch_soccer_games(start_date, end_date):
    """
    Fetch soccer games for watched teams + top PL matchups.
    """
    games = []
    seen_ids = set()  # Avoid duplicates across league queries

    # Build a league → {watched team ids} map for pass 2's filter.
    # E.g. {"eng.1": {"359", "382"}, "uefa.champions": {"86", "83", ...}}.
    watched_by_league = {}
    for team in config.WATCHED_TEAMS:
        if team["sport"] != "soccer":
            continue
        for league in team["leagues"]:
            watched_by_league.setdefault(league, set()).add(team["espn_id"])

    # ── Pass 1: each watched team's schedule endpoint ──
    # Returns past games with full records / final scores. Future games
    # are handled by pass 2 because this endpoint doesn't return them.
    team_league_pairs = []
    for team in config.WATCHED_TEAMS:
        if team["sport"] != "soccer":
            continue
        for league in team["leagues"]:
            team_league_pairs.append((league, team["espn_id"]))

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        results = executor.map(
            lambda p: fetch_team_schedule("soccer", p[0], p[1]),
            team_league_pairs,
        )
        for team_games in results:
            for game in team_games:
                if game["id"] not in seen_ids:
                    seen_ids.add(game["id"])
                    games.append(game)

    # ── Pass 2: one date-range scoreboard call per league ──
    # ESPN's scoreboard endpoint accepts dates=YYYYMMDD-YYYYMMDD and
    # returns every event in that window in a single response, for both
    # domestic leagues and cup competitions. One call per league — no
    # per-day scanning, no calendar parsing. We keep games that involve
    # a watched team or (PL only) are a top-6 vs top-6 matchup.
    top_ids = set(config.PL_TOP_TEAMS.keys())
    date_range = (
        f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"
    )

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        league_results = executor.map(
            lambda slug: (slug, fetch_scoreboard("soccer", slug, date_range)),
            list(watched_by_league.keys()),
        )
        for league_slug, league_games in league_results:
            watched_ids = watched_by_league[league_slug]
            for game in league_games:
                if game["id"] in seen_ids:
                    continue
                home_id = game["home_team"]["id"]
                away_id = game["away_team"]["id"]
                involves_watched = (
                    home_id in watched_ids or away_id in watched_ids
                )
                # PL top-6 matchup is a separate inclusion path
                is_top_pl_matchup = (
                    league_slug == "eng.1"
                    and home_id in top_ids
                    and away_id in top_ids
                )
                if involves_watched or is_top_pl_matchup:
                    seen_ids.add(game["id"])
                    games.append(game)

    # Filter to requested date range
    return _filter_to_date_range(games, start_date, end_date)


def fetch_nba_games(start_date, end_date):
    """
    Fetch NBA games — only playoffs and play-in tournament.
    Regular season games are excluded no matter how big they seem.
    """
    day_games = _parallel_fetch_days(
        "basketball", "nba", start_date, end_date)

    games = []
    seen_ids = set()
    for game in day_games:
        if game["id"] in seen_ids:
            continue

        # Only include playoff (season type 3) or play-in (season type 5)
        season_type = game.get("season_type", 2)
        notes_lower = game.get("notes", "").lower()

        is_postseason = season_type in (3, 5)
        has_playoff_notes = any(
            kw in notes_lower
            for kw in ("playoff", "play-in", "finals", "semifinal", "conference")
        )

        if is_postseason or has_playoff_notes:
            # is_playoff itself is set later by app.playoff.tag_playoff
            seen_ids.add(game["id"])
            games.append(game)

    return games


# ── Main entry point ──────────────────────────────────────────────

def get_all_games(start_date, end_date):
    """
    Fetch all relevant games across all sports for a date range.
    Returns a list of game dicts sorted by date.
    """
    # Run the three sport fetchers in parallel. Each one internally runs
    # its own per-day pool, but they don't share state so they can nest.
    fetchers = [fetch_nfl_games, fetch_soccer_games, fetch_nba_games]
    all_games = []
    with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
        futures = [
            executor.submit(fn, start_date, end_date) for fn in fetchers
        ]
        for f in futures:
            try:
                all_games.extend(f.result())
            except Exception as e:
                print(f"[ESPN] sport fetch failed: {e}")

    # Sort by date
    all_games.sort(key=lambda g: g.get("date", ""))

    # Deduplicate by ID (just in case)
    seen = set()
    unique = []
    for game in all_games:
        if game["id"] not in seen:
            seen.add(game["id"])
            unique.append(game)

    return unique


# ── Standings ─────────────────────────────────────────────────────

# ESPN clincher codes → human-readable labels
NBA_CLINCH_LABELS = {
    "z": "clinched #1",
    "y": "clinched div",
    "x": "clinched playoff",
    "pb": "play-in",
    "e": "eliminated",
}


def _stat_val(stats_list, name, default=""):
    """Pull a stat's displayValue from ESPN's stats array."""
    for s in stats_list:
        if s["name"] == name:
            return s.get("displayValue", s.get("value", default))
    return default


def fetch_standings(sport, league_slug):
    """
    Fetch standings for a sport/league.
    Returns a dict with league info and groups of team entries.
    """
    url = f"https://site.api.espn.com/apis/v2/sports/{sport}/{league_slug}/standings"
    data = _cached_get(url)
    if not data:
        return None

    league_name = config.LEAGUE_NAMES.get(league_slug, data.get("name", league_slug))

    # Build a set of watched team IDs for highlighting
    watched_ids = set()
    for t in config.WATCHED_TEAMS:
        watched_ids.add(t["espn_id"])
    top_pl_ids = set(config.PL_TOP_TEAMS.keys())

    groups = []
    for child in data.get("children", []):
        entries = child.get("standings", {}).get("entries", [])
        teams = []

        for entry in entries:
            team_data = entry.get("team", {})
            team_id = str(team_data.get("id", ""))
            raw_stats = entry.get("stats", [])
            note = entry.get("note", {})

            # Build a stat dict based on sport type
            if sport == "soccer":
                stats = {
                    "gp":  _stat_val(raw_stats, "gamesPlayed"),
                    "w":   _stat_val(raw_stats, "wins"),
                    "d":   _stat_val(raw_stats, "ties"),
                    "l":   _stat_val(raw_stats, "losses"),
                    "gf":  _stat_val(raw_stats, "pointsFor"),
                    "ga":  _stat_val(raw_stats, "pointsAgainst"),
                    "gd":  _stat_val(raw_stats, "pointDifferential"),
                    "pts": _stat_val(raw_stats, "points"),
                }
            else:
                # Basketball (NBA)
                stats = {
                    "w":      _stat_val(raw_stats, "wins"),
                    "l":      _stat_val(raw_stats, "losses"),
                    "pct":    _stat_val(raw_stats, "winPercent"),
                    "gb":     _stat_val(raw_stats, "gamesBehind"),
                    "streak": _stat_val(raw_stats, "streak"),
                    "l10":    _stat_val(raw_stats, "Last Ten Games"),
                }

            rank = _stat_val(raw_stats, "rank", "0")
            if sport == "basketball":
                rank = _stat_val(raw_stats, "playoffSeed", rank)

            # Clincher (NBA only)
            clincher = _stat_val(raw_stats, "clincher", "")

            teams.append({
                "rank": rank,
                "team": {
                    "id": team_id,
                    "name": team_data.get("displayName", "Unknown"),
                    "abbr": team_data.get("abbreviation", "???"),
                    "logo": team_data.get("logos", [{}])[0].get("href", "")
                            if team_data.get("logos") else "",
                },
                "stats": stats,
                "zone": note.get("description", ""),
                "zone_color": note.get("color", ""),
                "clincher": clincher,
                "clinch_label": NBA_CLINCH_LABELS.get(clincher, ""),
                "is_watched": team_id in watched_ids,
                "is_top6":   team_id in top_pl_ids,
            })

        # Sort by rank
        teams.sort(key=lambda t: int(t["rank"]) if str(t["rank"]).isdigit() else 99)

        groups.append({
            "name": child.get("name", ""),
            "teams": teams,
        })

    return {
        "id": league_slug,
        "name": league_name,
        "sport": sport,
        "groups": groups,
    }


def get_all_standings():
    """Fetch standings for all relevant leagues."""
    leagues = [
        ("soccer", "eng.1"),
        ("soccer", "esp.1"),
        ("soccer", "ger.1"),
        ("soccer", "uefa.champions"),
        ("basketball", "nba"),
    ]

    results = []
    for sport, slug in leagues:
        standing = fetch_standings(sport, slug)
        if standing:
            results.append(standing)

    return results


def _fetch_upcoming_fixtures(league_slug, team_id):
    """
    Find a team's upcoming fixtures by scanning the league calendar.
    The team schedule endpoint only returns past games, so we use the
    scoreboard for future dates instead.
    """
    # First get the league calendar to know which dates have games
    scoreboard_url = f"{BASE_URL}/soccer/{league_slug}/scoreboard"
    data = _cached_get(scoreboard_url)
    if not data:
        return []

    calendar = data.get("leagues", [{}])[0].get("calendar", [])
    today = datetime.now(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Filter to future dates only
    future_dates = [d for d in calendar if d > today]

    upcoming = []
    for date_str in future_dates[:20]:  # Check up to 20 future matchdays
        # Convert calendar date to YYYYMMDD format for the scoreboard query
        day_str = date_str[:10].replace("-", "")
        day_games = fetch_scoreboard("soccer", league_slug, day_str)

        for game in day_games:
            home_id = game["home_team"]["id"]
            away_id = game["away_team"]["id"]

            if team_id in (home_id, away_id):
                is_home = home_id == team_id
                opponent = game["away_team"] if is_home else game["home_team"]
                upcoming.append({
                    "opponent": opponent["abbreviation"],
                    "opponent_name": opponent["name"],
                    "home": is_home,
                    "date": game["date"],
                })
                break  # Found this team's game on this date

        if len(upcoming) >= 8:
            break

    return upcoming


def get_title_races():
    """
    Build title race comparison data for configured races.
    For each race, pulls standings + remaining fixtures for the contenders.
    """
    races = []

    for race_cfg in config.TITLE_RACES:
        league_slug = race_cfg["league"]
        team_ids = race_cfg["team_ids"]

        # Get standings to find current points and games played
        standing = fetch_standings("soccer", league_slug)
        if not standing:
            continue

        # Find the teams in the standings
        all_teams = []
        for group in standing["groups"]:
            all_teams.extend(group["teams"])

        contenders = []
        for tid in team_ids:
            for t in all_teams:
                if t["team"]["id"] == tid:
                    pts = int(t["stats"].get("pts", 0))
                    gp = int(t["stats"].get("gp", 0))
                    # Premier League has 38 match days
                    remaining = 38 - gp

                    # Fetch remaining fixtures from the league calendar
                    upcoming_list = _fetch_upcoming_fixtures(league_slug, tid)

                    contenders.append({
                        "team": t["team"],
                        "rank": t["rank"],
                        "pts": pts,
                        "gp": gp,
                        "remaining": remaining,
                        "max_pts": pts + (remaining * 3),
                        "ppg": round(pts / gp, 2) if gp > 0 else 0,
                        "upcoming": upcoming_list,
                    })
                    break

        if len(contenders) < 2:
            continue

        # Sort by points descending
        contenders.sort(key=lambda c: c["pts"], reverse=True)
        leader = contenders[0]
        challenger = contenders[1]

        races.append({
            "label": race_cfg["label"],
            "league": league_slug,
            "league_name": standing["name"],
            "contenders": contenders,
            "gap": leader["pts"] - challenger["pts"],
            "games_in_hand": challenger["remaining"] - leader["remaining"],
        })

    return races
