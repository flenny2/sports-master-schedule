"""
Pre-match facts panel — the FREE layer of the tactical preview (brief D3).

One ESPN summary call per game (cached 1h via espn._cached_get), parsed
per sport into a small display-ready dict. Every field is optional: ESPN
populates lineups only near kickoff, injuries only for some sports, etc.
The frontend hides whatever is missing.

Shapes verified against live responses on 2026-07-18
(soccer: fifa.world event 760516; NFL: playoff event 401772977).
"""

from app.espn import BASE_URL, _cached_get

# Sports that get the facts panel + tactical read (brief D4)
PREVIEW_SPORTS = ("soccer", "football")


def fetch_event_summary(sport, league_slug, event_id):
    """GET the ESPN summary payload for one event (cached), or None."""
    url = f"{BASE_URL}/{sport}/{league_slug}/summary"
    return _cached_get(url, {"event": event_id})


def get_game_facts(sport, league_slug, event_id):
    """
    Return a facts dict for the expanded-card panel, or None when the
    summary is unavailable or the sport isn't covered.
    """
    if sport not in PREVIEW_SPORTS:
        return None
    data = fetch_event_summary(sport, league_slug, event_id)
    if not data:
        return None
    try:
        if sport == "soccer":
            return _soccer_facts(data)
        return _nfl_facts(data)
    except (KeyError, IndexError, TypeError, AttributeError):
        # ESPN shape surprise — facts are optional garnish, never a 500
        return None


# ── Soccer ────────────────────────────────────────────────────────

def _soccer_facts(data):
    facts = {"sport": "soccer"}

    venue = (data.get("gameInfo") or {}).get("venue") or {}
    if venue.get("fullName"):
        facts["venue"] = venue["fullName"]

    # Betting line — a one-line framing of expectations ("FRA -115 · O/U 3.5")
    odds = data.get("odds") or []
    if odds and isinstance(odds[0], dict):
        parts = []
        if odds[0].get("details"):
            parts.append(str(odds[0]["details"]))
        if odds[0].get("overUnder") is not None:
            parts.append("O/U " + str(odds[0]["overUnder"]))
        if parts:
            facts["odds"] = " · ".join(parts)

    # Recent form: boxscore.form = [{team, events: [{gameResult, ...}]}]
    form_out = []
    for side in (data.get("boxscore") or {}).get("form") or []:
        team = (side.get("team") or {}).get("abbreviation", "")
        results = [e.get("gameResult", "?")
                   for e in (side.get("events") or [])[:5]]
        if team and results:
            form_out.append({"team": team, "results": " ".join(results)})
    if form_out:
        facts["form"] = form_out

    # Head-to-head: headToHeadGames = [{team, events: [{gameDate, score}]}]
    h2h_groups = data.get("headToHeadGames") or []
    meetings = []
    if h2h_groups and isinstance(h2h_groups[0], dict):
        for e in (h2h_groups[0].get("events") or [])[:5]:
            date = str(e.get("gameDate", ""))[:7]  # "2022-12"
            score = e.get("score", "")
            if date and score:
                meetings.append(date + " · " + score)
    if meetings:
        facts["h2h"] = meetings

    # Lineups (rosters carry players only near kickoff)
    lineups = []
    for side in data.get("rosters") or []:
        players = side.get("roster") or []
        starters = []
        for p in players:
            if p.get("starter"):
                athlete = p.get("athlete") or {}
                if athlete.get("displayName"):
                    starters.append(athlete["displayName"])
        if starters:
            lineups.append({
                "team": (side.get("team") or {}).get("abbreviation", ""),
                "formation": side.get("formation", ""),
                "starters": starters,
            })
    if lineups:
        facts["lineups"] = lineups

    return facts if len(facts) > 1 else None


# ── NFL ───────────────────────────────────────────────────────────

def _nfl_facts(data):
    facts = {"sport": "football"}

    venue = (data.get("gameInfo") or {}).get("venue") or {}
    if venue.get("fullName"):
        facts["venue"] = venue["fullName"]

    odds = data.get("odds") or []
    if odds and isinstance(odds[0], dict):
        parts = []
        if odds[0].get("details"):
            parts.append(str(odds[0]["details"]))
        if odds[0].get("overUnder") is not None:
            parts.append("O/U " + str(odds[0]["overUnder"]))
        if parts:
            facts["odds"] = " · ".join(parts)

    # Injuries: [{team, injuries: [{athlete, status}]}] per side
    injuries_out = []
    for side in data.get("injuries") or []:
        team = (side.get("team") or {}).get("abbreviation", "")
        players = []
        for inj in (side.get("injuries") or [])[:8]:
            athlete = inj.get("athlete") or {}
            name = athlete.get("displayName", "")
            pos = ""
            if isinstance(athlete.get("position"), dict):
                pos = athlete["position"].get("abbreviation", "")
            status = inj.get("status", "")
            if name and status:
                label = name + ((" (" + pos + ")") if pos else "")
                players.append(label + " — " + status)
        if team and players:
            injuries_out.append({"team": team, "players": players})
    if injuries_out:
        facts["injuries"] = injuries_out

    # Statistical leaders: [{team, leaders: [{displayName, leaders: [...]}]}]
    leaders_out = []
    for side in data.get("leaders") or []:
        team = (side.get("team") or {}).get("abbreviation", "")
        lines = []
        for cat in (side.get("leaders") or [])[:3]:
            inner = cat.get("leaders") or []
            if not inner:
                continue
            athlete = inner[0].get("athlete") or {}
            name = athlete.get("displayName", "")
            stat = inner[0].get("displayValue", "")
            if name and stat:
                lines.append(cat.get("displayName", "") + ": " +
                             name + " — " + stat)
        if team and lines:
            leaders_out.append({"team": team, "lines": lines})
    if leaders_out:
        facts["leaders"] = leaders_out

    return facts if len(facts) > 1 else None
