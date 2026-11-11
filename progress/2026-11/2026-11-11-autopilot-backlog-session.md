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
