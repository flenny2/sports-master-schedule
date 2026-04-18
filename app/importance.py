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
    must_watch_team_ids = {
        t["espn_id"]
        for t in config.WATCHED_TEAMS
        if t["tier"] == "must_watch"
    }

    for game in games:
        sport = game["sport"]
        team_ids = {game["home_team"]["id"], game["away_team"]["id"]}

        # ── NFL ───────────────────────────────────────────────
        # Every NFL game we fetch is either primetime or a RedZone
        # window game — both are must-watch.
        if sport == "football":
            game["tier"] = "must_watch"

        # ── Soccer ────────────────────────────────────────────
        # Only a must-watch team on the pitch upgrades the tier;
        # every other soccer fixture we fetch (UCL, notable teams,
        # top-6 PL matchups) is "notable".
        elif sport == "soccer":
            if team_ids & must_watch_team_ids:
                game["tier"] = "must_watch"
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
