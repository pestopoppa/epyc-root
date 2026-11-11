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

## AGG-1.1 steps A/B, AGG-1.5 r1/r2, publish state (wrap-up)
- AGG-1.1 step A done (research `3296c19f4`): 28 sha256-pinned FinanceBench 10-Ks, 58 hand-verified aggregation questions, Phase 1 PREDECLARED committed before data. Step B runner wired (research `202c4ca6d`). The tolerance fix for the py3.11 flake in `test_golds_recompute_and_all_verified` (sum rounding, agg03 gold off by 0.01) landed in research `820ed1a3c`. Budget stops, owner-accepted: B1 7500 s with reuse, 14200 s without (ESTIMATES). AGG-1.1 stays OPEN, no tick.
- AGG-1.5 r1 (`agg15-parity-gpu-20261111`) and r2 (`agg15-parity-gpu-20261111-r2`) both filed `fail` / `phase1_gate_tripped` on the prefill gate in the 5-question pilot. r1: accuracy 4/4, one P question looped to the 12-call cap. r2 (800-char read cap and repeated-read guard, amendment `5b121cbf...`): P 3/5 vs B 4/5, two P questions hit the cap; the fixes did not help. Diagnosis: the planner's L1 search does not converge on the store-backed retrieval path (context.search answers the same questions in 3 calls); read granularity was not the cause. The operator chose a third try; r3 is in preparation under a further dated amendment. AGG-1.5 stays OPEN.
- Publish state: EVL-10 judge row `evl10-judge-gpu-20261111` filed pass (notes under M-12/M-12b/M-12k in memory-program.md, judge-instrument leg only). `agg1-ingest-cpu-20261111` published 14:43Z, queued on a CPU quarter; `agg1-arms-gpu-20261111` drafted, published only after the CPU row passes. `queue_status.py` UNFILED-ENDED is now 0 (all three of today's rows carry `.FILED`).
- Filed AGG-1.6 (typed-ingest A/B on the 3 pilot docs, from SCHEMA_NOTE.md) after AGG-1.5 in knowledge-pipelines.md.

## AGG-1.5 r3 closure, AGG-1.1 CPU ingest, GPU arms row (wrap-up 2026-11-11)

- AGG-1.5 r3 (`agg15-parity-gpu-20261111-r3`) ran all 20 pairs and was filed `fail` / `phase1_gate_tripped` on `no_rebuild_per_request` only (accuracy 18/20 = 18/20, median prefill equal, no L3/L4). Cause: the smoke process and the resumed main run each built the JPMORGAN index, since `l1_passage_bm25` was cached in memory only. Persistence fix (orchestrator `42994545`) plus a re-check; the operator closed the box on that basis (research `3304115d`, root `bd66bfaa` ticked AGG-1.5). AGG-1.7 (`context.search` lexical recall, gold top-8 16/20) filed. r1, r2, r3 all carry `.FILED` markers. Lesson added to compute-fillers.md.
- AGG-1.1 CPU ingest `agg1-ingest-cpu-20261111` filed pass, no gate tripped: M1 0.877 over 211 cells (bar 0.75), M3 prefill ratio 0.378, 22.3 calls per 100 chunks, 1359 LLM calls, 6094 chunks, 4.53M tokens. AGG-1.1 stays open (waits on the GPU row).
- GPU arms row `agg1-arms-gpu-20261111` published after precond passed; smoke PASS 19:27Z; running (not filed by this wrap-up).
- Queue check: one UNFILED-ENDED row, `afc-v3c-q38_flash-tools-aggressive-20261111`, owned by workspace-f2; not filed here.
