# 2026-11-11 autopilot-backlog-session

## AGG Phase 0 fix and rerun
- First GPU run `agg0-arms-gpu-20261110` failed mechanically (`superseded_v2_not_viable`, M2 and M5) with three harness defects (facts table not deduplicated, planner routed single-fact questions to SQL, empty/runaway B-today and P-small answers).
- Fixed: orchestrator `9a0ab00d`, research `13afe97c`, PREDECLARED rerun amendment `976a5fe8` (before rerun data).
- `agg0-arms-cpu-20261110-r2` PASS (M1 0.92). `agg0-arms-gpu-20261110-r2` RUNNING; AGG-0.4 stays OPEN, notes filed in knowledge-pipelines.md.
- Launcher role for GPU r2 changed from bench to build: it measures accuracy and tokens, not timing. The first run was accepted with bench before a keeper rule change.

## Filing audit and cleanup
- Audited owning boxes: R23-4 (VB-AK-R23-4-SWEEP-WIRE, commit refs added), Group A adapters (PIPE-EVE-VIDYA-GROUP-A ticked, owned by Pipeline Management; adapter README already lists all three sources), PaddleOCR-VL precondition present, dripreview1-r5 ticked, R18-D r4 FAIL noted, SLIDERS declined, INF-87 owned by dispatch-placement-telemetry.md.

## Wrap-up addendum (c)
- AGG-0.4 GPU: r2 yielded to the AutoKernel floor r5 at 01:37Z (rc=75), 9 B1 answers kept. r3 published but its smoke predicate wrongly required status ok. r4 published 08:08Z (predicate accepts any final answer, e.g. B1 agg10 budget_exhausted at the 30-call cap), RUNNING; job dir `/mnt/raid0/llm/tmp/agg0-arms-gpu-20261110-r2`. Box not ticked.
- EVL-10 judge: operator chose GPU with the pinned `qwen3.8-27b-q8-gpu-judge-np4` recipe (research `48c43a547`). Row `evl10-judge-gpu-20261111` published 08:04Z, smoke PASS, queued; job dir `/mnt/raid0/llm/tmp/evl10-judge-gpu-20261111`. pyarrow fixed via `uv sync --extra benchmark --inexact --frozen` (additions only, uv.lock unchanged). Notes filed at M-12k / M-12j in memory-program.md; not ticked.
- Cleanup: the abandoned Group A worktree was force-removed without its backup being saved because a save command was blocked. Content is fully recoverable from main `9047ad47f` plus the intact source worktree `vb-belief-park-20261108`. All old branches deleted.
- Shared-clone dirty files `.opencode/plugins/filesystem-containment.ts` and `scripts/hooks/tests/test_harness_guard_parity.py` are not this session's; referred to Pipeline Management with a caution about V2 opencode.
- Re-verified on origin/main: VB-AK-R23-4-SWEEP-WIRE ticked; PIPE-EVE-VIDYA-GROUP-A ticked; PaddleOCR precondition present in AP-HOLD-RELEASE-REVIEW; INF-87 owned once (inference-research-index.md).
- AGG Phase 0 verdict recorded: `agg0-arms-gpu-20261110-r4` PASS, `go_phase_1` (M1 0.92; M2 0.55 vs B1 0.20, +35 pp; M3 0.31 / 19.4 calls per 100 chunks; M4 median 2 calls; M5 holds) under PREDECLARED `976a5fe8...`. AGG-0.4 ticked in knowledge-pipelines.md; design doc has a Phase 0 result section. AGG-0.5 and AGG-1.x not started. Caveats: post-data fixes after the failed first run, n=20 on one corpus, verdict spans r2/r3/r4.


## AGG-0.5 verdict recorded; AGG-1.x filed; AGG-0.2/0.3 ticked
- AGG-0.5 ticked: `go_phase_1` recorded with closure scoped to "integrated planner + lazy fact layer on Qwen3.6-35B-A3B / Qwen3.8-27B at 10-doc scale"; caveats (post-data fixes, n=20, one 10-filing corpus) carried forward.
- Filed AGG-1.1 (25-30 doc scale run, with a no-compute freeze + hand-verified golds + PREDECLARED amendment as step A), AGG-1.2 (Oolong-real, local only), AGG-1.3 (incremental re-ingest of 3 changed docs), AGG-1.4 (one lazy backfill field, <= 100 calls), AGG-1.5 (mid-size retrieval parity vs `context.search`). Each has a DONE WHEN, the Phase 1 gate, an `[inference]` tag with a provisional est and a bounded pilot, and `[no-belief: prospective task]`.
- Phase 2 integration decision package written as the last section of `docs/design/integrated-document-aggregation-plan-20261110.md` (options A full cut-over, B staged/shadow-first, C opt-in side-car, D stop). Recommendation B. Operator decision not due until the Phase 1 gates are read.
- AGG-0.2 and AGG-0.3 ticked with evidence: r3 L3 load complete (10 docs, 181 tables, 15,780 facts, L3-only M1 0.827 informational, `model_calls` 0), unit tests for the shared store and grammar rejection, and the arms CPU job's 80 fsynced `l4_unit` per-stage receipts. Remaining non-blocking gap: ODL-LOCAL-NO-BORDERLESS-TABLES.
- Proposed (not applied) index-row change: `pipeline-integration-index.md` PIP-04 still reads "AGG-0.1 corpus + hand-verified golds", which is stale; see the report to the main session for the diff.
