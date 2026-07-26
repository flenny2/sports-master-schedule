# Overnight lane — the standing law for this repo

what: the rules an unattended overnight session in sports-master-schedule works to
adapted-from: `fantasy-football-claude/docs/overnight/README.md` (2026-07-25) — read as
  read-only context, never written to. Deviations below are deliberate and are marked
  **SMS-SPECIFIC**; everything else is the ff law restated for this repo.
created: 2026-07-26 (Opus 5, lane `auto/overnight-sms-ux`)

## The one thing that decides whether the night was worth it

**Dylan reviews from a PHONE and keeps or discards CHANGE BY CHANGE.** A 20-file branch
diff fails even if every change in it is good. So:

- **ONE proposal file: `docs/overnight/proposals/<lane>.md`.** Updated as you go, not at
  the end — a lane that dies at 3am must still leave a readable file.
- **Numbered entries, newest last, each with a stable lane-prefixed ID (`SMS-1`).** The ID
  is the decision surface: Dylan replies with IDs ("keep SMS-1, discard SMS-3"), so an ID
  is **never renumbered and never reused**. Each entry is ~5 lines:
  - **WHAT** — one plain sentence. Assume he has not seen the code.
  - **WHY** — the problem it solves, in his terms (a phone moment, a game-day moment).
  - **WHERE** — files touched + commit hash.
  - **RISK** — honestly. "None" is almost never true.
  - **KEEP / DISCARD** — left blank. That column is his.
- **Screenshots for anything visual**, saved to `docs/overnight/shots/`, path on the
  proposal. Use the `headless-qa` skill — it encodes the traps (animation-clock scrub,
  geometry asserts over DOM-existence checks, case-tolerant text asserts).
- **Plain language.** Same register as his chat. He should decide without opening a file.
- **Delivery:** the proposal file lives on a local branch and a phone cannot open it, so
  the lane also publishes **ONE private Artifact** — mockups + the proposal list — and
  **refreshes that same Artifact each pass** (same file path → same URL; never mint a
  second one, he decides from whichever link he has).

## Hard fences — not style preferences

1. **`git push` is HARD-DENIED in `.claude/settings.json`, because push = Render deploy.**
   Never attempt it, never ask for it, never suggest a workaround. Shipping is Dylan's hand.
2. **Never work on `master`.** The lane owns its own branch. Dylan merges what he keeps.
3. **The suite must be green when you stop.** `./tools/validate` (pytest + `VALIDATE PASS`).
   Baseline at lane start: **178 passed**. If you cannot get it green, say so in plain words
   at the TOP of the proposal file and stop touching code.
4. **No new dependencies.** Flask + the pinned list, vanilla frontend, no build step. If you
   think you need a library, that is a proposal, not an install.
5. **SINGLE LIGHT THEME.** One `:root` token block in `static/style.css`. No dark mode, no
   toggle (Dylan's Jul-15 ruling). New tokens are contrast-checked (≥4.5:1 text, ≥3:1 UI)
   before they ship — the palette is documented as numerically AA-verified and stays that way.
6. **Preview generation stays on-demand.** Spend is a button press, never automatic. A lane
   never triggers a tactical read to "test" something; dry-run mode exists for that.
7. **SMS-SPECIFIC — taste calls are presented, not decided.** Design in this repo is Fable's
   seat (meta `DOCTRINE.md` rule 2, scoped explicitly: the Opus design seat was ruled for
   fantasy-football ONLY and "no session may widen it by analogy"). So where a change turns
   on what Dylan *likes* rather than what is correct, the lane **builds every option as a
   mockup and lets him pick.** Building options is working; choosing between them is not.
8. **Mockups are inert.** A mockup under `docs/overnight/mockups/` is a standalone page. It
   never imports from `static/`, and shipping one changes nothing a user sees. That is what
   makes a taste fork zero-risk to review.

## ⭐ THE CYCLE — you do not stop, you start over

1. **PICK** the next idea — top unstruck item in the proposal file's idea queue. When the
   queue empties, **generate the next three yourself**, ranked by one test: *would Dylan
   notice this on his phone, on a game day?*
2. **BUILD** it, small and complete. One idea per cycle.
3. **ITERATE** — as many passes as it takes to be genuinely good, not merely working.
   Critique your own output: is it honest, is it decidable on a phone, does it survive
   `./tools/validate`.
4. **SHIP** the cycle: commit, write the proposal entry, screenshot if visual, suite green,
   refresh the Artifact.
5. **CLOSE** it: append `CYCLE n — <idea> — SHIPPED <hash>` to the cycle log, then **go back
   to step 1 with a NEW idea.**

Rules that keep perpetual motion from becoming sprawl:

- **A cycle finishes before the next starts.** Never leave two half-built ideas on the
  branch; he discards per change and a tangle is undiscardable.
- **Each cycle is independently keepable.** If cycle 4 depends on cycle 2, say so in its
  WHERE line — keeping one then implies keeping the other, and he must see that.
- **Do not re-open a shipped cycle to polish it.** Log the improvement as a new idea and let
  it compete with everything else in the queue.
- **Diminishing returns are a signal, not a failure.** Three consecutive cycles producing
  proposals you would not defend to Dylan means change area.
- **Quality bar over cycle count.** Nobody counts cycles in the morning.
- **If you are stopping, say so as your last act:** commit one line to the cycle log —
  `STOPPING: <reason>` — and stop at a cycle boundary.
- **Before ending any turn, schedule your own next wakeup** so a usage ceiling pauses the
  lane instead of killing it. The lane ends permanently only on a marked `STOPPING` line.

## Context worth reading before you start

- `CLAUDE.md` — the repo's own law: the ESPN gotchas, the duel seam, the light-theme ruling,
  the app.js escape-mixing editing trap.
- `PRODUCT_BRIEF.md` — converged product decisions D1–D8. If code contradicts it, the brief
  wins or gets amended first.
- `TODOS.md` — the idea inbox. §mobile-month-calendar is where this lane starts.
