# PRODUCT_BRIEF — the REVAMP: meta sports tracker / fan-experience hub

what: converged product definition for the revamp — the single product-truth this build answers to
born: Dylan's Jul-15 voice notes (TODOS.md §revamp) + Jul-12 live-eyeball visual verdict
converged: 2026-07-17, Fable T4 session — 3 AskUserQuestion rounds (10 questions), answers verbatim in §Appendix
rules: replace-semantics; if a build decision contradicts this brief, the brief wins or gets amended first
status: v1 build in flight on `ws/revamp-v1` — branch-only; push = Render deploy = Dylan's explicit words

## The one-liner

From "a calendar I check briefly to see what games are on" to **Dylan's meta sports
tracker** — the place he *starts* as a fan: what matters today, the stories in motion,
and a tactical read on any match he's about to watch, one button-press away.

## Decisions (D1–D8, converged Jul-17)

### D1 — Phone-first
Dylan opens the app on his **phone via the Render URL**. Mobile is the primary design
target (desktop still handled); anything generated must be generated **server-side** so
it reaches him out of the house. No desk-only features.

### D2 — Landing = the Front Page hub
A new **Front Page** tab is home. v1 blocks, top to bottom:
1. **Today / tonight's slate** — the day's watchable games, must-watch first, live scores
   when in progress (the today-strip's job, grown up).
2. **Storyline cards** — the narratives in motion (PL title race, WC knockout run, later
   NFL playoff pushes) as rich editorial cards: standings context + next fixture + stakes,
   not just filter chips.
3. **Mini standings** — compact PL (and NFL, in season) snapshots; the race state visible
   without visiting Tables.

The **Calendar stays** — kept as the second tab, beautified, still the full-month planning
surface. Playoffs and Tables tabs remain (final tab set is a plan-level detail).

### D3 — Tactical previews: hybrid, on demand only (the marquee feature)
Two layers on a game's expanded view (soccer + NFL):
- **Facts panel (free, instant, always):** injuries, recent form, head-to-head, records —
  assembled from ESPN endpoints at view time. No LLM involved.
- **Tactical read (the button):** "Generate tactical read" calls a server-side endpoint →
  **Claude API with web research** → coach philosophies, expected shapes/schemes, key
  matchups, key absences — written fresh for that fixture, stored, then rendered.

Ground rules:
- **On demand ONLY.** Nothing auto-generates, ever — spend happens only when Dylan presses
  the button (the vision's explicit "not for countless games I won't watch" constraint).
- **Cost:** ~5–20¢ per press (estimate; exact model/pricing pinned at build time via the
  claude-api reference). Cached per game in `data/previews/` — re-opening a generated
  preview is free; an explicit "refresh" re-spends.
- **Key handling:** Dylan's own Anthropic API key, `ANTHROPIC_API_KEY` env var on Render +
  local shell. Never committed, never read by sessions; the app reads it from the
  environment at runtime. **Dry-run mode when the key is absent** (canned output, $0) so
  the pipeline is buildable/testable keyless.
- **Spend protection:** the generate endpoint sits behind the app's existing auth gate —
  a public URL must not let strangers burn the key.
- **Lifecycle:** button on upcoming (`pre`) games; a cached read stays viewable after
  kickoff/final. Render's ephemeral disk may drop caches on restarts — acceptable
  (previews are pre-match ephemera; regenerating costs cents).

### D4 — Preview scope: soccer + NFL
Sport-aware prompts: soccer = philosophies, expected formations, key men, absences;
NFL = scheme matchups, coordinator tendencies, key injuries. NBA is a later candidate,
not v1.

### D5 — NFL pillar (fan-side, explicitly separate from the fantasy-football app)
- **Steelers are Dylan's team** → join `WATCHED_TEAMS` (nfl, must_watch): every Steelers
  game surfaces, not just primetime.
- **NFL standings + playoff picture** — Tables tab + Front Page mini (divisions,
  conference seeding as the season develops).
- **Richer weekly slate** — keep the primetime/big-matchup filter, add matchup context:
  records, streaks, division stakes.
- **My-guys tags:** `FANTASY_ROSTER` in config.py — a small hand-maintained
  `player → NFL team` map (updated after the late-Aug LPPC draft, then on waivers). NFL
  game cards show which of his fantasy players are in that game ("Your guys: Jacobs,
  St. Brown"). No ESPN-fantasy auth, no league API — fan-level crossover only; league
  stats stay 100% in fantasy-football-claude.
- **Draft + offseason tracker: DEFERRED** (selected as interesting, but next NFL draft is
  April 2027 — not v1).

### D6 — Design: light-only, modern sports app
- **Light mode ONLY** — single mode, **no dark/light toggle**, dark tokens removed
  (Dylan Jul-15 ruling, recorded in personal-style-tracker/PREFERENCES.md).
- **Direction: modern sports app** — Dylan chose it over evolving the broadsheet: bright,
  app-like, vivid team colors, logos everywhere, card/chip language, rounded geometry,
  ESPN-meets-Athletic energy. The newsprint/editorial identity (cream paper, Fraunces
  scores) is **retired**.
- Fixes the Jul-12 verdict head-on: "more logos, more color, more excitement… wasted
  space… things aren't aligned" → spacing + alignment discipline is a first-class
  requirement, not polish.
- Typography/palette/geometry specifics = Fable's latitude inside this direction
  (personal-style-tracker is reference, not mandate). **WCAG AA holds** (≥4.5:1 body,
  ≥3:1 UI) — one theme now, still non-negotiable.

### D7 — Build order (if the session lands only part)
1. **Design system + Front Page** (whole app goes light/modern; calendar beautified) —
   immediate payoff, World Cup final weekend looks right the moment Dylan deploys.
2. **Preview pipeline** (facts panel → dry-run button → live Claude endpoint).
3. **NFL structures** (standings, Steelers/watched-team fetch, slate context, my-guys).

### D8 — What v1 is NOT (deselected or deferred at interview)
- Milestone watch (big players chasing numbers) — deselected for v1 Front Page; strong
  later candidate, needs a curated chase list from Dylan.
- Your-teams strip on the Front Page — deselected for v1.
- NBA tactical previews · draft/offseason tracker · MLB/NHL coverage.
- ESPN-fantasy roster auto-pull (manual config map instead — no cookies/credentials).
- Dark mode (removed, not hidden).

## Carried constraints (unchanged by the revamp)
- Flask + vanilla HTML/CSS/JS, no DB, no build step; ESPN public API for all sports data.
- Anthropic API is the ONLY new external call, and only on button press.
- Frontend rules hold: `var` + function declarations, `el()` helper, safe DOM methods
  (no `innerHTML`), interactive card elements call `stopPropagation()`.
- `./tools/validate` green before any hand-back (93 tests at branch time; new features
  bring tests).
- **Never push** — push = Render auto-deploy; shipping is Dylan's call, always.

## Dylan's future moves (owed to him, not by him now)
1. **When the preview phase lands:** create an Anthropic API key (console.anthropic.com),
   fund ~$5, set `ANTHROPIC_API_KEY` on Render + locally. The feature dry-runs until then.
2. **Late Aug (post-LPPC-draft):** fill `FANTASY_ROSTER` in config.py.
3. **Deploy timing:** merge + push when he wants it live (WC final Sun Jul-19 is a
   natural moment for phase 1).

## Appendix — interview record (Jul-17, 3 rounds, answers verbatim)

| # | Question | Answer |
|---|---|---|
| 1.1 | Where do you actually open this app? | **Phone (Render URL)** |
| 1.2 | What powers the tactical preview button? | **Hybrid: data + Claude** |
| 1.3 | What greets you on open? | **Front Page hub** |
| 1.4 | NFL coverage includes? (multi) | **All four: standings+playoffs · richer slate · my-team hub · draft tracker** + Other: **"steelers + my fantasy football teams"** |
| 2.1 | Which games get the preview button? | **Soccer + NFL** |
| 2.2 | Server-side Claude on your key — comfort + richness? | **Key + web research (~5–20¢/press)** |
| 2.3 | What does fantasy presence mean here? | **My-guys tags on games** (config roster) |
| 2.4 | Front Page v1 blocks beyond the slate? (multi) | **Storyline cards + Mini standings** (milestone watch + teams strip NOT selected) |
| 3.1 | Design identity? | **Modern sports app** (over broadsheet-evolved; over Fable's-call) |
| 3.2 | If only part lands, what ships first? | **Design + Front Page** |
