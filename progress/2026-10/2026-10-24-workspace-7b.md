# 2026-10-24 — workspace-7b: AK Q38FN focused test close-out, harness fixes landed, CH-27 prep, handover to workspace-58

Session covered 2026-10-22 → 2026-10-24. Final wrap-up before the operator's 2026-10-24 consolidation to two sessions:
7b's work transfers to workspace-58 (handover `/mnt/raid0/llm/tmp/handover-7b-to-ws58-20261024.md`).

## 1. Focused AK test, 2026-10-22 14:30–18:00Z (operator-approved, cpu_fa_schedule route, Q38FN 64k surface)

- Verdict **DISCARD**; champion stayed `dd3d9721c`; window released 16:46:47Z (`7B_AK_ENDED`).
- it3 `akm-cpu-fa-query-major-row-schedule` measured +4.73% 64k decode over 5 pairs (floor 1.365%), was committed, then the
  anchor guard aborted on a stale incremental scratch build (`store/anchor-verify-cpu` configured from an older source tree),
  so the keep was never recorded. An identical-diff replicate measured −1.10% decode / −1.34% prefill → null.
  History branch `experimental/q38fn-fa-ak-20261022-keep1` (65b9dc558; merges cleanly onto later champions).
- In-window repairs: restored the deleted op80-capturefix verifier capture dir from hash-pinned store copies
  (`/mnt/raid0/llm/worktrees/llama.cpp-experimental-codex-op80-capturefix-20261007`, `RESTORED-FOR-AK-VERIFIER.txt`);
  moved the stale scratch aside (`anchor-verify-cpu.stale-src-q38fn-20261005`); re-queued the replicate.
- Audits answered for peers: the llama-bench `autokernel_harden` UB (CH-28) does not touch this campaign — every floor is a
  `matched_process_v2` llama-server floor, and the pp512 bench floor is never read under `--cpu-serving-launch`.

## 2. Harness fixes — landed on research main `eb753e422` (2026-10-24, operator-approved push)

| Commit | Change |
|---|---|
| `b6e80d24e` | `gates.py` clears a CMake build dir whose cache names another source tree; anchor RunAborted carries configure stderr; in-flight keep evidence travels on `run_aborted` (the 10-22 lost-keep cause) |
| `f131a9f7b` | `run.py` says "bench floor NOT USED" under a direct serving launch instead of the false "UNCALIBRATED … keeps refused" |
| `eb753e422` | CH-27: store-image anchor admitted on an experimental lane; `champion_reanchor` names the exact store COR build on a plain advance (`--cor-build`); 64k floor sealed per anchor under `floors/anchors/<exec16>/`, consults/plans the floor registry |

Tests: 417 passed + 13 subtests across the 10 AK loop test files (one timing-flaky gates test passes 3/3 in isolation).

## 3. CH-27 prep (non-inference) — ready but NOT armed

- Champion moves tracked: `dd3d9721c` → `49550eda5` (C2) → `141e4bcf5` (CH-28) → `dcc853b55` (C3, `src/llama-kv-cache.cpp`).
- Bundle `inputs-ch27-20261023` + launchers `/mnt/raid0/llm/tmp/ak-q38fn-ch27-20261024/` built on `141e4bcf5`'s store image;
  `ch27_window.sh --apply-dry` PASS. Nominal ~80 min, peak RAM ~95 GiB, grant `ch27-q38fn-floors` (5700 s, 200 GiB).
- The 10-24 ~06:37Z slot was skipped (no FILLERS row, no pid): arming was waiting on operator approval.
- Remaining: re-anchor on C3, fix the launcher's hard-coded deadline, register the row with a live pid — now workspace-58's.

## Handoff updates

- `autokernel-champion-aggregate.md` CH-27: owner → workspace-58; 2 `[x]` (fixes landed; prep done) + 2 `[ ]` (re-anchor on C3; arm row).
- `autokernel-all-devices-all-dimensions.md` AK-Q38FN-64K-FLOOR: folded into CH-27; 2 new `[ ]` (verify the side-agent
  sparse-attention surface claim; misleading UNATTESTED log + dry-run store write).
- Declined (not filed): the flaky `test_completion_inputs_and_child_tmp_release_when_runner_raises` — pre-existing timing flake, passes in isolation.

## Owned state at hand-over

No live pids, no subagents, nothing armed. Worktrees: `llama-q38fn-fa-ak-20261022` (branch at `141e4bcf5`, build-cpu stale),
`research-ak-guardfix-20261022` (landed), `research-ch27-20261023` (prep agent's, uncommitted copy of the landed patch), root
`root-wrapup-7b-20261024` (this wrap-up).
