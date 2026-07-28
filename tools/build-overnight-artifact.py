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
/* The notch pair is the exception to the side-by-side default: its evidence
   is a thin red band overlapping four words of text, and that does not
   survive being halved on a phone AND cropped. Show these whole, stacked,
   and pair them only once there is room. */
.ba.tall-pair { grid-template-columns: 1fr; }
.ba.tall-pair .shot { height: auto; object-fit: contain; }
@media (min-width: 620px) { .ba.tall-pair { grid-template-columns: 1fr 1fr; } }
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
/* A grid item defaults to min-width:auto, so anything with a wide intrinsic
   size — the .term block below, a long unbroken code span — widens the whole
   column. And because `.prop` above sets overflow:hidden for its rounded
   corners, the result is not a sideways scrollbar you would notice: the card
   silently CUTS the text instead. Measured at 390px without this line,
   2026-07-27: `article.prop cuts 208px`, i.e. half of every sentence in the
   SMS-6 entry was gone, while the page still reported a clean 390px width.
   tools/shoot-review-board.py asserts it so it cannot come back quietly. */
.prop dl > div { min-width: 0; }
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

/* Terminal output, quoted verbatim. Scrolls in its own box rather than
   wrapping — a wrapped column report stops being a column report — and the
   page body never scrolls sideways because of it. */
.term {
  margin: 0;
  padding: 12px 14px;
  background: var(--desk-3);
  border-radius: 6px;
  font-family: var(--f-mono);
  font-size: 0.66rem;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre;
}

/* Triage bands. A flat list of proposals is what makes review slow, so each
   one sits under the heading that says how hard the call is. The label is a
   rule + a word rather than a colour block: the board already spends its one
   accent on gold, and a second fill would compete with the specimens. */
.band {
  display: flex; align-items: baseline; gap: 12px;
  margin: 6px 0 -6px;
}
.band-name {
  font-family: var(--f-disp); font-weight: 700; font-size: 1.02rem;
  letter-spacing: 0.06em; text-transform: uppercase; color: var(--gold-tx);
  white-space: nowrap;
}
.band-note { color: var(--txt-2); font-size: 0.88rem; }
.band::after { content: ""; flex: 1; height: 1px; background: var(--line); }

/* Settled proposals stay on the board as the record, at lower contrast so
   they cannot be mistaken for something still waiting on him. */
.prop.settled { opacity: 0.72; }

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
    <div class="eyebrow">Sports hub · lane · Mon 27 Jul 2026</div>
    <h1>Six to rule on,<br>one to deploy</h1>
    <p class="lede">
      Six new things. Five are defects fixed, and you only have to say keep or discard:
      the tab row was sliding up behind the iPhone clock as you scrolled and a third of
      the things you can tap were too small (<b>SMS-4</b>) · the list of settings that
      quietly go out of date every August is a command now instead of a note, and the
      one real bug on it is fixed (<b>SMS-6</b>) · the Calendar's storyline filter
      expired on 31 May and has been missing for two months (<b>SMS-7</b>) · the banner
      card was cutting "CAROLINA PANTHERS" in half (<b>SMS-8</b>) · and Home was showing
      two cards for the same story (<b>SMS-9</b>).
      One needs a real choice: <b>SMS-5</b>, the big banner at the top of Home draws
      nothing at all out of season, so here are two things that could fill it.
    </p>
    <p class="muted">
      SMS-1, SMS-2 and SMS-3 are the calendar work you already kept on 26 July. They are
      still on this board, greyed, as the record — nothing there needs you again.
    </p>
  </header>

  <section class="decide">
    <h2>What is still owed by you</h2>
    <p><b>Three things, and they are separate.</b></p>

    <div class="opt">
      <span class="opt-name">1 · Keep or discard SMS-4, 6, 7, 8 and 9</span>
      <span class="muted">Reply with the ID. The full case is below, with a picture of the
      before and after.</span>
    </div>
    <div class="opt">
      <span class="opt-name">2 · Pick A or B on SMS-5</span>
      <span class="muted">Or say neither — "leave the banner empty out of season" is a
      real answer and I would rather have it than a guess.</span>
    </div>
    <div class="opt">
      <span class="opt-name">3 · The deploy you already approved</span>
      <span class="muted">SMS-1, SMS-2 and SMS-3 are merged onto <code>master</code> and
      have never been pushed, because pushing this repo is a deploy and that is only ever
      your hand.</span>
    </div>

    <div class="rec">
      <b>Nothing is live.</b> One command deploys what you kept last night:
      <br><br>
      <code class="cmd">git push origin master</code>
      <br>
      SMS-4 through SMS-9 are <b>not</b> in that push — they sit on the branch
      <code>auto/lane-sms-jul27</code> until you rule on them.
    </div>
  </section>

  <section style="display:flex;flex-direction:column;gap:16px">
    <h2>The proposals</h2>
    <p class="muted">
      Reply with IDs — "keep 4, 6, 7, 8, 9; SMS-5 is B" — and the next session does exactly that.
      IDs are never reused, so they stay valid forever.
    </p>

    <div class="band">
      <span class="band-name">Obvious keep</span>
      <span class="band-note">defects fixed, no taste call in them</span>
    </div>

    <article class="prop">
      <div class="prop-head">
        <span class="prop-id">SMS-4</span>
        <span class="prop-title">The phone chrome stops hiding behind the notch</span>
      </div>
      <dl>
        <div><dt>What</dt><dd>
          Two fixes to the frame that wraps every screen. <b>The notch:</b> when you
          scrolled, the HOME / CALENDAR / PLAYOFFS / TABLES row slid up behind the iPhone's
          clock, and the bottom line of the footer sat under the home bar. Both now stop at
          the edge of the safe area. <b>Fingertips:</b> the three filter chips, the ‹ ›
          month arrows, the Mark Watched button and the "Full tables" link were all shorter
          than a fingertip. All four are now the standard size.
        </dd></div>
        <div><dt>Before / after</dt><dd>
          <div class="ba tall-pair">
            <figure>
              <img class="shot" alt="Tab labels sitting inside the reserved status bar zone"
                   src="__SHOT_CHROME_BEFORE__">
              <figcaption>Before — the tabs, and the footer's last line, are inside the
                red zones</figcaption>
            </figure>
            <figure>
              <img class="shot" alt="Tab labels sitting clear below the reserved zone"
                   src="__SHOT_CHROME_AFTER__">
              <figcaption>After — both clear of them</figcaption>
            </figure>
          </div>
          <p class="muted" style="margin-top:10px">
            The red bands are the strips an iPhone keeps for its own clock and home bar.
            Anything the app draws under one of them is something you cannot read or tap.
            A desktop browser never shows them, which is why this survived since 22 July.
          </p>
        </dd></div>
        <div><dt>Why</dt><dd>
          I measured the running app at a real phone width rather than reading the code:
          <b>16 of the 71 things you can tap</b> were under the 44-pixel minimum the app's
          own design notes already ask for. The notch half is the worse one. The page is
          deliberately set to run edge to edge under the notch — that is the right look —
          but nothing in the styling ever gave that space back, so on your phone, and
          especially once it is added to the Home Screen, the tabs were unreadable while
          scrolled.
        </dd></div>
        <div><dt>Where</dt><dd>
          <code>static/style.css</code>, a new test file, and a new phone harness
          <code>tools/qa-phone-chrome.py</code>. Commit <code>667c6bb</code> on branch
          <code>auto/lane-sms-jul27</code>. 197 → 206 tests. Desktop re-shot to show it
          did not move.
        </dd></div>
        <div class="risk"><dt>Risk</dt><dd>
          I have no iPhone to check this on, and neither does the test — no headless
          browser reports real notch measurements, so the harness feeds it fake ones and
          proves the layout <i>responds</i>. That is strong evidence the wiring is right
          and weak evidence about the exact look on your handset, which is the one thing
          worth eyeballing after a deploy. The taller chips also cost about 10 pixels of
          vertical space at the top of every screen — a real trade against a bigger target.
          Live code: keeping it means a deploy.
        </dd></div>
        <div class="verdict"><dt>Keep / discard</dt><dd>waiting on you</dd></div>
      </dl>
    </article>

    <article class="prop">
      <div class="prop-head">
        <span class="prop-id">SMS-6</span>
        <span class="prop-title">The August checklist runs itself now</span>
      </div>
      <dl>
        <div><dt>What</dt><dd>
          Two things. <b>A real bug:</b> the title-race widget worked out "matches
          left" by assuming every league plays 38 — true of the Premier League, wrong
          for the Bundesliga and Ligue 1, where it would have shown twelve points of
          "still winnable" that do not exist. It now works the number out from the
          size of the table, so it is right for any league.
          <b>The checklist:</b> there is a list in the repo of five settings that
          quietly go out of date every August. It was a note for a human to remember.
          It is now a command, and the test run prints a one-line summary of it every
          time.
        </dd></div>
        <div><dt>What it says today</dt><dd>
          <!-- Re-wrapped narrow rather than quoted in the tool's own column
               layout: the columns need ~90 characters, and a phone gets ~40.
               Quoting it verbatim meant the detail — the part that says what
               is actually wrong — sat off-screen inside a scroll box. -->
          <pre class="term">$ ./tools/rollover-check

STALE  STORYLINES
       every active storyline has expired
       (PL Title Race ended 2026-05-31), so
       the Calendar has no storyline filter

STALE  NBA_NATIONAL_NETWORKS
       defined, used by nothing

you    TITLE_RACES
       are these THIS season's contenders?

you    NFL_PRIMETIME_NETWORKS
       Friday games are included ONLY via
       this set — recheck the rights deals

you    FANTASY_ROSTER
       empty until the LPPC draft (late Aug)</pre>
          <p class="muted" style="margin-top:8px">
            <b>STALE</b> means a date has passed or a value is empty — no judgement,
            a session can just fix it. <b>you</b> means a call only you can make, and
            the checker's whole job there is to ask at the right time of year rather
            than guess. Acting on the two stale ones is the next thing I do; it is
            kept separate so you can keep this and still discard those.
          </p>
        </dd></div>
        <div><dt>Why</dt><dd>
          August is ten days away and that list had never been walked. Running it for
          the first time is what turned up the expired Premier League storyline — which
          is why the Calendar has no storyline filter right now. Nothing crashed and
          nothing looked broken, which is exactly the failure the list warns about.
        </dd></div>
        <div><dt>Where</dt><dd>
          New <code>app/rollover.py</code> and <code>tools/rollover-check</code>, a
          summary line in <code>tools/validate</code>, the season-length fix in
          <code>app/espn.py</code>. Commit <code>2a4ddbb</code>. 206 → 246 tests.
        </dd></div>
        <div class="risk"><dt>Risk</dt><dd>
          The summary prints but never fails the test run, on purpose — what it catches
          are choices only you can make, and a failing suite would block every future
          session waiting on you. The trade is that a printed warning can be scrolled
          past. The season-length fix assumes a normal home-and-away league; a split
          season like the Scottish Premiership would be wrong in the same direction the
          old number was, which is written down at the code.
        </dd></div>
        <div class="verdict"><dt>Keep / discard</dt><dd>waiting on you</dd></div>
      </dl>
    </article>

    <article class="prop">
      <div class="prop-head">
        <span class="prop-id">SMS-7</span>
        <span class="prop-title">The Calendar has its storyline filter back</span>
      </div>
      <dl>
        <div><dt>What</dt><dd>
          Three things, all from acting on what the checker above reported.
          <b>The filter:</b> the PL Title Race chip on the Calendar — the one that
          shows only Arsenal and Man City games — expired on 31 May and nothing
          replaced it, so it has been gone for two months. Renewed; it is back.
          <b>A dead setting:</b> a leftover NBA value that nothing has used since NBA
          was unplugged is deleted. <b>And one it was hiding:</b> bringing the chip
          back made it visible to the phone measurements for the first time, and it
          was 38 pixels tall against the 44 the app asks for. Fixed too.
        </dd></div>
        <div><dt>On a real phone</dt><dd>
          <div class="ba tall-pair">
            <figure>
              <img class="shot" alt="The Calendar with the PL Title Race filter chip restored"
                   src="__SHOT_STORYLINE__">
              <figcaption>The chip, back under the month grid</figcaption>
            </figure>
          </div>
        </dd></div>
        <div><dt>Why</dt><dd>
          Nothing was broken, which is the point. An expired storyline correctly stops
          showing, then nothing replaces it, and the Calendar quietly loses a feature.
          That is the exact failure the checklist warns about, and it had already
          happened before anybody ran the checklist.
        </dd></div>
        <div><dt>Where</dt><dd>
          <code>config.py</code>, <code>static/style.css</code>, and tests.
          Commit <code>a97934e</code>. 246 → 249 tests, and
          <code>./tools/rollover-check</code> now reports <b>0 stale</b>.
        </dd></div>
        <div class="risk"><dt>Risk</dt><dd>
          I picked the contenders by carrying last season's forward — Arsenal and Man
          City again. That is a guess about your new season, not a fact, and it is the
          same guess the title-race widget is already making, which is why the checker
          asks you about it separately. If you want different teams it is two ids in
          one file. Deleting the NBA value is only awkward if NBA comes back, and a
          comment in its place says where the old values live.
        </dd></div>
        <div class="verdict"><dt>Keep / discard</dt><dd>waiting on you</dd></div>
      </dl>
    </article>

    <article class="prop">
      <div class="prop-head">
        <span class="prop-id">SMS-8</span>
        <span class="prop-title">The big card wraps a long team name</span>
      </div>
      <dl>
        <div><dt>What</dt><dd>
          On the banner card at the top of Home, "CAROLINA PANTHERS" was being cut to
          "CAROLINA PANTHE…". It wraps onto two lines now and shows the whole name.
          The ordinary cards in the Calendar list are unchanged, on purpose.
        </dd></div>
        <div><dt>Why</dt><dd>
          I measured every card the app draws at phone width, closed and opened:
          <b>nothing is being cut</b> — 19 cards, zero losses. The one place text was
          disappearing is the banner, where the team name is set larger. It was short
          by six pixels.
        </dd></div>
        <div><dt>Where</dt><dd>
          One rule in <code>static/style.css</code>, two tests, and a new measuring
          tool. Commit <code>612fff0</code>. The wrapped banner is in the SMS-5 shots
          below; an opened card at phone width is
          <code>sms-8-card-expanded-390.png</code>.
        </dd></div>
        <div class="risk"><dt>Risk</dt><dd>
          A two-line name makes the banner taller, and two teams with different name
          lengths make it slightly lopsided. I chose wrapping over a smaller font
          because six pixels would have fixed those two names and still failed on
          something like "Wolverhampton Wanderers" — but if you would rather the
          banner stayed one line at any cost, that is a one-line revert.
        </dd></div>
        <div class="verdict"><dt>Keep / discard</dt><dd>waiting on you</dd></div>
      </dl>
    </article>

    <article class="prop">
      <div class="prop-head">
        <span class="prop-id">SMS-9</span>
        <span class="prop-title">One card per story, not two</span>
      </div>
      <dl>
        <div><dt>What</dt><dd>
          The Storylines block on Home was showing two cards for the same Premier
          League title race — the proper race card and a thinner duplicate under it.
          Now just the one.
        </dd></div>
        <div><dt>Why</dt><dd>
          Renewing the storyline in SMS-7 is what made the second card appear. The app
          already knew not to show both, but it worked out which competition a
          storyline belonged to by looking through the games it had loaded — and right
          now it has loaded no Premier League games at all, so it found nothing and
          skipped nothing. It reads the setting directly now.
        </dd></div>
        <div><dt>Where</dt><dd>
          <code>app/storylines.py</code> and <code>static/app.js</code>. Commit
          <code>15e9474</code>. Verified against the running app at 390px: one card
          where there were two. 252 tests.
        </dd></div>
        <div class="risk"><dt>Risk</dt><dd>
          The half that decides which card to hide is browser code, and this repo has
          no way to test browser code without adding a new tool — which the lane rules
          forbid. So the server half is covered by tests and the browser half by a
          screenshot. It also only bites when a storyline and a title race describe the
          same competition, which is exactly your current setup.
        </dd></div>
        <div class="verdict"><dt>Keep / discard</dt><dd>waiting on you</dd></div>
      </dl>
    </article>

    <div class="band">
      <span class="band-name">Needs your taste</span>
      <span class="band-note">two versions built; the pick is yours, not mine</span>
    </div>

    <article class="prop">
      <div class="prop-head">
        <span class="prop-id">SMS-5</span>
        <span class="prop-title">Something to headline Home out of season</span>
      </div>
      <dl>
        <div><dt>What</dt><dd>
          The big banner slot at the top of Home is empty right now, and stays empty
          until the season starts. Two things that could fill it — pick one, or say
          neither.
        </dd></div>
        <div><dt>The two</dt><dd>
          <div class="ba tall-pair">
            <figure>
              <img class="shot" alt="Home page with the next fixture as a full-size banner card"
                   src="__SHOT_HEAD_A__">
              <figcaption>A · the next game IS the main event</figcaption>
            </figure>
            <figure>
              <img class="shot" alt="Home page with a countdown board listing season openers"
                   src="__SHOT_HEAD_B__">
              <figcaption>B · a countdown board instead of a game</figcaption>
            </figure>
          </div>
          <p class="muted" style="margin-top:10px">
            <b>A</b> — the next fixture becomes the big card, team colours and all, with
            "Kicks off in 9d 23h" under it, so the page looks the same in August as it
            does in October. The small "next up" line goes away, because two cards for
            one game reads as a bug.<br><br>
            <b>B</b> — instead of one game, when each of your competitions starts:
            NFL in 10 days, Premier League in 25. The "next up" line stays.
          </p>
        </dd></div>
        <div><dt>Why</dt><dd>
          That banner is the front page's centrepiece, and on a day with no games it
          draws nothing at all — which is why Home currently opens with Your Teams and
          then a small line. Weeks of the page having no headline.
        </dd></div>
        <div><dt>Where</dt><dd>
          <code>docs/overnight/mockups/headline-variants.html</code>, commit
          <code>ffe2f1b</code>. <b>Nothing the app loads was touched</b> — but these are
          not hand-drawn either: each one is the <i>running app</i> with the change
          applied to it, so what you see is what shipping looks like.
        </dd></div>
        <div class="risk"><dt>Risk</dt><dd>
          A gives a game ten days out the same weight as a kickoff happening now, which
          may read louder than it deserves — and at phone size it costs you the team
          name: the shot shows "CAROLINA PANTHE…" where the small card fits "CAR".
          B is quieter and always honest, but on a normal Saturday it has nothing to
          say, so B is really a <i>second</i> state the page needs rather than a
          replacement for the banner. That is the part I would want your read on.
          Choosing either is then a real change to the page you open most.
        </dd></div>
        <div class="verdict"><dt>Keep / discard</dt><dd>waiting on you — reply "A", "B", or "neither"</dd></div>
      </dl>
    </article>

    <div class="band">
      <span class="band-name">Already decided</span>
      <span class="band-note">kept 26 July, merged, on the branch — the record only</span>
    </div>

    <article class="prop settled">
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

    <article class="prop settled">
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
          Branch <code>auto/overnight-sms-ux</code>, commit <code>83674f0</code>.
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

    <article class="prop settled">
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

  <section style="display:flex;flex-direction:column;gap:12px">
    <h2>Next in the queue</h2>
    <ol class="list">
      <li><b>Game-card size on a phone.</b> How much fits before a card stops being
        glanceable. The SMS-5 shots already gave this evidence: at banner size a full
        team name truncates to "CAROLINA PANTHE…" on your phone.</li>
    </ol>
    <p class="muted">Done so far tonight: the phone chrome pass (SMS-4), the two headline
      mockups (SMS-5), the August checklist as a command (SMS-6) and the two stale
      settings it found (SMS-7).</p>
  </section>

  <footer class="foot">
    <b>Branch</b> auto/lane-sms-jul27 (SMS-4 through SMS-9 — all undecided) · off master,
    which carries SMS-1..3 merged and <b>never pushed</b><br>
    <b>Deploy</b> untouched — pushing this repo is a deploy and only ever your hand<br>
    <b>Tests</b> 252 passing (./tools/validate) · was 197 at the start of this lane<br>
    <b>Measured</b> against the running app at a true 390px viewport — 71 tap targets,
    all four tabs, safe areas simulated at iPhone 15 values<br>
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
    # Only used in the "wrote …" line now. Commit hashes in the board are
    # literals, because each proposal names the commit that SHIPPED it and
    # HEAD moves on to the next cycle — templating them made SMS-1's line
    # start claiming a commit it had nothing to do with.
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
        "<title>Sports hub — the review board</title>",
        "<style>",
        read("fonts.css"),
        BOARD_CSS,
        read("calendar.css"),
        "</style>",
        (BOARD_HTML
            .replace("__SHOT_BEFORE__", shot_uri("audit-home-390.png"))
            .replace("__SHOT_AFTER__", shot_uri("sms-2-home-nextup-after.png"))
            .replace("__SHOT_CAL__", shot_uri("sms-3-calendar-390.png"))
            .replace("__SHOT_DESK__", shot_uri("sms-3-calendar-desktop.png"))
            .replace("__SHOT_STORYLINE__", shot_uri("sms-7-calendar-storyline-390.png"))
            .replace("__SHOT_HEAD_A__", shot_uri("sms-5-headline-a-nextgame.png"))
            .replace("__SHOT_HEAD_B__", shot_uri("sms-5-headline-b-countdown.png"))
            .replace("__SHOT_CHROME_BEFORE__", shot_uri("sms-4-chrome-before.png"))
            .replace("__SHOT_CHROME_AFTER__", shot_uri("sms-4-chrome-after.png"))),
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
