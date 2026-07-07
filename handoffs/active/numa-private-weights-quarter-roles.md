# NUMA Private Node-Local Weights for Shared-mmap Quarter Roles

**Status**: Launcher argv plumbing fixed/tested for generic + vision builders (2026-06-26 follow-up). `vision_escalation`, `frontdoor`, and `ingest_long_context` A/Bs were run 2026-06-27 and **refuted** the private-copy flip for all three measured shared-mmap quarter roles. Leave `vision_escalation.no_mmap=false`, `frontdoor.no_mmap=false`, and `ingest_long_context.no_mmap=false`; no production config flip is supported by the current v6+iqk evidence.
**Created**: 2026-06-26
**Owner**: unclaimed — dedicated future session (high-ROI, low-effort, NPS4-gated and we are on NPS4)
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md)
**Cross-refs**: [`numa-page-cache-prewarm.md`](../completed/numa-page-cache-prewarm.md) (the `[1.5]` interleave prewarm this supersedes for quarter roles), [`single-instance-system-tuning.md`](../completed/single-instance-system-tuning.md) §Phase 4 (the unimplemented weight-replication estimate), [`orchestrator-nps4-48x4-notes.md`](orchestrator-nps4-48x4-notes.md) (mmap/mbind dedupe open question).
**Source finding**: `/mnt/raid0/llm/tmp/orchestrator_numa_finding.md` (2026-06-26).

> **Measurement discipline**: every t/s in this file is an **observation** (no protocol-id / attestation), usable to motivate the work and size the prize, never to gate the production flip. The flip is gated on the Arm A vs Arm B A/B in the Validation Plan, run via the codified recipe under operator approval per `/workspace/MEASUREMENT.md`.

---

## Objective

Test whether the shared-mmap quarter-able roles — `frontdoor` (Qwen3.6-35B-A3B Q8), `ingest_long_context` (Qwen3-Next-80B Q4), and formerly `vision_escalation` (Qwen3-VL-30B Q4) — should use **private, node-local weight copies** (`--no-mmap`, one private RAM copy per quarter instance) instead of the current single shared interleaved mmap copy that every quarter reads 75% cross-node.

`worker_general` (gemma-26B Q4 MTP) emits `--no-mmap` from its dedicated builder, but the 2026-06-27 live `numa_maps` strict preflight showed the quarter processes were still memory-interleaved because a role-level `interleave=all` policy wrapped every instance. Orchestrator `5573e465` scopes that interleave policy to the full worker instance only; the live quarter PIDs remain stale until a controlled worker restart plus strict `affinity_preflight.py --require-memory-locality` proves node-local anonymous pages. The production question for the remaining shared-mmap quarter roles is now closed negative under the measured v6+iqk protocol: `vision_escalation`, `frontdoor`, and `ingest_long_context` should stay shared-mmap unless a future protocol materially differs.

**2026-07-06 addendum**: the controlled `worker_general` quarter restart / strict
`affinity_preflight.py --require-memory-locality` verification passed, so the
N12 observability tail is now closed negative for the current protocol. The
live quarter placement proof is in
`/mnt/raid0/llm/tmp/affinity_preflight_worker_general_after_q2_reload_20260706T134655Z.json`.
No production config flip follows; revisit only if a materially different
protocol reopens the question.

**2026-07-06 live re-check**: a later broad `affinity_preflight.py --roles
frontdoor ingest_long_context vision_escalation worker_general worker_vision
architect_general` pass also came back clean on the checked live placements.
`worker_general` quarters remained fully local (`live_memory_placement_verified=true`,
`required=4`, `mismatches=0`), while the shared-mmap quarter roles stayed on
their expected interleaved placement. The run wrote
`/mnt/raid0/llm/tmp/affinity_preflight_live_20260706T184407Z.json` and
did not reveal a new N12 flip opportunity.

- [x] 2026-07-06 live re-check completed: broad `affinity_preflight.py`
  confirmed the checked live roles still match the expected placement model and
  did not uncover a new N12 flip path. ✅ 2026-07-06

---

## 2026-06-26 ACTIVATION ATTEMPT (v6+iqk cutover) — launch-path blockers, REVERTED

Tried to activate N12 by setting `no_mmap: true` on the frontdoor/ingest/vision (+ coder/worker_summarize alias) registry blocks + recompiling. The compiler side works (`_role_no_mmap_prior` in `stack_priors.py` reads it; the generic `_build_role_command` emits `--no-mmap`). But three **launcher-level** blockers surfaced — N12 is NOT a config flip:

1. **`no_mmap` lands on the FULL instance, not the NUMA quarters.** After the flip, `--no-mmap` applied to the consolidated **full** instance (frontdoor `:8070`, ingest `:8085`) while the **quarter** instances (`:8080/:8180/:8280/:8380`, `:8185/:8285/:8385/:8485`) stayed shared-mmap. The N12 win IS the quarters being private node-local, so the launcher must emit `--no-mmap` per-quarter-instance (the worker already does — its dedicated builder hardwires it per instance).
2. **The vision launch path emits no `--no-mmap` at all.** `vision_escalation` (`:8087` + quarters, launched via the vision/`--mmproj` builder) reloaded with a fresh PID but stayed shared-mmap — the vision command builder ignores the `no_mmap` prior. Needs wiring (and `mmproj` is itself a shared-mmap file to weigh).
3. **`reload <role>` only restarts the FULL instance, not the quarters.** Use `stop --only` + `start --only` to cycle all instances. Also: alias roles (coder_escalation, worker_summarize) must carry `no_mmap` matching their host process or `runtime_attestation` flags them.

Reverted to a clean state (all three back to shared-mmap, `runtime_attestation: ok`). **Remaining (dedicated session):** (a) make the generic + vision launchers apply `--no-mmap` to the QUARTER instances; (b) RAM is verified to fit (~+303 GB private → ~626 GB of the ~701 GB mlock budget, ~500 GB free at activation, actual-used basis not RSS); (c) per-role `/proc/<pid>/numa_maps` placement gate + the operator's clean-window Arm A vs Arm B A/B (throughput is throttle-caveated until the post-reboot window).

## 2026-06-26 FOLLOW-UP — launcher plumbing fixed, no production flip

Commit pending in `epyc-orchestrator` wires the missing inert launcher path:

- `_build_role_command` already honors `runtime.cache.no_mmap` for generic registry-backed roles, with default `False`.
- `_build_vision_command` now also honors `runtime.cache.no_mmap` for both `vision_escalation` and `worker_vision`, with default `False`.
- Tests now cover the vision prior-to-argv behavior, and reload-attestation fixtures were aligned to the current v6 grammar (`--spec-type draft-mtp`, `--spec-draft-n-max`).

Validation: `.venv/bin/pytest tests/unit/test_build_server_command_helpers.py tests/unit/test_orchestrator_stack_threads.py tests/unit/test_orchestrator_stack_reload.py -q` -> **77 passed**.

No role has been flipped to `no_mmap: true` by this follow-up. The next actionable gate is still the per-role operator Arm A vs Arm B A/B plus live memory-placement verification for any role not yet measured. Use `stop --only` + `start --only` rather than `reload <role>` if cycling all quarter instances.

## 2026-06-27 VISION A/B — negative, do not flip `vision_escalation`

Temporary isolated A/B runner: `/mnt/raid0/llm/tmp/n12_vision_ab.py`; output: `/mnt/raid0/llm/tmp/n12_vision_ab/summary.json`.

Protocol:

- Arm A `shared_mmap`: interleave-prewarm model + mmproj, launch 4 temporary `vision_escalation` quarter servers on ports `19087-19090` with `taskset`, mmap, `--mlock`, `-t 48`, `-np 1`.
- Arm B `private_no_mmap`: launch 4 temporary servers on ports `19187-19190` with `numactl --cpunodebind=N --membind=N`, `taskset`, `--no-mmap`, `--mlock`, `-t 48`, `-np 1`.
- Both arms used the same v6 binary, Qwen3-VL-30B-A3B Q4 GGUF, mmproj, `qwen3vlmoe.expert_used_count=int:4`, fixed prompt, `n_predict=192`, three measured reps.
- Teardown verified after the run: no `19087-19090` / `19187-19190` listeners and all temporary PIDs gone; production `/health` remained green.

Result:

| Role | Arm A shared-mmap median aggregate | Arm B private `--no-mmap` median aggregate | Decision |
|------|------:|------:|------|
| `vision_escalation` | **99.076 t/s** | **65.760 t/s** | **Do not flip** |

Placement check:

- Arm A confirmed interleaved file mapping: each model mapping had roughly equal `N0/N1/N2/N3` pages.
- Arm B confirmed node-local private placement at process-total level: each temporary process had ~5.22M pages on its bound node and near-zero pages elsewhere; file-backed model mapping is absent because `--no-mmap` loads anonymous private pages.

Interpretation: for Qwen3-VL-30B-A3B under this quarter-concurrent protocol, shared interleaved mmap is materially faster than private node-local copies despite the remote-read intuition. Leave `vision_escalation.no_mmap=false`; do not spend a production quiet window flipping this role. Frontdoor and ingest still need their own measurements; do not generalize the vision negative to those models.

## 2026-06-27 FRONTDOOR A/B — negative, do not flip `frontdoor`

Temporary isolated A/B runners:

- Arm A: `/mnt/raid0/llm/tmp/n12_frontdoor_arm_a.py`; output `/mnt/raid0/llm/tmp/n12_frontdoor_arm_a/summary.json`.
- Arm B: `/mnt/raid0/llm/tmp/n12_frontdoor_arm_b.py`; output `/mnt/raid0/llm/tmp/n12_frontdoor_arm_b/summary.json`.

Protocol:

- Arm A `shared_mmap`: interleave-prewarm Qwen3.6-35B-A3B MTP Q8, launch 4 temporary `frontdoor` quarter servers on ports `19280-19283` with `taskset`, mmap, `--mlock`, `-t 48`, `-np 1`, `--spec-type draft-mtp`, and `--spec-draft-n-max 4`.
- Arm B `private_no_mmap`: launch 4 temporary servers on ports `19380-19383` with `numactl --cpunodebind=N --membind=N`, `taskset`, `--no-mmap`, `--mlock`, the same MTP settings, `-t 48`, and `-np 1`.
- Both arms used the same v6 binary, `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf`, fixed prompt, `n_predict=192`, three measured reps.
- Teardown verified after the run: no `19280-19283` / `19380-19383` listeners and all temporary PIDs gone; production `/health` remained green.

Result:

| Role | Arm A shared-mmap median aggregate | Arm B private `--no-mmap` median aggregate | Decision |
|------|------:|------:|------|
| `frontdoor` | **56.203 t/s** | **42.428 t/s** | **Do not flip** |

Placement check:

- Arm A confirmed interleaved file mapping: each model mapping had roughly equal `N0/N1/N2/N3` pages.
- Arm B confirmed node-local private placement at process-total level: each temporary process had ~18.81M pages on its bound node and near-zero pages elsewhere.

Interpretation: for Qwen3.6-35B-A3B MTP Q8 under this quarter-concurrent protocol, private node-local copies are about **24.5% slower** than shared interleaved mmap. Leave `frontdoor.no_mmap=false`; because `coder_escalation` and `worker_summarize` share the frontdoor process/model, do not flip those aliases independently for this topology.

## 2026-06-27 INGEST A/B — negative, do not flip `ingest_long_context`

Temporary isolated A/B runner: `/mnt/raid0/llm/tmp/n12_ingest_ab.py`; outputs:

- Arm A: `/mnt/raid0/llm/tmp/n12_ingest_ab/shared_summary.json`.
- Arm B: `/mnt/raid0/llm/tmp/n12_ingest_ab/private_summary.json`.
- Combined summary: `/mnt/raid0/llm/tmp/n12_ingest_ab/summary.json`.

Protocol:

- Arm A `shared_mmap`: interleave-prewarm Qwen3-Next-80B-A3B Q4, launch 4 temporary `ingest_long_context` quarter servers on ports `19485-19488` with `taskset`, mmap, `--mlock`, `-t 48`, `-np 1`, `-c 32768`, `-ub 8192`, `--flash-attn on`, `--jinja`, `-ctk q4_0`, and `-ctv q4_0`.
- Arm B `private_no_mmap`: launch 4 temporary servers on ports `19585-19588` with `numactl --cpunodebind=N --membind=N`, `taskset`, `--no-mmap`, `--mlock`, and the same context/cache settings.
- Both arms used the same v6 binary, `/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Next-80B-A3B-Instruct-GGUF/Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf`, `qwen3next.expert_used_count=int:4`, fixed prompt, `n_predict=192`, and three measured reps.
- Teardown verified after the run: no `19485-19488` / `19585-19588` listeners and all temporary PIDs gone; production `/health` remained green.

Result:

| Role | Arm A shared-mmap median aggregate | Arm B private `--no-mmap` median aggregate | Decision |
|------|------:|------:|------|
| `ingest_long_context` | **57.528 t/s** | **41.655 t/s** | **Do not flip** |

Placement check:

- Arm A confirmed interleaved file mapping: each model mapping had roughly equal `N0/N1/N2/N3` pages.
- Arm B confirmed node-local private placement at process-total level: each temporary process had about 12.02M pages on its bound node and near-zero pages elsewhere.

Interpretation: for Qwen3-Next-80B-A3B Q4 under this quarter-concurrent protocol, private node-local copies are about **27.6% slower** than shared interleaved mmap. Leave `ingest_long_context.no_mmap=false`. This closes the initial N12 role set negative for private node-local copies except the already-private `worker_general`, where prior gemma evidence remains positive.

## Evidence (observations — motivate, do not gate)

- **gemma-26B 4×quarter, clean host, same window**: shared-interleaved mmap = **43.5 t/s** aggregate vs **`--no-mmap` private node-local = 119.5 t/s** aggregate (`numa_mtp.gemma-26B.jsonl`: quarter / 4 instances / MTP-on `agg_tps=119.46`, replicates `[119.31, 119.46, 120.49]`). **~2.7×.** This is the worker model; it already runs the fast arm in production, so the bench measures exactly the topology the other three roles are missing.
- **Qwen3.6-35B (frontdoor) direct A/B is negative**: shared-mmap median aggregate **56.203 t/s** vs private `--no-mmap` **42.428 t/s** on 2026-06-27. Do **not** flip frontdoor based on the gemma observation or the older non-equivalent suite result.
- **vision_escalation direct A/B is negative**: shared-mmap median aggregate **99.076 t/s** vs private `--no-mmap` **65.760 t/s** on 2026-06-27. Do **not** flip vision based on the gemma observation.
- **ingest_long_context direct A/B is negative**: shared-mmap median aggregate **57.528 t/s** vs private `--no-mmap` **41.655 t/s** on 2026-06-27. Do **not** flip ingest based on the gemma observation.
- **Phase-4 estimate (likely conservative for some models, false for the measured Qwen/VL set)**: `single-instance-system-tuning.md:89,207-219` estimates **+10-30%** for per-NUMA-node weight replication under NPS≥4. The gemma 2.7× suggests the prize may be real when the model fits 4× in RAM and the workload is quarter-concurrent, but the Qwen/VL negatives prove this must stay per-role.

---

## Root cause / per-role launch matrix

From the finding doc, updated after the launcher follow-up:

| Role | Model (GGUF, approx) | mmap today | Memory placement (multi-instance) |
|------|------|------|------|
| **frontdoor** | Qwen3.6-35B-A3B Q8 (~34 GB) | mmap (`no_mmap: false`) | **shared interleaved — 1 copy, 4 quarters each 75% cross-node; private-copy flip refuted 2026-06-27** |
| coder_escalation | (shares frontdoor GGUF/process) | mmap | shares frontdoor copy; follows frontdoor negative |
| **ingest_long_context** | Qwen3-Next-80B Q4 (~45 GB) | mmap (`no_mmap: false`) | **shared interleaved — multi-instance, 1 copy; private-copy flip refuted 2026-06-27** |
| **vision_escalation** | Qwen3-VL-30B Q4 (~17 GB) | mmap (`no_mmap: false`) | **shared interleaved — multi-instance, 1 copy; private-copy flip refuted 2026-06-27** |
| worker_general | gemma-26B Q4 MTP (~16 GB) | **`--no-mmap`** (`no_mmap: true`) | **private per-instance node-local — ALREADY FAST** |
| architect_general | Qwen3.5-122B Q4 (~69 GB) | mmap + `interleave=all` | interleaved, single instance (correct — too big to replicate cheaply) |
| worker_vision | Qwen2.5-VL-7B Q4 (~4 GB) | mmap | first-touch, single instance |

Three mechanisms compound the slow path:

1. **The launcher now honors `no_mmap` in both generic and vision builders.** The field is present in every role's prior (`stack_priors.yaml`: `worker_general` true; `frontdoor`, `ingest_long_context`, and `vision_escalation` still false). Before the follow-up, the vision/`--mmproj` builder ignored the prior; that gap is fixed. The remaining shared-mmap behavior is now a deliberate `no_mmap: false` configuration state, not an argv plumbing miss.
2. **No `--membind` / `--cpunodebind` anywhere.** `_numa_prefix` (`stack_numa.py:200-222`) emits a bare `taskset` (plus an optional `numactl --interleave=all` wrapper for the few canonical-recipe roles). `--membind`/`--cpunodebind` appear only in comments. So even the page placement is never pinned per node.
3. **The interleave prewarm is bandwidth, not locality.** The `[1.5] numactl --interleave=all` page-cache prewarm (`stack_prewarm.py`; [`numa-page-cache-prewarm.md`](../completed/numa-page-cache-prewarm.md)) fixed the 2026-05-28 cold-collapse (mlock first-touching the whole GGUF onto ONE node → −50-65%). It forces a clean 25%-per-node spread → full aggregate **bandwidth** but **not locality** — every quarter still reads 75% of weights off-node. Better than collapse; not the fast path.

### Codebase contradiction to resolve (do this once measured)

`stack_numa.py:13,203` asserts "taskset alone is sufficient — `numactl --membind` adds no benefit (S4)", which contradicts memory `feedback_mmap_numa_sharing` ("never bare taskset"; M2.7 saw instance-2 at 0.69 t/s under shared mmap). The finding reconciles them along the **mmap dimension**: S4 was a `--no-mmap` / single-instance test (membind redundant when each process owns its own first-touched copy); the failure mode `feedback_mmap_numa_sharing` warns about is **shared mmap across instances**, where membind/`--no-mmap` is mandatory. Both are right for their regime. Encode this reconciliation in a code comment at `stack_numa.py:203` **after** the A/B confirms it — don't pre-edit the comment on theory.

Resolved 2026-06-27 in orchestrator `c07f2de3`: `stack_numa.py` now scopes the S4 "taskset alone" finding to the no-mmap/single-owner regime and explicitly says shared-mmap quarter fleets require role-specific A/B plus live `numa_maps` proof before changing memory policy. The regenerated stack-prior source hash passed `stack_change_pipeline.py check --run-promotion-gate`.

---

## The fix (the actual deliverable)

The code-side deliverable is complete; production activation remains:

1. **Evidence**: complete the per-role operator Arm A vs Arm B A/B and record attested results per `/workspace/MEASUREMENT.md`. The initial target set is now complete and negative for `vision_escalation`, `frontdoor`, and `ingest_long_context`.
2. **Data**: do not set `no_mmap: true` for any of these three roles under current evidence. Alias roles sharing a process must continue to match their host process to avoid runtime-attestation drift.
3. **Deploy**: no deployment is supported for this N12 flip path. If a future materially different protocol reopens a role, cycle all affected instances with `stop --only` + `start --only`, not `reload <role>`, then re-run runtime attestation and a live NUMA placement check.

Optional, stronger (decide from the A/B): also add per-node `numactl --cpunodebind=N --membind=N` for `--no-mmap` quarter instances via `_numa_prefix`, to guarantee each private copy first-touches its own node rather than relying on `taskset` + first-touch. The A/B's Arm B uses explicit membind; if Arm B wins and the membind-free `--no-mmap` variant matches it, the `taskset`-only path is sufficient and simpler.

### Memory budget (fits comfortably on 1.1 TB)

Four private copies per role (replacing 1 shared copy):

| Role | 1 copy | 4× private | Headroom note |
|------|------|------|------|
| vision_escalation | ~17 GB | **~68 GB** | measured negative 2026-06-27; leave shared-mmap |
| frontdoor | ~34 GB | **~136 GB** | measured negative 2026-06-27; leave shared-mmap |
| ingest_long_context | ~45 GB | **~180 GB** | measured negative 2026-06-27; leave shared-mmap |

Total if all three flipped simultaneously would be ≈ **384 GB** of private weights, on top of `worker_general`'s existing private copies, but the measured role results do not support that flip. Keep the table as sizing context only for any future materially different protocol.

---

## Validation plan (the gate)

Operator-run / owned-bench only, `-fa 1` explicit, full OMP env stack (`OMP_PROC_BIND=spread`, `OMP_PLACES=cores`, `OMP_WAIT_POLICY=active`, `KMP_BLOCKTIME=10` for the MTP/AOCC path), one server at a time (no concurrent inference — another agent may be benching), pgrep zombie-check first, host-throttle + drop_caches/re-warm checked per `feedback_host_throttle_check` / `feedback_drop_caches_numa_eviction`.

Per role, 4×quarter, sum the per-quarter t/s:

- **Arm A — current orchestrator pattern (shared mmap, interleave prewarm, no membind)**: `numactl --interleave=all cat MODEL >/dev/null` to prewarm page cache, then 4× `taskset -c <quarter_cpus> llama-server/llama-bench -m MODEL --mlock` (mmap, no membind).
- **Arm B — private node-local**: 4× `numactl --cpunodebind=N --membind=N taskset -c <quarter_cpus> ... --no-mmap --mlock`.

Sum per-quarter decode t/s for each arm; Arm B wins is the flip signal. `frontdoor`, `vision_escalation`, and `ingest_long_context` are closed negative for this flip path.

Acceptance: flip a role's `no_mmap` to `true` in production only after its own Arm A vs Arm B A/B shows Arm B materially ahead under the codified recipe with operator sign-off; stage and re-attest one role per quiet window. Re-confirm with `affinity_preflight.py` (see Secondary) that the live placement actually changed post-flip — do not trust the topology hash alone (`feedback_verify_live_affinity_not_just_topology_hash`). Current evidence says **do not flip** `vision_escalation`, `frontdoor`, or `ingest_long_context`.

---

## Secondary work

1. ✅ **Observability gap closed 2026-06-27**: orchestrator `5aebe641` extends `affinity_preflight.py` (`scripts/server/affinity_preflight.py`) to read `/proc/<pid>/numa_maps`, report shared-mmap `.gguf` page placement, and enforce single-node private-copy locality when run with `--require-memory-locality` (default threshold `0.85`). Live strict worker check `/mnt/raid0/llm/tmp/affinity_preflight_worker_strict_numa_maps_final.json` found CPU affinity correct but all four `worker_general` quarters failing memory locality (`~0.25` local anonymous pages each), exposing the exact silent topology failure this gap was meant to catch. No production config flip follows from this; it is an observability/control finding for future private-copy gates.
2. ✅ **Comment contradiction resolved 2026-06-27**: orchestrator `c07f2de3` annotates `stack_numa.py` so "taskset is sufficient" is limited to the no-mmap/single-owner regime, not shared-mmap quarter fleets. Stack-prior hashes were regenerated and the no-inference promotion gate passed.
3. ✅ **Worker interleave scope fixed 2026-06-27**: orchestrator `5573e465` changes `worker_general` from a role-wide `numactl_policy: interleave=all` to an instance-scoped full-worker policy. Quarter `--no-mmap` instances should now launch without interleave wrapping, but the current live PIDs predate the fix; verify after `stop --only worker_general` / `start --only worker_general` with strict `affinity_preflight.py`.

---

## Key files (with line numbers)

| What | Where |
|------|------|
| Generic role builder — emits opt-in `--no-mmap` | `epyc-orchestrator/scripts/server/orchestrator_stack.py:825-912` |
| Vision builder — emits opt-in `--no-mmap` for `runtime.cache.no_mmap` | `epyc-orchestrator/scripts/server/orchestrator_stack.py:433-501` |
| Worker builder — emits `--no-mmap` for worker_general | `epyc-orchestrator/scripts/server/orchestrator_stack.py:606` |
| `_numa_prefix` — bare taskset, no membind (optional membind site) | `epyc-orchestrator/scripts/server/stack_numa.py:200-222` |
| `stack_numa.py` "taskset sufficient" claim to reconcile | `epyc-orchestrator/scripts/server/stack_numa.py:13,203` |
| Launch priors (`no_mmap` field per role) | `epyc-orchestrator/orchestration/derived/stack_priors.yaml` (worker 833 `true`; frontdoor 254/399, ingest 543, vision 997 `false`) |
| Interleave page-cache prewarm (`[1.5]`) | `epyc-orchestrator/scripts/server/stack_prewarm.py` + [`numa-page-cache-prewarm.md`](../completed/numa-page-cache-prewarm.md) |
| Phase-4 weight-replication estimate (unimplemented) | [`single-instance-system-tuning.md`](../completed/single-instance-system-tuning.md):89,207-219 |
| Affinity preflight (CPU + `numa_maps` placement; strict locality via `--require-memory-locality`) | `epyc-orchestrator/scripts/server/affinity_preflight.py` |
| Bench evidence (Arm B) | `/mnt/raid0/llm/tmp/iqk_sweep_2026-06-25/numa_mtp.gemma-26B.jsonl`, `numa_mtp.Qwen3.6-35B.jsonl` |
| Source finding | `/mnt/raid0/llm/tmp/orchestrator_numa_finding.md` |

---

## Open questions

1. Does `--no-mmap` + `--membind` actually beat the simpler `--no-mmap` + bare-`taskset` (first-touch) on these three models, or is membind redundant once mmap is off? (Determines whether `_numa_prefix` needs the membind edit or just the builder edit suffices.) — the A/B's two Arm-B variants answer this.
2. Production instance multiplicity per role: do `frontdoor` / `ingest_long_context` / `vision_escalation` actually run 4 quarters concurrently in the live stack, or fewer? The memory-budget table assumes 4× worst case; confirm from `stack_priors.yaml` instance lists so the budget and the expected gain reflect real multiplicity.
3. Is `stack_priors.yaml` under `orchestration/derived/` a generated artifact? If so, the `no_mmap: true` edit must go to its source and be regenerated (N11a SSoT pipeline), not hand-patched.
4. Interaction with `--mlock`: private `--no-mmap` copies are already locked; confirm the per-role `mlock` budget still clears with three roles flipped (stage one at a time).
5. Does flipping `ingest_long_context` (long-context, multi-instance) interact with its KV budget at the long contexts it serves? Re-check KV + weights memory together for that role.

---

## Reporting instructions

On completing any part of this work:

1. Update **this handoff** first (it is the task-level source of truth) — record the Arm A/B numbers per role with their protocol-id/attestation per `/workspace/MEASUREMENT.md`, and which roles flipped.
2. Update [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) (the owning domain row) and the master-index ladder row only if priority / gate / next-action changes; delete the master-index row on full completion.
3. If the stack behavior changes, update [`routing-and-optimization-index.md`](routing-and-optimization-index.md) and the relevant stack-change / SSoT handoff (N11a).
4. Append `progress/YYYY-MM/YYYY-MM-DD.md` with the measurement protocol, cache state, host-health state, commit IDs, and the per-role decision.
5. If the A/B falsifies the prize (Arm B not materially ahead on a role), record that as a closed negative for that role and leave its `no_mmap: false` — do not flip on the gemma observation alone.

## Changelog

- 2026-06-26 — created from `orchestrator_numa_finding.md`; stub/opportunity, A/B + code change pending a dedicated session.
- 2026-06-26 — launcher argv plumbing fixed/tested for generic + vision builders; production `no_mmap:true` role flips still gated on operator A/B + live memory-placement verification.
- 2026-06-27 — ran isolated `vision_escalation` A/B; private `--no-mmap` was slower (65.760 t/s) than shared mmap (99.076 t/s) despite successful node-local placement; leave vision shared-mmap.
- 2026-06-27 — ran isolated `frontdoor` A/B; private `--no-mmap` was slower (42.428 t/s) than shared mmap (56.203 t/s) despite successful node-local placement; leave frontdoor shared-mmap.
- 2026-06-27 — ran isolated `ingest_long_context` A/B; private `--no-mmap` was slower (41.655 t/s) than shared mmap (57.528 t/s) despite successful node-local placement; leave ingest shared-mmap. Initial N12 target set is closed negative.
- 2026-06-27 — `affinity_preflight.py` gained `numa_maps` placement telemetry + opt-in strict locality; live strict worker-quarter check shows `worker_general` quarters are CPU-pinned correctly but memory-interleaved across N0-N3, so future private-copy claims must include this artifact and cannot rely on CPU affinity alone.
- 2026-06-27 — `stack_numa.py` now scopes `worker_general` interleave to instance 0 only (`5573e465`); live worker quarters still need a controlled restart and strict `numa_maps` verification before the fast-path claim can be marked proven.
