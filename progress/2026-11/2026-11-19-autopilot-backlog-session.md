# 2026-11-19 — autopilot-backlog-session

Continues `2026-11-18-autopilot-backlog-session.md` (code-mode reliability, Monty, containment). All orchestrator and research commits below are pushed to their `main`; nothing is reloaded into the running API yet (see STACK-UP-RELOAD-QUEUE).

## Code mode (harness-program.md: CODEMODE-AB-V2, CODEMODE-REL, CODEMODE-REL-ABL-MEM, CODEMODE-REL-FLIP)

- **Import bug.** The REPL stripped imports it could not satisfy, so a C3 cell that imported a module failed silently. It sank 20 of 44 35B C3 episodes before the fix (24/24 clean after). Fixed in orchestrator `de0f1144` ("stop stripping imports the REPL cannot satisfy").
- **C3 results.** 27B r2 (`codemode-ab-v2-27b-gpu-20261118-r2`, filed pass): C3 42/42, A_pick 0.62, B1 0.57, A 0.40, B2 0.26, B 0.02; C3 vs A about 23x fewer tokens, vs A_pick about 4x. Post-fix GPU rows on the C15 champion: 35B `-fix` C3 9/10 vs A_pick 3/10 (sign p 0.031; 2.9 s vs 27.9 s wall); 27B `-fix` C3 30/30. Flash-Next and 35B CPU rows were dropped by the operator.
- **Turn-memory decision (ABL-MEM).** 35B: C3 29/30 vs 26/30 without memory, rule says ON. 27B: 30/30 vs 30/30, rule says OFF. Operator chose GLOBAL ON because the flag is global. Turn memory hurt B1 on the 27B pre-fix, so the pre-fix harm does not reappear inside C3.
- **C3 flip.** Branch `feat/codemode-rel-flip` (C3 flags, turn memory 4, name repair) is built and waits only on the stack being up; it is step 2 of the STACK-UP-RELOAD-QUEUE. Not touched in this wrap-up.
- **CM-2/4/5.** Probe prepared and gated on S4: rows `codemode-cm-{27b,35b}-gpu-20261119` (harness branch `probe/codemode-cm-20261119`, `9e278f5a`); the precondition refuses until `S4 Omega A/B` is ticked. Finding: with the picker on, `search_tools`/`describe_tool` are already installed in C3, so the CM-2 flag alone is a no-op next to C3.

## Embedder stack change (CODEMODE-REL-EMBED-PLACE)

Operator signed option A (GPU co-host `embedder_gpu` :8099 beside the 27B). Phase-7 code is orchestrator `d2be521c` (falls back to the CPU pool while :8099 is absent). Bring-up row `embedder-gpu-bringup-20261119` filed FAIL because the production stack was down (G1-G4 could not run, marker cleared). Republish is STACK-UP-RELOAD-QUEUE step 1.

## Cross-worker race (autokernel-loop.md OAB-17)

The OAB-17 F8 decline "cross-worker needs a shared counter" was wrong: the live API runs `uvicorn --workers 6`. Owner review of the 8 landed OAB-17 commits found one real bug (F8 reservation leak on cancel). Fixes: `2c0117d3` (F8 leak, F9, F10, F15 `_select_mode`, F16 a/b, json_diet fail-open); `ad9432c1` cross-process scout slot reservation (flock per URL, dead-owner/TTL reaping, fails closed; 10 processes contending for 3 slots admit exactly 3); `7f70e338` host-wide KV-pool token reservations and queue bound through the same `xproc_reservations` primitive. Research `6f142e9ba` (R3 inline fallback) and R4 sidecar retention (`fix/oab17-r4-sidecar-retention`) done; OAB-17-R4 ticked. OAB-19 `e1d34759` retires REPL-turn compaction by default behind `repl_compaction`. OAB-NI18: the earlier "incomplete registry migration" diagnosis was wrong; the cross-repo test fed lean as master and research grammar lacked two flags: orchestrator `74e91757` plus research `24207333`.

## Backlog waves A-D (all flagged default off, orchestrator main unless noted)

| Wave | Item | Commit |
|---|---|---|
| A | REPL-EMB-3.1 extractive spill summary (`spill_extractive_summary`) | `f2c0cd5b` |
| A | REPL-EMB-R1-HTTP-TIMEOUT-INTEGRATE | `b6ba1164` |
| A | UFH14-TOOLS-1 tool-surface counting and cap | `273ba3ff` |
| A | M-27d.1 `episodic_source_label` flag | `814a6ba6` |
| B | SEQ-5-PQP-FOLLOWUP / SEQ-5-ALPHAWIN-FOLLOWUP (report-only monitors M1, M3) | `039b1e76`, `290b3e04` |
| B | AP-71 real-journal lineage-depth audit (6 keeps, no ICRH signature) | `5ff1b08d` |
| C | RTG-VAR-1 host-capability manifest | `e5cf9528` |
| C | TD-29.M2 validate-first shadow (`typed_decisions_validate_first`) | `b22cc796` |
| D | AP-72 per-model speed ceiling table (`autopilot_speed_physical_bound`) | `a6f65249` |
| D | M-12k memory-off switch (`episodic_routing_lookups`, `episodic_lookups`) | `f644f5f7` |
| D | UTM-B1 `ms.search`/`ms.expand` (MCP and REPL; `trace_navigation_tools`) | `51734a46` |

Follow-up `c1df9962`: MCP ms.* take their session from the server (`ORCHESTRATOR_MCP_SESSION_ID`), refuse a foreign client `session_id`, and fail closed unbound; new open box UTM-B1-MCP-SESSION (no launcher sets the id yet). Monty `lane_build` `fff650b6` closes VB-MONTY-LANE-BUILD-FIELD.

## Root

`7e6ea3c03` VB-AP70-ROTATION-READ reader (`cli.py ingest autopilot-rotation`, canary; first real rotation set still 0 events); `54b9fc070` CF-3c reader slice (strict `epyc.cf3c.native.v1` sealed-window reader, VB-CF3C-POLICY-WIRE first slice). Both stay open for real-data and remaining producers.

## Boxes and gating

- **STACK-UP-RELOAD-QUEUE** (harness-program.md): embedder bring-up, C3 flip, one API-only reload (ships `de0f1144`, `2c0117d3`, `ad9432c1`, `7f70e338`, `fff650b6`, `e1d34759`, `f644f5f7`, the flip), M-12k A/B, VB-TOOL-SELECTOR-WIRE real-log canary. Blocker: the production stack is down (external event).
- **AP-JOURNAL-STALENESS-AUDIT** (autopilot-program.md): filed, DO LAST per operator; autopilot has not run since 2026-08-09.
- **BSV-2:** operator approved the paired runs; row prepared and PARKED until the autopilot relaunch after the journal audit (`/mnt/raid0/llm/tmp/bsv2-paired-20261119T082025Z/`).

## Row verdicts filed

`codemode-ab-v2-27b-gpu-20261118-r2` pass; `codemode-ab-v2-{35b,27b}-gpu-20261118-fix` pass; `embedder-gpu-bringup-20261119` fail (stack down); `dripreview12-20261119T021331Z` FUTILITY_NO_GAP at n=20 paired (current 0/20, bounded_k3 2/20, half_first25 2/20; the model finalises after about 3.5 turns). D-RI-PREVIEW-1.2 was reopened with the note and the redesign "reveal the full question up front".
