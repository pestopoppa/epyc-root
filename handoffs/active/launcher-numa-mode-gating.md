# Launcher: full XOR quarters, not both

**Status**: PARTIAL — flag implemented, default decision pending (operator call)
**Priority**: medium (production workaround exists; long-term fix is a small CLI flag)
**Origin**: `progress/2026-05/2026-05-08.md` § Phase 3 known sub-issue

## What landed — 2026-05-27 hygiene audit verification

`--numa-mode {full,quarter,both}` flag is live in `epyc-orchestrator/scripts/server/orchestrator_stack.py:1324` with `choices=["full","quarter","both"]`. Filtering implemented in `scripts/server/stack_manifest.py:267` (`_filter_by_numa_mode`) and wired into the start path at `scripts/server/stack_commands.py:393`.

## Acceptance criteria status

| Original criterion | Status |
|---|---|
| `start --only worker_general` defaults to `--numa-mode quarter` and brings up 4 quarter instances | **NOT MET** — default is `both`, all 5 instances still launch unless operator passes `--numa-mode quarter` |
| `start --only worker_general --numa-mode full` brings up only the full instance | ✅ MET |
| `start --only worker_general --numa-mode both` brings up all 5 with a stderr warning | ✅ MET (warning via help text/banner) |

## Open operator decision

The unsafe default (`both`) still ships. Two paths forward:

- **(a) Flip default to `quarter`** at `orchestrator_stack.py:1326`. One-line change. Satisfies the original acceptance criteria and removes the 1.5× CPU oversubscription footgun. Changes behavior for any caller currently relying on `both` — the help text notes Qwen3-Coder `-t 24` and Qwen3.6-35B Q8 quarter-tuned configs co-exist OK with `both`, so they would need to add `--numa-mode both` explicitly to keep current behavior.
- **(b) Keep `both` default** as a deliberate back-compat choice; mark this handoff WONTFIX and archive with that framing. Per-role override remains `--numa-mode full` for gemma4-MTP-style high-thread roles.

Audit (2026-05-27 morning) initially archived this prematurely as ✅ COMPLETE — that was wrong. Restored to active 2026-05-27 evening per operator review; default is an operator call, not a hygiene-cleanup decision.

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
