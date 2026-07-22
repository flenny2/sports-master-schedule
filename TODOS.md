# TODOS — sports-master-schedule inbox

what: repo-native idea/task inbox (capture-ritual target); sessions sweep + prune, replace-semantics
updated: 2026-07-22 (§myteams BUILT on ws/myteams-strip; §preseason-zeros logged, unfixed)

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

## §myteams — "Your Teams" strip BUILT 2026-07-22 on `ws/myteams-strip`

First §D8 item off the deferred list (brief amendment A2). Branch-only, 167 tests green,
headless-verified at 390px + 1280px. Merge + push (= Render deploy) is Dylan's call.

- [x] `favorite: True` config flag → Steelers + Man City (kept separate from `tier`)
- [x] `app/myteams.py` + `GET /api/myteams`; strip renders above the marquee
- [x] `tests/test_myteams.py` — 23 tests, no network

## §preseason-zeros — the Home page currently states standings that don't exist

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
