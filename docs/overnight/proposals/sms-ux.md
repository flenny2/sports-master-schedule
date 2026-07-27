# Proposals — lane `sms-ux` (Opus 5, night of 2026-07-26)

**How to use this file:** each entry has an ID (`SMS-1`, `SMS-2`…). Reply with IDs —
"keep SMS-1, discard SMS-2" — and the morning session executes exactly that. The
KEEP / DISCARD column is yours; I leave it blank. IDs are never renumbered or reused.

**Review board (the phone-friendly version of this file):**
<https://claude.ai/code/artifact/a1ac028b-0ea0-47bc-b52a-918e87ce2a65> — private,
rebuilt in place each pass from `docs/overnight/review-board.html`, so the URL is stable.
**Branch:** `auto/overnight-sms-ux` · **Nothing is pushed. Nothing is merged.**
**Suite:** 197 passed (`./tools/validate`), green at every commit on this branch.

---

## Proposals

### SMS-1 — Phone month calendar, built twice so you can pick

- **WHAT** — Two working versions of a month-grid calendar for the phone, side by side,
  so you choose the shape. **A (replace):** the grid *is* the calendar; tap a day and
  that day's games appear underneath; the rolling seven-day list retires.
  **B (keep both):** the grid sits on top as the glance layer with the seven-day list
  still under it, and tapping a day moves the list to start there. Nothing in the app
  changed — both are standalone pages that cannot affect it.
- **WHY** — You said you want the calendar to "look like an actual calendar… so i can
  see the next few weeks at a glance". The phone shows a rolling seven-day list today,
  so a Sunday three weeks out with fourteen games on it is invisible until you arrow
  there twice. The fork above is a taste call and yours; both are built rather than one
  guessed at.
- **WHERE** — `docs/overnight/mockups/` (both pages + shared CSS/JS + captured ESPN data
  + a measurement harness), `docs/overnight/review-board.html`, `tools/shoot-mockups.py`,
  `tools/build-overnight-artifact.py`. Commits `83674f0` and the artifact commit that
  follows it. **No file the running app loads was touched.**
- **RISK** — A day cell on a 390px phone is ~49px wide, so it carries a date, one dot per
  sport, and a game count and nothing more; you cannot see *who* is playing without
  tapping. The mockups also pin "today" to Sun Sep 13 and open on September, because the
  real today sits in the dead week between the World Cup final and the NFL opener — so
  you are judging the design under load, not under today's emptiness (arrow back to
  July/August to see that). And a mockup is not the app: wiring the winner in means
  retiring or rewiring the seven-day window code, which is a real change to a page you
  use, on a repo where shipping is a deploy.
- **KEEP / DISCARD** —

### SMS-2 — The front page can name the next game again

- **WHAT** — Between seasons the Home page's "Today's Slate" showed a dead line:
  *"No games in this window — browse the calendar."* It now shows a card:
  **NO GAMES TODAY · NEXT UP — CAR at ARI, Thu Aug 6, 5:00 PM, in 10d 23h.**
- **WHY** — There are no games for another eleven days, so that dead line is what the
  front page has been showing you every time you open it, and will keep showing until
  August 7. The app already knew how to display "next up" — it just could not find the
  game, because the front page only ever looks inside the month it has loaded, and the
  next fixture was five days past the end of it.
- **WHERE** — New `app/lookahead.py` (pure, 19 tests, no network) + a scan wired into
  `/api/schedule` + three lines in `static/app.js`. Commit `fd10a53`.
  Before/after: `docs/overnight/shots/audit-home-390.png` →
  `docs/overnight/shots/sms-2-home-nextup-after.png`.
- **RISK** — This is the first change on this branch that touches code the live app
  runs, so unlike SMS-1 it is a real deploy if you keep it. When the window runs dry the
  server makes one extra ESPN call to look 45 days ahead — that is a slower response on
  those days only, and on Render's free tier a slow request is more noticeable than it
  sounds. If ESPN fails during that scan the page quietly falls back to the old message
  rather than erroring, which is the right trade but does mean the failure is invisible.
  A gap longer than 45 days would still show the old line.
- **KEEP / DISCARD** —

---

## Idea queue

1. ~~§mobile-month-calendar~~ → **CYCLE 1, shipped as SMS-1.**
2. ~~Off-season Home audit~~ → **CYCLE 2, shipped as SMS-2.** The audit found one real
   defect and it is fixed. Still open from the same look: the MAIN EVENT marquee — the
   front page's designed centrepiece — renders nothing at all when there are no games
   today, so the page has no headline for weeks at a time. Promoting the next fixture
   into that slot is a taste call, so it would ship as mockups.
3. Phone chrome pass — sticky tabs, safe-area/notch, tap-target sizes. Owed since the
   Jul-22 deploy.
4. Game-card density at 390px — how much fits before it stops being glanceable.

## Cycle log

- **CYCLE 1 — phone month calendar, two mockups — SHIPPED `83674f0`** (+ review board).
  Two things went wrong mid-cycle and both are worth remembering:
  (a) headless Chrome clamps its window to 500px wide on Linux, so the first pass measured
  and screenshotted a 500px "phone" — fixed with an iframe harness that pins 390px, and
  the probe now asserts the width so it cannot regress silently;
  (b) the first overflow assert measured the dot *row* rather than its children and passed
  green while the "+10" marker was visibly clipped in the screenshot.
- **CYCLE 2 — off-season "next up" lookahead — SHIPPED `fd10a53`.** Found by looking at
  the running app on a phone-width viewport, not by reading code — the dead line was in a
  branch that should have been unreachable. First pass got the contract wrong (the
  endpoint returned a game the caller already had, duplicating it); tightened so the new
  field can only ever mean "a fixture your window does not contain", with a test pinning
  that the key is absent in the ordinary case. 178 → 197 tests.

- **PAUSED at a clean cycle boundary, 2026-07-26 evening.** Not a STOPPING line — the queue
  is not empty and the lane can resume at idea 3 (phone chrome pass) whenever it is picked
  up. Paused rather than continued because SMS-1 is a question only Dylan can answer, and
  cycle 3 would stack a third undecided change on top of it.
- **One cross-repo item owed, needs Dylan's word:** the "headless Chrome clamps its window
  to 500px" finding belongs in the `headless-qa` skill (its own rule 8 says so), but that
  file lives under `~/.claude/`, which no session edits without him. Banked meanwhile in
  the repo memory `sms-session-gotchas`.
