# TODOS — sports-master-schedule inbox

what: repo-native idea/task inbox (capture-ritual target); sessions sweep + prune, replace-semantics
updated: 2026-07-18 (§revamp BUILT on ws/revamp-v1 — awaiting Dylan review/merge/deploy)

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
- Deferred-by-interview (brief §D8, revisit on Dylan's word): milestone watch ·
  your-teams strip · NBA previews · draft/offseason tracker · ESPN-fantasy auto-pull ·
  NFC mini table on Home (AFC ships; NFC lives on Tables)
