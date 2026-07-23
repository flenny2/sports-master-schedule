# TODOS — sports-master-schedule inbox

what: repo-native idea/task inbox (capture-ritual target); sessions sweep + prune, replace-semantics
updated: 2026-07-22 (§myteams + §preseason-zeros SHIPPED LIVE; §mobile-month-calendar captured for next session)

## §revamp — BUILT 2026-07-18 on `ws/revamp-v1` (brief: PRODUCT_BRIEF.md)

All three phases landed, 123 tests green, screenshot-verified. Branch-only — merge +
push (= Render deploy) is Dylan's call. The WC final (ARG–ESP, Sun Jul-19) is on the
Front Page marquee the moment it deploys.

- [x] Phase 1 — light-only modern design system + Front Page hub (`594994c`)
- [x] Phase 2 — tactical previews: facts panel + on-demand Claude read, dry-run
      without key (`70d4581`)
- [x] Phase 3 — NFL pillar: Steelers watched, NFL standings, my-guys tags (`43b0cb4`)
- [ ] **Dylan**: set `ANTHROPIC_API_KEY` (Render dashboard + local shell) to switch
      tactical reads from dry-run to live; optional `PREVIEW_MODEL=claude-sonnet-5`
      for cheaper presses
- [ ] **Dylan**: fill `FANTASY_ROSTER` in config.py after the LPPC draft (late Aug)
- [ ] **Dylan (optional)**: render.yaml env-var comment block — the file is
      edit-protected for sessions; equivalent docs live in app/tactical.py + CLAUDE.md
- [ ] Real-phone pass after deploy (iOS fonts/sticky tabs/notch)
- Deferred-by-interview (brief §D8, revisit on Dylan's word): milestone watch (blocked —
  needs a curated chase list from Dylan) · NBA previews · draft/offseason tracker ·
  ESPN-fantasy auto-pull · NFC mini table on Home (AFC ships; NFC lives on Tables)

## §mobile-month-calendar — NEXT SESSION (Dylan, 2026-07-22, after seeing the strip ship)

**His words:** *"I just want the calendar to look like an actual calendar, like the full
month version so i can see the next few weeks at a glance."* Explicitly deferred to the
next session — nothing started.

**What exists today.** `renderCalendar()` (`static/app.js:1080`) forks on `isMobile()`
(`MOBILE_BP = 640`, line 35): desktop gets `renderDesktopCalendar()` (line 1101, a real
month grid + a `renderDetail()` side panel at 1237); **mobile gets
`renderMobileCalendar()` (line 1187), a rolling 7-DAY LIST**, not a grid. That's the
thing he's asking to replace. The 7-day window is a whole subsystem, not one function:
`mobileWindowStart` state · `mobileWindowDates()` 162 · `mobileWindowMidpointMonth()` 178
· `initMobileWindowIfNeeded()` 188 · `shiftMobileWindow(days)` 198 ·
`formatMobileWindowLabel()` 219, plus a branch in `render()` that re-fetches when the
window slides into a new month, and the `btnPrev`/`btnNext` arrows which mean ±7 days on
mobile but ±1 month on desktop.

**The real design problem** (why this is a Fable-class job, not a one-liner): a 7-column
month grid on a 390px phone gives ~50px cells. Game cards don't fit. So the mobile grid
needs a compact day cell — probably sport-colored dots or a count — plus a tap target
that opens that day's games, since mobile has no room for the desktop detail panel (a
bottom sheet, or an expanding row beneath the tapped week). Decide that interaction
BEFORE writing the grid.

**Worth confirming with Dylan first:** does he want the 7-day list *replaced*, or kept as
a secondary view under the month grid? "See the next few weeks at a glance" could mean a
true month grid, or a 2–3 week rolling grid anchored on today — the latter is arguably
closer to what he said and is easier to fit on a phone.

**Fences unchanged:** branch-only, `./tools/validate` green, single light theme, and
`git push` is HARD-DENIED in `.claude/settings.json` — Dylan must run the push himself.

## §myteams — "Your Teams" strip BUILT 2026-07-22 on `ws/myteams-strip`

First §D8 item off the deferred list (brief amendment A2). **MERGED + DEPLOYED LIVE
2026-07-22** (`aa0c9d9`, in `000dd09..8a2a803`, Dylan pushed by hand). Headless-verified
at 390px + 1280px before shipping.

- [x] `favorite: True` config flag → Steelers + Man City (kept separate from `tier`)
- [x] `app/myteams.py` + `GET /api/myteams`; strip renders above the marquee
- [x] `tests/test_myteams.py` — 23 tests, no network

## §preseason-zeros — FIXED + DEPLOYED LIVE 2026-07-22 (`8a2a803`; Dylan: "Fix the zeros")

`fetch_standings` now sets `preseason: True` when every row is at 0 games played
(`app/espn.py:games_played`, the same rule the strip uses), `get_title_races` carries it,
and all four render sites honour it: mini tables and Tables sections show
"Season hasn't started — no games played yet." instead of a zeroed alphabetical table;
the race headline reads "SEASON OPENS AUG 21" instead of "LEVEL ON POINTS"; the race
widget drops its rank number and leader highlight (the 0 pts / 0 GP / 38 left stat boxes
stay — those are true). 178 tests green, headless-verified. Original report below.

## §preseason-zeros (original report) — the Home page stated standings that don't exist

Found while building the strip (Jul-22, evidenced by headless screenshots). Between
seasons ESPN zeroes every stat and sorts tables ALPHABETICALLY, and two Home blocks
render that as fact:

- **Mini tables** (`buildMiniTable`, static/app.js) — PL shows "1 AFC Bournemouth 0 pts,
  2 Arsenal 0 pts … 15 Manchester City 0 pts"; NFL shows every team at rank `0`, `0-0`.
  Man City are not 15th; that is their position in the alphabet.
- **Title-race card** (`buildGapString`) — reads "LEVEL ON POINTS" for Arsenal vs City
  before either has kicked a ball, which looks like a dramatic race rather than an
  unplayed season.

The new strip already gates on games-played (`app/myteams.py:_games_played`), so the fix
is to reuse that rule in both blocks — likely an off-season line ("Season starts Aug 21")
instead of a zeroed table. **Deliberately NOT fixed in the §myteams branch** — it changes
shipped behaviour on a deploy-coupled repo and wasn't in the approved scope. Dylan's call.
