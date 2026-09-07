# 2026-09-07 — research-intake-adhoc — Stage 3/4 of the research-intake wave, then wrap-up

Session kind: ad-hoc, operator-spawned. **No lane worktree** (`check_lane_worktree.py --strict` = 3,
SHARED CLONE), so every commit was made with a staged index and each shared file was diffed before
staging. Stated here because the checkbox gate and the pathspec protections do not apply to me.

## What this session did

1. **Stage 3** — assembled the plan for the `/research-intake` wave (`intake-1311..1345` + the
   `intake-408` re-dive) from three Plan agents, 224 derived-actionable ledger rows, and got operator
   approval. Plan: `/home/node/.claude/plans/steady-kindling-summit.md`.
2. **Stage 4** — implemented it with six opus subagents on disjoint file sets (operator steering:
   "use opus low subagents to churn through the handoff/index updates"). Detail:
   `progress/2026-09/2026-09-07-research-intake-wave.md` (the wave's own note).
3. **Wrap-up (operator-invoked)** — merged and promoted to `main`, pushed both repos, and ran the
   wiki compilation sweep for this wave's queued prose.

## Results

| Artifact | Result |
|---|---|
| `research/intake_index.yaml` | 1341 entries, validator OK; 26 dive-verified entries flipped to `integrated` with `handoffs_updated` filled |
| New handoffs | INF-72 routing tap · RTG-55 PromptForge mutation safety · EVL-50 conversational-memory instruments |
| Existing handoffs | riders/rows in 37 files; `EVL-10`/`EVL-47` next actions refreshed |
| Operator queue | `OP-42` (BEAM + Tulving instrument admission and one inference window) |
| Belief kernel | `SC65`–`SC68` source rows + program tasks |
| Chapters | `docs/chapters/06`, `07`, `08` in `epyc-inference-research` |
| Wiki | factual fixes applied in Stage 4; this wave's compiled prose applied in the wrap-up sweep |
| Checkbox flips | 0 state changes by design — this wave FILES work, it does not complete it. 55 new `- [ ]` rows added, 1 `- [x]` added (a follow-up closed on arrival by the promotion merge) |

## Deferred, with named blockers

- **Four operator token requests** (human-only paths, cannot be agent-edited): `HARNESS_RUN_POLICY.md:93`;
  `INVARIANTS.md` 1/4 (the PostToolUse `classifierContext` consent write path); two MEASUREMENT_POLICY
  conventions that need a decision package; the HS-5/HS-6 duplicate-id remedy in
  `harness-selection-and-integration.md`.
- **A blocking cite-check defect I did not fix, because it is not mine to decide**:
  `docs/design/vidya-pilot-spec.md:188` cites `intake-1300` entry-level as external corroboration, and
  that entry has an overturned claim (its deprecation claim), so the entry-level citation inherits the
  defect and `index_state.py --check` reports 1 problem. The faithful narrowing is ambiguous between
  claim 0 (half-scoped immutability) and claim 2 (the trust score gates nothing); guessing would
  re-decide a peer session's evidence mapping. Filed for its owner in
  `handoffs/active/vidya-belief-substrate-program.md`. Introduced by commit `51f9ef61`, not by this wave.
- **The wiki compile watermark is 940 sources behind.** This sweep compiled only this wave's queued
  prose, so `compile_sources.py --touch` was NOT run — touching it would mark all 940 as compiled.
  That is exactly the defect the operator queue already tracks as `OP-34` (no scoped `--touch` form).
