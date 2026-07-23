<!-- Worksheet provenance (wrap-session Step 3.5):
     Approved plan for the §D8 Your Teams strip, executed 2026-07-22 → commit aa0c9d9.
     Dylan then asked for two follow-ons NOT in this plan: merge to master, and the
     pre-season-zeros fix (commit 8a2a803, TODOS §preseason-zeros). Both shipped live
     in 000dd09..8a2a803. Everything below is the plan as approved, unedited. -->

# Your Teams strip — brief §D8, built as the non-Fable body for Fable's 10 PM review

## Context

**Why now.** §D8 lists six things deselected at the Jul-17 interview. Live probes today
show the your-teams strip is the only one that is both buildable tonight and *useful
tonight*, because the app is currently dead:

- The July calendar window (`2026-06-29 → 2026-08-02`) holds **31 games, every one
  `post`** — the World Cup, finished Jul-19. Zero games today or later, so Home renders
  "No games in this window — browse the calendar."
- The PL storyline expired May 31 with nothing to replace it (the season-rollover
  checklist already flags this as pending), so the Storylines block is thin.
- Both standings feeds have reset to pre-season zeros. NFL returns every team at
  `rank 0, 0-0-0`; the PL table is **sorted alphabetically** at 0 pts (Bournemouth 1st,
  Arsenal 2nd). The Home mini-tables are rendering that on Render right now.

So between now and mid-August there is nothing on the Front Page. A "Your Teams" strip —
next fixture with a countdown, last result, table position — is exactly the block that
carries the off-season, and it grows into the D5 "my-team hub" once the seasons start.

**Fandom, clarified (Dylan, Jul-22).** Asked whose teams belong on the strip:
*"Steelers and Man City are my favorite teams. Arsenal and Bayern were because I was
following the champions league"* — then, immediately after: *"Yes, champions league and I
forgot to say Arsenal for the premier league race as well."* So there are three distinct
relationships in one flat config list:

| team | why it's tracked | surface |
|---|---|---|
| Steelers, Man City | **favorite teams** | the new strip |
| Arsenal | PL **title race** (+ UCL) | already the title-race story card |
| Bayern | UCL only | game cards when it plays |

**The strip must not reuse `tier`.** `tier` feeds `app/importance.py` and the marquee
scorer, so bending it to mean "favorite" would quietly change which games headline the
Front Page. The two favorites get an explicit new `favorite: True` flag instead. Arsenal
keeps `must_watch` — now positively justified rather than left as an open question, since
he follows the race it contests and it is already a `TITLE_RACES` contender
(`config.py:83`).

**Arsenal is deliberately not on the strip.** Its PL-race interest is already rendered on
the Front Page by `buildRaceStoryCard()` (gap headline + next fixtures for Arsenal and
City) and by the Tables widget — a third Arsenal surface would be duplication. Easy to
change: adding `favorite: True` to its config entry is the whole edit.

**Outcome.** Two cards on Home tonight, verified against live ESPN:

| | next fixture | last result | table |
|---|---|---|---|
| Steelers | Sun Sep 13 vs ATL (in ~53d) | none published yet | suppressed (0-0-0) |
| Man City | Sun Aug 23 vs BOU (in ~32d) | W 1–0 @ CHE, FA Cup, May 16 | suppressed (0 pts) |

## Data sourcing (probed live, not assumed)

The existing CLAUDE.md gotcha *"team schedule endpoint only returns PAST games"* is
**sport-specific**, which matters here:

- `fetch_team_schedule("football","nfl","23")` → **17 events, all `pre`**, the full 2026
  season (opener Sep 13). One call gives NFL next-fixture.
- `fetch_team_schedule("soccer", …)` → completed matches only. Arsenal/City `eng.1`
  return **0** games (26-27 not published there); `uefa.champions` + `eng.fa` return the
  finished 25-26 run, which is where City's last result comes from.
- `_fetch_upcoming_fixtures(slug, team_id)` (`app/espn.py:742`, already written and
  already called by `get_title_races()` for exactly Arsenal + City) **does** return soccer
  futures today: Arsenal Aug 21 vs COV, City Aug 23 vs BOU.

So: team-schedule for results + NFL futures, `_fetch_upcoming_fixtures` as the soccer
futures fallback. Both are already in the ESPN cache after a normal Home load
(`CACHE_TTL_SECONDS = 3600`), so the marginal upstream cost is ~1 new call (the Steelers'
schedule).

**Rejected:** widening `get_all_games()` to a ±45-day rolling window — ~70 upstream calls
and it *still* misses the Steelers' Sep 13 opener at 53 days out. Also rejected:
assembling in JS from `allGames` + `standingsData`, which needs no new endpoint but puts
the sport-scoped matching and last/next selection somewhere the pytest suite cannot reach.

## Implementation

### 1. `config.py` — mark the favorites
Add `"favorite": True` to the **Pittsburgh Steelers** and **Manchester City** entries in
`WATCHED_TEAMS`, with a comment recording Dylan's Jul-22 wording and *why* it is a
separate key from `tier` (tier drives importance/marquee; favorite drives the strip).

### 2. `app/myteams.py` (new) — all logic, pure and testable
Mirrors the `app/storylines.py` shape (pure helpers + one config-driven entry point).

- `get_favorite_teams()` — `WATCHED_TEAMS` entries with `favorite` set.
- `_team_side(game, team)` — `"home" | "away" | None`. **Guards on
  `game["sport"] == team["sport"]` before comparing ids** — ESPN ids are unique only
  within a sport (Steelers `"23"` ≠ soccer `"23"`), the same trap `fetch_standings`
  already scopes around for watched rows.
- `_result_from(game, side)` — `{outcome: "W"|"L"|"D", score: "1-0", opponent, home,
  league_name, date}`. Parses via `int(float(v))` because soccer scores arrive as floats.
- `_games_played(sport, stats)` — soccer reads `gp`; football sums `w+l+t`.
- `_standing_row(standings, team)` — sport-scoped walk of `get_all_standings()` output;
  **returns `None` when `_games_played` is 0**, because ESPN's pre-season reset ranks
  alphabetically and printing "Arsenal 2nd" in July would be a fabricated fact.
- `build_team_card(team, games, standings, fallback_fixtures, now)` — **pure**; returns
  `{name, abbr, sport, logo, color, next, last, standing}`. Harvests `logo`/`color` from
  the standings entry first, then any schedule game (config has neither).
- `get_my_teams()` — the only impure function: parallel `fetch_team_schedule` per
  (team, league) via `ThreadPoolExecutor` like `fetch_soccer_games` does, one
  `get_all_standings()`, `_fetch_upcoming_fixtures` only for soccer teams with no `pre`
  game, then `build_team_card` per team. League display names come from the standings
  payload (`{id → name}`), so `_fetch_upcoming_fixtures` is left untouched.

### 3. `app/routes.py` — one public read
`GET /api/myteams` → `{"teams": [...]}`, honouring `?refresh=true` like `/api/standings`.
No auth gate (read-only, no spend). **This knowingly amends the CLAUDE.md line "no
front-page-specific endpoints"** — recorded with its reason, since the strip needs
games ∩ standings and no existing endpoint carries both.

### 4. `static/app.js` — render only
- State `myTeamsData` / `myTeamsLoaded`; `loadMyTeams()` alongside `loadStandings()`.
- `buildMyTeamsStrip()` → `.fp-block.fp-myteams` with `sec-tag` "Your Teams" and one
  `.myteam-card` per team: crest + name, `NEXT` row (fixture + `countdownText()`), `LAST`
  row (W/L/D pill + score + competition + date), table row, or "Season not started".
- Inserted as the **first child of `colMain`**, above the marquee hero — the layout Dylan
  picked, which on mobile puts it directly under the dateline.
- Reuses `el()`, `appendIf()`, `logoImg()`, `countdownText()`, `fmtDateShort()`,
  `seamColor()`; `var` + function declarations, no `innerHTML`.
- **`app.js` edits go in via a small Python splice on unambiguous anchor lines** — the
  file mixes literal `\uXXXX` escapes with real Unicode and defeats exact-match editors.

### 5. `static/style.css` — one block, existing tokens
`.fp-myteams` strip: horizontal scroll-snap row on mobile, equal-width flex on desktop.
Team kit color appears only as a 3px left border via `seamColor()` (colour belongs to
teams; chrome stays ink). New custom properties, if any, go in the single `:root` block
and get contrast-checked — no second theme block.

### 6. `tests/test_myteams.py` (new) — ~12 tests, no network
Sport-scope guard (football "23" must not match soccer "23") · next = earliest `pre` at or
after now, ignoring stale `pre` and `post` · last = latest `post` · W/L/D for home and away
sides, including a draw · standings suppressed at soccer `gp: 0` · suppressed at NFL
`0-0-0` · present with rank + record once played · soccer fallback fixture used when the
schedule has no `pre` · team with no data at all returns a card with null fields and does
not raise · `get_favorite_teams()` pins the config flag · route shape with `get_my_teams`
monkeypatched.

### 7. Docs
`CLAUDE.md` — `/api/myteams` in API Routes, `app/myteams.py` in Project Layout, a Key
Design Decisions bullet (favorite ≠ tier, pre-season suppression, the amended
front-page-endpoint rule, the sport-split team-schedule finding), updated test count.
`PRODUCT_BRIEF.md` — Amendment **A2**: strip shipped post-v1, plus the three-way fandom
split (favorites / title-race / UCL-only) so a future model doesn't read the flat
`WATCHED_TEAMS` list as one undifferentiated set.
`TODOS.md` — tick the D8 item.
Repo memory `dylan-sports-fandom.md` — corrected at wrap: it currently records City +
Arsenal as equivalent must-watch, which today's answers supersede.

## Verification

1. `./tools/validate` → expect **156 passed** (144 baseline + 12) and `VALIDATE PASS`.
2. `python app.py`, then `curl -s localhost:5000/api/myteams | python3 -m json.tool` —
   confirm Steelers next Sep 13 vs ATL, City next Aug 23 vs BOU + last W 1–0 @ CHE, and
   `standing: null` on both (the pre-season suppression doing its job).
3. Headless Chrome screenshots of `#front` at 390px and 1280px (read the `headless-qa`
   skill first for the fleet's logged gotchas). Confirm the strip sits under the dateline,
   scrolls on mobile, and that the rest of the Front Page is unchanged.
4. Commit on branch `ws/myteams-strip`. **No push, no deploy** — sms is deploy-coupled.

## Fences

- Claim `sports-master-schedule-claude` in the STATE Ownership table **before** writing;
  release at wrap.
- Branch only. Never `git push` — push = Render auto-deploy = Dylan's call, every time.
- Single light theme; no dark-mode tokens.
- Nothing touches the Anthropic key or the preview spend path.
