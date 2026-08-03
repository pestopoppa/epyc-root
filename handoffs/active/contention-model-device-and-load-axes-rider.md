# RIDER — Contention model: the device, batching and context axes

**Rides on:** [`shape-keyed-contention-gating.md`](shape-keyed-contention-gating.md) (Parts A/B/C) and
W8 in [`numa-topology-cutover-resume-20260730.md`](numa-topology-cutover-resume-20260730.md).
**Status:** DESIGN — audit + open questions. No code. Written 2026-08-01 while W1 was landing,
so that when execution starts it is execution, not design.
**Why a rider:** the parent plan is sound and largely built. This does not replace it. It records
(1) what the W1 cutover invalidated in it, and (2) the one dimension it does not model at all.

---

## 1. What W1 invalidated in the parent plan — fix before executing it

The parent plan's **Decisions locked** section contains an assumption that is now false. Executing
against it unmodified would encode a topology that no longer exists.

| Parent plan says | Reality after W1 (2026-08-01) |
|---|---|
| *"`architect_general` is strictly solo — its only feasible instance is whole-machine, so every candidate placement overlaps any other holder."* | **FALSE.** `architect_general` is now Qwen3.6-27B on MI210 on the **shared 8-thread GPU host lane** `184-191` (`membind=3`). It is no longer whole-machine and no longer solo. MEASURED 2026-08-01: its worst pair went **0.66 block → 1.40 allow**; +`frontdoor` 0.90 → 1.43; +`worker_general` 0.91 → 1.57. It went from the *least* co-residency-friendly role to one of the *most*. (An interim 24-thread node-3 quarter was wired first and superseded by the operator's lane ruling.) |
| Invariant 1: `vision_escalation` (8087) primary = upper half `{q2,q3}` | **Role has no server.** It is an alias on `worker_vision`'s `:8086`. Port 8087 is retired. |
| Invariant 1: `architect_general` (8083) "full" = all four `{q0,q1,q2,q3}` | Now the shared GPU host lane `184-191`, 8 threads — SMT siblings of physical 88-95, so zero physical cores by the region formula. |
| *"all of this assumes `topology_hash df373c79cc4af06f`"* | RESOLVED 2026-08-01: the matrix was re-benched for the live hash **`171f86f9`** (15 pairs, zero catastrophic). It had drifted through `df373c79` → `8c8cfcbb` → `911d3dea` → `1c654634` → `171f86f9`, spanning the half-fleet cutover (2026-07-30) and W1. |
| — | **NEW role** `architect_critic` inherits the full `0-95` `interleave=all` instance on `:8074`. The "whole-machine solo heavy role" role did not disappear; it changed name. Every place the plan reasons about `architect_general`-the-whole-machine-blocker now means `architect_critic`. |

**Consequence:** the matrix has never been regenerated for a topology in which a heavy architect
role is GPU-resident. Every measured `architect_general` pair row in
`orchestration/contention_matrix.yaml` describes a 96-thread CPU instance that no longer exists.
They are not merely stale, they are **about a different machine configuration**.

`tests/unit/test_scheduling_contention.py` carried 3 stale witnesses validating the matrix against
live `NUMA_CONFIG`. The matrix is now regenerated; re-check them against `171f86f9`.

---

## 2. The dimension the model does not have: DEVICE

Verified 2026-08-01 by direct search: **zero** occurrences of `device`, `gpu`, `ROCm` or any
equivalent in `src/scheduling/contention.py`, `src/scheduling/contention_gate.py`, or
`src/runtime/cpu_region_lock.py`. Regions are derived purely from NUMA cpusets.

So a role whose weights are VRAM-resident under `-ngl 999`, and whose cpuset exists only to give
it host threads for tokenising and sampling, is accounted **identically to a CPU decode holding
the same cpuset**.

Two concrete wrong answers this produces today:

1. **False exclusion.** `enumerate_feasible()` (`scripts/server/contention_matrix.py:658`) marks a
   role-set `topology_infeasible` whenever no mutually-disjoint cpuset assignment exists. A GPU
   lane and a half/full CPU instance overlap on cpuset, so the set is excluded — even though the
   GPU role's actual draw on the contended resource (DRAM bandwidth on those regions) is close to
   nil. *This is the operator's stated example: GPU-lane usage is not mutually exclusive with
   running half B or a full instance.*
2. **Unmodelled real contention.** Conversely, two GPU roles that share **no** cpuset at all
   contend for HBM bandwidth and VRAM capacity — and the model cannot see it, because it has no
   resource other than CPU regions. The measured four-model GPU steady state is **62.59 of
   63.98 GiB (1.40 GiB headroom)**, and VRAM grows on first *execution*, not at load. Nothing in
   the admission path checks it.

The device axis is therefore not a refinement. It is the difference between the model's resource
vocabulary and the machine's actual resources.

---

## 3. Why batching and context cannot simply become matrix cells

The natural instinct is to add `np` and context depth as further matrix dimensions. The
combinatorics forbid it:

```
roles² × shapes² × np ∈ {1,2,4,8,16,32} × L-buckets
```

Even the 2D NUMA×batch cross alone — waypoint **E5** in
[`batched-decode-measurement.md`](batched-decode-measurement.md) — is described there as *"the
never-measured 2D cross"*, is gated on a post-promotion quiet window, and has not run. The two
axes have only ever been measured **separately**: NUMA-split built the pinning map, `-np` alone is
E1 (`qwen36_q8_0` ladder `np=1,2,4,8,16` complete 2026-07-06).

E5's own hypothesis is the reason this matters: batching amortises the per-token weight read, which
shifts CPU decode from **bandwidth-bound to compute-bound** — so the NUMA-locality advantage *may
flip at high K*, and the crossover point is unknown. A contention verdict measured at one `np` is
therefore not valid at another, in a direction that can reverse.

Enumerating that surface conflicts with the standing operator constraint: **do not re-bench
anything already measured**. So the load axes have to enter as a *computed* quantity, not a
measured cell.

---

## 4. Proposed split: hard constraints vs soft costs

This is the answer to the standing open question — *what belongs in contention management vs the
autopilot/router-exposed surface*. Recommendation, stated so it can be ratified or rejected:

> **Contention management owns hard constraints and must fail CLOSED.
> The router/autopilot owns soft costs and must fail OPEN with a penalty.**

Today's code conflates them, and that conflation is the root defect: a measured ratio of `0.37`
becomes a hard `QUEUE`, so a *stale or missing* measurement can block work that is physically fine.
A cost that cannot be computed should degrade to a penalty, never to a veto.

This maps onto W8's three artifacts:

| # | Artifact | Answers | Needs measurement? | Owner | Failure mode |
|---|---|---|---|---|---|
| 1 | **Feasibility** | *Can these placements coexist at all?* Pure topology + **device**: CPU regions, GPU host cores, exclusivity. | **No** — fully derived from `NUMA_CONFIG` + declared `device`. | Contention mgmt | Fail **closed** |
| 2 | **Capacity fit** | *Does the set fit in the resources?* VRAM, host RAM, host cores. **Non-separable**: KV grows with `np × L`, so this is where batching and context enter — as arithmetic, not as measured cells. | **No** — computed from declared shapes. | Contention mgmt | Fail **closed** |
| 3 | **Interference coefficients** | *How much do they slow each other?* Measured degradation, parameterised rather than enumerated. | **Yes** — the only artifact that does. | Router / autopilot, as a **cost term** | Fail **open** with a penalty |

Two things fall out immediately:

- **Artifact 1 fixes the GPU false-exclusion with zero benchmarking.** Give the feasibility model a
  device concept and "GPU lane + half B" stops being a conflict, because the GPU role's claim is
  *8 host cores*, not *the DRAM bandwidth of every region its cpuset spans*.
- **Artifact 2 gives VRAM a first-class seat.** With 1.40 GiB headroom measured, VRAM is currently
  the binding constraint on the GPU and is entirely unmodelled. It is also *non-separable* — you
  cannot decide it per-pair, only for the whole resident set — which is exactly why W8 insisted the
  raw per-cell vector be defined before any sweep.

---

## 5. Open questions — need an operator ruling before implementation

**Q1 — Ratify the constraint/cost split in §4?** If yes, the follow-on is mechanical: `admit_set`
splits into a feasibility+capacity gate (fail closed) and an interference score (fail open), and
`pair_policy`'s hard `QUEUE` on a low ratio becomes a cost.

**Q2 — GPU host-core accounting.** The proven GPU recipe pins host threads to `taskset -c 184-191`
with `-t 8` (8 logical = SMT siblings of physical 88-95, i.e. region `q3`). W1 currently gives
`architect_general` a 24-thread quarter on `72-95,168-191` instead. Which is canonical? And does a
GPU role hold its host cores **exclusively**, or may a CPU role share them? This decides whether
two GPU roles can share one host lane.

**Q3 — Is VRAM a contention resource or a placement precondition?** i.e. does it belong in
artifact 2 (checked at admission, every request) or only at launch (checked once, when the server
starts)? VRAM grows on first *execution*, which argues for admission-time.

**Q4 — Does the interference model need E5 first?** E5 (NUMA×batch) is designed and unrun. Options:
ship artifact 3 parameterised on the separately-measured axes and let E5 *calibrate* it later, or
block artifact 3 until E5 runs. Shipping first is cheaper and testable; it risks a model whose
crossover term is guessed. Note artifacts 1 and 2 need **neither** — they can land regardless.

---

## 6. Sequencing once ratified

1. **Refresh the parent plan against §1** — it has a locked decision that is now false.
2. **Artifact 1 (feasibility + device)** ✅ 2026-08-01 — `src/scheduling/device_model.py`. Derived, no measurement. NOTE the honest result: on the LIVE topology it changes no verdict, because the GPU lane is SMT-siblings-only and already had empty region sets — the old model was right by accident. On the counterfactual node-3-quarter wiring it admits 10 sets the old model excluded (18/102 → 28/92).
3. **Artifact 2 (capacity fit incl. VRAM)** — derived, no measurement.
4. **Regenerate `contention_matrix.yaml`** ✅ 2026-08-01 — done for topology `171f86f9`, 15 pairs, ZERO catastrophic. `architect_general`+`ingest` 0.66 block → 1.40 allow; every GPU-involving pair concurrency-positive.
5. **Artifact 3 (interference)** as a cost term; E5 calibrates per Q4.
6. Only then the parent plan's Step-2 flag-on, its three bridge residuals, and Part C.

Nothing in steps 2–3 requires inference, a quiet window, or the stack to be idle.

---

## 7. RATIFIED 2026-08-01

**Q1 — constraint/cost split: RATIFIED with an interference veto floor.**
Feasibility and capacity fit are hard constraints owned by contention management and fail CLOSED.
Interference is a router/autopilot cost term that fails OPEN with a penalty — **except** that a
measured catastrophic pair (ratio below ~0.65) still vetoes. Unmeasured pairs get a cost plus a
penalty, never a veto.
*Note for the implementer:* on the current topology there is **no** pair below the floor — the
re-benched matrix has zero catastrophic pairs — so the veto branch is presently unexercised. It must
still be implemented (a future topology can reintroduce one), but it should not be treated as the
common path, and the floor value needs an owner rather than being an anonymous constant.

**Q2 — GPU host lane: RATIFIED as `184-191`, `-t 8`, SHARED between GPU roles.**
Rationale: this is the placement every GPU measurement on this host was taken under (the 27B
SWE-bench arm A3 and the Qwen3-VL MMMU-250 cutover both used `taskset -c 184-191 … -t 8`), so the
deployed shape matches the measured shape and the quality/throughput transfers hold. Two roles
needing ~8 host threads each do not justify fencing 48 physical cores from the CPU fleet.
Consequence already handled: `_assert_instance_invariants` gained a device-aware branch, because
`184-191` is all SMT siblings and reads as ZERO physical cores under the `-t == physical` rule —
the correct placement would otherwise have been rejected at import as infinite oversubscription.

- [ ] **Q3 — is VRAM a contention resource or a launch precondition?** STILL OPEN. `vram_fit` is
      implemented and exported but deliberately not wired into `admit_set`/`seam_admit`: it is a
      set-wide capacity, undecidable per-pair. VRAM grows on first EXECUTION, not at load, which
      argues for admission-time.
- [ ] **Q4 — does the interference model need E5 (NUMA×batch) first?** STILL OPEN. Artifacts 1 and 2
      need neither and are done/scoped.

### Implementation note recorded 2026-08-01

Artifact 1 chose a **2.0 GiB VRAM headroom** (declared total 64 GiB, 63.98 usable). Justification:
declared per-role figures are load-time, and the measured four-model set grew 61.66 → 62.59 GiB
after each model executed once — about 0.93 GiB the sum cannot see. 2.0 covers that with ~2× margin
and leaves the live pair (36.70 + 20.56 = 57.26) feasible with 4.74 spare. Configurable via
`--vram-headroom` / `$ORCHESTRATOR_VRAM_HEADROOM_GIB`. **Nothing declares this number** — it is a
judgement over measured values and is the one restated constant in the artifact.

### Open defect found at 2026-08-02 wrap-up — `slots_by_port` is compile-mode-scoped

- [ ] **Make `runtime.cache.slots_by_port` independent of the compile-time NUMA mode.**
      `orchestrator_stack.py status` reports four attestation warnings against
      CORRECTLY-launched servers:

          server_8080/8180 (frontdoor halves) runtime slots expected 16; live cmdline has 4
          server_8082/8182 (worker halves)    runtime slots expected 16; live cmdline has 4

      The halves are right — per-instance `-np` is full 16 / half 4, set 2026-08-02.
      The producer is right too: `stack_manifest.declared_slots_by_port('frontdoor')`
      returns `{8070: 16, 8080: 4, 8180: 4}`, and recompiling the priors with
      `numa_mode='both'` reproduces exactly that map.

      The COMPILED artifact carries only `{8070: 16}`, because
      `orchestration/derived/stack_priors.yaml` was compiled in the default
      `full` mode while the live fleet runs `both`. Attestation looks up the
      live `--port`, misses, and falls back to the role-level `slots: 16`.

      This is the precise failure `_slots_by_port`'s own docstring says it exists
      to prevent — "it would report drift on correctly-launched servers, which is
      the fastest way to teach a reader to ignore this output." It is now doing
      that, so the warning channel is actively training readers to ignore it.

      Fix direction: `slots_by_port` is a port -> slots LOOKUP, so carrying ports
      that are not launched in the current mode costs nothing and makes
      attestation correct in every mode. Merge the mode-independent
      `declared_slots_by_port(role)` in as a floor. Watch for the circular import
      between `src/registry/stack_priors` and `scripts/server/stack_manifest`
      (already observed emitting "partially initialized module" warnings on the
      `_stack_manifest_info` path) — a lazy import inside the function is likely
      required.

      NOT a functional break: launches are correct, only the attestation
      expectation is wrong. Deferred at wrap-up rather than fixed unverified.
