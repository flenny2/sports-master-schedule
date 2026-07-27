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


def read(name):
    with open(os.path.join(MOCKUPS, name), encoding="utf-8") as f:
        return f.read()


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
    <h1>The calendar,<br>two ways</h1>
    <p class="lede">
      You asked for the calendar to look like an actual calendar — the full month, so you
      can see the next few weeks at a glance. Underneath that ask there is a fork, and it
      is a taste call, so I built both instead of picking one.
    </p>
    <p class="muted">
      Both are live and real. Tap days, use the arrows, scroll. The games are genuine ESPN
      fixtures captured tonight. Nothing in the app has changed — these are separate pages
      that cannot touch it.
    </p>
  </header>

  <section class="decide">
    <h2>The one thing to decide</h2>
    <p>Does the month grid <b>replace</b> the scrolling list you have now, or sit <b>above</b> it?</p>

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
      <b>My recommendation: B.</b> Your words were "so I can see the next few weeks at a
      glance" — that reads as something you want <em>added</em> above what is there, not a
      swap. The scrolling list is also what actually answers "what is on this weekend", and
      B keeps it while giving the grid a real job: steering it. B is the safer keep, too —
      it removes nothing, so if the grid turns out to be a novelty you have lost nothing.
      <br><br>
      A's honest case: it is cleaner and it is less code to carry. If you find yourself
      never scrolling past the grid, A is the better long-term shape and B was clutter.
      Answer with one letter and the next session builds it.
    </div>
  </section>

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
      Reply with IDs — "keep SMS-1" or "discard SMS-1" — and the morning session does
      exactly that. IDs are never reused, so they stay valid forever.
    </p>

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
        <div class="verdict"><dt>Keep / discard</dt><dd>yours — reply A, B, or discard</dd></div>
      </dl>
    </article>
  </section>

  <section style="display:flex;flex-direction:column;gap:12px">
    <h2>Next in the queue</h2>
    <ol class="list">
      <li><b>Off-season home page.</b> It is late July, so the front page's job right now is
        "what is coming", not "what is on". Worth checking it is not mostly empty boxes.</li>
      <li><b>Phone chrome pass.</b> Sticky tabs, the notch safe area, tap-target sizes —
        owed since the July 22 deploy.</li>
      <li><b>Game-card size on a phone.</b> How much fits before a card stops being
        glanceable.</li>
    </ol>
  </section>

  <footer class="foot">
    <b>Branch</b> auto/overnight-sms-ux · nothing merged, nothing pushed<br>
    <b>Deploy</b> untouched — pushing this repo is a deploy and only ever your hand<br>
    <b>Tests</b> 178 passing (./tools/validate)<br>
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
        BOARD_HTML.replace("__HASH__", head),
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
