# Proposed amendment — replace per-run operator approval with a held region claim

**Status**: DRAFT — awaiting operator apply. Authored 2026-07-27.
**Target**: `agents/shared/OPERATING_CONSTRAINTS.md` → *Inference and Benchmarks*
**Precondition**: A0 has landed (it has — see *Enabling change* below). Do **not** apply this
before A0, or the last serializer between benches and orchestrator placements is removed.

---

## Current text (verbatim)

```
## Inference and Benchmarks

- Never launch inference/benchmark runs (llama-bench/cli/server, run_benchmark.py, eval suites)
  without explicit per-run operator approval — a parallel agent or the autopilot may be running;
  concurrent runs silently poison both sides.
```

## Proposed replacement

```
## Inference and Benchmarks

- Never launch inference/benchmark runs (llama-bench/cli/server, run_benchmark.py, eval suites)
  without a held CPU-region claim covering the cores the run pins. Use
  `region-lock run --cpu-list <list> -- <command>`; `bench_canonical.sh` acquires it
  automatically and refuses to run unlocked. Concurrent runs on overlapping regions silently
  poison both sides — the claim, not a human, is what prevents that.
- Operator approval is required only where the run's `operator_gates[]` names an actual trust
  boundary (era registry rows, MEASUREMENT.md, AutoPilot baseline applies, production
  freezes/cutovers, host reboots). Concurrency alone is never grounds for a human gate.
- Co-residency policy lives in versioned, staleness-guarded data
  (`orchestration/contention_matrix.yaml`, guarded by `topology_hash`), never in prose.
- The dispatch path must keep `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1`. Without it the
  orchestrator takes per-role locks only and will not contend a bench's GLOBAL claim — exclusion
  becomes one-sided, which is worse than none because it looks safe.
```

## Why

1. **The clause conflates two orthogonal axes.** Co-residency is scheduling; trust boundaries are
   human. It answers the first with the instrument for the second, making the operator the
   serializer for every run.
2. **Precedent on the same host.** `epyc-orchestrator/src/scheduling/contention_gate.py`
   (`admit()`) already places-or-queues concurrent inference continuously against a measured
   matrix and live region holders — unsigned. Requiring a signature per *benchmark* is an
   inconsistency, not a stricter principle.
3. **It contradicts two 2026-07-27 ratifications.** *Consolidated apply-time ratification*:
   "Evidence collection and validation NEVER wait on a human signature," and benchmark launches
   are not in the enumerated human-only list. *Long-horizon throughput contract*: saturation
   scheduling — "on ANY block, immediately start the next queued item."
4. **It blocks the session-bus M4 acceptance criterion** (48h with zero idle-lane time while
   eligible work existed), which is unachievable while every lane refill needs a signature.

## Enabling change (A0) — already landed

The clause was wrongly *framed* but was genuinely **load-bearing**: three disjoint exclusion
domains existed over the same physical cores.

| Path | Lock taken (before A0) |
|---|---|
| Orchestrator dispatch | per-region `flock` on `cpu_region.{role}.{region}.lock` (+ `GLOBAL` layer) |
| `run_benchmark.py` | its own `fcntl.flock`, a **different namespace** |
| `bench_canonical.sh` / llama-bench — the sanctioned path | **none** |

A0 closes this without a second lock implementation:

- `epyc-orchestrator/src/runtime/region_lock_cli.py` + `scripts/region-lock` — a **wrapper** that
  calls the same `cpu_region_lock()` and holds the regions for the child's lifetime.
- `bench_canonical.sh` derives its cpu list from the emitted canonical command and acquires the
  claim, **failing closed** if it cannot (override: `CANONICAL_SKIP_REGION_LOCK=1`, which warns).

Verified: exit-code propagation, `--cpu-list 0-95` → all four regions, contention serializes,
SIGKILL releases the lock (kernel fd-close), signals forwarded to the child so drain works,
stale payloads never reported as holders (probe, not stored record — fabric axiom 2).

## What this does NOT change

- The human-only write list is untouched: era registry rows, `MEASUREMENT.md`, AutoPilot baseline
  applies, production freezes/cutovers, host reboots.
- Codified-recipe discipline is untouched — throughput numbers still come only from
  `bench_canonical.sh` / `canonical_recipe.py`.
- Host-health preflight is untouched.

## Apply

Operator edit to `agents/shared/OPERATING_CONSTRAINTS.md`, replacing the block above. Then update
the digest reference in `CLAUDE.md` § Measurement & Claims if the wording there is quoted.
Superseding note for memory: `feedback_no_concurrent_inference` becomes obsolete on apply and
should be replaced by `feedback_contention_is_scheduling_not_trust`.
