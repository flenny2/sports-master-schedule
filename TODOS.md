# TODOS — sports-master-schedule inbox

what: repo-native idea/task inbox (capture-ritual target); sessions sweep + prune, replace-semantics
updated: 2026-07-26 (§mobile-month-calendar BUILT + §offseason-next-up FIXED — both merged to master, un-pushed; overnight-lane law + proposals live in docs/overnight/)

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

## §mobile-month-calendar — BUILT 2026-07-26, MERGED to master, awaiting Dylan's push

**His words were:** *"I just want the calendar to look like an actual calendar, like the
full month version so i can see the next few weeks at a glance."* The fork this TODO
flagged — replace the rolling 7-day list, or keep it under a month grid — was a TASTE
call, so the overnight lane built BOTH as inert mockups and **Dylan chose B: keep both**
(2026-07-26). Then built it for real.

- [x] Two mockups under `docs/overnight/mockups/` (proposal SMS-1) — standalone pages that
      never import from `static/`, so the fork cost nothing to review
- [x] Option B in the app (SMS-3, `6e604ee`): month grid above the day list on mobile;
      tapping a day moves the list to start there
- [x] Mobile arrows now page **months**, not ±7 days — they have to agree with the grid.
      That orphaned `shiftMobileWindow`, `mobileWindowMidpointMonth` and
      `formatMobileWindowLabel`; all three deleted rather than left dead. The documented
      month-boundary trade-off (1–3 trailing days rendering empty) is retired with them
- [x] `mobileWindowDates()` clamped to the loaded padded range, plus a "More in <month>"
      button when the list comes up short — an unclamped window would print "No games" for
      days nobody fetched
- [x] `tools/qa-phone-calendar.py` — proxies the app + harness through one origin so the
      running app can be pinned to a **true 390px** and measured into. **Headless Chrome
      will not give a viewport under 500px on Linux**, which silently widened a whole first
      pass; the harness asserts `innerWidth` so that cannot recur
- [ ] **Dylan**: `git push origin master` — merged locally (`f33309b`), NOT deployed

**Design notes worth keeping.** Day cells are ~49px on a 390px phone, so they carry a
date, one dot per SPORT, and the game count — *not* one dot per game, because on a 14-game
Sunday the first few dots are all NFL and the Premier League fixture that morning
disappears. "Played" is a hollow ring rather than a faded dot: no opacity that still reads
as dimmed clears the palette's documented 3:1 (measured — `--nfl` over white is 1.67:1 at
32%, 2.54:1 at 55%, against 6.26:1 solid), and a shape difference survives colour-blindness.
Grid columns are Monday-first, matching `DAY_NAMES` and the server's padded range.

## §offseason-next-up — FIXED 2026-07-26, MERGED to master, awaiting Dylan's push

Found by screenshotting the running app at 390px (proposal SMS-2, `fd10a53`). The Home
page's Today's Slate showed *"No games in this window — browse the calendar."* — the
last-resort branch, which should have been unreachable because `buildNextUpCard` already
exists for exactly this case. `findNextGame()` only ever searched the loaded padded month;
the padded July range ends Aug 2 and the next fixture was Aug 7, five days out of reach.

`/api/schedule` now scans forward 45 days **only when its own window has no upcoming
fixture left** and returns that one game as `next_upcoming` (new `app/lookahead.py`, pure,
19 tests, ESPN fetch injected). The scan result goes through the same tagging chain, so the
front page renders it with the ordinary card builder. An ESPN failure inside the scan
degrades to the old message rather than raising — a quiet front page is cosmetic, a 500 on
the main endpoint is not.

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
