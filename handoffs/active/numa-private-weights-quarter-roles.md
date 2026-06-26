# NUMA Private Node-Local Weights for Shared-mmap Quarter Roles

**Status**: STUB / OPPORTUNITY — analysis complete + bench-evidenced on the worker model; production A/B and the load-bearing code change are pending a dedicated session.
**Created**: 2026-06-26
**Owner**: unclaimed — dedicated future session (high-ROI, low-effort, NPS4-gated and we are on NPS4)
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md)
**Cross-refs**: [`numa-page-cache-prewarm.md`](../completed/numa-page-cache-prewarm.md) (the `[1.5]` interleave prewarm this supersedes for quarter roles), [`single-instance-system-tuning.md`](../completed/single-instance-system-tuning.md) §Phase 4 (the unimplemented weight-replication estimate), [`orchestrator-nps4-48x4-notes.md`](orchestrator-nps4-48x4-notes.md) (mmap/mbind dedupe open question).
**Source finding**: `/mnt/raid0/llm/tmp/orchestrator_numa_finding.md` (2026-06-26).

> **Measurement discipline**: every t/s in this file is an **observation** (no protocol-id / attestation), usable to motivate the work and size the prize, never to gate the production flip. The flip is gated on the Arm A vs Arm B A/B in the Validation Plan, run via the codified recipe under operator approval per `/workspace/MEASUREMENT.md`.

---

## Objective

Give the three **shared-mmap quarter-able roles** — `frontdoor` (Qwen3.6-35B-A3B Q8), `ingest_long_context` (Qwen3-Next-80B Q4), `vision_escalation` (Qwen3-VL-30B Q4) — **private, node-local weight copies** (`--no-mmap`, one private RAM copy per quarter instance) instead of the current single shared interleaved mmap copy that every quarter reads 75% cross-node.

`worker_general` (gemma-26B Q4 MTP) **already realizes this fast path** (`--no-mmap` is hard-wired into its dedicated builder). The other three quarter roles do not, because the generic role builder silently ignores the `no_mmap` field that already exists in their priors. This is the entire gap.

---

## Evidence (observations — motivate, do not gate)

- **gemma-26B 4×quarter, clean host, same window**: shared-interleaved mmap = **43.5 t/s** aggregate vs **`--no-mmap` private node-local = 119.5 t/s** aggregate (`numa_mtp.gemma-26B.jsonl`: quarter / 4 instances / MTP-on `agg_tps=119.46`, replicates `[119.31, 119.46, 120.49]`). **~2.7×.** This is the worker model; it already runs the fast arm in production, so the bench measures exactly the topology the other three roles are missing.
- **Qwen3.6-35B (frontdoor) Arm B already measured**: the corrected NUMA suite (`numa_mtp.Qwen3.6-35B.jsonl`) gives the private `--no-mmap` quarter number (4 instances, MTP-on `agg_tps=19.32`, `[19.32, 19.21, 19.38]`). Only **Arm A** (the orchestrator's current interleave-prewarm-mmap pattern) needs measuring to complete the head-to-head for frontdoor.
- **Phase-4 estimate (likely conservative)**: `single-instance-system-tuning.md:89,207-219` estimates **+10-30%** for per-NUMA-node weight replication under NPS≥4. The gemma 2.7× suggests the real prize is larger when the model fits 4× in RAM and the workload is quarter-concurrent (bandwidth-bound aggregate, where cross-node reads cost the most).

---

## Root cause / per-role launch matrix

From the finding doc (verified against current code/priors):

| Role | Model (GGUF, approx) | mmap today | Memory placement (multi-instance) |
|------|------|------|------|
| **frontdoor** | Qwen3.6-35B-A3B Q8 (~34 GB) | mmap (`no_mmap: false`) | **shared interleaved — 1 copy, 4 quarters each 75% cross-node** |
| coder_escalation | (shares frontdoor GGUF/process) | mmap | shares frontdoor copy |
| **ingest_long_context** | Qwen3-Next-80B Q4 (~45 GB) | mmap (`no_mmap: false`) | **shared interleaved — multi-instance, 1 copy** |
| **vision_escalation** | Qwen3-VL-30B Q4 (~17 GB) | mmap (`no_mmap: false`) | **shared interleaved — multi-instance, 1 copy** |
| worker_general | gemma-26B Q4 MTP (~16 GB) | **`--no-mmap`** (`no_mmap: true`) | **private per-instance node-local — ALREADY FAST** |
| architect_general | Qwen3.5-122B Q4 (~69 GB) | mmap + `interleave=all` | interleaved, single instance (correct — too big to replicate cheaply) |
| worker_vision | Qwen2.5-VL-7B Q4 (~4 GB) | mmap | first-touch, single instance |

Three mechanisms compound the slow path:

1. **The generic builder ignores `no_mmap`.** `_build_role_command` (`orchestrator_stack.py:825-912`) never references the `no_mmap` field. The field is present in every role's prior (`stack_priors.yaml`: `worker_general` line 833 `no_mmap: true`; `frontdoor` 254/399, `ingest_long_context` 543, `vision_escalation` 997 all `no_mmap: false`), but only `worker_general`'s **dedicated** builder reads it (`orchestrator_stack.py:606`, `cache.get("no_mmap", True)`). So the three target roles fall through to shared mmap regardless of their prior. **This is the load-bearing bug.**
2. **No `--membind` / `--cpunodebind` anywhere.** `_numa_prefix` (`stack_numa.py:200-222`) emits a bare `taskset` (plus an optional `numactl --interleave=all` wrapper for the few canonical-recipe roles). `--membind`/`--cpunodebind` appear only in comments. So even the page placement is never pinned per node.
3. **The interleave prewarm is bandwidth, not locality.** The `[1.5] numactl --interleave=all` page-cache prewarm (`stack_prewarm.py`; [`numa-page-cache-prewarm.md`](../completed/numa-page-cache-prewarm.md)) fixed the 2026-05-28 cold-collapse (mlock first-touching the whole GGUF onto ONE node → −50-65%). It forces a clean 25%-per-node spread → full aggregate **bandwidth** but **not locality** — every quarter still reads 75% of weights off-node. Better than collapse; not the fast path.

### Codebase contradiction to resolve (do this once measured)

`stack_numa.py:13,203` asserts "taskset alone is sufficient — `numactl --membind` adds no benefit (S4)", which contradicts memory `feedback_mmap_numa_sharing` ("never bare taskset"; M2.7 saw instance-2 at 0.69 t/s under shared mmap). The finding reconciles them along the **mmap dimension**: S4 was a `--no-mmap` / single-instance test (membind redundant when each process owns its own first-touched copy); the failure mode `feedback_mmap_numa_sharing` warns about is **shared mmap across instances**, where membind/`--no-mmap` is mandatory. Both are right for their regime. Encode this reconciliation in a code comment at `stack_numa.py:203` **after** the A/B confirms it — don't pre-edit the comment on theory.

---

## The fix (the actual deliverable)

Two coupled edits, both in `epyc-orchestrator`:

1. **Data**: set `no_mmap: true` in the launch priors for the three target roles in `orchestration/derived/stack_priors.yaml` (`frontdoor` 254/399, `ingest_long_context` 543, `vision_escalation` 997). *(Derived file — confirm it is regenerated from / consistent with the prior source per the model-stack SSoT pipeline; do not hand-edit a generated artifact without updating its source. See N11a / `model-stack-single-source-update-pipeline.md`.)*
2. **Code (load-bearing)**: **wire `--no-mmap` into the generic `_build_role_command`** (`orchestrator_stack.py:825-912`) exactly as the worker builder does it (`orchestrator_stack.py:606`): `*(["--no-mmap"] if cache.get("no_mmap", <default>) is True else [])`. Choose the default deliberately — recommend `False` for the generic path (opt-in per role) so this change is inert for every role that does not set the flag. Today the field is simply dropped on the floor for all non-worker roles.

Optional, stronger (decide from the A/B): also add per-node `numactl --cpunodebind=N --membind=N` for `--no-mmap` quarter instances via `_numa_prefix`, to guarantee each private copy first-touches its own node rather than relying on `taskset` + first-touch. The A/B's Arm B uses explicit membind; if Arm B wins and the membind-free `--no-mmap` variant matches it, the `taskset`-only path is sufficient and simpler.

### Memory budget (fits comfortably on 1.1 TB)

Four private copies per role (replacing 1 shared copy):

| Role | 1 copy | 4× private | Headroom note |
|------|------|------|------|
| vision_escalation | ~17 GB | **~68 GB** | smallest; highest per-quarter t/s — best first candidate |
| frontdoor | ~34 GB | **~136 GB** | Arm B already measured |
| ingest_long_context | ~45 GB | **~180 GB** | largest of the three; still fits |

Total if all three flip simultaneously ≈ **384 GB** of private weights, on top of `worker_general`'s existing private copies — well within ~1.1 TB. Verify against the live `--mlock` budget (memory `feedback_host_throttle_check` / the ~701 GB mlock figure in `stack_numa.py:15`) before flipping all three at once; stage one role at a time. Note these roles do **not** all run 4 quarters in production simultaneously today — confirm instance counts per role in `stack_priors.yaml` so the budget reflects the real deployed multiplicity, not the worst case.

---

## Validation plan (the gate)

Operator-run / owned-bench only, `-fa 1` explicit, full OMP env stack (`OMP_PROC_BIND=spread`, `OMP_PLACES=cores`, `OMP_WAIT_POLICY=active`, `KMP_BLOCKTIME=10` for the MTP/AOCC path), one server at a time (no concurrent inference — another agent may be benching), pgrep zombie-check first, host-throttle + drop_caches/re-warm checked per `feedback_host_throttle_check` / `feedback_drop_caches_numa_eviction`.

Per role, 4×quarter, sum the per-quarter t/s:

- **Arm A — current orchestrator pattern (shared mmap, interleave prewarm, no membind)**: `numactl --interleave=all cat MODEL >/dev/null` to prewarm page cache, then 4× `taskset -c <quarter_cpus> llama-server/llama-bench -m MODEL --mlock` (mmap, no membind).
- **Arm B — private node-local**: 4× `numactl --cpunodebind=N --membind=N taskset -c <quarter_cpus> ... --no-mmap --mlock`.

Sum per-quarter decode t/s for each arm; Arm B wins is the flip signal. **Suite already provides Arm B for frontdoor** (`numa_mtp.Qwen3.6-35B.jsonl`, quarter MTP-on 19.32 t/s) — frontdoor only needs Arm A measured. Priority order by leverage: **vision_escalation** (smallest, highest per-quarter t/s, cheapest copy), then **frontdoor** (Arm A only), then **ingest_long_context** (largest copy).

Acceptance: flip a role's `no_mmap` to `true` in production only after its own Arm A vs Arm B A/B shows Arm B materially ahead under the codified recipe with operator sign-off; stage and re-attest one role per quiet window. Re-confirm with `affinity_preflight.py` (see Secondary) that the live placement actually changed post-flip — do not trust the topology hash alone (`feedback_verify_live_affinity_not_just_topology_hash`).

---

## Secondary work

1. **Observability gap (do this alongside, low effort)**: `affinity_preflight.py` (`scripts/server/affinity_preflight.py`) checks the CPU thread-union only — it has **no `/proc/<pid>/numa_maps` read**, so memory mis-placement (a quarter reading off-node, a private copy that first-touched the wrong node) is **undetectable by the production gate**. Extend it to parse `numa_maps` and assert each instance's weight pages are ≥X% on its bound node. This is what makes the `--no-mmap` flip safe to keep deployed and is the only way to catch a silent regression to the slow topology.
2. **Resolve the `stack_numa.py` contradiction in a comment** (see Root-cause §): after the A/B confirms the mmap-dimension reconciliation, annotate `stack_numa.py:203` so the next reader doesn't re-litigate "taskset is sufficient" vs `feedback_mmap_numa_sharing`. Append, don't rewrite history.

---

## Key files (with line numbers)

| What | Where |
|------|------|
| Generic role builder — **ignores `no_mmap`** (the fix site) | `epyc-orchestrator/scripts/server/orchestrator_stack.py:825-912` |
| Worker builder — emits `--no-mmap` (the pattern to copy) | `epyc-orchestrator/scripts/server/orchestrator_stack.py:606` |
| `_numa_prefix` — bare taskset, no membind (optional membind site) | `epyc-orchestrator/scripts/server/stack_numa.py:200-222` |
| `stack_numa.py` "taskset sufficient" claim to reconcile | `epyc-orchestrator/scripts/server/stack_numa.py:13,203` |
| Launch priors (`no_mmap` field per role) | `epyc-orchestrator/orchestration/derived/stack_priors.yaml` (worker 833 `true`; frontdoor 254/399, ingest 543, vision 997 `false`) |
| Interleave page-cache prewarm (`[1.5]`) | `epyc-orchestrator/scripts/server/stack_prewarm.py` + [`numa-page-cache-prewarm.md`](../completed/numa-page-cache-prewarm.md) |
| Phase-4 weight-replication estimate (unimplemented) | [`single-instance-system-tuning.md`](../completed/single-instance-system-tuning.md):89,207-219 |
| Affinity preflight (CPU-only, no numa_maps) | `epyc-orchestrator/scripts/server/affinity_preflight.py` |
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
