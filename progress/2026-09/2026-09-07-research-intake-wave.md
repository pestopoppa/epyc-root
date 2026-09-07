# 2026-09-07 — research-intake wave (intake-1311..1345 + intake-408 re-dive)

**Pipeline**: `/research-intake` on 11 operator-submitted sources → Stage 1 (20 entries, 1311–1330) →
Stage 2 (9 operator-selected dives) → Stage 2b (14 dive-surfaced sources, combined ingest+dive) →
Stage 2c (2 more: arXiv 2605.23950 → intake-1344, FreeToken #350 → intake-1345) → Stage 3 plan
(`/home/node/.claude/plans/steady-kindling-summit.md`, operator-approved) → Stage 4 (this note).

## Entries
- 35 entries touched, validator `OK: 1341 entries`. 23 dive-verified, 3 dive-overturned (1316 Scroll,
  1328 Local Routing Consistency, 1341 Belief Divergence), intake-408 (Tulving) re-dived and upgraded to
  `adopt_component`. Verdict changes after diving: 1320 JIT-Agent → adopt_patterns; 408 → adopt_component.
- Duplicate not minted: the re-submitted dual-loop write-up is a re-encounter of intake-1253 (both inline
  write-ups archived under `research/sources/intake-20260907/`).
- Incident: intake-1316's tail was truncated during an in-place LOCA edit and reconstructed from the
  scratchpad drafts; a tail-field audit over all 36 touched entries found no missing fields.

## What landed (Stage 4)
- 224 derived-actionable ledger rows routed: 3 new handoff stubs (INF-72 `moe-routing-tap-and-locality-measurement.md`,
  RTG-55 `promptforge-mutation-safety-contract.md`, EVL-50 `conversational-memory-eval-instrument.md`), riders/rows
  in 37 existing handoffs, `EVL-10`/`EVL-47` next-action refreshes, operator-queue row `OP-42` (plan said OP-34; origin/main had advanced to OP-41).
- Belief-kernel wiring filed WITH the sources: SC65 (PS-1 sink+window sweep), SC66 (routing tap), SC67
  (Tulving write side), SC68 (BEAM write side) — plan said SC63/SC64 but those ids were claimed between plan
  and apply.
- Chapters (research repo): 08 cost-accounting grammar + CPM/quality-per-dollar; 06 rule CH-8 "arms differed in
  more than the named variable"; 07 task-admission criteria + inert-gate lesson.
- Wiki: factual corrections only (Tulving "24 models" → 21 with pinned SHA; "4 narrative styles" → 3/4 released
  variants). All wiki prose (A-P-16/17, B-O1..O4, C-M2, ssm-hybrid record) is QUEUED for the next
  operator-invoked `/wrap-up` compilation sweep.
- Declines recorded with reasons in the owning handoffs (FreeToken port on gfx90a; hot-expert offload reopen;
  LOCA-bench; BEAM Table-1 reproduction; Harness-R1 reward reproduction; and 40+ more — see plan §A/§B-T/§C-Q).
- Housekeeping: dangling `completed/meta-harness-optimization.md` pointer re-pointed; four rotted `state.py`
  anchors in `repl-session-memory-maturity.md` re-resolved; `cpu-decode-roofline-program.md` main-vs-lane
  superseded-figure hazard filed; F-33..F-36 id collision (coordinator) and HS-5/HS-6 id reuse (harness) reported,
  not renumbered.
- No checkbox changed state. No inference run. No edit under `agents/shared/`, `MEASUREMENT.md`, or
  `human_only_paths.yaml`.

## Operator token requests (human-only paths — NOT edited)
1. `agents/shared/HARNESS_RUN_POLICY.md:93` — point "the applicable Harness Card" at HS-6c once the conformant
   card exists (plan B-P1).
2. `agents/shared/INVARIANTS.md` invariants 1 and 4 — note the PostToolUse `classifierContext` consent write path
   as out of bounds for coordination-plane hooks (plan B-D1; handoff row P5-1 carries the text).
3. `agents/shared/MEASUREMENT_POLICY.md` — paired-recovery-ratio convention and the two-regime harness
   admissibility rule are filed sweep-local / chapter-local; promotion to policy is a decision package, not a
   session write (plan A-P-6c, B-N1/N2, B-O3).
4. HS-5/HS-6 duplicate ids in `harness-selection-and-integration.md`: suffix-at-citation remedy recommended;
   renumbering is an operator call.

## Expansion queue (Stage-1 ingest only, no compute)
Recorded in `.research-session.json` → `expansion_queue`: 104 dive-surfaced refs deferred by the operator, five KV
sources (TidalDecode, Quest, SeerAttention-R, SWAA, Cabannes et al.), arXiv 2609.00006, and the Part-2 dive
queue (1312+1326, 1319, 1322 after 1319).
