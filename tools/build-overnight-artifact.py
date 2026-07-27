#!/usr/bin/env python3
"""Assemble the overnight lane's review board into one self-contained page.

Run from the repo root:  python3 tools/build-overnight-artifact.py

Output: docs/overnight/review-board.html — published as ONE private
Artifact and REFRESHED IN PLACE each pass (same file path, same URL).
Dylan reviews from a phone and cannot open a file on a local branch, so
this page is the review surface: the live mockups and the proposal list
in one place, decidable without opening anything.

Everything is inlined because a published Artifact runs under a strict
CSP that blocks every external host — no CDN, no font URL, no remote
image. A linked stylesheet would fail silently and hand him a page in
system fonts, which is not the product.

The board copy lives in BOARD_* below rather than in a separate file:
one page, one place to edit, and the proposal text has to stay in step
with docs/overnight/proposals/sms-ux.md by hand anyway.

Stdlib only. No new dependencies (lane fence 4).
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCKUPS = os.path.join(REPO, "docs", "overnight", "mockups")
OUT = os.path.join(REPO, "docs", "overnight", "review-board.html")


SHOTS = os.path.join(REPO, "docs", "overnight", "shots")


def read(name):
    with open(os.path.join(MOCKUPS, name), encoding="utf-8") as f:
        return f.read()


def shot_uri(name):
    """A screenshot as a data URI — the Artifact CSP blocks image hosts."""
    import base64
    with open(os.path.join(SHOTS, name), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


# ── Board styles ────────────────────────────────────────────────────
# A "review desk": a deep slate ground so the light phone specimens read
# as lit objects sitting on it. The one colour shared with the product is
# its gold lead, which ties the board to the app without imitating it.
# The specimens themselves are always light — the app is single-light by
# Dylan's Jul-15 ruling — while the board around them follows the
# viewer's theme, as an Artifact must.
BOARD_CSS = """
:root {
  --desk:    #151A22;
  --desk-2:  #1E2530;
  --desk-3:  #2A3341;
  --txt:     #E9EEF5;
  --txt-2:   #98A6B8;
  --line:    rgba(233, 238, 245, 0.13);
  --gold:    #FFC93C;
  --gold-tx: #FFC93C;
  --keep:    #4ADE80;
  --risk:    #FCA5A5;
  --f-disp:  "Saira Condensed", "Arial Narrow", sans-serif;
  --f-body:  "Instrument Sans", system-ui, sans-serif;
  --f-mono:  "JetBrains Mono", ui-monospace, monospace;
  color-scheme: dark;
}
@media (prefers-color-scheme: light) {
  :root {
    --desk:    #E7EBF1;
    --desk-2:  #FFFFFF;
    --desk-3:  #DCE2EA;
    --txt:     #101720;
    --txt-2:   #55606F;
    --line:    rgba(12, 21, 34, 0.14);
    --gold-tx: #8A5A06;
    --keep:    #15803D;
    --risk:    #B91C1C;
    color-scheme: light;
  }
}
:root[data-theme="light"] {
  --desk:    #E7EBF1;
  --desk-2:  #FFFFFF;
  --desk-3:  #DCE2EA;
  --txt:     #101720;
  --txt-2:   #55606F;
  --line:    rgba(12, 21, 34, 0.14);
  --gold-tx: #8A5A06;
  --keep:    #15803D;
  --risk:    #B91C1C;
  color-scheme: light;
}
:root[data-theme="dark"] {
  --desk:    #151A22;
  --desk-2:  #1E2530;
  --desk-3:  #2A3341;
  --txt:     #E9EEF5;
  --txt-2:   #98A6B8;
  --line:    rgba(233, 238, 245, 0.13);
  --gold-tx: #FFC93C;
  --keep:    #4ADE80;
  --risk:    #FCA5A5;
  color-scheme: dark;
}

.board {
  background: var(--desk);
  color: var(--txt);
  font-family: var(--f-body);
  font-size: 16px;
  line-height: 1.55;
  min-height: 100vh;
  padding: 0 0 64px;
}
.board *, .board *::before, .board *::after { box-sizing: border-box; }
.wrap {
  max-width: 640px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 30px;
}
.board p { max-width: 62ch; }
.board :focus-visible { outline: 2px solid var(--gold); outline-offset: 3px; }

.eyebrow {
  font-family: var(--f-mono);
  font-size: 0.66rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--txt-2);
}
.board h1 {
  font-family: var(--f-disp);
  font-weight: 700;
  font-size: clamp(2.4rem, 9vw, 3.4rem);
  line-height: 0.95;
  letter-spacing: 0.01em;
  text-transform: uppercase;
  text-wrap: balance;
  margin: 0;
}
.board h2 {
  font-family: var(--f-disp);
  font-style: italic;
  font-weight: 700;
  font-size: 1.5rem;
  line-height: 1;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  margin: 0;
}
.head { padding-top: 34px; display: flex; flex-direction: column; gap: 12px; }
.lede { font-size: 1.06rem; color: var(--txt); }
.muted { color: var(--txt-2); font-size: 0.94rem; }

/* The decision block. Deliberately the loudest thing on the page after
   the title: Dylan's standing rule is that a reply asking him to decide
   must be decidable from the reply alone. */
.decide {
  background: var(--desk-2);
  border: 1px solid var(--line);
  border-left: 4px solid var(--gold);
  border-radius: 4px;
  padding: 20px 22px 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.decide h2 { color: var(--gold-tx); }
.opt { display: flex; flex-direction: column; gap: 3px; }
.opt-name {
  font-family: var(--f-disp);
  font-weight: 700;
  font-size: 1.12rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.rec {
  border-top: 1px solid var(--line);
  padding-top: 14px;
  font-size: 0.97rem;
}
.rec b { color: var(--gold-tx); }
.rec .cmd {
  display: block;
  padding: 11px 13px;
  border-radius: 6px;
  background: var(--desk-3);
  font-family: var(--f-mono);
  font-size: 0.86rem;
  overflow-x: auto;
}

/* Segmented A/B control. Hidden once both specimens fit side by side. */
.switch {
  display: flex;
  gap: 6px;
  background: var(--desk-3);
  border-radius: 10px;
  padding: 5px;
  position: sticky;
  top: 8px;
  z-index: 5;
}
.switch button {
  flex: 1;
  min-height: 46px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--txt-2);
  font-family: var(--f-disp);
  font-weight: 700;
  font-size: 1.02rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  cursor: pointer;
}
.switch button[aria-pressed="true"] { background: var(--gold); color: #0C1522; }

.stages { display: flex; flex-direction: column; gap: 26px; }
.stage { display: flex; flex-direction: column; gap: 10px; }
.stage[hidden] { display: none; }
.stage-cap {
  font-family: var(--f-mono);
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--txt-2);
}
.stage-cap b { color: var(--txt); font-weight: 500; }
/* The specimen sits in a plain bezel, not a drawn phone: a fake notch
   would be decoration, and he is reading this ON a phone anyway. */
.bezel {
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  max-width: 414px;
  width: 100%;
  background: #EEF1F5;
}

/* Before/after pair. The images are full-fold phone screenshots with
   dead space below the interesting part, so CSS crops from the top
   rather than shipping a second, cropped copy of each PNG. */
.ba { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.ba figure { margin: 0; display: flex; flex-direction: column; gap: 6px; }
.ba figcaption {
  font-family: var(--f-mono);
  font-size: 0.63rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-2);
}
.ba .shot.tall { height: 420px; object-position: 50% 20%; }
.ba .shot {
  width: 100%;
  height: 300px;
  object-fit: cover;
  object-position: 50% 62%;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #EEF1F5;
}

/* Proposal entries. The ID is the decision surface, so it leads. */
.prop {
  background: var(--desk-2);
  border: 1px solid var(--line);
  border-radius: 4px;
  overflow: hidden;
}
.prop-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 14px 18px;
  background: var(--desk-3);
  flex-wrap: wrap;
}
.prop-id {
  font-family: var(--f-mono);
  font-weight: 700;
  font-size: 0.86rem;
  letter-spacing: 0.08em;
  color: var(--gold-tx);
}
.prop-title { font-family: var(--f-disp); font-weight: 700; font-size: 1.2rem;
              letter-spacing: 0.03em; text-transform: uppercase; }
.prop dl { margin: 0; padding: 16px 18px 18px; display: grid; gap: 12px; }
.prop dt {
  font-family: var(--f-mono);
  font-size: 0.63rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--txt-2);
  margin-bottom: 3px;
}
.prop dd { margin: 0; font-size: 0.96rem; }
.prop dd code {
  font-family: var(--f-mono);
  font-size: 0.84em;
  background: var(--desk-3);
  padding: 1px 5px;
  border-radius: 3px;
}
.risk dd { color: var(--risk); }
.verdict dd { color: var(--txt-2); font-style: italic; }

.list { margin: 0; padding-left: 1.15rem; display: grid; gap: 7px; }
.list li { font-size: 0.96rem; }
.foot {
  border-top: 1px solid var(--line);
  padding-top: 20px;
  font-family: var(--f-mono);
  font-size: 0.72rem;
  line-height: 1.75;
  letter-spacing: 0.03em;
  color: var(--txt-2);
}
.foot b { color: var(--txt); font-weight: 500; }

/* Wide screens see both specimens at once; the switch becomes noise. */
@media (min-width: 940px) {
  .wrap { max-width: 960px; }
  .switch { display: none; }
  .stages { flex-direction: row; align-items: flex-start; gap: 24px; }
  .stage { flex: 1; min-width: 0; }
  .stage[hidden] { display: flex; }
}
@media (prefers-reduced-motion: reduce) {
  .board * { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}
"""


BOARD_HTML = """
<div class="board">
<div class="wrap">

  <header class="head">
    <div class="eyebrow">Sports hub · overnight lane · night of Sat 26 Jul 2026</div>
    <h1>The calendar,<br>built your way</h1>
    <p class="lede">
      You picked <b>B — keep both</b>, so the phone Calendar tab now opens on a month grid
      with your scrolling day list still underneath it. Tap a day in the grid and the list
      jumps there. It is built, measured on a real 390px phone viewport, and waiting on
      your branch.
    </p>
    <p class="muted">
      The two mockups are still below, unchanged, as the record of what you were choosing
      between. They are separate pages that cannot touch the app.
    </p>
  </header>

  <section class="decide">
    <h2>Decided — B</h2>
    <p>You chose: the month grid sits <b>above</b> the scrolling list rather than replacing it.
    Built as SMS-3 below. Here is what each option was, for the record.</p>

    <div class="opt">
      <span class="opt-name">A · Replace</span>
      <span class="muted">Month grid, tap a day, that day's games appear below it. The scrolling
      list is retired. Simplest result: one calendar, one way to read it.</span>
    </div>
    <div class="opt">
      <span class="opt-name">B · Keep both</span>
      <span class="muted">Month grid on top for the glance, the scrolling list still underneath.
      Tapping a day moves the list to start there, so the grid steers the feed.</span>
    </div>

    <div class="rec">
      <b>All three kept</b> — your word, 26 July — and merged onto <code>master</code> as
      <code>f33309b</code>. 197 tests green, verified against the running app at a real
      390px viewport. <b>Nothing is deployed.</b> One command from you does that:
      <br><br>
      <code class="cmd">git push origin master</code>
      <br>
      Kept, for the record: SMS-3 is the calendar you chose, SMS-2 removes the dead line
      the front page shows every day until 7 August, and SMS-1 is the pair of mockups that
      record why SMS-3 looks the way it does.
    </div>
  </section>

  <h2 style="margin-bottom:-14px">The two mockups, for the record</h2>
  <div class="switch" role="group" aria-label="Choose a layout to view">
    <button type="button" id="btn-a" aria-pressed="true">A · Replace</button>
    <button type="button" id="btn-b" aria-pressed="false">B · Keep both</button>
  </div>

  <div class="stages">
    <div class="stage" id="stage-a">
      <div class="stage-cap"><b>A · Replace</b> — grid, then the day you tapped</div>
      <div class="bezel">
        <div class="phone">
          <header class="mock-mast">
            <h1>Sports Master Schedule</h1>
            <nav class="mock-tabs">
              <span>Home</span><span class="on">Calendar</span><span>Playoffs</span><span>Tables</span>
            </nav>
          </header>
          <main id="view-a"></main>
        </div>
      </div>
    </div>

    <div class="stage" id="stage-b" hidden>
      <div class="stage-cap"><b>B · Keep both</b> — grid, then the scrolling list</div>
      <div class="bezel">
        <div class="phone">
          <header class="mock-mast">
            <h1>Sports Master Schedule</h1>
            <nav class="mock-tabs">
              <span>Home</span><span class="on">Calendar</span><span>Playoffs</span><span>Tables</span>
            </nav>
          </header>
          <main id="view-b"></main>
        </div>
      </div>
    </div>
  </div>

  <section>
    <h2 style="margin-bottom:10px">Why it opens on September</h2>
    <p class="muted">
      Today is a dead week — the World Cup final was the 19th and the NFL does not start
      until September. A month grid of empty squares would tell you nothing about whether
      the design works, so both mockups open on September and treat Sunday the 13th as
      "today". Arrow back to July and August to see what the quiet weeks really look like.
      The real app always uses the real date.
    </p>
  </section>

  <section style="display:flex;flex-direction:column;gap:16px">
    <h2>The proposal</h2>
    <p class="muted">
      Reply with IDs — "keep SMS-1 SMS-2 SMS-3", "discard SMS-2" — and the next session
      does exactly that. IDs are never reused, so they stay valid forever.
    </p>

    <article class="prop">
      <div class="prop-head">
        <span class="prop-id">SMS-3</span>
        <span class="prop-title">Option B, built for real</span>
      </div>
      <dl>
        <div><dt>What</dt><dd>
          The phone Calendar tab now opens on a month grid, with your scrolling day list
          still underneath it. Tap any day in the grid and the list jumps to start there.
          The arrows move a <b>month</b> at a time on the phone now — they used to move
          seven days — because they have to agree with the grid above them.
        </dd></div>
        <div><dt>On a real phone</dt><dd>
          <div class="ba">
            <figure>
              <img class="shot tall" alt="The phone calendar with a month grid above the day list"
                   src="__SHOT_CAL__">
              <figcaption>Phone · 390px · the live app</figcaption>
            </figure>
            <figure>
              <img class="shot tall" alt="The desktop calendar, unchanged"
                   src="__SHOT_DESK__">
              <figcaption>Desktop · unchanged</figcaption>
            </figure>
          </div>
        </dd></div>
        <div><dt>Why</dt><dd>
          "See the next few weeks at a glance" is the grid's job; the list is what answers
          "so what is actually on". This keeps both and gives the grid something real to
          do — steering the list.
        </dd></div>
        <div><dt>Where</dt><dd>
          <code>static/app.js</code>, <code>static/style.css</code>, and a new phone test
          harness <code>tools/qa-phone-calendar.py</code>. Commit <code>6e604ee</code>.
          <b>Supersedes SMS-1</b> — keeping this is what "keep B" means in code.
        </dd></div>
        <div class="risk"><dt>Risk</dt><dd>
          The arrows changing meaning is the real one: a swipe on the phone used to move
          you a week and now moves you a month, and that is muscle memory you already have.
          Three now-unused functions were deleted along with it, so undoing this is a
          revert of the whole change rather than flipping a switch. The day list is capped
          at the loaded month, so tapping a day near the end of the month shows fewer than
          seven days and offers a "More in August" button rather than pretending those days
          are empty. Live code: keeping it means a deploy.
        </dd></div>
        <div class="verdict"><dt>Keep / discard</dt><dd>KEPT</dd></div>
      </dl>
    </article>

    <article class="prop">
      <div class="prop-head">
        <span class="prop-id">SMS-1</span>
        <span class="prop-title">Phone month calendar — two mockups</span>
      </div>
      <dl>
        <div><dt>What</dt><dd>
          Two working versions of a month-grid calendar for the phone, built so you can
          pick one. Nothing in the app changed; these are standalone pages.
        </dd></div>
        <div><dt>Why</dt><dd>
          The phone currently shows a rolling seven-day list, not a calendar. You cannot
          see that a Sunday three weeks out has fourteen games on it, which is exactly the
          "next few weeks at a glance" you asked for.
        </dd></div>
        <div><dt>Where</dt><dd>
          Branch <code>auto/overnight-sms-ux</code>, commit <code>__HASH__</code>.
          New files only, all under <code>docs/overnight/</code> plus two scripts in
          <code>tools/</code>. No file the app loads was touched.
        </dd></div>
        <div class="risk"><dt>Risk</dt><dd>
          A day cell on a 390px phone is about 49 pixels wide, so it can only carry a
          number, a dot per sport, and a game count — you will not see who is playing until
          you tap. And a mockup is not the app: wiring the winner in means retiring or
          rewiring the seven-day window code, which is a real change to a page you use, on
          a repo where shipping is a deploy.
        </dd></div>
        <div class="verdict"><dt>Keep / discard</dt><dd>KEPT — you chose B; SMS-3 is that, built</dd></div>
      </dl>
    </article>

    <article class="prop">
      <div class="prop-head">
        <span class="prop-id">SMS-2</span>
        <span class="prop-title">The front page can name the next game again</span>
      </div>
      <dl>
        <div><dt>What</dt><dd>
          Between seasons the Home page's Today's Slate showed a dead line —
          "No games in this window — browse the calendar." It now shows the actual next
          fixture: <b>no games today · next up — CAR at ARI, Thu Aug 6, 5:00 PM,
          in 10 days.</b>
        </dd></div>
        <div><dt>Before / after</dt><dd>
          <div class="ba">
            <figure>
              <img class="shot" alt="Home page showing a no-games message"
                   src="__SHOT_BEFORE__">
              <figcaption>Before — a dead line</figcaption>
            </figure>
            <figure>
              <img class="shot" alt="Home page showing the next fixture"
                   src="__SHOT_AFTER__">
              <figcaption>After — the real next game</figcaption>
            </figure>
          </div>
        </dd></div>
        <div><dt>Why</dt><dd>
          There are no games for another eleven days, so that dead line is what the front
          page shows you every time you open it until August 7. The app already knew how
          to display "next up" — it just could not find the game, because the front page
          only ever looks inside the month it has loaded and the next fixture was five
          days past the end of it.
        </dd></div>
        <div><dt>Where</dt><dd>
          New <code>app/lookahead.py</code> (19 tests, no network), a scan wired into the
          schedule endpoint, and three lines in <code>static/app.js</code>.
          Commit <code>fd10a53</code>.
        </dd></div>
        <div class="risk"><dt>Risk</dt><dd>
          This is the first change here that touches code the live app runs — unlike
          SMS-1, keeping it means a deploy. When the window runs dry the server makes one
          extra ESPN call to look 45 days ahead, so those days answer more slowly, and on
          Render's free tier slow is more noticeable than it sounds. If ESPN fails during
          that scan the page quietly falls back to the old message rather than erroring:
          the right trade, but it makes the failure invisible. A gap longer than 45 days
          would still show the old line.
        </dd></div>
        <div class="verdict"><dt>Keep / discard</dt><dd>KEPT</dd></div>
      </dl>
    </article>
  </section>

  <section style="display:flex;flex-direction:column;gap:12px">
    <h2>Next in the queue</h2>
    <ol class="list">
      <li><b>The empty headline slot.</b> The front page's Main Event banner renders nothing
        at all on a day with no games, so for weeks at a time the page has no headline.
        Putting the next fixture there is a taste call, so it would come to you as
        mockups.</li>
      <li><b>Phone chrome pass.</b> Sticky tabs, the notch safe area, tap-target sizes —
        owed since the July 22 deploy.</li>
      <li><b>Game-card size on a phone.</b> How much fits before a card stops being
        glanceable.</li>
    </ol>
  </section>

  <footer class="foot">
    <b>Branch</b> auto/overnight-sms-ux · merged to master (f33309b) · <b>not pushed</b><br>
    <b>Deploy</b> untouched — pushing this repo is a deploy and only ever your hand<br>
    <b>Tests</b> 197 passing (./tools/validate)<br>
    <b>Measured</b> at a true 390px viewport, both layouts, all geometry checks green<br>
    <b>Full detail</b> docs/overnight/proposals/sms-ux.md
  </footer>

</div>
</div>
"""

BOARD_INIT = """
<script>
(function () {
  var a = document.getElementById("stage-a");
  var b = document.getElementById("stage-b");
  var btnA = document.getElementById("btn-a");
  var btnB = document.getElementById("btn-b");

  function show(which) {
    var wantA = which === "a";
    a.hidden = !wantA;
    b.hidden = wantA;
    btnA.setAttribute("aria-pressed", String(wantA));
    btnB.setAttribute("aria-pressed", String(!wantA));
  }
  btnA.addEventListener("click", function () { show("a"); });
  btnB.addEventListener("click", function () { show("b"); });

  makeCalendar(document.getElementById("view-a"), "replace");
  makeCalendar(document.getElementById("view-b"), "both");
})();
</script>
"""


def main():
    head = subprocess_hash()
    # Order matters twice over:
    #  - BOARD_CSS before calendar.css, because `.board h1` and
    #    `.mock-mast h1` have identical specificity and the specimen's
    #    masthead must win inside .phone.
    #  - the data and renderer scripts before BOARD_INIT, because the
    #    init call needs makeCalendar() to already exist.
    page = "\n".join([
        # Charset FIRST and within the first 1024 bytes. The publish
        # wrapper supplies the <head>, so this is the only lever the
        # page has over encoding sniffing — without it a browser that
        # gets no charset header falls back to windows-1252 and every
        # em dash and section tag turns to mojibake (seen in the
        # headless smoke test before this line existed). A duplicate
        # charset meta in the wrapper is harmless.
        '<meta charset="utf-8">',
        "<title>Sports hub — the calendar, two ways</title>",
        "<style>",
        read("fonts.css"),
        BOARD_CSS,
        read("calendar.css"),
        "</style>",
        (BOARD_HTML
            .replace("__HASH__", head)
            .replace("__SHOT_BEFORE__", shot_uri("audit-home-390.png"))
            .replace("__SHOT_AFTER__", shot_uri("sms-2-home-nextup-after.png"))
            .replace("__SHOT_CAL__", shot_uri("sms-3-calendar-390.png"))
            .replace("__SHOT_DESK__", shot_uri("sms-3-calendar-desktop.png"))),
        "<script>",
        read("data.js"),
        "</script>",
        "<script>",
        read("calendar.js"),
        "</script>",
        BOARD_INIT,
    ])
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {os.path.relpath(OUT, REPO)}  ({len(page) / 1024:.0f} KB, commit {head})")
    return 0


def subprocess_hash():
    """Short hash of HEAD, so the proposal's WHERE line is never stale."""
    import subprocess
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())
