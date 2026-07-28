# Proposals — lane `sms-ux` (Opus 5, night of 2026-07-26)

**How to use this file:** each entry has an ID (`SMS-1`, `SMS-2`…). Reply with IDs —
"keep SMS-1, discard SMS-2" — and the morning session executes exactly that. The
KEEP / DISCARD column is yours; I leave it blank. IDs are never renumbered or reused.

**Review board (the phone-friendly version of this file):**
<https://claude.ai/code/artifact/a1ac028b-0ea0-47bc-b52a-918e87ce2a65> — private,
rebuilt in place each pass from `docs/overnight/review-board.html`, so the URL is stable.
**Branch:** SMS-1..SMS-3 came from `auto/overnight-sms-ux` — **all three KEPT by Dylan
2026-07-26 and merged to `master` locally (`--no-ff`). STILL NOT PUSHED: push is a Render
deploy and is his hand only.** SMS-4 onward are on `auto/lane-sms-jul27`, branched from
that merge, and are **undecided**.
**Suite:** 206 passed (`./tools/validate`), green at every commit. Baseline at the start of
the Jul-27 lane was 197.

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
- **KEEP / DISCARD** — **KEEP** (Dylan, 2026-07-26: "Keep all 3")

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
- **KEEP / DISCARD** — **KEEP** (Dylan, 2026-07-26: "Keep all 3")

### SMS-3 — Option B, built for real

- **WHAT** — You picked B, so the phone Calendar tab now opens on a month grid with your
  scrolling day list still underneath it. Tap any day in the grid and the list jumps to
  start there. The ‹ › arrows now move a **month** at a time on the phone (they used to
  move seven days), because they have to agree with the grid above them.
- **WHY** — "See the next few weeks at a glance" is what the grid does; the list is what
  answers "so what's actually on". This keeps both and makes the grid steer the list.
- **WHERE** — `static/app.js` + `static/style.css` + a new phone QA harness
  `tools/qa-phone-calendar.py`. Commit `6e604ee`. Live shots:
  `docs/overnight/shots/sms-3-calendar-390.png` (phone) and
  `sms-3-calendar-desktop.png` (desktop, re-shot to prove it did not move).
  **This supersedes SMS-1** — keeping SMS-3 is what "keep B" means in code.
- **RISK** — The arrows changing meaning on the phone is the real one: seven days ago a
  swipe moved you a week, now it moves you a month, and that is muscle memory you already
  have. Three functions were deleted as part of it, so reverting is a revert of the whole
  commit rather than a flag. The day list is also capped at the loaded month, so tapping
  a day near month-end shows fewer than seven days and offers a "More in August" button
  instead of silently pretending those days are empty. And like SMS-2 this is live code:
  keeping it means a deploy.
- **KEEP / DISCARD** — **KEEP** (Dylan, 2026-07-26: "Keep all 3")

### SMS-4 — The phone chrome stops hiding behind the notch

- **WHAT** — Two fixes to the frame around every screen. **The notch:** when you
  scroll, the HOME / CALENDAR / PLAYOFFS / TABLES row was sliding up behind the
  iPhone's clock, and the bottom line of the footer was sitting under the home-bar.
  Both now stop at the edge of the safe area instead. **Fingertips:** the three
  filter chips (All / NFL / Soccer), the ‹ › month arrows, the Mark Watched button
  and the "Full tables →" link were all shorter than a fingertip. All four are now
  the standard size.
- **WHY** — I measured the running app at a real phone width instead of reading the
  code, and 16 of the 71 things you can tap were under the 44-pixel minimum the app's
  own design notes already ask for. The notch half is worse than it sounds: the page
  is deliberately set to run edge to edge under the notch — which is the right look —
  but nothing in the styling ever gave that space back, so on a real iPhone, and
  especially once it is added to your Home Screen, the tabs were genuinely unreadable
  while scrolled. It has been that way since the Jul-22 deploy.
- **WHERE** — `static/style.css` (four safe-area tokens + the tab bar, masthead,
  footer and page edges that use them; four control sizes), new
  `tests/test_phone_chrome.py` (9 tests), new `tools/qa-phone-chrome.py` +
  `docs/overnight/mockups/qa-chrome.html`. Commit `667c6bb`. Pictures — the red
  bands are the zones the iPhone reserves:
  `docs/overnight/shots/sms-4-chrome-before.png` (tabs and footer text inside them)
  → `sms-4-chrome-after.png` (both clear). Normal views:
  `sms-4-home-390.png`, `sms-4-calendar-390.png`, and `sms-4-desktop.png` re-shot to
  show desktop did not move.
- **RISK** — I do not own an iPhone to check this on, and neither does the test: no
  headless browser reports real notch measurements, so the harness feeds it fake ones
  and proves the layout *responds*. That is strong evidence the wiring is right and
  weak evidence about the exact look on your handset — the one thing worth eyeballing
  after a deploy. The taller chips also cost about 10 pixels of vertical space at the
  top of every screen, which is a real trade against a slightly larger target. And
  like SMS-2 and SMS-3 this is live code: keeping it means a deploy.
- **KEEP / DISCARD** —

---

## Idea queue

1. ~~§mobile-month-calendar~~ → **CYCLE 1 (mockups, SMS-1) → Dylan picked B →
   CYCLE 3 built it for real (SMS-3). CLOSED.**
2. ~~Off-season Home audit~~ → **CYCLE 2, shipped as SMS-2.** The audit found one real
   defect and it is fixed. Still open from the same look: the MAIN EVENT marquee — the
   front page's designed centrepiece — renders nothing at all when there are no games
   today, so the page has no headline for weeks at a time. Promoting the next fixture
   into that slot is a taste call, so it would ship as mockups.
3. ~~Phone chrome pass — sticky tabs, safe-area/notch, tap-target sizes~~ →
   **CYCLE 4, shipped as SMS-4. CLOSED.**
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

- **CYCLE 3 — option B built into the app — SHIPPED `6e604ee`.** Dylan answered "B, keep
  both". Two things surfaced during the port that the mockup had hidden: the mockup's
  weekday headers were Sunday-first while the server's padded range always starts on a
  Monday (every column mislabelled by one day — the app was already correct, the mockup
  was not), and "played" days rendered as 32%-opacity dots that are near-invisible at 5px
  and cannot reach the palette's documented 3:1 at any opacity that still reads as dimmed
  (measured: 1.67 / 2.10 / 2.54 : 1 at 32 / 45 / 55%, vs 6.26:1 solid). Played is now a
  hollow ring — full-strength colour, and a shape difference survives colour-blindness.
  New `tools/qa-phone-calendar.py` proxies the app and the harness through one origin so
  the running app can be pinned to a true 390px *and* measured into; 9 asserts green,
  including a real click that moves the real list.
- **CYCLE 4 — phone chrome pass — SHIPPED `667c6bb`.** Resumed 2026-07-27 on branch
  `auto/lane-sms-jul27`. Two things are worth remembering from it:
  (a) the safe-area defect was **invisible to every check the repo had** — the app
  renders perfectly in a desktop browser and in headless Chrome, because headless
  Chrome always reports 0px for `env(safe-area-inset-*)`. The fix for that is the
  reason the insets became named `--sa-*` tokens instead of inline `env()`: the
  harness can override the tokens and measure that the chrome moved. A layout that
  ignores the notch does not move at all, and that difference is the assert;
  (b) the first version of the new pytest guards asserted the *property* that carried
  the offset (`.tab-bar { top }`), which would have gone red the moment someone solved
  it a different way. Rewritten to assert where things land — and separately verified
  by checking out the pre-fix stylesheet and confirming 7 of the 9 fail against it,
  because a guard that passes on the broken version guards nothing.
  Also fixed mid-cycle: the tap-target regex matched `line-height: 1` and reported a
  40px arrow as "1". 197 → 206 tests.
- ~~PAUSED~~ **RESUMED and paused again after cycle 3, 2026-07-26.** Original note:
  **PAUSED at a clean cycle boundary, 2026-07-26 evening.** Not a STOPPING line — the queue
  is not empty and the lane can resume at idea 3 (phone chrome pass) whenever it is picked
  up. Paused rather than continued because SMS-1 is a question only Dylan can answer, and
  cycle 3 would stack a third undecided change on top of it.
- ~~One cross-repo item owed, needs Dylan's word:~~ **DONE — Dylan approved one line,
  added as `headless-qa` rule 9 (backup `SKILL.md.bak-2026-07-26`).** Original note: the "headless Chrome clamps its window
  to 500px" finding belongs in the `headless-qa` skill (its own rule 8 says so), but that
  file lives under `~/.claude/`, which no session edits without him. Banked meanwhile in
  the repo memory `sms-session-gotchas`.
