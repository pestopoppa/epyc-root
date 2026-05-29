# NUMA Page-Cache Prewarm for Shared GGUF Startup

**Status**: IMPLEMENTED 2026-05-29 (P0-P4 landed + warm-path live-validation on the running J6 stack). P5 controlled cold-start validation remains as the only outstanding gate; defer to the next intentional cold start so the in-flight J6 24h soak is not disrupted.
**Priority**: HIGH for production stack reliability; low code volume.
**Effort**: 0.5-1 day implementation + one controlled cold-start validation.
**Owner**: epyc-orchestrator stack startup.
**Repos**: `/mnt/raid0/llm/epyc-orchestrator` implementation; `/mnt/raid0/llm/epyc-root` tracking.
**Parent indices**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md), [`routing-and-optimization-index.md`](routing-and-optimization-index.md), [`master-handoff-index.md`](master-handoff-index.md).

---

## Executor Start Here

Implement a startup prewarm step that runs after model-path validation and before any new `llama-server` process is launched. The minimum viable fix is:

```bash
numactl --interleave=all cat <unique target GGUF> >/dev/null
```

Do this for each unique GGUF needed by the start command, deduped by device+inode. Do not automate `drop_caches`; normal stack startup must require no sudo beyond the existing host-prereq machinery.

Validation is not complete until a controlled cold start shows both:

1. `/proc/<llama_pid>/numa_maps` reports near-even GGUF page placement across N0/N1/N2/N3 for the affected shared models.
2. The next autopilot seed/eval trial returns to the pre-collapse aggregate speed envelope, approximately 55-70 t/s for the comparable seed trials seen before the 2026-05-28 slowdown.

---

## Problem

`orchestrator_stack.py start` already enforces canonical host prerequisites through `apply_host_prerequisites()`:

- `kernel.numa_balancing=0`
- THP `enabled=always`
- THP `defrag=always`
- CPU governor `performance`
- `kernel.perf_event_paranoid=1`

That covers host knobs, but it does not control NUMA placement of file-backed GGUF pages in the Linux page cache. After cache eviction or first-cold startup, sequential model load plus `mlock` can first-touch large GGUFs from a single node or an uneven node set. The result is a "healthy" stack with badly collapsed model pages and much lower throughput.

This bit on 2026-05-28 after a cold/cache-disturbed restart. The manual recovery was:

| Step | Evidence |
|------|----------|
| Stop stack | 35 services + 3 Docker containers stopped; no `llama-server` PIDs left. |
| Drop caches manually | `buff/cache` fell from about 307 GB to about 1 GB. |
| Interleaved GGUF read | `numactl --interleave=all cat <3 GGUFs>` raised page cache to about 98 GB, distributed at about 25 GB +/- 1 GB per NUMA node. |
| Restart stack | 35 native services + 3 Docker services healthy. |
| Spot-check placement | Qwen3.6, Qwen3-Next-80B, and Qwen3-VL-30B model pages were balanced across N0/N1/N2/N3. |

The process exposed a real automation gap: startup says host prerequisites are satisfied, but the model page-cache residency can still be non-canonical.

---

## Prioritized Task List

- [x] **P0: Locate the implementation point.** Landed at `scripts/server/stack_commands.py::cmd_start` between the `--numa-mode` filter and `[2] Checking target ports`, labelled `[1.5] Page-cache prewarm`. Uses the post-filter `servers_to_start` so prewarm scope tracks `--only` / `--include-warm` / `--numa-mode` exactly.
- [x] **P1: Add a prewarm helper.** `scripts/server/stack_prewarm.py` (~200 lines): `_extract_paths_from_cmd`, `collect_targets` (inode dedupe), `prewarm_file` (single `numactl --interleave=all cat` invocation), `prewarm_all` (top-level entry).
- [x] **P2: Scope prewarm to the requested launch set.** `prewarm_all` is called with the post-filter `servers_to_start`. For each server entry it dispatches `build_server_command` (the same dispatcher the launcher uses), scans `-m` / `-md` / `--mmproj` flags, then dedupes by `(st_dev, st_ino)`. No WARM models warmed unless the start request asks for them.
- [x] **P3: Add an explicit escape hatch.** `--skip-page-cache-prewarm` on `orchestrator_stack.py start`, plus the equivalent `ORCHESTRATOR_SKIP_PAGE_CACHE_PREWARM=1` env. Skip path prints `[1.5] Page-cache prewarm SKIPPED` and an inline recovery recipe.
- [x] **P4: Test without real GGUF reads.** `tests/unit/test_stack_prewarm.py` — 15 tests covering flag extraction (3), inode dedupe / distinct inodes / unstatable paths / build-command failures (4), `prewarm_file` happy / CalledProcessError / missing-numactl (3), and `prewarm_all` orchestration including CLI-flag skip, env skip, happy path with size-ordered warm, mixed failure, and empty-target case (5). All 15 pass in 0.10 s.
- [ ] **P5: Controlled cold-start validation.** Deferred — the in-flight J6 24h soak (PID 219740, etime 5h21m at landing) must not be disrupted. Path: after the soak finishes or at next intentional restart, `orchestrator_stack.py stop --all && sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches && orchestrator_stack.py start`, confirm `[1.5]` warm reports ~30s aggregate (cold), spot-check `/proc/<llama_pid>/numa_maps` for N0/N1/N2/N3 balance, then verify next autopilot trial speed lands in the 55-70 t/s envelope.

### Live-validation evidence (warm path, 2026-05-29)

Ran `orchestrator_stack.py start` against the already-running stack with `[1.5]` active. Output (truncated to the new phase):

```
[1.5] Page-cache prewarm (numactl --interleave=all)
  [prewarm] 10 unique GGUF(s), 120.1 GiB total, across 39 server instance(s)
  [ 45.1 GiB] Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf → ports [8085,8185,8285,8385,8485]: OK in 0.8s
  [ 34.4 GiB] Qwen_Qwen3.6-35B-A3B-Q8_0.gguf → ports [8070,8080,8180,8280,8380]: OK in 0.7s
  [ 17.3 GiB] Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf → ports [8087,8187,8287,8387,8487]: OK in 0.3s
  [ 15.6 GiB] gemma-4-26B-A4B-it-Q4_K_M.gguf → ports [8072,8082,8182,8282,8382]: OK in 0.3s
  ... (6 more entries) ...
```

39 server entries dedupe to 10 unique GGUFs. Warm-cache reads are all sub-second (cache fully resident from the running soak's mlock). The skip path was independently verified: `--skip-page-cache-prewarm` prints the banner + recovery recipe instead. Soak undisturbed (PID 219740 still alive, all ports preserved as `already healthy, skipping`).

---

## Implementation Notes

Recommended behavior:

1. Gather model paths from the exact server entries that will launch.
2. Normalize paths with `Path.resolve()`.
3. Deduplicate by `(st_dev, st_ino)`, not by string path, because shared aliases can refer to the same physical GGUF.
4. Run `numactl --interleave=all cat <path>` with stdout redirected to `subprocess.DEVNULL`.
5. Log path, size GiB, elapsed seconds, and whether the path was skipped as a duplicate.
6. Fail closed only if the target start would otherwise load a model and prewarm fails. The emergency skip flag is the operator override.

Avoid in the first pass:

- Automatic `drop_caches`.
- Pagemap or inode-level page-cache NUMA detection.
- Runtime migration of an already-running `llama-server`.
- Changing launch NUMA policy in `stack_numa.py`.

The cheap always-warm strategy is acceptable because warm-cache reads should be fast, while cold-cache reads are exactly when correctness matters. Startup cost is expected to be roughly tens of seconds cold and near-cache-hit speed warm.

---

## Dependency Graph

```
model path validation
        |
        v
target server set resolved (--only / --include-warm / --numa-mode)
        |
        v
unique GGUF page-cache prewarm under numactl --interleave=all
        |
        v
llama-server launch + mlock
        |
        v
numa_maps verification + autopilot throughput recovery
```

This blocks reliable cold-start performance for:

- AutoPilot seed/eval wall-clock stability.
- Any benchmark run immediately following `drop_caches`, container rebuild, model overwrite, or full stack teardown.
- Shared-GGUF role consolidation where several ports rely on one physical model file.

---

## Key File Locations

| Repo | File | Purpose |
|------|------|---------|
| epyc-orchestrator | `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_commands.py` | `cmd_start`; insertion point around `[0.5] Validating model paths` and the server launch sequence. |
| epyc-orchestrator | `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_manifest.py` | `ROLE_LAUNCH_META`, `HOT_SERVERS`, `WARM_SERVERS`, `validate_model_paths()`. |
| epyc-orchestrator | `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_numa.py` | Existing NUMA launch policies; do not conflate process policy with page-cache warm policy. |
| epyc-orchestrator | `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_host.py` | Existing host-prereq machinery; keep `drop_caches` out of normal startup. |
| epyc-orchestrator | `/mnt/raid0/llm/epyc-orchestrator/tests/` | Add unit tests for prewarm helper and CLI skip flag. |
| epyc-root | `/mnt/raid0/llm/epyc-root/progress/2026-05/2026-05-28.md` | Record implementation and validation results. |

---

## Acceptance Criteria

- [ ] `rg -n "page-cache|prewarm|numactl.*cat|interleave=all" scripts/server tests` in `epyc-orchestrator` finds the new codified prewarm path and tests.
- [ ] `python3 -m pytest` target tests for the new helper pass.
- [ ] `python3 scripts/server/orchestrator_stack.py start --help` documents the skip flag if a CLI flag is used.
- [ ] A normal `orchestrator_stack.py start` prints a clear prewarm phase and reports each unique GGUF once.
- [ ] A controlled cold-cache run shows model pages distributed across all four NUMA nodes for the affected GGUFs, with no single node holding more than 30% of the model pages unless the role intentionally uses a node-local policy.
- [ ] The first comparable autopilot journal trial after validation lands at or above the recovery threshold agreed for that run. For the 2026-05-28 incident, use 55-70 aggregate t/s as the target envelope.

---

## Reporting Instructions

After implementation or validation:

1. Update this handoff's status and task checkboxes.
2. Update [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) and [`routing-and-optimization-index.md`](routing-and-optimization-index.md) if the stack-start behavior changes.
3. Add a self-contained entry to `progress/YYYY-MM/YYYY-MM-DD.md` with:
   - code files changed,
   - validation commands,
   - `numa_maps` page distribution summary,
   - autopilot trial ID and speed result.
4. If the implementation reveals a broader host-health policy issue, cross-link `autopilot-continuous-optimization.md` rather than expanding this handoff.

---

## Non-Goals

- Do not create a sudoers rule or setuid wrapper for `drop_caches`.
- Do not add autonomous `drop_caches` remediation to AutoPilot in this handoff.
- Do not treat `apply_host_prerequisites()` success as sufficient evidence after this work; page-cache placement needs its own validation signal.
- Do not re-open closed NUMA_MIRROR or weight-replication work based solely on this incident. This is about deterministic page-cache population before `mlock`, not about duplicating weights per node.
