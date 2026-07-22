# WP-9 + WP-10 Lineup / Recert Event — Turnkey Operator Procedure (PREP ONLY)

**Status:** PREPARED, NOT EXECUTED. This document is a ready-to-run runbook. No config was
edited, nothing was committed, no server was restarted, no inference was run while preparing it.
**Owner of execution:** operator (this is a measured-role NUMA change → §H recert cascade → human-gated bench).
**Created:** 2026-07-21 · **Prep author:** read-only investigation session.

**Cross-refs:** [within-role-placement-state-machine.md](within-role-placement-state-machine.md) (WP-9/WP-10 tasks + mode-exclusivity contract),
[eval-tower-loop-robustness-audit-2026-07-20.md](eval-tower-loop-robustness-audit-2026-07-20.md) (§H hardening, A1-A5),
`scripts/server/stack_numa.py` (NUMA_CONFIG), `orchestration/contention_matrix.yaml`.

---

## Executive summary (10 lines)

1. **WP-9** = move `ingest_long_context`'s half instance (idx 0, port 8085) from NODE0 `0-47,96-143` → NODE1 `48-95,144-191`; frontdoor's half stays NODE0. Result: the two halves become core-disjoint and can run concurrently (mode-exclusivity contract). One-line cpuset edit; **ingest's four quarters (8185/8285/8385/8485) are unchanged** (verified).
2. **WP-10** = `worker_math` has no NUMA_CONFIG entry, so its decodes acquire no region locks. Investigation shows **worker_math is not a separate server — it shares `worker_general`'s gemma4 server** (`server_mode.worker`, `shared_with: [worker_math, toolrunner]`, ports 8072 full + 8082/8182/8282/8382 quarters). The reality-reflecting fix is a NUMA_CONFIG entry that **mirrors `worker_general`** exactly.
3. Both edits change the topology fingerprint → the full §H recert cascade fires (re-measure, re-pin, re-cert, un-skip H1).
4. **Computed new fingerprints (imported the real `topology_fingerprint_for_matrix` read-only; current-config sanity check reproduced the committed `8c8cfcbb13d2611d` exactly):**
   - WP-9 only (or WP-9 + WP-10 with worker_math kept OUT of the measured matrix): matrix hash → **`de208a54c09f9a17`**.
   - WP-9 + WP-10 with worker_math added as a measured role: matrix hash → **`13617d67910fd34a`**.
   - Full-topology fingerprint (fallback path): WP-9 `09009fdbe9c424cd`; WP-9+WP-10 `c572f889fd186a67`.
5. **Low physical blast radius:** neither edit touches a *launched* instance's cpuset — the ingest half (8085) is not in the live quarters-only stack, and worker_math mirrors already-live worker quarters. **No llama-server needs restarting**; only the 6 API workers need a `reload orchestrator` to refresh their NUMA_CONFIG + load-once matrix cache.
6. Recert = re-run `scripts/server/contention_matrix.py run` (the exact 2026-07-20 recert vehicle) against the live stack, plus the within-role bench for quarterable roles; then sweep every `required_topology_hash: 8c8cfcbb13d2611d` pin (≈32 in `entries/*.yaml`, ≈20 in `manifest.yaml`, +1 straggler `df373c79…` at `manifest.yaml:2087`) to the new hash.
7. Un-skip nothing — H1's `test_real_matrix_against_live_numa_config` is **already un-skipped** (asserts `matrix.topology_hash == topology_fingerprint_for_matrix(NUMA_CONFIG)`); it will simply go RED the moment you edit the config and GREEN once the matrix is re-stamped.
8. **Design-changing finding:** WP-10's cross-role protection depends on the GLOBAL region mutex, which is gated by `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT`. **It is ON in the live orchestrator (verified in `/proc/<uvicorn>/environ`)** — so a mirrored worker_math entry genuinely serializes worker_math vs worker_general on shared cores. If that flag were ever off, the mirror alone would not protect (per-role lock namespaces don't intersect).
9. **Design-changing finding:** WP-9 has **zero effect on the current live (quarters-only) matrix numbers** — cross-role pairs are measured on ingest's *quarter* 8185 (unchanged), and the half isn't launched. The recert is a legitimate re-measure that re-stamps the hash with (predictably) stable numbers; §H still forbids a hash-only bump. The concurrency benefit is realized only when the ingest half is actually launched in solo mode.
10. **Cost:** ~0.5–1.5 h wall (bench dominated), host must be quiet (no eval/bench/autopilot inference). No host reboot. Everything is reversible by reverting the two config hunks + `git checkout` the matrix.

### Findings that change the WP-9 / WP-10 design (call-outs)

- **worker_math shares worker_general's server** (confirmed: `orchestration/model_registry.yaml` server_mode `worker` → `model_role: worker_general`, `shared_with: [worker_math, toolrunner]`; `stack_priors.yaml` roles `worker_math.serving.served_by: worker_general`, endpoint `http://localhost:8082`, `binding: server_mode.shared_with`). The stale `worker_math: Qwen2.5-Math-7B` block in the research registry (line ~3992) is **DEPRECATED** (GGUF not on disk) and is NOT what serves worker_math today. → WP-10 config must **mirror worker_general**, not invent a dedicated core set.
- **Whole-topology is quarters-only right now.** Live llama-servers: frontdoor 8080/8180/8280/8380, worker 8082/8182/8282/8382, ingest 8185/8285/8385/8485, architect 8083, worker_vision 8086, vision_escalation 8087. **The half/full instances 8070 / 8085 / 8072 are NOT launched** (consistent with `full_disabled` / mode-exclusivity). So WP-9 moves a config-only, currently-unlaunched instance.
- **The GLOBAL cross-role mutex is live** (`ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1`, alongside `PER_REGION_LOCKS=1`, `SHAPE_AWARE_CONTENTION=1`, `PLACEMENT_STATE_MACHINE=1`, `REVERSE_MIGRATION=1`). This is the mechanism that makes the worker_math mirror protective.
- **Adding worker_math to NUMA_CONFIG does NOT auto-launch a server.** The launch set is driven by `ORCHESTRATOR_PROFILES` + the process layout / `server_mode`, not by iterating `NUMA_CONFIG.keys()`. `MLOCK_ROLES` only matters for a role that is actually launched. → give worker_math **no `mlock` key** so it never enters MLOCK_ROLES and never claims budget or a duplicate 8072/8082 server (port-collision safe).
- **n_way section of the matrix is already v6-era** (`topology_hash df373c79cc4af06f` inline comment; measured 2026-05-26) while the authoritative `pairs:` block is v7 (2026-07-20). This event is the right time to regenerate the n_way/feasibility layer too, because WP-9 flips ingest's half↔quarter disjointness (half NODE0 contains q0/q1 → half NODE1 contains q2/q3).

---

## 1. Exact config diffs (ready to apply)

All edits are in **`/workspace/repos/epyc-orchestrator/scripts/server/stack_numa.py`** (single source of truth; the lean registry does not carry NUMA_CONFIG).

### WP-9 — ingest_long_context half → NODE1

Verified current cpusets before editing:
- ingest idx0 (half): `NUMA_NODE0[0]` = `0-47,96-143`, port 8085, 96t  ← **the only line that changes**
- ingest idx1 q0: `NUMA_Q0A` = `0-23,96-119`, 8185, 48  ← unchanged
- ingest idx2 q1: `NUMA_Q0B` = `24-47,120-143`, 8285, 48  ← unchanged
- ingest idx3 q2: `NUMA_Q1A` = `48-71,144-167`, 8385, 48  ← unchanged
- ingest idx4 q3: `NUMA_Q1B` = `72-95,168-191`, 8485, 48  ← unchanged
- (frontdoor half idx0 stays `NUMA_NODE0`, port 8070 — **not touched**, per the contract "frontdoor NODE0, ingest NODE1")

```diff
--- a/scripts/server/stack_numa.py
+++ b/scripts/server/stack_numa.py
@@ ingest_long_context "instances"
     "ingest_long_context": {
         "instances": [
-            (NUMA_NODE0[0], 8085, NUMA_NODE0[1]),    # full: 1×96t on cores 0-47+SMT
+            # WP-9 (2026-07-21): distinct-halves contract. Half moved NODE0 -> NODE1
+            # so frontdoor's half (NODE0 0-47,96-143) and this half (NODE1
+            # 48-95,144-191) are core-disjoint and can run concurrently. Quarters
+            # below are unchanged. Measured-role NUMA change -> §H recert.
+            (NUMA_NODE1[0], 8085, NUMA_NODE1[1]),    # half: 1×96t on cores 48-95+SMT (NODE1)
             (NUMA_Q0A[0], 8185, NUMA_Q0A[1]),        # quarter 0
             (NUMA_Q0B[0], 8285, NUMA_Q0B[1]),        # quarter 1
             (NUMA_Q1A[0], 8385, NUMA_Q1A[1]),        # quarter 2
             (NUMA_Q1B[0], 8485, NUMA_Q1B[1]),        # quarter 3
         ],
         "full_instance_idx": 0,
         "mlock": True,    # ~46 GB per instance — latency-critical for ingest pipeline (Stage 1 of three_stage_summarization since 2026-05-06)
     },
```

`NUMA_NODE1 = ("48-95,144-191", 96)` already exists in the module (line 35) — no new constant needed.

> Note: after WP-9 the ingest half (48-95) becomes disjoint from ingest q0/q1 (0-23 / 24-47) and overlaps ingest q2/q3 (48-71 / 72-95). The runtime derives half↔quarter overlap live from NUMA_CONFIG (`build_instance_regions`), and the ingest `same_role` YAML entry is coarse (no explicit `instance_pairs`), so no same-role YAML hand-edit is required for the flip — but the cross-role feasibility/n_way layer must be regenerated (§3).

### WP-10 — worker_math NUMA_CONFIG entry (mirror worker_general)

worker_math is served by worker_general's server today. The config that reflects reality is a mirror of
worker_general's instances (identical ports, cpu_lists, threads), so a worker_math decode computes the
same atomic regions and — with `CROSS_ROLE_DISJOINT_PLACEMENT=1` live — acquires the role-agnostic GLOBAL
region mutex on those physical cores, giving it the cross-role protection it lacks today. Insert directly
**after** the `worker_general` block and **before** `worker_vision`:

```diff
--- a/scripts/server/stack_numa.py
+++ b/scripts/server/stack_numa.py
@@ after the worker_general entry, before worker_vision
         "spec_overrides": {"draft_max": 2, "p_split": 0},  # gemma4 MTP recipe (was dm=8 for Qwen3-Coder)
         "numactl_policy_instances": {0: "interleave=all"},  # required for gemma4 MTP idx0
     },
+    # WP-10 (2026-07-21): worker_math is NOT a separate server — it shares
+    # worker_general's gemma4-26B-A4B MTP server (server_mode.worker,
+    # shared_with: [worker_math, toolrunner]; stack_priors served_by=worker_general,
+    # endpoint :8082). It previously had NO NUMA_CONFIG entry, so its decodes
+    # acquired no region locks -> unprotected physical contention with the quarter
+    # fleets (EV-11c worker_math arm). This entry MIRRORS worker_general exactly so
+    # a worker_math decode maps to the same atomic regions and takes the GLOBAL
+    # cross-role region mutex (ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1, live).
+    # It does NOT launch a server (launch set is profile/server_mode-driven, not
+    # NUMA_CONFIG.keys()) and deliberately has NO "mlock" key so it never enters
+    # MLOCK_ROLES / claims budget / collides on 8072/8082. full_disabled matches
+    # worker_general (no live 8072 full). Measured-role change -> §H recert.
+    "worker_math": {
+        "instances": [
+            ("0-95", 8072, 96),                    # full canonical (shared w/ worker_general; not launched)
+            (NUMA_Q0A[0], 8082, NUMA_Q0A[1]),      # quarter 0 (shared physical server)
+            (NUMA_Q0B[0], 8182, NUMA_Q0B[1]),      # quarter 1
+            (NUMA_Q1A[0], 8282, NUMA_Q1A[1]),      # quarter 2
+            (NUMA_Q1B[0], 8382, NUMA_Q1B[1]),      # quarter 3
+        ],
+        "full_instance_idx": 0,
+        "placement_policy": "full_disabled",
+        "numactl_policy_instances": {0: "interleave=all"},
+        # intentionally NO "mlock" (shares worker_general's already-mlocked process)
+    },
     "worker_vision": {
```

**Alternative to consider before applying WP-10 (operator/owner call):** the mirror gives worker_math its own
per-role lock namespace that only the GLOBAL mutex reconciles with worker_general. A cleaner-but-code
alternative is to route worker_math dispatch through worker_general's backend with
`topology_role="worker_general"` (the `ConcurrencyAwareBackend` already supports a distinct `topology_role`,
`concurrency_aware.py:200-201,359`), which would put worker_math on worker_general's *own* per-role locks with
no config duplication and no matrix growth. That is a code change (out of scope for a config-only event) — the
mirror entry is the config-only path and is correct given the GLOBAL mutex is live. Flag for the owner.

---

## 2. Relaunch commands

**What must restart:** only the 6 orchestrator API workers (to re-import NUMA_CONFIG and drop the load-once
contention-matrix cache). **No llama-server restart is required** — the WP-9 half (8085) is not launched, and
the WP-10 mirror points at already-live worker quarters. This is the key reason the event is low-risk.

**What stays untouched:** every llama-server (frontdoor 8080-8380, worker 8082-8382, ingest 8185-8485,
architect 8083, worker_vision 8086, vision_escalation 8087, embedders 8090-8095), autopilot (API-only reload;
it reconnects — do NOT stop it for an API-only reload per CLAUDE.md).

Ordered procedure (cwd `/mnt/raid0/llm/epyc-orchestrator` throughout):

```bash
# 0. Confirm host is quiet (no eval/bench/autopilot inference in flight) — see §5.
# 1. Apply the two stack_numa.py hunks from §1.
# 2. Re-measure the matrix against the LIVE stack (servers already reflect the new
#    topology because only unlaunched/mirrored instances changed) — see §3 for the
#    exact bench command. This writes orchestration/contention_matrix.yaml stamped
#    with the new topology_hash.
# 3. Validate the fresh matrix locally (no inference):
scripts/server/contention_matrix.py validate
scripts/validate/check_contention_matrix_fresh.py            # expect OK, new hash
.venv/bin/python -m pytest tests/unit/test_scheduling_contention.py -q \
    -k real_matrix_against_live_numa_config                  # H1 gate, expect PASS
# 4. Reload ONLY the API (refreshes NUMA_CONFIG import + matrix cache on all 6 workers):
scripts/server/orchestrator_stack.py reload orchestrator     # do NOT stop autopilot
# 5. Sweep the topology-hash pins in coordination entries (§3) and recompile.
```

**Optional extension (only if the operator wants the concurrent-halves benefit realized now):** launch the
ingest half on NODE1 in solo mode and bench half-instance contention:
```bash
scripts/server/orchestrator_stack.py start --only ingest_long_context   # brings up 8085 on NODE1 (+ re-affirms quarters)
```
This is NOT required for the recert; without it the half remains config-only and the matrix numbers are
quarter-measured. If launched, add half-instance cross-role pairs to the bench (§3) and confirm live affinity
of 8085 lands on `48-95,144-191`.

---

## 3. Recert checklist (per §H)

### 3a. Expected new topology fingerprint (computed read-only)

Reproduction: imported `scripts/server/stack_numa.NUMA_CONFIG` + `src.scheduling.contention.{topology_fingerprint,
topology_fingerprint_for_matrix, matrix_measured_roles, load_contention_matrix}`, applied the §1 edits to a deep
copy, and hashed. **Sanity check passed:** `topology_fingerprint_for_matrix(current NUMA_CONFIG, committed matrix)`
== `8c8cfcbb13d2611d` (the committed hash), confirming the method.

| Scenario | matrix `topology_hash` to stamp | full-topology fingerprint (fallback) |
|---|---|---|
| current (baseline) | `8c8cfcbb13d2611d` | `81a994bebe8364ae` |
| WP-9 only, or WP-9+WP-10 with **worker_math NOT a measured role** | **`de208a54c09f9a17`** | `09009fdbe9c424cd` (WP-9), `c572f889fd186a67` (WP-9+WP-10) |
| WP-9 + WP-10 with **worker_math measured** (7-role subset) | **`13617d67910fd34a`** | `c572f889fd186a67` |

Why two possible matrix hashes: `topology_fingerprint_for_matrix` hashes only `matrix_measured_roles(matrix)`
(currently the 6 prod roles: architect_general, frontdoor, ingest_long_context, vision_escalation,
worker_general, worker_vision). Adding worker_math to NUMA_CONFIG does **not** move the matrix hash unless the
recert also *measures* worker_math into the matrix. `contention_matrix.py run` with no `--roles` enumerates all
NUMA_CONFIG roles → it WILL measure worker_math → hash `13617d67910fd34a`. To keep worker_math out of the
measured matrix (alias-only, cross-role pairs fail-closed), run with an explicit
`--roles frontdoor worker_general ingest_long_context vision_escalation architect_general worker_vision` → hash
`de208a54c09f9a17`. **Recommended (§H-complete): measure worker_math → target `13617d67910fd34a`.** Because
worker_math ≡ worker_general physically, its measured ratios will equal worker_general's; that is expected, not
a bug (and (worker_math, worker_general) is topology-infeasible → excluded automatically).

### 3b. Contention-matrix re-measure (exact 2026-07-20 recert vehicle)

The 2026-07-20 v7 recert (audit A3/A5, artifact `data/contention_matrix/v7-live-recert-20260720T180916Z/`)
ran the default `run` subcommand against the live stack — it enumerated 15 cross-role pairs and wrote 6
same-role entries. Reuse the same vehicle:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
# Cross-role pair matrix + same-role coarse entries (writes canonical YAML, stamps new hash).
# Include worker_math (default enumerates all NUMA_CONFIG roles) for the §H-complete path:
scripts/server/contention_matrix.py run \
    --output data/contention_matrix/wp9-wp10-recert-$(date -u +%Y%m%dT%H%M%SZ)/pair_matrix.yaml
# (drop --output to write straight to orchestration/contention_matrix.yaml, as 2026-07-20 did;
#  staging + diff-then-promote is safer.)

# Within-role instance-pair recert for the quarterable roles (same command family the
# 2026-07-20 within-role artifact used: v7-quarter-j5-frontdoor-worker_20260720T154812Z):
scripts/server/contention_matrix.py bench-within-role \
    --roles frontdoor worker_general worker_math ingest_long_context vision_escalation \
    --safe-sampling --live-only \
    --output data/contention_matrix/wp9-wp10-within-role-$(date -u +%Y%m%dT%H%M%SZ)/
```

Runs ALONE (no other inference). `--safe-sampling` is the gemma4-crash mitigation. Preconditions per project
policy: host quiet + verified boost clocks (`feedback_host_throttle_check`), `affinity_preflight.py`
live-affinity pass (do NOT trust `taskset -cp <mainpid>` — the main thread legitimately reads a narrow
`0,96`-style mask under per-thread OMP pinning; use `affinity_preflight.py` which walks the whole OMP team).

### 3c. Which matrix sections need re-measuring

- **`pairs:` (cross-role, authoritative v7 layer)** — re-measure ALL. WP-9 changes ingest's half placement
  (only matters if the half is launched; cross-role pairs currently use ingest quarter 8185, unchanged →
  numbers stable, hash re-stamped). WP-10 adds worker_math pairs (≈5 new: worker_math × {frontdoor, ingest,
  vision_escalation, architect_general, worker_vision}; worker_math×worker_general is infeasible/excluded).
- **`same_role:`** — re-run within-role for frontdoor, worker_general, worker_math (mirror), vision_escalation.
  ingest same_role is coarse "allow" (non-quarterable for cross-role) — regenerate its coarse entry via `run`.
- **`n_way:` + `triples:` + feasibility** — STALE (v6-era `df373c79`, 2026-05-26). WP-9 flips ingest half↔quarter
  disjointness (half now contains q2/q3 not q0/q1) → every n_way set that places ingest on its half changes
  feasibility. Regenerate via `enumerate` (feasibility) → `nway` after `run`. This also finally brings the
  n_way layer onto v7.
- **`n_way_full_instance_coarse:`** — historical, not used for placement; optional refresh.
- **`same_role_certifications:`** — the narrow per-role live-port certs. frontdoor (`d09241b04e26b3bc`) and
  worker_general (`20ec95e925380990`) role hashes are unchanged by WP-9/WP-10 (those roles' own instances
  don't move), so the certs stay valid; add a worker_math cert if worker_math same-role fanout is wanted
  (its `role_topology_fingerprint` differs from worker_general's because the hash includes the role name).

### 3d. Entry topology-pin sweep (the old hash appears widely)

Repoint every `required_topology_hash: 8c8cfcbb13d2611d` to the new hash (`13617d67910fd34a` recommended),
and fix the one v6 straggler:

| File | occurrences of `8c8cfcbb13d2611d` | notes |
|---|---|---|
| `coordination/inference-batch/manifest.yaml` | ~20 `required_topology_hash` + inline refs (lines 41,55,72,81,86,127,180,321,554,679,807,930,1049,1173,1302,1435,1563,1678,1792,1910,2201) | also update the attest command literal at line 55 and prose at 72/81/86/127 |
| `coordination/inference-batch/entries/30-bulk-campaign.yaml` | 10 | |
| `coordination/inference-batch/entries/20-eval-tower.yaml` | 8 | includes the EV-4/EV-5/7/8/10a/11 rows swept to v7 on 2026-07-20 |
| `coordination/inference-batch/entries/10-reviewer-plane.yaml` | 8 | |
| `coordination/inference-batch/entries/40-routing.yaml` | 3 | |
| `coordination/inference-batch/entries/00-rcp-prologue.yaml` | 3 | |
| `coordination/inference-batch/manifest.yaml:2087` | 1× `df373c79cc4af06f` (v6 straggler) | repoint to new hash too |

Then recompile + revalidate:
```bash
scripts/coordination/compile_inference_batch.py validate      # expect all entries valid
```
(Per CLAUDE.md, entry/index edits are traceable to this operator-approved event; do not fan this sweep out to sub-agents.)

### 3e. Cert refresh + the H1 CI test

- Update the canonical `orchestration/contention_matrix.yaml` `topology_hash:` and `measured_at:` from the
  `run` output (the tool stamps them). Update the `same_role_certifications[*].topology_hash` only for roles
  actually re-measured.
- **H1 test is already un-skipped:** `tests/unit/test_scheduling_contention.py::test_real_matrix_against_live_numa_config`
  asserts `matrix.topology_hash == topology_fingerprint_for_matrix(stack_numa.NUMA_CONFIG, matrix)` and
  `len == 16`. It goes RED the instant §1 is applied (config moved, matrix not yet re-stamped) and must go
  GREEN after the re-measure + commit. Run it as the closing gate:
  ```bash
  .venv/bin/python -m pytest tests/unit/test_scheduling_contention.py -q
  ```
- Stack-start / preflight hard gate: `scripts/server/preflight_gate.py --expected-topology-hash <NEW> --require-servers --json`
  (this is the `manifest.yaml:55` attestation vehicle; update its literal to the new hash). Also
  `scripts/validate/check_contention_matrix_fresh.py` must print OK for the new hash (it is wired into
  pre-commit + preflight as a hard gate per Phase-4 H1).

---

## 4. Validation — post-event acceptance probes

Run only after the host is quiet and with per-run approval (these drive inference):

1. **Concurrent distinct halves (WP-9 core acceptance).** Launch both halves
   (`start --only frontdoor` brings up 8070 NODE0; `start --only ingest_long_context` brings up 8085 NODE1),
   then drive one request at frontdoor's half and one at ingest's half concurrently. **Expected:**
   `affinity_preflight.py` shows 8070 pinned `0-47,96-143` and 8085 pinned `48-95,144-191` (disjoint);
   `/dashboard/api/region_locks` shows frontdoor holding NODE0 regions {q0,q1} and ingest holding NODE1
   regions {q2,q3} **simultaneously** with no GLOBAL-mutex contention between them (before WP-9 they'd have
   serialized on shared NODE0 regions). Lock-file evidence: `cpu_region.GLOBAL.q0/q1.lock` held by frontdoor
   PID, `cpu_region.GLOBAL.q2/q3.lock` held by ingest PID, concurrently.
2. **worker_math region locks present during a decode (WP-10 core acceptance).** Route a request to
   `worker_math` (e.g. `force_role=worker_math` via the eval/autopilot path, per
   `feedback_placement_queue_test_via_eval_path` — NOT bare `/chat`, which round-robins across 6 workers).
   **Expected during the decode:** a held `cpu_region.worker_math.<region>.lock` **and** the role-agnostic
   `cpu_region.GLOBAL.<region>.lock` for the gemma quarter it lands on; `active_region_holders()` now surfaces
   `worker_math` as a holder (it was invisible before). Cross-check: a concurrent worker_general request
   cannot take the same physical quarter (GLOBAL mutex) — it places on a disjoint quarter or queues.
3. **Gate no longer fail-closes.** `contention_gate.matrix_health()` == OK for the new hash (before commit it
   reads stale → `QUEUE`/`DEGRADED_ALLOW`); confirm via the dashboard contention panel + a background
   cross-role decode being ADMITTED rather than serialized.

---

## 5. Cost / duration + scheduling constraint

- **Wall time:** ~0.5–1.5 h. Dominated by the bench: cross-role `run` ≈ 0.3–0.5 h (15–20 pairs, 1 sample
  each as in the 2026-07-20 run) + within-role `bench-within-role --samples 3` ≈ 0.3–0.7 h. Config edit +
  API reload + pin sweep + tests ≈ 15 min. Optional half-launch adds a few minutes + memory (~46 GB mlock
  for the ingest half if launched).
- **Compute/risk:** low. No kernel build, no host reboot (operator-owned anyway), no llama-server restart
  required for the recert path. Reversible: revert the two `stack_numa.py` hunks + `git checkout
  orchestration/contention_matrix.yaml` + revert the pin sweep; `reload orchestrator`.
- **Safe scheduling constraint (hard):** run **only when the host is quiet** — NO eval-tower / benchmark /
  autopilot inference in flight (`feedback_no_concurrent_inference`, bench must run ALONE). At prep time a
  **live GPU eval was observed running** (architect-bench A1 on 18072, pids 1441696/1442041/1442044) — that is
  GPU-resident (ROCm0) and does not touch the CPU quarters, but confirm it and any CPU autopilot/eval are done
  before benching. Verify boost clocks first (`feedback_host_throttle_check`); the recert bench MUST run with
  `affinity_preflight.py` green and the OMP/affinity env the live servers already carry. Do not start until an
  operator has explicitly approved the inference window.

---

## Appendix — evidence pointers

- Live serving of worker_math: `orchestration/model_registry.yaml` server_mode `worker`
  (`model_role: worker_general`, `shared_with: [worker_math, toolrunner]`, `:8072`);
  `orchestration/derived/stack_priors.yaml` `worker_math` role → `served_by: worker_general`, endpoint `:8082`,
  `binding: server_mode.shared_with`.
- Live flags: `/proc/1348652/environ` (uvicorn `--workers 6`) →
  `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1`, `PER_REGION_LOCKS=1`, `SHAPE_AWARE_CONTENTION=1`,
  `PLACEMENT_STATE_MACHINE=1`, `REVERSE_MIGRATION=1`.
- Region-lock model: `src/runtime/cpu_region_lock.py` — per-role `cpu_region.{role}.{region}.lock`; GLOBAL
  `cpu_region.GLOBAL.{region}.lock` (role-agnostic, acquired first when
  `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT` is on) = cross-role physical exclusion. Regions derived from
  NUMA_CONFIG via `src/runtime/instance_topology.py:build_instance_regions` — a role absent from NUMA_CONFIG
  yields no regions and no locks (the WP-10 defect).
- Fingerprint fns: `src/scheduling/contention.py:806 topology_fingerprint`, `:877 topology_fingerprint_for_matrix`,
  `:863 matrix_measured_roles`. H1 test: `tests/unit/test_scheduling_contention.py:420`.
- Recert vehicle: `scripts/server/contention_matrix.py` (`cmd_run` :1058, `bench-within-role` :1252);
  2026-07-20 artifacts `data/contention_matrix/v7-live-recert-20260720T180916Z/`,
  `data/contention_matrix/v7-quarter-j5-frontdoor-worker_20260720T154812Z/`.
```
