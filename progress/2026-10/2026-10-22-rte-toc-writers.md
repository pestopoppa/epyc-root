# 2026-10-22 rte-toc-writers

Cross-session audit producer gaps (RTE-LOG-1 remainder, TOC-SP-6 writer, VB-TOC-AB-WRITE). Non-inference; stack not touched.

- orchestrator `e9cf0949`, `0226a4c6` (origin/main): `prompt_layout.rebase_layout` + `tool_output` block kind (RTE-LOG-1 producer gaps), `prompt_layout_live_check.py`, `src/graph/trajectory_artifact.py` (flag `trajectory_artifact`, default off, plus `ORCHESTRATOR_TRAJECTORY_ARTIFACT_DIR`), `scripts/benchmark/toc_ab_sidecar.py`.
- Tests: 44 passed (prompt_layout, trajectory_artifact, output_spill), 111 with features/runtime_flags, 251 adjacent; flag-off byte identity covered in three cases. Run in the foreground under nice, no region-lock (coordinator-authorized: correctness work, no bench claim held at 10:50Z).
- Ticked: RTE-LOG-1 producer sub-boxes (2), tool-output-compression line-480 build half, VB-TOC-AB-WRITE. Open with notes: RTE-LOG-1 main box (live run), TOC-SP-5 (no artifacts yet).
- Filed: TOC-WRITER-HOOKS-1, TOC-WRITER-TOOLCALLS-1 (tool-output-compression.md); RTE-LOG-1 live run kept as its open sub-box.
- Adapter README toc_ab row updated; no extra belief row needed (the trajectory artifact is the attested file).
