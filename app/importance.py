"""
Importance tagger — classifies each game into a tier.

Tiers:
  "must_watch"  — NFL primetime, RedZone, Man City matches
  "notable"     — Big club soccer, Champions League, top PL matchups
  "major_event" — NBA playoffs, championship games
"""

import config


def tag_importance(games):
    """
    Set the 'tier' field on each game based on sport-specific rules.
    Modifies games in place and returns them.
    """
    # Build lookup sets for fast matching
    must_watch_team_ids = {
        t["espn_id"]
        for t in config.WATCHED_TEAMS
        if t["tier"] == "must_watch"
    }
    notable_team_ids = {
        t["espn_id"]
        for t in config.WATCHED_TEAMS
        if t["tier"] == "notable"
    }
    top_pl_ids = set(config.PL_TOP_TEAMS.keys())

    for game in games:
        sport = game["sport"]
        home_id = game["home_team"]["id"]
        away_id = game["away_team"]["id"]
        team_ids = {home_id, away_id}

        # ── NFL ───────────────────────────────────────────────
        if sport == "football":
            slot = game.get("nfl_slot", "")
            if "Primetime" in slot:
                game["tier"] = "must_watch"
            else:
                # RedZone window games
                game["tier"] = "must_watch"

        # ── Soccer ────────────────────────────────────────────
        elif sport == "soccer":
            league = game["league"]

            # Must-watch teams (Man City)
            if team_ids & must_watch_team_ids:
                game["tier"] = "must_watch"
            # Champions League is always at least notable
            elif league == "uefa.champions":
                game["tier"] = "notable"
            # Notable teams (Real Madrid, Barcelona)
            elif team_ids & notable_team_ids:
                game["tier"] = "notable"
            # Two top-6 PL teams playing each other
            elif league == "eng.1" and len(team_ids & top_pl_ids) == 2:
                game["tier"] = "notable"
            else:
                game["tier"] = "notable"

        # ── NBA ───────────────────────────────────────────────
        # Only playoff/play-in games make it here, so they're all major
        elif sport == "basketball":
            game["tier"] = "major_event"

        # ── Fallback ──────────────────────────────────────────
        else:
            game["tier"] = "notable"

    return games
