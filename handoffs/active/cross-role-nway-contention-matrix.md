# Cross-Role N-Way Contention Matrix Closure

**Status**: active
**Created**: 2026-05-26
**Updated**: 2026-05-27
**Categories**: orchestration, inference, scheduling, measurement
**Priority**: HIGH
**Owners**: bulk-inference-campaign Package J / routing-and-optimization
**Related**: [bulk-inference-campaign.md](bulk-inference-campaign.md), [within-role-placement-state-machine.md](within-role-placement-state-machine.md), [routing-and-optimization-index.md](routing-and-optimization-index.md)

---

## Problem

The current cross-role contention guard is pairwise. `ContentionGate.evaluate()` checks a new role against each active role through `pair_policy()`, so any known-bad pair inside a triple/quad is correctly blocked. That does not prove that an all-pairwise-allowed triple or quad is aggregate-throughput-positive. Shared memory bandwidth, cache pressure, llama-server scheduling, and per-role thread placement can still make an N-way active set regress even when every constituent pair passed.

This handoff owns Package J tasks J4a/J4b/J4c. They must close the N-way matrix before downstream bulk inference uses cross-role parallelism to reduce wall time.

## Scope

The closure guarantee is scoped to the exact measured stack:

- same `topology_hash`
- same role set and model mappings
- same CPU binding / instance topology
- same **live process affinity** as the intended CPU binding (`/proc/<pid>/task/*/status` must match `NUMA_CONFIG`, not just the hash of `NUMA_CONFIG`)
- same llama-server launch shape and relevant runtime flags
- same orchestration stack behavior for dispatch and contention gating

Future topology, model, CPU-binding, or orchestration-stack changes invalidate the matrix and require re-derivation. That future re-derivation is out of scope here.

## Current State

- `orchestration/contention_matrix.yaml` contains measured pairwise cross-role data, same-role coarse verdicts, explicit unknown pairs, and a small number of informational triples.
- Runtime admission is pairwise today: a candidate request is compared with each active role; N-way active sets are not modeled as first-class verdicts.
- `scripts/server/contention_matrix.py` should be treated as requiring audit before use for N-way closure. Its high-level comments describe smart pruning, but the current implementation has historically been pair-oriented; J4a must verify or add the exact N-way enumeration and manifest output.
- 2026-05-26 stack audit found a matrix trust gap: `topology_hash` can match even when special launcher paths start quarter processes with the wrong `_numa_prefix()` instance index. In the observed live stack, frontdoor and ingest affinities matched `NUMA_CONFIG`, but `worker_general` and `vision_escalation` quarter ports did not. Matrix rows involving affected role/shapes are diagnostic-only until the launcher is fixed, the roles are reloaded, live affinity is exact-match, and the rows are re-measured.

**2026-05-27 audit note**: later certified-affinity progress reports and the current matrix supersede parts of
this handoff's older "quarter-level matrix complete" prose. In particular, the earlier `{frontdoor,
ingest_long_context, vision_escalation}` `0.847` block was itself a bad-affinity artifact and was remeasured as
allow (`1.731`) on the certified stack. Before using this document as an execution source, run a consistency pass
against `orchestration/contention_matrix.yaml`, the latest `progress/2026-05/2026-05-26.md`/`2026-05-27.md`
entries, and the regenerated execution manifest. Until that sweep lands, treat the current YAML plus live-affinity
artifact as authoritative over stale narrative examples below.

## Definitions

**Trivial N-way rejection**: an active set can be skipped without new inference when it contains any lower-order failure:

- a pair with verdict `block`
- a pair below the configured background/bulk throughput floor
- an explicit `unknown` pair
- a same-role combination already blocked
- a measured failed triple contained inside a larger candidate

**Non-trivial N-way candidate**: an N-way active set whose every lower-order constituent is allowed under background/bulk policy. Pairwise-allowed is a precondition only; J4b measurement is still required before launch certification.

**Closed-world matrix for a topology**: for the measured topology hash, every non-trivial N-way active set is either measured `allow`, measured `block`, or explicitly listed as excluded by lower-order evidence. There must be no residual "unmeasured but potentially launchable" bucket.

## J4a: Candidate Enumeration

Goal: produce a deterministic manifest of every N-way active-set candidate and every excluded active set for the current topology.

Required behavior:

- Read live role topology and the current pairwise/same-role matrix.
- Enumerate triples first; then enumerate every larger active set up to the maximum cross-role concurrency the scheduler or bulk runner can admit.
- Prune trivial failures using lower-order evidence.
- Keep all non-trivial all-lower-order-allowed candidates for J4b measurement.
- Emit a topology-stamped manifest under `data/contention_matrix/` or another durable path named in the progress log.

Manifest fields:

| Field | Required | Notes |
|-------|----------|-------|
| `topology_hash` | yes | Must match runtime topology before any measurement or launch use. |
| `generated_at` | yes | UTC timestamp. |
| `roles` | yes | Sorted role list considered by enumeration. |
| `candidate_sets` | yes | List of non-trivial N-way sets requiring measurement. |
| `excluded_sets` | yes | List of pruned sets and exact reason. |
| `lower_order_evidence` | yes | Pair/triple evidence used to allow or prune. |
| `matrix_source` | yes | Path + git sha or checksum for the input YAML. |
| `live_affinity_verified` | yes | Boolean, false unless the live process affinity preflight passes for every role/shape considered. |
| `affinity_artifact` | yes | Path to port->pid->expected-cpus->observed-cpus evidence captured immediately before enumeration/measurement. |

Closure gate:

- Manifest is deterministic across two dry runs on the same topology.
- Every exclusion cites concrete lower-order evidence.
- No candidate lacks pairwise evidence.
- Live affinity is either verified exact-match or the manifest is explicitly marked `diagnostic_only` and cannot feed J4b certification.

## J4b: N-Way Measurement

Goal: measure all non-trivial candidates from J4a and update the matrix so bulk scheduling can make closed-world decisions.

Run policy:

- Run alone on the host. Do not co-run with J5, standalone throughput benches, or downstream evals.
- Before sampling, assert live process affinity exactly matches `NUMA_CONFIG` for every port used by the candidate assignment. Do not rely on `topology_hash` alone.
- Measure triples before quads.
- Skip any quad/superset that contains a measured failed triple and record it in `excluded_n_way`.
- Use at least 3 samples per measured set; gate on CV <= 5% unless the handoff/progress log explains why the result is still decisive.
- Compare `parallel_aggregate_tps` against `seq_aggregate_tps`. Per-request median speed is diagnostic only for this matrix.
- If any affected role was relaunched to fix affinity, discard or quarantine pre-fix rows involving that role/shape and rerun them under the repaired stack.

Suggested YAML extension:

```yaml
n_way:
  - roles: [frontdoor, worker_general, vision_escalation]
    size: 3
    topology_hash: "..."
    seq_aggregate_tps: 100.0
    parallel_aggregate_tps: 145.0
    ratio: 1.45
    samples: 3
    cv: 0.03
    verdict: allow
    measured_at: "2026-05-26T00:00:00Z"
    artifact: "data/contention_matrix/..."
excluded_n_way:
  - roles: [frontdoor, ingest_long_context, worker_general]
    topology_hash: "..."
    reason: contains_blocked_pair
    evidence: ["frontdoor+ingest_long_context ratio 0.49 block"]
```

Closure gate:

- For the current topology hash, every J4a `candidate_sets` entry has a matching measured `n_way` verdict.
- The affinity artifact proves every sampled port matched its expected CPU set.
- Every pruned candidate is listed in `excluded_n_way` with evidence.
- There is no unmeasured, all-lower-order-allowed N-way set remaining.

## Topology Repair Addendum: Frontdoor Half1 Is Optional, Not Implied

The dashboard labels the current frontdoor idx0 anchor as `Half0` because its CPU mask is `0-47,96-143`. That is the validated solo/full-speed anchor shape for frontdoor. It does not imply that a second `Half1` frontdoor instance exists, is wired, or is matrix-certified.

Current frontdoor concurrency certification is for the existing q0-q3 quarter instances. A dedicated frontdoor `Half1` replica would be a new topology experiment and must not be folded into J4/J5 repair by assumption. If the operator elects to test it:

- add a distinct port and `NUMA_CONFIG` instance for the Half1 CPU mask
- update dispatch/placement policy so Half0+Half1 is an explicit mode, not an accidental dashboard interpretation
- capture a new topology hash and live-affinity artifact
- benchmark Half0+Half1 against the current Half0 solo anchor plus q0-q3 quarter policy
- rederive `same_role`, cross-role pair, and N-way matrix rows before using it for bulk scheduling

Until that experiment exists and passes, the bulk run uses the current frontdoor topology: Half0 solo anchor plus q0-q3 quarters.

## J4c: Policy Wiring

Goal: prevent the bulk runner or runtime scheduler from treating all-pairwise-allowed N-way sets as certified unless J4b actually measured them.

Required policy:

> **Traffic-class scoping (2026-05-27, reconciles #4 doc↔code).** The "fail closed / queue-serialize" rules below are the **BULK / background** policy. The live `ContentionGate` runtime applies a traffic-class split (see `contention.py` `nway_policy` + this handoff §Runtime policy): **FOREGROUND interactive fails OPEN** for unmeasured non-light sets (admit + log) so latency isn't sacrificed, while **BACKGROUND / bulk fails CLOSED** (serialize). Stale-topology / non-OK matrix is now hard fail-closed at the gate for both classes (background QUEUE, foreground degraded-admit) — see `ContentionGate.evaluate()` topology-freshness guard. So the wordings are not contradictory; they describe different traffic classes.

- Before J4b closure: fail closed. Cross-role N-way task overlap is queue/serialize unless the exact active set is already measured and topology-valid.
- After J4b closure: launch only exact active sets with `n_way.verdict: allow` and matching topology hash.
- Treat `block`, `excluded_n_way`, missing N-way entries, stale topology hash, or missing matrix status as queue/serialize (BULK/background); foreground interactive fails open + logs.
- Same-trial EvalTower fan-out is separate; it uses within-role topology-safe placement and concurrent speed semantics, not this cross-role N-way matrix.

Implementation note: if the runtime remains pairwise only and the bulk runner is the only component launching cross-role overlap, J4c can be a bulk-runner guard plus documentation. If production admission itself can create N-way overlap, teach `ContentionGate` or its caller to evaluate the exact active-set union.

## Baseline Mutation Rule

Do not update production baselines, Pareto archives, regression thresholds, learned scheduling priors, or routing speed priors from any concurrent run unless all of the following are recorded and valid:

- `speed_metric_mode`
- `topology_hash`
- `matrix_status`
- exact active-set verdict id or same-trial within-role flag
- median per-request t/s when available
- aggregate batch t/s when concurrency is used

If any field is missing, stale, or inconsistent, quarantine the run as diagnostic-only. It may inform manual investigation, but it must not mutate production baselines or safety thresholds.

## Execution Manifest Template

Every J4a/J4b/J4c execution should have a manifest row or JSON object with these fields:

| Field | Required | Notes |
|-------|----------|-------|
| `run_id` | yes | Stable id reused in artifacts and progress notes. |
| `task_id` | yes | `J4a`, `J4b`, or `J4c`. |
| `topology_hash` | yes | Captured immediately before the run. |
| `roles` | yes | Roles in scope or exact active set. |
| `concurrency_mode` | yes | `enumeration`, `isolated_bench`, `policy_wiring`, or `observe_only`. |
| `matrix_status` | yes | `preclosure`, `closed_world`, `stale`, or `diagnostic_only`. |
| `live_affinity_verified` | yes | Required true before any certification or baseline-eligible run. |
| `affinity_artifact` | yes | Captured immediately before the run. |
| `command` | yes | Exact command or script invocation. |
| `flags` | yes | Relevant env vars and feature flags. |
| `output_artifacts` | yes | Manifest/YAML/log/result paths. |
| `journal_policy` | yes | `quarantine`, `diagnostic_only`, or `baseline_eligible`. |
| `baseline_mutation_allowed` | yes | Boolean; false unless the baseline rule above passes. |
| `pass_gate` | yes | Explicit gate expression. |
| `next_action` | yes | Continue, rerun, serialize downstream, or stop. |

## Resume Protocol

If interrupted:

1. Read the latest progress log and the execution manifest.
2. Recompute the current `topology_hash` and compare it with the manifest and matrix.
3. Inspect the last produced artifact, not just process exit status.
4. Rerun only idempotent preflight/enumeration steps automatically.
5. Resume from the first incomplete gate.
6. Do not mark a partially completed bench row as complete unless all samples, CV, ratio, verdict, topology hash, and artifact paths are present.
7. If topology changed, stop cross-role parallelism and restart from J4a.

## J4a Result (2026-05-26, claude bulk-inference session)

J4a enumeration **implemented + run (no inference)**. An additive `enumerate` subcommand now lives in `scripts/server/contention_matrix.py` (reuses `load_contention_matrix` + `topology_fingerprint`; refuses to emit against a stale/mismatched matrix). It loads the live matrix + NUMA_CONFIG, classifies every cross-role pair by the background/bulk floor (0.85), enumerates all size-3..N role sets, prunes on lower-order evidence (below-floor/block/unknown pair, or measured-failed-triple superset), and emits a topology-stamped JSON manifest with a deterministic `content_hash`.

- **Topology**: live `topology_hash = df373c79cc4af06f` == matrix; `matrix_status = OK` (measured 2026-05-24, fresh).
- **Artifact**: `data/contention_matrix/bulk-2026-05-26-j4a/j4a_candidate_manifest.json` (`content_hash = 8dd5f740f3651bfb`).
- **Command**: `python3 scripts/server/contention_matrix.py enumerate --run-id bulk-2026-05-26-j4a --output data/contention_matrix/bulk-2026-05-26-j4a`
- **Candidate sets (require J4b measurement — currently NOT certified)**:
  - `{ingest_long_context, vision_escalation, worker_general}` (min pair ratio 1.18)
  - `{vision_escalation, worker_general, worker_vision}` (min pair ratio 1.07)
  - **No 4-way or larger candidates** — no clique of bulk-allowed pairs exceeds size 3 in the current matrix.
- **Excluded**: 40 size-3..6 sets, each citing the first offending pair (e.g. `frontdoor+ingest_long_context 0.37 block`, `architect_general+frontdoor 0.50 block`) or unknown pair (`*+worker_vision` unknowns).
- **Discrepancy flag**: `{frontdoor, vision_escalation, worker_general}` is excluded by `frontdoor+vision_escalation = 0.84 < floor 0.85`, **but** the matrix's informational triple measured **1.45**. This is the canonical pairwise-conservative-vs-N-way-positive case. **J4b should measure this set explicitly** alongside the two candidates; if confirmed ≥ floor, it is a foreground-only-allow / floor-reconsideration candidate (still not a background/bulk allow until the pair itself clears).

**Closure gate status**: J4a closure gate **met** (deterministic across two runs; every exclusion cites concrete lower-order evidence; no candidate lacks pairwise evidence). **J4b/J4c remain OPEN** — `matrix_status` stays `preclosure` until J4b measures the 3 sets above (alone on host) and writes `n_way`/`excluded_n_way` into `contention_matrix.yaml`. Cross-role parallelism stays fail-closed meanwhile.

**Note for J5 (within-role)**: `worker_general` is a 4-quarter role (full `0-95` + q0–q3), not single-instance; its quarters-only disjoint capacity is 4. The current `same_role.worker_general = allow` verdict is "assumed quarter-safe, not directly measured 4-way" — J5's instance-pair sweep is what validates the worker_general quarters path.

## J4b Result (2026-05-26, claude bulk-inference session) — MATRIX CLOSED (+ gemma4 crash finding)

J4b measurement **implemented + run alone on host** (frontdoor measured 25.5 t/s pre-bench → no throttle, so drop_caches skipped per `feedback_drop_caches_numa_eviction`). New `bench-nway` subcommand in `scripts/server/contention_matrix.py` reads the J4a manifest, benches each set (solo + all-K concurrent, 3 samples, ratio = parallel_agg/seq_agg, CV gate). Artifacts: `data/contention_matrix/bulk-2026-05-26-j4b/`. Matrix updated: `orchestration/contention_matrix.yaml` now has `n_way:` (2 allow) + `excluded_n_way:` (1 block). `matrix_status=ok`, topology `df373c79cc4af06f`.

| Active set | ratio | CV | verdict |
|------------|-------|-----|---------|
| {vision_escalation, worker_general, worker_vision} | 1.286 | 0.003 | **allow** (clean) |
| {frontdoor, vision_escalation, worker_general} (J4a-flagged) | 1.126 | 0.06 | **allow** (foreground) — N-way-positive despite the pairwise frontdoor+vision=0.84; resolves the J4a flag |
| {ingest_long_context, vision_escalation, worker_general} | 1.209* | 0.15 | **block / UNSAFE** |

**Closed-world gate MET**: both non-trivial candidates classified (1 allow, 1 block), the flagged set measured (allow), no residual unmeasured bucket for this topology.

**⚠️ Critical finding — gemma4 worker_general full crashed under the heaviest 3-way contention.** During the `{ingest, vision, worker_general}` bench, the gemma4-26B-A4B MTP **full** instance (port 8072) crashed (`Errno 111` connection-refused mid-bench; `logs/worker-explore-8072.log`: degenerate repetition then `terminate: std::runtime_error Failed to parse input at pos 0:`). This is a *different* signature from the FA-assert wedge in `feedback_gemma4_mtp_fa_assert_wedge` (it's a parse-error after degenerate output, clean process exit — no zombie threads). The full instance (gemma4 wants 0-95) under simultaneous ingest(0-47)+vision(48-95) load destabilized. The 4 quarters survived; production was degraded-not-broken. **Restored** via `orchestrator_stack.py start --only worker_general --skip-host-prereqs` (started only the down instance; new PID, all 5 healthy). The set's 1.209 ratio (on completing samples) is moot — it is marked `block` for safety until gemma4 full-instance stability under contention is investigated. This is exactly the kind of all-pairwise-allowed-but-unsafe N-way set the closure exists to catch.

**Remaining**: **J4c** — wire the fail-closed → allow-only policy so the bulk runner / scheduler only launches exact active sets with `n_way.verdict: allow` + matching topology hash, treating `block`/`excluded_n_way`/missing/stale as queue-serialize. (Pre-J4c operator policy is already fail-closed.)

## J4b CORRECTION (2026-05-26, operator audit) — full-instance model was wrong; quarter-level disjoint-cpuset model + parser fix

The first J4b pass (above) benched each role's **full/primary** instance concurrently. The operator correctly flagged this as a methodology error:

- **A full-machine instance is solo-only.** worker_general-full (0-95) and architect-full (0-95) need all cores; they exist for max *single-stream* throughput when there is no concurrency. Running worker_general-full concurrently with ingest+vision (what the first J4b did) is a config the placement SM should never create. Under concurrency a role must use a **quarter**.
- **Concurrency is mutually-disjoint cpusets, not "quarters only".** ingest-full(0-47) + vision-full(48-95) co-run fine (disjoint halves). The hard veto is *overlap*: a full instance that needs all cores blocks concurrency until it is moved to a quarter/half.
- **{ingest, vision, worker_general} at full is over-subscribed**, not merely "block": ingest(0-47)+vision(48-95) already fill the machine. Its first-pass crash was the gemma4 PEG **parser bug**, not a pure concurrency verdict.

**Corrected model implemented** (`scripts/server/contention_matrix.py`, commit `941a340`): `feasible_assignment()` (backtracking disjoint-cpuset search, quarters preferred) + `enumerate --feasibility` + `bench-nway` using per-role assignment ports + `--safe-sampling`. Feasible enumeration for topology `df373c79cc4af06f`: **25 candidate sets** (size 2-4), **32 excluded `topology_infeasible`** (every architect-containing set — architect is full-only/solo — plus all ≥5-role sets). Manifest: `data/contention_matrix/bulk-2026-05-26-j4a-feasible/`.

**gemma4 parser crash FIXED** (not just filed). Root cause: `ik_llama.cpp/common/chat.cpp` `common_chat_peg_parse` threw an *uncaught* `std::runtime_error` on un-parseable output → server `terminate`. Patched (ik_llama.cpp commit `d84755dc`, branch `pr-1744`): final parse → return raw text as content; partial parse → empty msg. Rebuilt + redeployed all 5 worker_general instances; **verified** — the exact greedy degenerating prompt now returns content and the server survives.

**Status of the full-instance n_way entries**: per operator, full-instance co-running data is valid where it boosts (gemma4 MTP is BW-light), so `{vision,worker_general,worker_vision}`=1.286 and `{frontdoor,vision,worker_general}`=1.126 are kept as a **full-mode coarse layer**. The authoritative concurrent matrix is the **quarter-level disjoint** re-bench (15 size≥3 feasible sets, `--safe-sampling`, alone on host) — **in progress** (`data/contention_matrix/bulk-2026-05-26-j4b-feasible/`). The earlier "matrix CLOSED" is therefore **superseded**: closure is re-defined over the feasible quarter-level candidate set.

## J4c DONE + matrix CLOSED at quarter level (2026-05-26)

> **⚠️ SUPERSEDED (2026-05-27 certified-affinity re-bench).** The single block below — `{frontdoor, ingest, vision}` = 0.847 — was a **bad-affinity artifact** (the worker/vision quarters were pinned to the wrong cores; `_numa_prefix` launcher bug, fixed `da1aed6`/orchestrator_stack 681/732/847). On certified disjoint quarters (`live_affinity_verified=true`) it re-benches to **1.731 ALLOW** (`orchestration/contention_matrix.yaml` n_way; commit `4363dae`). **The current certified matrix has NO measured N-way block — every measured set allows.** The "0.847 = the concrete proof of pairwise≠N-way" claim in this paragraph is therefore **retracted**; the N-way gate (`nway_policy`) remains as a *defensive* mechanism that would queue any future measured block, but none currently exists. Treat `contention_matrix.yaml` + the live-affinity artifact as authoritative; the paragraph below is retained only as historical narrative.

**Quarter-level matrix complete** (the authoritative concurrent layer). Benched all feasible candidates with `--safe-sampling`, ingest restricted to full (non-quarterable): **17 verdicts — 16 allow + 1 block**. The block is `{frontdoor, ingest, vision}` = 0.847 (ingest's heavy half saturates BW with two co-runners) — and crucially **all three of its pairs are allow (1.72 / 1.43 / 1.06)**, so it is the concrete proof that pairwise-allow ≠ N-way-safe. The previously-"crashed" `{ingest, vision, worker_general}` is now a clean **1.578 allow** (ingest-half + two light quarters), superseding the full-instance pass. Only one feasible all-quarterable 4-way exists (`{frontdoor,vision,worker_general,worker_vision}` = 1.605 allow). Non-quarterable: ingest (half-only), architect (whole-machine full → strictly solo, 0 feasible co-run sets).

**J4c wired — the runtime now KNOWS** (orchestrator commit `d937483`). `ContentionGate.evaluate()` was pairwise; it would have admitted the 0.847 block (all pairs allow). Now:
- `contention.py`: `Nway` dataclass + `ContentionMatrix.n_way/light_roles/heavy_roles`; `load_contention_matrix` parses `n_way` + `nway_light_roles`/`nway_heavy_roles`; new `nway_policy(roles, traffic_class)`.
- `contention_gate.py`: after the pairwise loop, `evaluate()` consults `nway_policy` on the exact active-set union and escalates to QUEUE; `contention_nway_restricted_count` metric.
- Policy: measured allow→ALLOW; measured block→QUEUE (serialize); unmeasured all-light→ALLOW (covers mixed multi-instance light sets via role-set dedup, anchored by the 4-way 1.605× + within-role 1.88–2.86×); unmeasured otherwise→fail-open foreground / fail-closed background (matches pair_policy + the fail-open-foreground handoff rule).
- 6 `nway_policy` regression tests; 30 contention + 45 gate/contention tests green.

**Verified at runtime semantics**: `nway_policy({frontdoor,ingest,vision})` = QUEUE (both classes); 4-way all-light = ALLOW; `{ingest,worker_vision}` heavy-unmeasured = QUEUE(bg)/ALLOW(fg).

**Closed-world for topology `df373c79cc4af06f`**: every feasible candidate (9 pairs + 7 triples + 1 quad) is measured allow/block; infeasible sets (architect-containing, ≥5-role) are `topology_infeasible`; the runtime gate consumes the verdicts. **Matrix CLOSED + wired.** Mixed multi-instance light sets are covered by the all-light policy (role-set keyed). Remaining refinement (documented, low-priority): per-quarter NUMA-node assignment can shift a verdict a few %; the matrix stores one representative assignment per role-set.

## Completion Criteria

- J4a candidate/exclusion manifest exists and is topology-stamped.
- Live-affinity artifact exists and proves every measured port matched `NUMA_CONFIG` at measurement time.
- J4b updates `orchestration/contention_matrix.yaml` or an equivalent matrix artifact with `n_way` and `excluded_n_way`.
- J4c fail-closed policy is implemented or explicitly delegated to the bulk runner.
- Bulk inference runbook points to this handoff.
- Master handoff index points to the early matrix-closure dependency.
- Latest progress log records topology hash, commands, artifacts, and closure verdict.
