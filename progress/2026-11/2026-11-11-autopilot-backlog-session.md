# 2026-11-11 autopilot-backlog-session

## AGG Phase 0 fix and rerun
- First GPU run `agg0-arms-gpu-20261110` failed mechanically (`superseded_v2_not_viable`, M2 and M5) with three harness defects (facts table not deduplicated, planner routed single-fact questions to SQL, empty/runaway B-today and P-small answers).
- Fixed: orchestrator `9a0ab00d`, research `13afe97c`, PREDECLARED rerun amendment `976a5fe8` (before rerun data).
- `agg0-arms-cpu-20261110-r2` PASS (M1 0.92). `agg0-arms-gpu-20261110-r2` RUNNING; AGG-0.4 stays OPEN, notes filed in knowledge-pipelines.md.
- Launcher role for GPU r2 changed from bench to build: it measures accuracy and tokens, not timing. The first run was accepted with bench before a keeper rule change.

## Filing audit and cleanup
- Audited owning boxes: R23-4 (VB-AK-R23-4-SWEEP-WIRE, commit refs added), Group A adapters (PIPE-EVE-VIDYA-GROUP-A ticked, owned by Pipeline Management; adapter README already lists all three sources), PaddleOCR-VL precondition present, dripreview1-r5 ticked, R18-D r4 FAIL noted, SLIDERS declined, INF-87 owned by dispatch-placement-telemetry.md.
