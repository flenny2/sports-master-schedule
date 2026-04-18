"""
Playoff / finals tagger.

Flags each game with `is_playoff` (true/false) and, when possible, a
human-readable `playoff_round` (e.g. "NBA Finals", "Quarterfinal").

Rules:
  NBA:    all fetched games are already playoff/play-in.
  NFL:    season_type == 3 (postseason).
  Soccer: knockout-only cup competitions (FA Cup, League Cup, Copa del
          Rey, DFB-Pokal, Conference League), or any UCL/Europa game
          whose notes contain a knockout-round keyword.
"""

# Soccer competitions where every fixture is a knockout tie
KNOCKOUT_CUP_LEAGUES = {
    "eng.fa",
    "eng.league_cup",
    "esp.copa_del_rey",
    "ger.dfb_pokal",
    "uefa.europa.conf",
    "fifa.cwc",
}

# Keywords ESPN uses in the `notes` field for knockout rounds
KNOCKOUT_NOTE_KEYWORDS = (
    "final",
    "semifinal",
    "semi-final",
    "quarterfinal",
    "quarter-final",
    "round of 16",
    "round of 32",
    "knockout",
    "playoff",
    "play-in",
    "championship",
    "conference",
)


def _detect_round(notes, sport, league, season_type):
    """Return a short round label, or empty string if we can't tell."""
    n = (notes or "").strip()
    if n:
        return n  # ESPN already gives us "Quarterfinal", "NBA Finals", etc.
    if sport == "basketball" and season_type == 5:
        return "Play-In Tournament"
    if sport == "basketball" and season_type == 3:
        return "NBA Playoffs"
    if sport == "football" and season_type == 3:
        return "NFL Playoffs"
    if league in KNOCKOUT_CUP_LEAGUES:
        return "Knockout"
    return ""


def tag_playoff(games):
    """Set `is_playoff` and `playoff_round` on each game in place."""
    for game in games:
        sport = game.get("sport", "")
        league = game.get("league", "")
        season_type = game.get("season_type", 2)
        notes = game.get("notes", "")

        is_playoff = False

        if sport == "basketball":
            # All NBA games we fetch are already playoff/play-in
            is_playoff = True
        elif sport == "football":
            is_playoff = season_type == 3
        elif sport == "soccer":
            if league in KNOCKOUT_CUP_LEAGUES:
                is_playoff = True
            else:
                notes_lower = notes.lower()
                if any(kw in notes_lower for kw in KNOCKOUT_NOTE_KEYWORDS):
                    is_playoff = True

        game["is_playoff"] = is_playoff
        game["playoff_round"] = (
            _detect_round(notes, sport, league, season_type)
            if is_playoff else ""
        )

    return games
