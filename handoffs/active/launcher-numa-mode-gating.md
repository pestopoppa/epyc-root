# Launcher: full XOR quarters, not both

**Status**: stub — discovered during 2026-05-08 worker_general gemma4-26B-A4B MTP swap (Phase 3)
**Priority**: medium (production workaround exists; long-term fix is a small CLI flag)
**Origin**: `progress/2026-05/2026-05-08.md` § Phase 3 known sub-issue

## Objective

When the operator runs `python3 scripts/server/orchestrator_stack.py start --only worker_general` (or `start` for the whole stack), the launcher currently brings up **all 5 instances** for that role: 1 full-NUMA-node instance (port 8072, 96 threads on CPUs 0-95) + 4 NUMA-quarter instances (ports 8082/8182/8282/8382, 48 threads each).

These 5 instances **share overlapping CPU sets**:
- Full instance: pinned to 0-95 (all 96 physical cores)
- 4 quarters together: Q0A (0-23,SMT) + Q0B (24-47,SMT) + Q1A (48-71,SMT) + Q1B (72-95,SMT) → also covers 0-95 and SMT siblings

Running all 5 simultaneously creates ~1.5× CPU oversubscription. Verified 2026-05-08: load average jumped to 420, full instance throughput dropped from 76.5 t/s solo → 9 t/s with quarters running.

The intent is "operator picks one **mode**: full-speed (1 instance, max single-request throughput) OR concurrent quarters (4 instances, max aggregate throughput under multi-request load)". The launcher should not silently start both.

## Current workaround

After `--only worker_general` finishes, manually stop the unwanted instances via `orchestrator_stack.py stop server_<port>`. Verified 2026-05-08 (smoke test).

## Proposed fix

Add a CLI flag `--numa-mode {full,quarter,both}` (default `quarter` to match historical Qwen3-Coder behavior) to `start_server` and the top-level CLI. Behavior:

- `--numa-mode full`: only start the instance at `NUMA_CONFIG[role]["full_instance_idx"]`.
- `--numa-mode quarter`: skip the full instance, start the 4 quarters.
- `--numa-mode both`: current behavior (start everything; warn on overlap).

Implementation sketch:
1. Filter `NUMA_CONFIG[role]["instances"]` per the flag before iterating in `cmd_start`.
2. Print a banner when `--numa-mode both` is in effect noting the CPU overlap and expected throughput penalty.
3. Default to `quarter` for backward compat (this is what the pre-2026-05-08 Qwen3-Coder worker did de facto, since its `-t 24` was light enough that the full instance + quarters could co-exist without the load-420 collapse — gemma4's `-t 96` makes the overlap visible).

## Files

| File | Touch |
|---|---|
| `epyc-orchestrator/scripts/server/orchestrator_stack.py` | Add `--numa-mode` arg; filter `instances` list per choice; warn on `both` |

## Acceptance criteria

- `start --only worker_general` defaults to `--numa-mode quarter` and brings up 4 quarter instances (not the full).
- `start --only worker_general --numa-mode full` brings up only the full instance.
- `start --only worker_general --numa-mode both` brings up all 5 with a stderr warning explaining the overlap.

## References

- `progress/2026-05/2026-05-08.md` § session 2 — original discovery
- `project_worker_general_swap_2026_05_08` memory — the swap that exposed the issue
- `project_gemma4_mtp_launch_recipe` memory — launch parameters that must match per-instance
