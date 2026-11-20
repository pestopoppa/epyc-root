# 2026-11-20 — Handoff standard Stage C (pipeline-mgmt builder)

Spec: `/mnt/raid0/llm/tmp/dispatcher-redesign-20261119/STAGE-C-BRIEF.md`. Branch `pm-handoff-std-c`, pushed in chunks
through `serialized_push.py`; each push reviewed by Fable, fixes folded in.

## Measured
- **C0.2 box-index build**: `index_state.py --box-index` 54 s -> **4.6 s** on the real repo (box build only; light state
  byte-identical to the full-state build: 1,413 boxes, 0 diffs). Concurrent `load()` x3 -> one build (test).
- **C0.1 generated rows**: the 4 bad spot-checks fixed (INF-50 G3 / INF-79 S-18 no longer named; INF-06 held; INF-80
  `NEEDS-OWNER: 25`).
- **Lint-OK**: 297 / 1,414 open boxes (21.0 %); top-10 rows 153 / 732 (20.9 %). Proposals do not move lint until owners
  accept them, so the 45 % canary is measured after acceptance (see C1).
- **C1 proposals (haiku, stripped context ~0.6 k overhead)**: 18 boxes proposed -> **51 NEEDS-OWNER children** in 5
  files (speech-and-multimodal 18, harness-program 8, vidya-belief-substrate 8, cpu-decode-roofline +
  engineering-hygiene 17); **66,872 uncached tokens** total (~3.7 k per box; budget 30 k/box, 30 M total). All 5 files
  at the per-handoff cap max(8, 20 %); speculative-decoding / long-context skipped (edited < 30 min). Acceptance rate:
  0 % so far (owners get a `proposals-pending` event once deployed). Ledger:
  `/mnt/raid0/llm/tmp/dispatcher-redesign-20261119/stageC/propose-ledger.jsonl`.
- **C6 first sample** (`stale_next_action.py --compare-generated`): 30 rows, 4 agree + 22 generated-fresher = 86.7 %
  (< 90 %), 1 lint-failing generated cell, 10 handoffs without `**Row**`/`**Domain**` -> criteria NOT met; no hand rows
  dropped.
- **C4 compaction dry run** (9 files > 4,000 lines): 1,072 ticked boxes > 30 d would fold, e.g.
  coordination-and-churn 6,339 -> 5,413 lines, rocm-kernel-authoring 4,057 -> 3,273, autopilot 5,084 -> 4,549. Not
  applied: compaction is an operator-invoked `/wrap-up` sweep step and needs a `closure_audit` JSON.
- **C7**: 3 live legacy markers retired (EPD-1/EPD-2 closed findings -> `## History`; numa-placement `C` -> `[ ]` +
  NEEDS-OWNER). Ratify package dry-applied through the real hooks, piped form included (rc 0).

## Operator command (ratify, human-only docs)
`git -C /mnt/raid0/llm/epyc-root fetch -q origin main && git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/ratify_handoff_standard_20261120.sh | ROOT=/mnt/raid0/llm/epyc-root RATIFY_OPERATOR='<your name>' bash -s -- --apply --attest RATIFY-HANDOFF-STANDARD-20261120`
