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
**Suite:** 254 passed (`./tools/validate`), green at every commit. Baseline at the start of
the Jul-27 lane was 197.
**Receipts:** every entry from SMS-4 on ends with a `RECEIPTS` line (run-law rule 14) so a
read-only audit can verify this run without a live reviewer seat.

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
- **RECEIPTS** — suite 206 vs baseline 197 · **never pushed** (push here is a Render deploy) · branch-only, nothing merged to `master` · phone chrome measured live at 390px; desktop re-shot unchanged

### SMS-5 — Something to headline the Home page out of season, built twice

- **WHAT** — The big banner slot at the top of Home is empty right now and stays
  empty until the season starts. Two things that could fill it, so you pick.
  **A (next game):** the next fixture becomes the big card — full size, team
  colours, "Kicks off in 9d 23h" under it — so the page looks the same in August
  as it does in October. **B (countdown board):** instead of one game, a short
  board of when each of your competitions starts — *NFL · Thu Aug 6 · 10 days* /
  *Premier League · Fri Aug 21 · 25 days*. Nothing in the app changed either way.
- **WHY** — The banner is the front page's designed centrepiece, and on a day with
  no games it renders nothing at all, which is why Home currently starts with the
  Your Teams strip and then a small "next up" line. That is weeks of the page having
  no headline. Which of the two is right is a taste question, so both are built.
- **WHERE** — `docs/overnight/mockups/headline-variants.html` +
  `tools/shoot-headline-mockups.py`. Commit `ffe2f1b`. Shots:
  `docs/overnight/shots/sms-5-headline-a-nextgame.png` and
  `sms-5-headline-b-countdown.png`. **No file the app loads was touched.**
- **RISK** — A puts a game that is ten days away at the same visual weight as a
  kickoff happening now, which may read as louder than it deserves; the shot also
  shows the cost of that size at 390px — "CAROLINA PANTHE…" truncates, where the
  small card fits "CAR". B is quieter and always honest, but on a normal Saturday
  it would have nothing to say, so B is really a *second* state the page needs
  rather than a replacement — that is the part I would want your read on. Both are
  mockups: choosing one is then a real change to the page you open most, on a repo
  where shipping is a deploy.
- **KEEP / DISCARD** — **DEFERRED, not declined** (Dylan by phone, 2026-07-27 ~20:30): *"I will wait"* — he wants a review sitting where he can see the two screenshots, because picking from titles would waste the work. Banked at the meta desk in `reports/dylan-rulings-jul27.md` under **Explicitly deferred — do NOT read as approval**. No verdict yet, so no `CLOSED` line; recorded here so nobody re-asks and nobody mistakes the silence for a keep.
- **RECEIPTS** — suite 206 vs baseline 197 · **never pushed** (push here is a Render deploy) · branch-only, nothing merged to `master` · mockups only — no file the app loads was touched

### SMS-6 — The August checklist now runs itself, and one real bug in it is fixed

- **WHAT** — Two things. **The bug:** the title-race widget worked out "matches
  left" by assuming every league plays 38, which is true of the Premier League and
  wrong for the Bundesliga and Ligue 1 — a race in either would have shown four
  matches, twelve points, of "still winnable" that do not exist. It now works the
  number out from the size of the table instead, so it is right for any league.
  **The checklist:** there is a list in the repo of five settings that quietly go
  out of date every August. It was a note for a human to remember. It is now a
  command — `./tools/rollover-check` — and the test run prints a one-line summary
  of it every time, so nobody has to remember.
- **WHY** — August is ten days away and this list has never been walked. Running it
  for the first time found the Premier League storyline expired on 31 May, which is
  why the Calendar has no storyline filter at all right now. Nothing crashed and
  nothing looked broken — that is exactly the failure mode the list warns about.
- **WHERE** — New `app/rollover.py` + `tools/rollover-check`, a summary line in
  `tools/validate`, the season-length fix in `app/espn.py`, three lines in
  `static/app.js`. Commit `2a4ddbb`. 206 → 246 tests.
- **RISK** — The summary prints but never fails the test run, on purpose: what it
  catches are choices only you can make, and a failing suite would block every
  future session on your say-so. The trade is that a printed warning can be
  scrolled past. The season-length fix assumes a normal home-and-away league; a
  split season like the Scottish Premiership would be wrong in the same direction
  the old number was, which is written down at the code. And the checker is honest
  about its limits — it cannot tell a year-old title race from a current one, so it
  asks rather than guessing.
- **KEEP / DISCARD** —
- **RECEIPTS** — suite 246 vs baseline 197 · **never pushed** (push here is a Render deploy) · branch-only, nothing merged to `master` · new tests verified to fail 15/17 against the old constant

### SMS-7 — The Calendar has its storyline filter back

- **WHAT** — Three things, all from acting on what SMS-6's checker reported.
  **The filter:** the PL Title Race chip on the Calendar — the one that shows only
  Arsenal and Man City games — expired on 31 May and nothing replaced it, so it has
  been gone for two months. Renewed for the new season; the chip is back.
  **Dead setting:** a leftover NBA setting that nothing had used since NBA was
  unplugged is deleted. **And one it was hiding:** bringing the chip back made it
  visible to the phone measurements for the first time, and it was 38 pixels tall
  against the 44 the app asks for. Fixed too.
- **WHY** — Nothing was broken, which is the point: an expired storyline correctly
  stops showing, and then nothing replaces it, and the Calendar just quietly loses a
  feature. That is the exact failure the August checklist warns about, and it had
  already happened before anybody ran the checklist.
- **WHERE** — `config.py`, `static/style.css`, tests in `tests/test_storylines.py`
  and `tests/test_phone_chrome.py`. Commit `a97934e`. Shot:
  `docs/overnight/shots/sms-7-calendar-storyline-390.png`. 246 → 249 tests, and the
  checker now reports **0 stale**.
- **RISK** — I chose the contenders by carrying last season's forward: Arsenal and
  Man City again. That is a guess about your new season, not a fact, and it is the
  same guess the title-race widget is already making — the checker asks you about it
  separately for that reason. If you want different teams, it is two ids in one file.
  Deleting the NBA setting is only awkward if NBA comes back, and a comment in its
  place says where the old values live. Live code: keeping it means a deploy.
- **KEEP / DISCARD** —
- **RECEIPTS** — suite 249 vs baseline 197 · **never pushed** (push here is a Render deploy) · branch-only, nothing merged to `master` · both storyline tests verified to fail against the old config

### SMS-8 — The big card wraps a long team name instead of cutting it

- **WHAT** — On the banner card at the top of Home, "CAROLINA PANTHERS" was being
  cut to "CAROLINA PANTHE…". It now wraps onto two lines and shows the whole name.
  The ordinary cards in the Calendar list are unchanged, on purpose.
- **WHY** — I measured every card the app draws at phone width, both closed and
  opened: **nothing is being cut** — 19 cards, zero losses. The one place text was
  disappearing is the big banner card, where the team name is set larger. It was
  short by six pixels.
- **WHERE** — `static/style.css` (one rule), two tests, and a new measuring tool
  `tools/qa-phone-cards.py`. Commit `612fff0`. The wrapped banner is visible in the
  re-shot `docs/overnight/shots/sms-5-headline-a-nextgame.png`; an opened card at
  phone width is `sms-8-card-expanded-390.png`.
- **RISK** — A two-line name makes the banner taller, and if the two teams have
  names of different lengths the card is slightly lopsided. I chose wrapping over a
  smaller font because six pixels would have fixed those two names and still failed
  on something like "Wolverhampton Wanderers" — but if you would rather the banner
  stayed one line at any cost, that is a one-line revert. Past two lines the "…"
  comes back, so the card cannot grow forever.
- **KEEP / DISCARD** —
- **RECEIPTS** — suite 251 vs baseline 197 · **never pushed** (push here is a Render deploy) · branch-only, nothing merged to `master` · measured against the running app at a true 390px; desktop re-rendered at 1100px unchanged

### SMS-9 — One card per story on the front page, not two

- **WHAT** — The Storylines block on Home was showing two cards for the same
  Premier League title race: the proper race card, and a second, thinner one
  underneath it. Now just the one.
- **WHY** — Renewing the storyline in SMS-7 is what made the second card appear.
  The app already knew not to show both — but it worked out which competition a
  storyline belonged to by looking through the games it had loaded, and right now
  it has loaded no Premier League games at all, so it found nothing and skipped
  nothing. It reads the setting directly now.
- **WHERE** — `app/storylines.py` (the endpoint now sends each storyline's league)
  and `static/app.js`. Commit `15e9474`. Verified against the running app at 390px:
  one card where there were two. 251 → 252 tests.
- **RISK** — The half that decides which card to hide is browser code, and this repo
  has no way to test browser code without adding a new tool — which the lane rules
  forbid. So the server half is covered by tests and the browser half is covered by
  a screenshot. It also only bites when a storyline and a title race describe the
  same competition, which is exactly your current setup, so if you change either one
  this is worth a second look.
- **KEEP / DISCARD** —
- **RECEIPTS** — suite 252 vs baseline 197 · **never pushed** (push here is a Render deploy) · branch-only, nothing merged to `master` · duplicate confirmed gone against the running app at 390px

### SMS-10 — The button that spends money is now big enough to hit

- **WHAT** — I drove the whole tactical-read flow on a phone for the first time:
  open an upcoming game, press the read button, wait for it, read it. The panel
  itself is in good shape — five sections, nothing cut off, nothing spilling out
  of the card, readable line length. One thing was wrong and it is the one that
  matters: **the button that spends money was too small to hit reliably**, and so
  was "Refresh read", which deliberately spends again. Both are the standard size
  now.
- **WHY** — This is the most expensive thing in the app and the reason the hub
  exists beyond a schedule, and nobody had ever looked at it on a phone. Whatever
  you saw the first time you pressed that button would have been whatever it
  happened to look like. The check costs **nothing to run**: with no API key set,
  the server returns stand-in text in the same shape a real read has, so the whole
  chain works end to end at $0.
- **WHERE** — `static/style.css` (two buttons), new `tools/qa-phone-intel.py` +
  `docs/overnight/mockups/qa-intel.html`, two tests. Commit `a4a557f`.
  Shot: `docs/overnight/shots/sms-10-intel-390.png`. 252 → 254 tests.
- **RISK** — Very low as a change: two buttons got taller. The honest caveat is
  about the *check*, not the change — it runs against stand-in text, so it proves
  the layout and the plumbing, not what a real read reads like. That is still your
  call to make when you set the key. Three bugs in my own test rig had to be fixed
  before it worked at all, which is a fair warning that this flow is the least
  exercised part of the app.
- **KEEP / DISCARD** —
- **RECEIPTS** — suite 254 vs baseline 197 · **never pushed** (push here is a Render deploy) · branch-only, nothing merged to `master` · driven at $0 in dry-run; the generated read was wiped from the user-data store afterwards

### SMS-11 — Cards stop claiming a league position before anyone has played

- **WHAT** — Open an August Premier League game and the card said
  **"ARS: 2nd in Premier League · AVL: 3rd in Premier League"**. Nobody has played
  a match. Between seasons the data source zeroes everything and sorts the table
  alphabetically, so "2nd" meant *second in the alphabet*. That line no longer
  appears until the season is real.
- **WHY** — This is the same thing you asked me to fix in July — "fix the zeros" —
  which was fixed in four places. The game card was a fifth that nobody had
  counted. It only shows up between seasons, which is exactly now.
- **WHERE** — `static/app.js`. Commit `d5dfd02`. Verified both ways against the
  running app: an August Premier League card shows no standings line, and a July
  World Cup card still shows **"JPN: 2nd in FIFA World Cup · BRA: 1st in FIFA
  World Cup"** — the fiction gone, the fact kept.
- **RISK** — While fixing it I found a second thing and fixed it in the same
  change: the card looked up a team's position in whichever league it found them
  in FIRST, not the one they were playing in. With the Premier League skipped it
  briefly showed "ARS: 1st in Champions League" on a Premier League fixture. It
  had always worked that way and had simply been getting lucky. That is a
  behaviour change beyond the headline fix, so it is worth knowing about. Like
  SMS-9, the gate lives in browser code and this repo has no way to test browser
  code without adding a tool the lane rules forbid — so it is verified by
  screenshots at both ends.
- **KEEP / DISCARD** —
- **RECEIPTS** — suite 254 vs baseline 197 · **never pushed** (push here is a Render deploy) · branch-only, nothing merged to `master` · verified in both directions against the running app at 390px

---

## Idea queue

1. ~~§mobile-month-calendar~~ → **CYCLE 1 (mockups, SMS-1) → Dylan picked B →
   CYCLE 3 built it for real (SMS-3). CLOSED.**
2. ~~Off-season Home audit~~ → **CYCLE 2, shipped as SMS-2.** ~~Still open: the empty
   MAIN EVENT marquee~~ → **CYCLE 5, shipped as SMS-5 (two mockups). Parked on Dylan.**
3. ~~Phone chrome pass — sticky tabs, safe-area/notch, tap-target sizes~~ →
   **CYCLE 4, shipped as SMS-4. CLOSED.**
4. ~~Game-card density at 390px~~ → **CYCLE 8, shipped as SMS-8.** Answer: ordinary
   cards lose nothing at 390px; only the banner did, and it now wraps.
8. ~~Two cards for one story on the Front Page~~ → **CYCLE 9, shipped as SMS-9.**
5. ~~The season-rollover checklist goes stale silently every August~~ → **CYCLE 6,
   shipped as SMS-6.** The checklist is a command now, and the one real bug in it (the
   hardcoded 38-match season) is fixed. What it found is the next cycle's work.
6. ~~Act on the two STALE items the checker reports~~ → **CYCLE 7, shipped as SMS-7.**
   Both cleared; the checker reports 0 stale.
7. The three `needs-you` items the checker asks about — title-race contenders for the
   new season, the primetime network set against the 26-27 rights deals, the fantasy
   roster after the late-August draft. All Dylan's; the checker's job is only to ask.

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
- **CYCLE 5 — the empty headline slot, built twice — SHIPPED `ffe2f1b`.** The taste call
  went to Dylan as two mockups rather than a guess (lane rule 5). The method changed from
  cycle 1 deliberately: instead of re-drawing the front page in a parallel stylesheet,
  each variant is a **transformation of the running app** — the harness calls the app's
  own `buildCard()`/`el()` with the app's own data, so the shots cannot drift from what
  shipping would look like. Cycle 1's mockup drifted exactly that way (Sunday-first
  weekday headers the app never had), and this removes the whole class of that mistake.
  One harness bug fixed on the way and worth remembering: waiting on `.fp-slate` raced the
  schedule fetch, so variant A failed on a cold cache while B passed on a warm one — same
  page, same code, different second. It now waits for the "next up" card, which IS the
  precondition both variants need. Also learned: variant B needs **no new endpoint** —
  the Premier League's 21 August restart is nowhere near the loaded month, but the page
  already knows it from the title race's `upcoming` list.
- **CYCLE 6 — the August rollover made visible + the 38-match bug — SHIPPED `2a4ddbb`.**
  Picked over the remaining polish ideas because it is the only dated item in the repo:
  the checklist is due in ten days and had never been walked. Three judgements worth
  keeping: (a) the season length is **derived from the standings table's own size**
  rather than a per-league map — a map fixes today's leagues and then goes stale
  exactly like everything else on the checklist, and the table already knows how many
  teams are in it; (b) where the size is not a league at all the helper returns None
  and the widget drops the figure, because inventing one is precisely what the old
  constant did; (c) the checker's `stale` / `needs-you` split is the whole design — one
  a session may act on unasked, the other only Dylan can answer, and blurring them
  turns the output into a nag list, which is how the prose version went unread for two
  months. Advisory, never fatal: a red suite would block every future session on a
  config choice that is his. Verified the new tests fail 15/17 against the old
  constant. 206 → 246 tests.
- **CYCLE 7 — clear both stale rollover items — SHIPPED `a97934e`.** The cycle's own
  lesson is the third thing it found. Renewing the storyline made the Calendar's filter
  chip render for the first time in two months, and the phone harness failed on it
  immediately: 38px against the documented 44. **SMS-4's live pass could not have caught
  it** — the whole filter row was hidden that day and measured 0×0. A measurement
  harness only covers what is on screen, so a control that appears seasonally needs a
  static check too; `.sl-chip` is now in both. Also worth keeping: the new storyline's
  `start_date` is **1 June, not 1 August**, so its window is exactly complementary to
  the expired entry's — an August floor would have left the chip missing another five
  days while the checker called it "ok", because `get_active_storylines` withholds a
  storyline whose start has not arrived. And it HAS a start_date at all, which its
  predecessor deliberately did not: that omission was safe when 25-26 was the only
  season the app had seen, and would now back-tag every Arsenal–City match from last
  season with a 26-27 chip. 246 → 249 tests.
- **CYCLE 8 — game-card density at 390px — SHIPPED `612fff0`.** The measurement was
  the point and it half-cleared the idea: **ordinary cards lose nothing** — 19 cards,
  collapsed and expanded, zero text cut. Only the banner did, by six pixels. Two things
  had to be right for the harness to find it, and the first version got both wrong.
  It must measure the **worst name in the data**, not the first game — a card reading
  "COD" and "ENG" fits at any size and answers nothing. And it must measure **both card
  layouts**: a finished game renders a scoreboard (name beside a two-digit score) while
  an upcoming one renders name-beside-kickoff-time, with far less room. Measuring only
  the finished layout reported "fits" and was wrong, because the loaded July window is
  all completed World Cup matches. The fix is a **wrap, not a smaller font** — six
  pixels would have fixed those two names and still failed on "Wolverhampton Wanderers".
  Also extracted `tools/phone_harness.py`: three drivers had each pasted the same
  one-origin proxy and a fourth was about to; all three re-run green after.
  249 → 251 tests.
- **CYCLE 9 — the duplicate story card — SHIPPED `15e9474`.** Kept as its own cycle
  rather than folded into 8, because it is independently keepable and because it was
  SMS-7's fallout, not SMS-8's subject. The shape of the bug is the lesson: the dedupe
  **derived** a storyline's league by scanning the loaded games, which is a correct
  answer mid-season and no answer at all in the off-season, when the window holds no
  Premier League fixture — so it found nothing, matched nothing, and skipped nothing.
  Deriving from data that is *usually* there fails exactly when the page is emptiest,
  which is also when it is most visible. It reads the configured `leagues` now, with
  the game scan kept only as the fallback for a storyline that names none. Honest
  limit recorded in the entry: the deciding half is browser code and this repo has no
  JS runner, so the server half is tested and the browser half is a screenshot.
  251 → 252 tests.
- **CYCLE 10 — the tactical read, driven on a phone for the first time — SHIPPED
  `a4a557f`.** The app's most expensive feature, never looked at on a phone, checked
  at $0 because dry-run returns the same SHAPE a real read has. The panel was fine;
  the button that SPENDS was 40px, and so was "Refresh read". Neither was reachable
  by any earlier sweep — both only exist inside an expanded card of an upcoming
  soccer or NFL game, and the off-season Calendar shows none. **Three bugs in my own
  rig had to be fixed first, and all three would have produced a confident wrong
  answer:** (a) the shared proxy had no `do_POST`, so every write hit a 501 the
  handler wrote itself and never reached Flask — and `fetch` resolves either way, so
  the symptom was "no read after 500 polls" against a server that was never asked;
  (b) waits keyed on `Date.now()` are wrong under a virtual clock, which races ahead
  whenever the page is idle, so a "60 second" deadline expires in a blink while the
  real round-trips have not landed — this harness counts ticks; (c) it waited only
  for the read BUTTON, so the screenshot run timed out against a healthy page that
  was showing a cached read and a Refresh link instead. 252 → 254 tests.
- **CYCLE 11 — the preseason standing on a game card — SHIPPED `d5dfd02`.** Found by
  reading cycle 10's screenshot, not the code. Worth keeping: the obvious fix was
  **not sufficient and its intermediate state looked plausible** — with the Premier
  League skipped as preseason, the finder fell through to the next league holding
  that team id and printed "ARS: 1st in Champions League" on a Premier League
  fixture. It had always taken the first id match anywhere and had simply been
  landing on the right league by luck. Scoping to the game's own competition fixes
  both and closes the documented id-collision trap. Verified in BOTH directions,
  which is what makes it a fix rather than a deletion: the August PL card shows no
  row, the July World Cup card still shows one.
- **PASS 2026-07-27 late — no new proposal, deliberately.** Checked for a ruling on
  SMS-4..SMS-11 (rule 11 re-read: no `STOP-THE-RUN`, no `SLOW-THE-RUN`). One verdict
  existed and was not in this file: **SMS-5 is DEFERRED by Dylan, not declined** — *"I
  will wait"* for a sitting where he can see the two screenshots. Banked at the meta desk
  (`reports/dylan-rulings-jul27.md`), whose own header says a proposal file showing the ID
  as open until someone stamps it is *expected, not a lost verdict*. Stamped here now, so
  no future session re-asks and nobody reads the silence as a keep.
  **Why nothing was built this pass, stated as a judgement rather than a rule firing:**
  rule 12's trigger is a lane that cannot name a next cycle, and I can name two (the team
  detail view; the NFC mini table on Home). What is actually true is different and worse —
  **the queue is review-bound, not idea-bound.** Seven defect proposals sit undecided, and
  Dylan's own stated blocker on SMS-5 is finding a sitting to review in. Adding an eighth
  would have made his one blocker heavier. Rule 16 covers "not now" but it is HIS lever and
  he has not pulled it, so this is my call and it is recorded as mine.
  **What was done instead attacks the constraint:** the board now opens with *the seven, in
  one screen* — one line of case per ID and a stated recommendation, so all seven can be
  answered with `keep all seven`. The full entries stay below as depth. SMS-5's slot on the
  board says he already answered rather than asking again.
  **Cadence: maintenance from here** — longest wake, and each wake re-reads this file's top,
  the charter, and TODOS before doing anything. Building resumes when he rules, or when
  something real turns up.
- **Run status, 2026-07-27: OPEN-ENDED on Dylan's direct word** (lane-kickoffs rule 10) —
  finishing the chartered job is not the end. Ends only on his word here, a
  `STOP-THE-RUN` line at the top of this file, or a fence that needs him.
  **Run-law rules 11–15 arrived mid-run** (meta `4baee52`) and are in force from cycle 7:
  re-read this file's top and the charter at every cycle start and wakeup, because
  `STOP-THE-RUN` is the fleet's only phone-reachable kill switch and it only works if a
  lane actually looks (11) · a dry queue **downshifts and files a proposal saying so**
  rather than inventing work, because Dylan's review minutes are the scarce resource (12)
  · verdicts get stamped back into THIS file when he rules (13) · every entry carries a
  `RECEIPTS` line — added retroactively to SMS-4..SMS-7 (14) · no machinery, ever (15).
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
