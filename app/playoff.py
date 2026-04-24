"""
Playoff / finals tagger.

Flags each game with `is_playoff` (true/false) and, when possible, a
human-readable `playoff_round` (e.g. "NBA Finals", "Quarterfinals").

Soccer triggers are belt-and-suspenders — any one is sufficient:
  1. League is in KNOCKOUT_CUP_LEAGUES (FA Cup etc. are knockout throughout)
  2. Notes contain a knockout keyword (covers legacy/text-only responses)
  3. raw_series.title is in KNOWN_KNOCKOUT_ROUND_TITLES (structured, stable)

NBA/NFL are flagged by season_type.
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

# Structured round titles ESPN uses in `competition.series.title` across
# UCL, Europa, Conference League, and similarly-shaped cup competitions.
# This is the most reliable trigger — structured data, stable across
# notes-format changes. Used both to flag is_playoff and to name the
# round (avoids the "1st Leg" / "2nd Leg - X advance Y-Z" ugliness that
# would otherwise land in `playoff_round`).
KNOWN_KNOCKOUT_ROUND_TITLES = {
    "Round of 16",
    "Quarterfinals",
    "Semifinals",
    "Final",
    "Knockout Round Playoffs",
}


def _detect_round(notes, sport, league, season_type, series_title=""):
    """Return a short round label, or empty string if we can't tell."""
    # Prefer the structured title when ESPN gives us one — it reads
    # cleaner ("Quarterfinals") than the raw notes for two-leg ties
    # ("1st Leg" / "2nd Leg - X advance Y-Z on aggregate").
    t = (series_title or "").strip()
    if t in KNOWN_KNOCKOUT_ROUND_TITLES:
        return t
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
        series_title = (game.get("raw_series") or {}).get("title", "")

        is_playoff = False

        if sport == "basketball":
            # All NBA games we fetch are already playoff/play-in
            is_playoff = True
        elif sport == "football":
            is_playoff = season_type == 3
        elif sport == "soccer":
            if league in KNOCKOUT_CUP_LEAGUES:
                is_playoff = True
            elif series_title in KNOWN_KNOCKOUT_ROUND_TITLES:
                # Structured trigger: any cup with these round titles
                # (UCL, Europa, Conference, etc.) is a knockout tie.
                is_playoff = True
            else:
                notes_lower = notes.lower()
                if any(kw in notes_lower for kw in KNOCKOUT_NOTE_KEYWORDS):
                    is_playoff = True

        game["is_playoff"] = is_playoff
        game["playoff_round"] = (
            _detect_round(notes, sport, league, season_type, series_title)
            if is_playoff else ""
        )

    return games
