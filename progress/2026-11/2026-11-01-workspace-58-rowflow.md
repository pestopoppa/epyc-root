# 2026-11-01 — ws58: simplified inference-row pipeline (operator: "remove every gate that is not indispensable")

- **Removed** (for new rows): `epyc.ready.v2` manifests, `ready/<id>.row.md`, the 18-cell FILLERS.md row, keeper nonces / receipt
  files / fixtures / cutoff proofs (`bin/qual-v1`, `bin/qual-v2-row`), the owner-wide worker breaker, the registry-row check,
  `validate_fillers.py` + `keeper_qual_gate` inside `grant_ok` (v4), `ws58_arm-v2.py`, keeper qualification memos, the sonnet
  filing subagent for piloted handoffs. Kept: one real attempt per lane per tick, lineage parking after 3 FAILs (+ escalation note).
- **New** `scripts/coordination/rowflow/` (commits d69c6cd4b, 523a23c20, f51dd0077): `publish_row.py <spec.json>` (owner tool),
  `rowflow.py` (status / dryrun-pick / dryrun-run / arm-tick / adopt-armed), `filler_run15.sh` (v14 minus the manifest coupling,
  plus `FILLER_DRYRUN`), `grant_ok_v4.sh` + `grant_ok_launcher.py`, `ws58-calendar-keeper-v10.sh`. Dry run = the exact launcher
  under the real region-lock claim on the real lane with a real short grant; PASS only on the first unit of output in
  `result_path` (filer format) + clean stop/exit (+ VRAM residency for GPU rows). Keeper runs in the host namespace (no `/workspace`)
  — the class-A launch failures (`region-lock: No such file`, `rg: command not found`) now surface in the dry run; v15 defaults
  the region-lock to its host path.
- **Backlogs**: `backlog_gen.py` ranks non-inference tasks by inference rows unblocked (transitive; lane weight `1/(1+ready)`,
  GPU first now; then effort). Old ranking was FILE ORDER with unblockers filtered out of the list (audit, backlog_gen.py:454-516
  pre-change). Workers: ni/refactor/codex3 closed → `codex-gen` (small tasks) + per-handoff sessions; legacy WORK queues re-routed.
- **Dispatcher** `handoff_sessions.py` v2: owner files its own results (+ `filing-done/<id>.FILED`), `WRAPPED <sha>` gate,
  `transfer <slug> --engine claude|opencode|codex` from files alone, self-sufficient brief.
- **Live**: keeper v10 pid 285858 (watchdog 1945976 via `.current`; v9 3946212 stopped), backlog_gen pid 285835, dispatcher pid
  286629, `grant_ok.sh` := v4 (v3 kept as `grant_ok.sh.v3-20261101`). Migration: 21/22 READY manifests → v3 rows
  (`ready/legacy-20261101/` keeps the originals; `refactor-c6-cpu-build-729599d69-20261030` stays a fix task: its launcher does
  not invoke an engine), 15 live legacy armed pollers adopted (`adopt-armed`). First dry runs: GPU `ufh14-a3a-single-warm-r2-20261028`
  (llama-server on the MI210, VRAM 55.5 GB sampled 17:07Z during the run), CPU `codex3-cs8-g1b-cascade-20261031` on q0.
- Tests: `scripts/coordination/tests/test_rowflow.py` (8, end-to-end on the engine with a stub region-lock),
  `test_backlog_gen_ranking.py`, `test_handoff_sessions_transfer.py` (7).
