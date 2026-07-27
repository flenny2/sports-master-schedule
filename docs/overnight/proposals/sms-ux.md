# Proposals — lane `sms-ux` (Opus 5, night of 2026-07-26)

**How to use this file:** each entry has an ID (`SMS-1`, `SMS-2`…). Reply with IDs —
"keep SMS-1, discard SMS-2" — and the morning session executes exactly that. The
KEEP / DISCARD column is yours; I leave it blank. IDs are never renumbered or reused.

**Review board (the phone-friendly version of this file):** published as a private
Artifact, rebuilt each pass from `docs/overnight/review-board.html`.
**Branch:** `auto/overnight-sms-ux` · **Nothing is pushed. Nothing is merged.**
**Suite:** 178 passed (`./tools/validate`), green at every commit on this branch.

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

---

## Idea queue

1. ~~§mobile-month-calendar~~ → **CYCLE 1, shipped as SMS-1.**
2. Off-season Home audit — late July, so the front page's job is "what's coming", not
   "what's on". Check it isn't mostly empty boxes.
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
