"""
Fantasy crossover tagger — fan-level only (brief D5).

Adds `my_guys: [player names]` to NFL games where a player from
config.FANTASY_ROSTER plays for either team, so the card can show
"YOUR GUYS: Jacobs, St. Brown" when deciding what to watch.

Deliberately dumb: the roster is a hand-maintained name -> NFL team
abbreviation map in config.py (no ESPN fantasy auth, no league API —
league stats stay in the fantasy-football app). Matching is by team
abbreviation, case-insensitive.
"""

import config


def tag_my_guys(games):
    """Set my_guys on football games. Modifies in place and returns."""
    roster = getattr(config, "FANTASY_ROSTER", {}) or {}

    # Invert to abbrev -> [names] once, uppercased for the compare
    by_team = {}
    for name, abbrev in roster.items():
        by_team.setdefault(str(abbrev).upper(), []).append(name)

    for game in games:
        if game.get("sport") != "football" or not by_team:
            game["my_guys"] = []
            continue
        home = str(game["home_team"].get("abbreviation", "")).upper()
        away = str(game["away_team"].get("abbreviation", "")).upper()
        game["my_guys"] = by_team.get(away, []) + by_team.get(home, [])

    return games
