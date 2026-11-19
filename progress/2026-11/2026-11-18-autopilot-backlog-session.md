# 2026-11-18 autopilot-backlog-session

## CODEMODE-AB probe results (35B + 27B)

- 35B-A3B (stop-on-answer n50, descriptive interim): code mode loses to direct calls (success 0.10 vs 0.43, p=1.2e-4) at ~20x fewer tokens; per-request top-8 tool selection beats static list+list_tools (0.38 vs 0.10, both C1 embed and C2 Jev oneshot); C1 ~ C2 (C2 recall 0.65 vs 0.45).
- 27B (complete, 264 eps): code mode 0.03 vs direct 0.30 (p=4e-5); selector arms floor-bound, inconclusive.
- Verdicts: /mnt/raid0/llm/tmp/codemode-ab-20261117/out/{35b,27b}/verdict.json (score.py 2c8490e3).
- Results committed as 3fcc9a711 (cited, not re-described).

## REPL containment hardening (epyc-orchestrator, pushed)

- Pushed to main: 1145b9ce..e5b95640. Adds untrusted tool-text labelling and capping, regeneration cap of 8, write dedupe, per-snippet tool-call budget, unswallowable deadline, memory-bomb refusal, and rewriting of bare-except handlers.
- Strict containment flag stays OFF: 4 tests fail with it on (follow-up).
- Follow-up ce631d31 (pushed): tool-call budget default raised 100 -> 1000 because 100 truncated code-mode batch loops; caught by a side agent.
- Shared orchestrator clone fast-forwarded to ce631d31. API is down, so no reload; the next start picks the changes up.
- Handoffs: D-RI-CONTAIN left unticked (partial; no child/cgroup lane yet), child tasks D-RI-CONTAIN-T1/T2 added in memory-program.md. UFH-01 index Next-action now points at CM-2..CM-5.

## Open follow-ups

- Fix the 4 containment-flag tests (D-RI-CONTAIN-T1).
- Branch probe/codemode-ab (selector code, off by default) is unpushed; base for CM-2..CM-5 per-request tool selection on direct calls.
- score.py labels p=1.0 ties as X_better/Y_better; quirk to fix.
- LiteParse figure boxes need PyMuPDF.
- vidya sync for intake-2675..2693.

## Wrap-up b: later 2026-11-18 work (epyc-orchestrator main, all pushed; verified in git)

The open follow-ups above are closed except the vidya sync: the 4 flag tests were 8 and are fixed with `exec_containment` default ON (`7c7a61f0`, D-RI-CONTAIN-T1); the probe branch is merged (the picker, CM-2..CM-5 code and the score.py tie fix are on main); PyMuPDF is declared and installed (`497ac374`, `b4449152`).

| Area | Commits | Result |
|---|---|---|
| REPL budget | `ce631d31` | per-snippet tool-call budget 100 -> 1000 |
| Code-mode reliability | `d8fce750`, `f0cf8838`, `570fd2ce`, `fcb58717`, `97b74ddf`, `ee432f78` | explicit-FINAL strict mode (one-line tool call no longer auto-wrapped as FINAL, default on), turn memory, prompt v2, typed stubs, read-only typed classifiers, replay recording default-on with handles; all flag-gated |
| Hardened picker | `bc18b941`, `8ba4f67b`, `a2790c82`, `128ea5ec`, `180493b3` | core pin, adaptive k, recovery, breaker; providers wired at startup; log rows carry picker version/delta/family cap; per-model validation harness |
| CM-2..CM-5 | `b5a30286`, `f28cef92` | code done flag-gated default off; live measurements still pending (`scripts/benchmark/codemode_ab/CM_FOLLOWUP.md`) |
| Autopilot surface | `6b0bf165`, `071c9f72`, `2fa0fca6`, `f86fc02e`, `8df12587`, `50f0e7e6` | flag_env, 15 FeatureSpec registrations, Tier 2b/3 program.md sections, numeric search surfaces, pinned observe-only security flags, 13 prompt-sink sites |
| Containment child lane | `e66ac1a9`, `072d1583`, `eb4d7f2b`, `aa1b4809`, `1d8cbe50`, `27059528` | lane built (D-RI-CONTAIN-T2), then brokers the full tool surface and is un-pinned for autopilot |
| Monty | `694f2bcb`, `658724c5`, `4b56ac68`, `3e44eea7`, `d4233871`, `66c62a4a`..`1e83dcb0`, `52db82df` | slice GO opt-in; T1 corpus share measured (tap now role-labelled); lane fully built; replay of 210 cells 74.8% routed, 0 CPython-ok/lane-failed, suite parity 458 passed; pydantic-monty 1.6.0 in the API venv, kept by `uv sync --extra monty` |

### Probe v2 (CODEMODE-AB-V2), stage 1 filed, still running

Both first rows stopped on the predeclared `harm_apick` stop from picker latency alone (p95 about 500 ms with the embedder at -t 2); recall, recovery and success checks were clean. Success per arm (30 pairs), 35B / 27B: A 0.43 / 0.47, A_pick 0.67 / 0.63, B 0.07 / 0.03, B1 0.70 / 0.53, B2 0.70 / 0.23, C3 0.80 / 1.00. C3 uses about 11x (35B) and 16x (27B) fewer tokens than A. Turn memory is neutral on 35B and hurts the 27B. Descriptive interim; filings in `/mnt/raid0/llm/tmp/codemode-ab-v2-20261118/out/{35b,27b}/filing.json`. Re-runs in flight: 35B CPU r2 (disjoint embedder cores), 27B GPU r2 (embedder on the GPU); Flash-Next CPU and 35B GPU rows auto-publish behind them. CODEMODE-AB-V2 and CODEMODE-REL stay unticked.

### Operator decisions recorded 2026-11-18

- Code-mode conclusion "direct calls win" is tentative (harness-program.md, CODEMODE-AB).
- New features may default off but must be fully wired and on the autopilot manipulation surface; proven improvements default ON.
- The C3 code-mode fixes go ON by default once the latency re-run confirms the picker (new box CODEMODE-REL-FLIP).
- Keep 35B on CPU and add a 35B GPU row. Install the pinned Monty wheel (done, `52db82df`). `repl_child_lane` must broker the full tool surface before autopilot trials it (done, `1d8cbe50`).

### Handoff changes

- Ticked: D-RI-MONTY-T1 (`[belief: cc]`), D-RI-MONTY-T2 (`[no-belief: native-pending:VB-MONTY-LANE-WIRE]`). D-RI-CONTAIN stays open on T3 (host cgroup delegation).
- Progress notes without ticks: CODEMODE-REL, CODEMODE-AB-V2, SELECTOR-HARDEN (validation outstanding), CM-2..CM-5 (code done, measurement pending), D-RI-CONTAIN-T2 follow-up.
- New boxes: CODEMODE-REL-FLIP, CODEMODE-REL-ABL-MEM (C3 without turn memory), CODEMODE-REL-EMBED-PLACE (stack-change package for the picker embedder: GPU co-host with the 27B or the A3B on GPU2), CODEMODE-REL-SCRATCH (leftover `/tmp/r2test-*` via guarded_rm), VB-MONTY-LANE-WIRE (plus a source-table row in `scripts/vidya/adapters/README.md`). VB-TOOL-SELECTOR-WIRE stays open pending a real log.
