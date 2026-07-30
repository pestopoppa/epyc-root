# NUMA Topology Cutover — RESUME DOCUMENT

> **THIS IS A RESUME DOCUMENT, NOT A NARRATIVE.** A production topology cutover is
> **applied in the working tree, uncommitted, and its commit is BLOCKED**, with
> **measurement runs in flight** on the machine. If the owning session died, read
> §0, then §1, then execute §2 P0 in order. **Nothing below needs to be
> re-derived** — the analysis is finished, the code is written, the ordering is
> forced by a pre-commit gate. Your job is to unblock and land it.

**Status**: ACTIVE — applied-uncommitted; P0 blocks the commit
**Created**: 2026-07-30
**Owner**: whichever session holds the CPU lane (this is a stack-mutating change)
**Parent index**: [`master-handoff-index.md`](master-handoff-index.md) (row N25)
**Sibling — DO NOT EDIT CONCURRENTLY**: [`numa-placement-defect-20260730.md`](numa-placement-defect-20260730.md)
is the *diagnosis* handoff (N24) and has its own writer. This document is the
*cutover-resume* half. Cross-reference it; do not duplicate its findings into it.
**Related**: [`batched-decode-measurement.md`](batched-decode-measurement.md) (E5
suspension banner) · [`shape-keyed-contention-gating.md`](shape-keyed-contention-gating.md)
(contention matrix owner) · [`within-role-placement-state-machine.md`](within-role-placement-state-machine.md)
(placement policy enum)

---

## 0. What do I do next (60-second resume)

Answer these three questions in order; each one tells you where in P0 you are.

| Check | Command | If … then |
|---|---|---|
| **1. Are the measurement runs still in flight?** | `repos/epyc-orchestrator/scripts/region-lock status` | Regions **q0/q1/q3 held** → runs are live. **Do not touch the stack, do not start the stack, do not run inference.** Work P1 (all zero-inference) while you wait. Regions **free** → go to check 2. |
| **2. Do the breaking tests still fail?** | `uv run pytest -q tests/unit/test_build_server_command_helpers.py tests/unit/test_orchestrator_stack_threads.py` (from `repos/epyc-orchestrator`) | **Failures** → do P0-1 and P0-2 first. Stack start is gated on these. **Green** → go to check 3. |
| **3. Is the contention matrix fresh?** | `uv run python scripts/server/contention_matrix.py validate` | **STALE** → the stack must be cold-started and the matrix re-benched (P0-3 steps 1-2) before any commit will pass. **Fresh** → commit (P0-3 step 3). |

**The single sentence that explains the whole blocker:** changing the cpusets
changed the topology hash, a pre-commit hook refuses to commit against a matrix
recorded under the old hash, and the only thing that refreshes the matrix needs a
live stack and runs inference — so the commit cannot land until the machine is
free.

---

## 1. State as of 2026-07-30

### 1.1 Applied in the working tree, UNCOMMITTED, commit BLOCKED

`epyc-orchestrator`:

| File | What changed |
|---|---|
| `scripts/server/stack_numa.py` | topology (the actual cutover) + import-time invariants + docstring correction |
| `orchestration/model_registry.yaml` | lean registry, recompiled from master |
| `orchestration/derived/stack_priors.yaml` | regenerated |
| `orchestration/model_descriptors.yaml` | regenerated |
| `docs/generated/current_stack_summary.md` | regenerated |
| `src/config/models.py` | port/fleet declarations |
| `src/fleet.py` | fleet shape |
| `src/registry/model_descriptors.py` | descriptor consumption |

`epyc-inference-research`:

| File | What changed |
|---|---|
| `orchestration/model_registry.yaml` | **master** registry — `no_mmap`, `numa_ports` |
| `docs/guides/benchmarking-guide.md` | placement recipes |
| `docs/guides/model-sizing.md` | placement recipes |

> ⚠ **The tree is shared.** `git status` in either repo shows work from *other*
> sessions (repl-memory, autopilot, trace, eval artifacts). **Commit with an
> explicit pathspec** — `git commit -- <paths>` — and never `git add -A`. See
> §4 Cross-cutting concerns.

### 1.2 THE BLOCKER

The pre-commit hook (`.git/hooks/pre-commit` → `scripts/validate/check_contention_matrix_fresh.py:89`)
rejects the commit with:

```
FAIL: contention matrix is STALE (live topology hash=bc28e15d ...)
```

`orchestration/contention_matrix.yaml` records `topology_hash: "8c8cfcbb13d2611d"`.
Changing the cpusets moved the live hash to `bc28e15d`. The **only** thing that
refreshes it is `python scripts/server/contention_matrix.py` (`run` subcommand),
which **requires a live stack and runs inference**.

**Therefore the ordering is forced, and it is not negotiable:**

1. Let the in-flight measurement runs finish (§1.4).
2. Fix the breaking tests (§1.5) — **stack start is gated on them**.
3. Cold-start the stack.
4. Re-bench the contention matrix.
5. Commit.

### 1.3 Topology now in the tree

**Quarters are retired.** Each quarterable role now has three shapes:

| Shape | cpuset | interleave | threads |
|---|---|---|---|
| full | `0-95` | `all` | `-t 96` |
| half A | `0-47,96-143` | `0,1` | `-t 48` |
| half B | `48-95,144-191` | `2,3` | `-t 48` |

Ports:

| Role | full | half A | half B |
|---|---|---|---|
| `frontdoor` | 8070 | 8080 | 8180 |
| `worker_general` | 8072 | 8082 | 8182 |
| `ingest_long_context` | 8085 | 8185 | 8285 |
| `architect_general` | 8083 | — (full-only) | — |

**FREED — must not be revived**: `8280` `8380` `8282` `8382` `8385` `8485`.

`no_mmap: true` for `frontdoor`, `coder_escalation`, `architect_general`,
`ingest_long_context`, `worker_vision`, `vision_escalation`.

**Half A is the GPU-disjoint half.** The GPU lane's logical `184-191` fold to
physical `88-95` = region **q3**, which is inside **half B**. Any CPU work that
must not collide with the GPU lane goes on half A.

### 1.4 Runs in flight — DO NOT DISTURB

Check with `scripts/region-lock status` before anything.

| Run | Results file | Regions held | Notes |
|---|---|---|---|
| GPU ngram sweep | `/mnt/raid0/llm/tmp/gpungram_results.txt` | **q3** | 36 cells. Script `/mnt/raid0/llm/tmp/gpungram_run.sh`. |
| CPU half-A arms | `/mnt/raid0/llm/tmp/halfa_live_results.txt` | **q0 + q1** | |
| Chained follow-on | — | q0+q1, then all four | `/mnt/raid0/llm/tmp/cpu_chain.sh` runs `halfa_rest.sh` (q0+q1), then — **after the GPU sweep releases q3** — `full_last.sh` (all four regions, 122B only). |

**GPU build gotcha (costs an hour if you rediscover it):** the v8 HIP build is at
`/mnt/raid0/llm/llama.cpp-experimental/build-v8-hip/bin/`. It needs
`LD_LIBRARY_PATH` set to **that dir plus `/opt/rocm/lib`**. Without it,
`--list-devices` prints nothing and the build looks broken when it is fine.

**Partial results preserved**: `/mnt/raid0/llm/tmp/ngramshapes_partial.txt` —
16 of 30 cells (the full and half blocks). The quarter block was **deliberately
abandoned** because that shape is retired. This is not an incomplete run to
resume; it is complete for the shapes that still exist.

### 1.5 Breaking tests — must land in the SAME commit

An A/B against a clean `git archive HEAD` measured **30 net-new failures across
14 files**.

Two of them are in `PROMOTION_GATE_TARGETS` (`scripts/registry/stack_change_pipeline.py:67`),
both in `tests/unit/test_build_server_command_helpers.py`, and **they gate the
launch itself** — the stack will not start until they pass.

One of those two is worth understanding before you "fix" it:

- `tests/unit/test_build_server_command_helpers.py:1031`
  `test_worker_general_numa_policy_is_full_instance_only` asserts
  `"numactl" not in quarter_prefix`. **It encodes the defect as a requirement.**
  Left in place it would have blocked the fix in CI. Do not repair it — retire it.
- Its replacement **already exists**:
  `tests/unit/test_orchestrator_stack_threads.py:159`
  `test_straddling_cpusets_declare_a_numa_policy`, currently marked
  `xfail(strict=True)` and now **XPASSing**. That is the marker working exactly as
  designed. **Delete the marker, keep the test.**

---

## 2. Prioritized task list

### P0 — unblocks the commit (3 tasks)

- [ ] **P0-1. Fix the 30 net-new breaking tests across 14 files**, including the
      two in `PROMOTION_GATE_TARGETS` (both in
      `tests/unit/test_build_server_command_helpers.py`). Retire
      `test_worker_general_numa_policy_is_full_instance_only` rather than
      repairing it — it asserts the defect (§1.5). Re-derive the exact 30 with an
      A/B against a clean `git archive HEAD` if the list has drifted.
- [ ] **P0-2. Remove the now-XPASSing `xfail(strict=True)` marker** on
      `tests/unit/test_orchestrator_stack_threads.py::test_straddling_cpusets_declare_a_numa_policy`.
      Keep the test; it is the replacement assertion for the one retired in P0-1.
- [ ] **P0-3. Cold-start the stack, re-bench the contention matrix, commit + push
      all three repos.** Strictly ordered; each step has a resume check so a crash
      mid-sequence is recoverable:
      1. **Cold-start** — `orchestrator_stack.py` (never a bespoke launcher).
         Gated on P0-1/P0-2 being green and on `region-lock status` showing the
         measurement regions **free**. *Resume check: is the stack up and does
         live == config?*
      2. **Re-bench** — `uv run python scripts/server/contention_matrix.py run`
         (writes `orchestration/contention_matrix.yaml`). *Resume check:
         `contention_matrix.py validate` reports fresh against live topology hash
         `bc28e15d`.*
      3. **Commit + push** — `epyc-orchestrator`, `epyc-inference-research`, and
         this repo. **Pathspec-limited commits only** (`git commit -- <paths>`),
         `git fetch` + `git log @{u}..main` first. *Resume check: `git status`
         shows the §1.1 files clean in both repos.*

### P1 — correctness gaps found by three parallel hygiene audits (10 tasks)

Sources — cite these, they contain the full reasoning:
`/mnt/raid0/llm/tmp/hygiene_scheduling.md` ·
`/mnt/raid0/llm/tmp/hygiene_autopilot.md` ·
`/mnt/raid0/llm/tmp/hygiene_config_tests.md`

All ten are **zero-inference** and can be worked while the measurement runs hold
the machine.

- [ ] **P1-1. Generalise the `placement_policy` enum vocabulary — it is
      quarter-shaped.** `src/scheduling/placement_policy.py:35` declares
      `BURST_PREFER_QUARTERS`, and `SOLO_PREFER_FULL`'s docstring says concurrent
      requests "spill to NUMA-disjoint quarters". On a machine with no quarters
      both options mean the same non-existent thing. Rename to shape-agnostic
      (`BURST_PREFER_SPLIT`) with an **alias map** for the existing
      `"burst_prefer_quarters"` strings already sitting in configs. **Note while
      you are in there:** `_coerce` returns `None` on an unknown string and the
      caller substitutes `DEFAULT_PLACEMENT_POLICY` — so a typo silently degrades
      to a **different policy** rather than erroring. Fix that too, or the alias
      map hides its own failures.
- [ ] **P1-2. `affinity_preflight` self-disarms.**
      `scripts/server/affinity_preflight.py:195` reads
      `required = no_mmap and len(expected_nodes) == 1`, so **every full and every
      half is exempt** — the gate that would *prove this cutover landed* passes
      vacuously. **Operator has chosen HARD-FAIL.** Blocked on ratifying
      `INTERLEAVE_TOLERANCE` (P2-3 item B.2), because a multi-node check needs a
      tolerance to check against.
- [ ] **P1-3. SUPERSEDE the `dual-half-negative` seed strategy.**
      `scripts/autopilot/operator_seed_strategies.yaml:353` — `confidence: high`,
      operator-seeded, no TTL, insight "quarters remain the granularity". It
      **forbids the topology we just deployed**. It is a *learned prior*:
      **supersede it, never edit it in place.**
- [ ] **P1-4. `stack_templates/default.yaml` is a 4th hand-maintained copy of the
      topology.** Its parity gate already fails 7 ways. Either derive it from the
      single source or delete it — a fourth copy is how the drift started.
- [ ] **P1-5. `src/registry/registry_validator.py` never cross-checks
      `numa_ports` against `NUMA_CONFIG`.** This is **the missing guard that
      allowed months of drift**. Add it; it is the cheapest permanent fix in this
      list.
- [ ] **P1-6. `scripts/autopilot/eval_tower.py:1155` tests
      `stack_numa_mode == "quarter"`.** A half fleet never matches, so eval
      fan-out **silently collapses to 1**. Silent, not loud — no error is emitted.
- [ ] **P1-7. `vision_escalation` has a PHANTOM 5-port fleet.** Ports
      `8187/8287/8387/8487` **never existed** and are declared in
      `src/config/models.py` (see the comment at `:273`) and
      `stack_templates/default.yaml:145-148`.
- [ ] **P1-8. Land `region_lock_wait_s_by_holder` telemetry BEFORE exposing any
      routing knob to autopilot.** A lever autopilot can move but cannot score is
      exactly how `dual-half-negative` (P1-3) got mislearned. This ordering is the
      point of the task.
- [ ] **P1-9. Delete-candidate: `scripts/server/quarter_scheduler.py`** — 403
      lines, **zero runtime importers**, and now factually wrong about the
      machine. Confirm the two test-only references
      (`tests/unit/test_dynamic_stack.py:177`,
      `tests/unit/test_stack_templates_v2.py:234`) and delete.
- [ ] **P1-10. Add a pre-commit check for `REQUIRED_SOURCE_ARTIFACTS` staleness.**
      `scripts/validate/stack_change_guard.py:40` — a commit touching any of those
      files **silently blocks `orchestrator_stack.py start`** until the priors are
      recompiled, with no warning at commit time. **Two occurrences today from two
      different sessions**; that is a recurrence rate, not an anecdote.

### P2 — measurement debt (5 tasks)

- [ ] **P2-1. Re-run 27 of 31 E5 Stage-B cells under `P-BENCH-PLACEMENT-1`.**
      4 are salvageable. Owning suspension banner:
      [`batched-decode-measurement.md`](batched-decode-measurement.md).
- [ ] **P2-2. Establish production anchors for the three roles that have none.**
      Only `frontdoor` has one — **median 35.7 tok/s, n=154**, derived from
      AutoPilot production traffic, *a path independent of the thing under test*,
      which is what makes it valid. `worker_general`, `architect_general` and
      `ingest_long_context` have no anchor, so
      `P-BENCH-PLACEMENT-1`'s **mandatory anchor gate has nothing to gate
      against**. Derive them the same way — not from a bench invocation.
- [ ] **P2-3. Ratify the 14 TBDs in
      [`../../artifacts/operator/ratification_queue_20260730.md`](../../artifacts/operator/ratification_queue_20260730.md).**
      **A gate whose threshold is unset cannot fail.** Human-amendment-only —
      prepare, present, park; never self-apply. P1-2 is blocked on item B.2
      (`INTERLEAVE_TOLERANCE`).
- [ ] **P2-4. Add a CONTEXT-DEPTH field to the claim grammar.** Same model, same
      recipe, same placement spans **40.22 tok/s at a 28-token prompt down to
      17.23 at 35k** — a 2.3× spread driven purely by depth — and **the ratified
      exemplar carries the 28-token figure with no depth term**. Proposal is
      drafted in §A of the ratification queue.
- [ ] **P2-5. Fold the ngram result into the production recipe once the sweeps
      land.** Measured CPU gain: **2.80× on Qwen3.6-35B at 14k tokens**
      (acceptance `.505 → .755`) and **+15% on Qwen3-Next-80B, which currently has
      NO speculation at all**. gemma and the 122B gained nothing — do not apply it
      there. The tuning surface is **ONE field per role**:
      `acceleration.spec_type` in the master registry, plus a recompile.

**Counts: P0 = 3 · P1 = 10 · P2 = 5 · total 18.**

---

## 3. Dependency graph

```
                 ┌─ P0-1 fix 30 breaking tests (2 in PROMOTION_GATE_TARGETS)
                 │
  tests green ───┤                                  ← stack start is GATED on these
                 └─ P0-2 drop the XPASSing xfail marker
                         │
                         ▼
              in-flight runs finish (region-lock status: q0/q1/q3 free)
                         │
                         ▼
              P0-3.1  cold-start the stack           ← requires a live stack
                         │
                         ▼
              P0-3.2  re-bench the contention matrix ← RUNS INFERENCE; only path
                         │                             to topology_hash bc28e15d
                         ▼
              P0-3.3  commit + push all three repos  ← pre-commit hook now passes


  GPU ngram sweep (q3) ──┐
                         ├──► full_last.sh (all four regions, 122B only)
  halfa_rest.sh (q0+q1) ─┘            │
                                      ▼
                          P2-5 fold ngram → acceleration.spec_type
                                      │
                                      ▼
                          SECOND registry recompile + a second contention
                          re-bench, because spec_type changes the launch
                          command and therefore the topology-adjacent priors


  P2-3 ratify INTERLEAVE_TOLERANCE (queue item B.2) ──► P1-2 arm the
                                                        affinity_preflight
                                                        hard-fail

  P1-8 region_lock_wait_s_by_holder telemetry ──► ANY autopilot routing knob
                                                  (incl. P1-1's generalised
                                                   placement_policy surface)
```

**Two hard sequencing facts a fresh agent must not reorder:**

1. **Tests before stack start.** Not stylistic — `orchestrator_stack.py start`
   runs the promotion gate, and two of the failures are in it.
2. **The ngram recipe change (P2-5) forces a SECOND recompile + contention
   re-bench.** If you land it in the same window, sequence it *after* P0-3 so the
   cutover commit is not entangled with a recipe change.

---

## 4. Cross-cutting concerns

- **Shared working tree.** `/workspace/repos/<name>` and `/mnt/raid0/llm/<name>`
  are the same physical clone. Other sessions are staging into the same index
  right now (visible in `git status`: repl-memory, autopilot, trace, eval
  artifacts). **Never `git add -A`. Always `git commit -- <explicit paths>`.**
  Subagents must never switch branch here.
- **Four copies of the topology.** `stack_numa.py`, the master registry, the lean
  registry, and `stack_templates/default.yaml` (P1-4). Any change to one that
  misses the others reproduces the drift this cutover exists to fix. P1-5 adds
  the guard that would have caught it.
- **Trust-boundary writes are human-only.** `MEASUREMENT.md` and
  `measurement/protocols/` are human-amendment-only. P2-3 and P2-4 are
  *prepare-and-park*, never self-apply.
- **A learned prior is evidence, not config.** P1-3's `dual-half-negative` must be
  **superseded with a dated successor**, not edited. Editing it destroys the
  record of what autopilot believed and why.
- **Silent failure is the theme of this whole handoff.** The disarmed preflight
  (P1-2), the vacuous eval fan-out (P1-6), the missing registry cross-check
  (P1-5), the unset thresholds (P2-3), the `_coerce` policy degradation (P1-1),
  and the no-warning priors staleness (P1-10) are all the *same defect class*: a
  check that cannot fail. Fixing any one of them without the others leaves the
  class intact.
- **Region discipline.** Half A is GPU-disjoint; half B contains q3 which the GPU
  lane holds. Schedule CPU work on half A while the GPU lane is live.
- **Reload ownership.** The session that owns the inference executes any reload,
  at a moment it chooses. Do not force a reload on another session's workflow —
  including the API-only case.
- **No inference from a subagent.** Subagents do zero process management. The
  cold-start and the re-bench are main-session actions.

---

## 5. Key file locations

**The cutover itself** (`repos/epyc-orchestrator`):

| Path | Role |
|---|---|
| `scripts/server/stack_numa.py` | `NUMA_CONFIG` — the topology; import-time invariants |
| `orchestration/model_registry.yaml` | lean registry (compiled) |
| `orchestration/derived/stack_priors.yaml` | generated priors |
| `orchestration/model_descriptors.yaml` · `src/registry/model_descriptors.py` | descriptors |
| `docs/generated/current_stack_summary.md` | generated summary |
| `src/config/models.py` · `src/fleet.py` | port/fleet declarations |

**The blocker**:

| Path | Role |
|---|---|
| `.git/hooks/pre-commit` | invokes the freshness check |
| `scripts/validate/check_contention_matrix_fresh.py:89` | emits the `FAIL: contention matrix is STALE` message |
| `orchestration/contention_matrix.yaml` | records `topology_hash: "8c8cfcbb13d2611d"`; live is `bc28e15d` |
| `scripts/server/contention_matrix.py` | `run` / `validate` subcommands; **`run` needs a live stack and runs inference** |

**Tests**:

| Path | Role |
|---|---|
| `scripts/registry/stack_change_pipeline.py:67` | `PROMOTION_GATE_TARGETS` |
| `tests/unit/test_build_server_command_helpers.py:1031` | `test_worker_general_numa_policy_is_full_instance_only` — **retire, do not repair** |
| `tests/unit/test_orchestrator_stack_threads.py:159` | `test_straddling_cpusets_declare_a_numa_policy` — **drop the `xfail(strict=True)`, keep the test** |

**P1 targets**:

| Path | Task |
|---|---|
| `src/scheduling/placement_policy.py:35` (+ `_coerce`) | P1-1 |
| `scripts/server/affinity_preflight.py:195` | P1-2 |
| `scripts/autopilot/operator_seed_strategies.yaml:353` | P1-3 |
| `stack_templates/default.yaml` (`:145-148` phantom ports) | P1-4, P1-7 |
| `src/registry/registry_validator.py` | P1-5 |
| `scripts/autopilot/eval_tower.py:1155` | P1-6 |
| `src/config/models.py:273` | P1-7 |
| `scripts/server/quarter_scheduler.py` (403 lines, 0 runtime importers) | P1-9 |
| `scripts/validate/stack_change_guard.py:40` `REQUIRED_SOURCE_ARTIFACTS` | P1-10 |
| `scripts/autopilot/config_applicator.py` `placement_policy_knobs` | P1-1/P1-8 knob surface |

**Research repo** (`repos/epyc-inference-research`):
`orchestration/model_registry.yaml` (**master** — `no_mmap`, `numa_ports`) ·
`docs/guides/benchmarking-guide.md` · `docs/guides/model-sizing.md`

**Evidence + audits** (scratch — copy anything load-bearing into the repo before
relying on it long-term):

| Path | Contents |
|---|---|
| `/mnt/raid0/llm/tmp/hygiene_scheduling.md` | scheduling/placement audit → P1-1, P1-6, P1-8, P1-9 |
| `/mnt/raid0/llm/tmp/hygiene_autopilot.md` | autopilot audit → P1-3, P1-8 |
| `/mnt/raid0/llm/tmp/hygiene_config_tests.md` | config/test audit → P1-4, P1-5, P1-7, P1-10 |
| `/workspace/artifacts/operator/ratification_queue_20260730.md` | the 14 TBDs → P2-3, P2-4 |
| `/mnt/raid0/llm/tmp/gpungram_results.txt` · `gpungram_run.sh` | GPU ngram sweep (q3) |
| `/mnt/raid0/llm/tmp/halfa_live_results.txt` | CPU half-A arms (q0+q1) |
| `/mnt/raid0/llm/tmp/cpu_chain.sh` → `halfa_rest.sh` → `full_last.sh` | chained CPU runs |
| `/mnt/raid0/llm/tmp/ngramshapes_partial.txt` | 16/30 cells; quarter block deliberately abandoned |
| `/mnt/raid0/llm/llama.cpp-experimental/build-v8-hip/bin/` | v8 HIP build — needs `LD_LIBRARY_PATH` = this dir **+** `/opt/rocm/lib` |

**Entry points**:
`repos/epyc-orchestrator/scripts/region-lock status` ·
`scripts/server/orchestrator_stack.py` ·
`scripts/server/contention_matrix.py {run,validate}` ·
`scripts/registry/stack_change_pipeline.py check --run-promotion-gate`

---

## 6. Reporting instructions

1. **Flip the checkbox in §2 the moment a task lands** — append `✅ YYYY-MM-DD`
   inline. The handoff dashboard counts checkbox state only; prose status is
   invisible to it. Work discovered mid-flight gets its own `- [ ]` line (or
   `- [x] … ✅ date` if already done).
2. **On P0-3 completion**: record the three commit SHAs (orchestrator, research,
   root) and the new `topology_hash` here, delete row **N25** from
   [`master-handoff-index.md`](master-handoff-index.md), and append to
   `progress/2026-07/2026-07-30.md`.
3. **Numbers use the claim grammar** — `(metric, protocol-id, n/reps, date,
   attestation ref)`. Until P2-4 lands, **also state the prompt depth in prose**;
   a bare decode rate is under-specified by up to 2.3×.
4. **Anything that changes a threshold, protocol, or learned prior** is
   prepare-and-park: write the exact patch, present it, do not apply it.
5. **Cross-reference, do not duplicate.** Diagnosis findings belong in
   [`numa-placement-defect-20260730.md`](numa-placement-defect-20260730.md) (N24),
   E5 re-run accounting in
   [`batched-decode-measurement.md`](batched-decode-measurement.md). This document
   holds only the *resume state* of the cutover.
6. **When P0 is fully green, this handoff's reason to exist is gone.** Move the
   surviving P1/P2 rows to their owning handoffs and archive this to
   `handoffs/completed/`. A resume document that outlives its blocker becomes
   stale documentation.

### P1-11 — the contention matrix cannot see the GPU lane (filed 2026-07-30)

- [ ] **Make the GPU shadow lane a participant in `contention_matrix.yaml`.** Its
  current participants are six CPU roles only; the lane is not a row. Measured
  footprint: the lane pins host threads to logical `184-191`, which fold to
  PHYSICAL cores 88-95 = region **q3**. So `full` (`0-95`) and `half B`
  (`48-95,144-191`) are physical co-tenants of the lane and `half A`
  (`0-47,96-143`) is not. Under a bandwidth-generating lane proxy the full
  instance lost **34%** while half A lost nothing. Half B has NEVER been measured
  against the lane — which is why every half measurement in this campaign was
  deliberately taken on half A.
- [ ] **Do not mechanically exclude `full` / `half B` pairs.** Their CPU-vs-CPU
  verdict is structural (cpuset intersection), but their lane contention is not,
  and a BLOCK verdict reached for CPU reasons would leave the lane channel
  permanently unmeasured. This is the dangerous direction of the error.
- [ ] **The tool simultaneously over- and under-measures.** 5 of the 15 pairs in
  the committed matrix are structurally overlapping and tagged
  `overlap_measured` — live inference spent re-deriving set intersection. Under
  the new topology 58 of 78 pairs are structurally blocked. Both halves of this
  are one root cause: the model is cpuset-intersection-only, so it cannot skip
  what is derivable nor represent what is not.
  Do NOT fix inline during the cutover — changing a safety gate's semantics
  mid-migration should be a reviewed change.


---

## UPDATE 2026-07-30 evening — ngram RETRACTED; artifact rebuilt; vision measured

### The ngram finding is withdrawn (this supersedes every ngram row above)

`--spec-type ngram-mod` buys **nothing**. The "2.80× at depth" result committed
earlier today was a harness artifact.

**Mechanism.** Each cell launched ONE server and sent the SAME prompt r times at
`temperature=0.3, seed=42`. Run 1 generates answer X; the server retains X in the
slot KV. Run 2 sends the identical prompt, hits the prompt cache
(`prompt eval = 4 tokens`), and `ngram-mod` — which drafts by matching text already
in context — copies its own previous answer verbatim. Mean accepted draft length
3.58 → 15.88; acceptance → 1.000.

**The control was already in the data.** Sorting all 68 cell logs by run2÷run1:
every cell inflated >1.15× is an ngram arm; all 25 `draft-mtp`-only and `none`
cells are flat at 0.92–1.08×. `draft-mtp` drafts from weights, so a warm context
cannot help it.

**Corrected (run 1 only), 16 model × depth × device cells: gain spans −17.4 % to
+2.7 %, centred on zero.** 35B CPU: 24.85 vs 24.86. `ngram-mod` alone is far worse
than MTP everywhere (122B CPU: 9.38 vs 15.76).

- [x] Retraction committed to research `84067a6e` (raw logs left unedited) ✅ 2026-07-30
- [x] Memory `feedback_ngram_fills_weak_drafter_headroom` rewritten as a retraction ✅ 2026-07-30
- [x] Artifact rebuilt on corrected numbers ✅ 2026-07-30
- [ ] **Cancel the queued `acceleration.spec_type` per-role field.** It was queued
  off the retracted finding. Nothing justifies enabling ngram on any role.
- [ ] Re-scope NG1–NG5 in `speculative-decoding-mtp-refresh.md` — they were filed
  against the retracted result.
- [ ] Fold the four P-BENCH-PLACEMENT-1 amendments (no repeated-prompt replication
  for context-reading drafters; mandatory non-context control arm; report n/min/max
  never a bare median; `accept=1.000` is a bug report) into MEASUREMENT.md proper.

### Confirmatory re-run IN FLIGHT

`/mnt/raid0/llm/tmp/ngramfix.sh` → `ngramfix_results.txt`, under a q0–q3 lock.
3 DISTINCT prompts per rep (disjoint corpus slices, `mkdistinct.py`), per-rep
values printed, `draft-mtp` control in every group. 12 cells: 35B CPU full + 27B
GPU × d8k/d16k × 3 arms. **If a cell still climbs monotonically rep0→rep2, the
harness fix failed and that cell is void** — the script flags this inline.

### Vision pair measured — the last unbenchmarked stack model

Qwen2.5-VL-7B-Instruct Q4_K_M, node1, 24t, `membind=1`. Same GGUF serves
`worker_vision` and `vision_escalation`, so this characterises both.

| depth | spec=none | spec=ngram-mod |
|---|---|---|
| 3.5k | 7.31 (min 7.20 max 7.47) | 9.18 — **artifact**, min 7.42 = the none arm |
| 14.1k | 5.36 (min 5.32 max 5.41) | 6.29 — **artifact**, min 5.29 |
| 27.6k | 4.03 (n=3, consistent) | not run |

- [ ] **NEW FINDING — VL-7B cannot serve deep context on a quarter.** Prefill on 24
  threads runs at ~27.5 tok/s, so a 27.6k prompt needs ~14 min and the first rep
  blew a 900 s client timeout. `g32k` was abandoned as guaranteed-void rather than
  burn an hour. If either vision role is expected to take long-context work, it
  needs more cores or GPU residency — this is a real capacity limit, not a bench
  artifact.
- [ ] **Harness parser bug:** depth is read from the FIRST `prompt eval time` line.
  When rep 1 times out before logging one, a later cache-warm incremental count is
  reported instead (observed: `prompt=2926` where true resident context was
  27,586, per `stop processing: n_tokens`). Read depth from `n_tokens` instead.

### Test progress — 6 of 35 topology failures closed

Both fixed guards had the defect as their passing condition, so the correction
necessarily failed them; replaced, not adjusted. **Uncommitted** — the pre-commit
gate blocks ALL commits to this repo, including test-only ones, until the
contention matrix is refreshed.

- [x] `test_placement_policy` — split ABSENT (→default) from UNRECOGNISED (→raises) ✅ 2026-07-30
- [x] `test_stack_numa` — frontdoor[0] asserts `NUMA_FULL` + `interleave=all`, not
  the NPS2-era `NUMA_NODE0`; policy-less-prefix test rebuilt on a fixture; added
  `test_every_live_role_declares_a_memory_policy` ✅ 2026-07-30
- [ ] Remaining 29: `test_gate_seam_wiring` (9), `test_scheduling_contention_gate`
  (5), `test_stack_priors_compiler` (4), `test_scheduling_contention` (3),
  `test_stack_templates_v2` (3), `test_quarter_stack_smoke` (3),
  `test_gpu_shadow_lane_p2` (1), `test_model_descriptors_schema` (1).
  Most funnel into the contention matrix or into quarter-shaped fixtures.
- [ ] `NUMA_NODE0` / `NUMA_Q0A` are now referenced **only by tests and comments** —
  no production path reads them. Deletion candidates once fixtures stop naming them.

### Operational lesson — do not re-arm a chain you have not positively identified

I concluded `full_last` was dead from `pgrep -af "full_last|region_lock"` and
re-armed it. It was alive: `cpu_chain.sh` was sitting in a `bash until … sleep 30`
loop whose command line contains neither pattern. Both then ran; they serialized
correctly on the region lock so nothing was poisoned, but full_last executed twice
(~15 min wasted) and the second pass **truncated `full_last_results.txt`** via its
`: > "$OUT"`. Recovered only because the file had been copied to
`/mnt/raid0/llm/tmp/preserved/` beforehand.

- [ ] Before re-arming any chained job, enumerate waiters by their **script name**
  (`pgrep -f cpu_chain.sh`), not by the tag of the job they will eventually launch.
- [ ] Bench harnesses should append or write to a run-stamped file, never truncate
  a shared results path at startup.
