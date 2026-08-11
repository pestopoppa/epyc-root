# Heterogeneous CPU×GPU Slot Fabric + Dynamic Residency

> ## ⚖ CORE GUIDING PRINCIPLE (OPERATOR-RATIFIED 2026-07-23 — governs every design decision in this handoff)
> **Optionality**: role→slot binding is POLICY DATA, never code — every topology, parallelism
> layout, and residency arrangement must be expressible as configuration the fabric executes.
> Data can be swept; code is a strategic decision forever.
> **Robustness axioms (campaign scars, non-negotiable)**: (1) one fact per physical resource —
> breaker/lock/health/residency on the SLOT, realized-probed, never per-role copies; (2)
> realized-first truth — the device↔model map comes from probing, never launch intent; (3)
> fail-closed residency — unverifiable teleport ⇒ slot UNKNOWN, excluded from placement; (4) no
> mid-decode preemption — session-handover is the only migration primitive.
> **Conversion rule**: a parameter is autopilot-sweepable IFF bounded ∧ reversible ∧
> protocol-measurable ∧ gate-protected; design every parameter to satisfy all four FROM BIRTH so
> strategic→sweepable conversion is a flag flip, not a redesign.
> (Full ratified contract with context: §"Fabric optionality/robustness contract" below.)


**Status (2026-07-20): DESIGN — GATED (post-v7-promotion). Provisioning + lane decisions PENDING
[E5](batched-decode-measurement.md) (NUMA×batch sweep).** No production/stack change proposed here —
this is the target-architecture design distilled from the 2026-07-20 strategic discussion. Nothing is
built until v7 is promoted, the E5 sweep lands, and the operator authorizes.

**This is the GPU / heterogeneous EXTENSION of the *already-live* CPU placement fabric**
([within-role-placement-state-machine.md](within-role-placement-state-machine.md)) — it **reuses and
generalizes** that machinery, it does **not** reinvent it. Read that handoff first.

**Full decision ledger** (13 decisions + corrections + reframes):
`/mnt/raid0/llm/tmp/heterogeneous-slot-architecture-notes-20260720.md`.

## One-line thesis
Model the whole machine as **one slot fabric** — CPU = `N×K` slots (NUMA instances × `-np` batch),
GPU = `1×K_gpu` slots — so that **teleport, residency-swap, and spillover are all slot operations**,
and the orchestrator needs *one* new abstraction (GPU-as-a-placement-target) rather than three
subsystems. Governing principle: **the GPU accelerates; the CPU guarantees.**

## What already exists vs what is new (reconciliation table)
| Discussion abstraction | Already live as (within-role-placement-state-machine.md) | New work here |
|---|---|---|
| CPU slot fabric (`N×K`) | `ConcurrencyAwareBackend` + `ContentionGate` + `NUMA_CONFIG` full/quarter instances per role | add the **`-np` batch dimension** per instance (sized by E5) |
| teleport / migration | KV save/restore migration transaction (WP-3 fwd / WP-4 rev), **session-handover only** | extend the target set to include **the GPU instance**; re-prefill-from-transcript variant |
| hysteresis / anti-thrash | cooldown + session-cap guards + `kv_migration_direction_total` / `thrash_skipped_total` Prometheus counters | add the **N-dwell formula** for the (expensive) GPU residency swap |
| spillover | `ContentionGate` placement fallthrough | fall back to the **designated CPU fallback** when GPU slots are full |
| **GPU placement target** | — | **NEW** — the GPU as an instance in the fabric |
| **residency actuator (Layer 2)** | `orchestrator_stack.py` lifecycle owner | **NEW** — allowlisted load/evict verb + kill-switch |
| **residency scheduler (Layer 3)** | autopilot 4D-Pareto + shadow telemetry | **NEW** — vet allowlist, tune Layer-1 thresholds, autonomously fire swaps in prod |

The load-bearing constraint inherited from the parent: **`_migrate_kv` cannot preempt an in-flight
llama-server decode.** All migration is **session-handover / turn-boundary**, never mid-decode. This
shapes the swap protocol below.

## The three control layers
| Layer | Does | Owner | Timescale | Gated? |
|---|---|---|---|---|
| **1. Runtime dispatcher** | route each request over the slot fabric; teleport-burst to an already-resident GPU model; spillover to CPU | orchestrator (live) | per-request | **No** — can't touch VRAM alloc, only routes to existing slots |
| **2. Residency actuator** | load/evict *which model occupies* the GPU slot | `orchestrator_stack.py` | minutes | **Yes** — the ONLY VRAM-touching op; allowlist + hysteresis + kill-switch |
| **3. Policy tuner / scheduler** | shadow-measure → vet allowlist → tune Layer-1 → **autonomously fire Layer-2 swaps in prod** | autopilot | background | its own gates |

Safety invariant: **only Layer 2 touches VRAM allocation.** Layer 1 is structurally incapable of
breaking the VRAM invariant, so it runs flat-out, ungated.

## Core mechanisms

**Resource asymmetry.** VRAM (64 GB) is the *only* scarce resource; CPU+RAM dual-residency is free
(1.1 TB) → every teleport-eligible model stays hot in RAM permanently (zero CPU-side load latency).
Two big IQ2 don't co-fit (122B 40 GB + 80B 26 GB); realistic 2-resident = **1 big GDN (122B-IQ2) + 1
small (35B-A3B IQ4) ≈ 58 GB**.

**Teleport = re-prefill (v1).** Transcript-only (the orchestrator already stores it → **no KV
plumbing**). Quant-asymmetric teleport makes a *copied* KV wrong (computed from different weights), so
re-prefill regenerates correct KV at the target quant. **KV-copy = v2**, long-context only — and
**near-moot** because our GPU residents are **GDN-hybrids with O(1) KV**. **KV-in-RAM offload** buys
capacity but is not free (HBM ~1.6 TB/s vs PCIe ~26 GB/s, ~60×) — negligible for O(1)-KV residents,
severe only for a full-attention/long-context model (dense-27B, bench-gated).

**Designated CPU fallback (generalizes "CPU copy").** Every GPU model has a fallback: its **own CPU
copy** for dual-resident models; a **substitute model** (122B-Q4 / 35B) for a **GPU-only** model
(dense-27B, ~4.4 t/s on CPU → no viable self-home). This is what keeps availability continuous.

**Swap protocol (evict A → load B) — respects no-mid-decode-preemption:**
1. **Quiesce** — dispatcher flips A's GPU slots to *draining*; new A-traffic routes to A's CPU fallback (spillover). Instant flag flip.
2. **Drain at turn boundaries** — each in-flight A session migrates to its CPU fallback **when its current decode completes (session-handover)** — NOT forced mid-decode. Slots free as sessions hand over. (For dual-resident A, this is a reverse-teleport; quality delta follows A's (CPU,GPU) quant pair — 122B up, frontdoor neutral, worker mild-down — always correct.)
3. **Reclaim + load B** — free A's VRAM, load B into HBM (the expensive seconds). **The CPU grid serves continuously throughout** (HBM load touches only the GPU).
4. **Admit to B** — dispatcher marks B resident; routes/teleports B-eligible sessions to it.
Fail-safe: CPU-fallback floor (no outage), no in-flight loss, **abortable until B is healthy** (kill-switch = revert to all-CPU), atomic routing epoch, rate-limited by hysteresis.

**Hysteresis + min-dwell.** Swap-in threshold > swap-out threshold; **min-dwell `N ≥ C·(1−X)/X`**
(C = measured swap cost, X = tolerated blended-throughput loss; C=20 s, X=5% → N ≈ 6.3 min). Reuses the
parent's anti-thrash cooldown/session-cap. **Policy prior:** swap on *sustained regime change*, NOT
transient bursts (e.g., an architect firing a research fan-out keeps the card and bursts the cheap MoE
fan-out on the CPU grid — it returns to synthesize, so don't pay a double load).

**Tracked-session promotion (Option 3).** Track a session iff **(router value/difficulty prior high)
OR (observed length ≥ break-even floor ~150–250 tokens)**; TTL/LRU demote on idle. Archetypes =
**delegating parents, escalated sessions, multi-turn consults**; never-tracked = one-shot
classifications / single eval questions / terminal frontdoor answers / one-shot fan-out children.
**Escalation is a discrete teleport trigger** (context + hard-judgment spike together). All thresholds
autopilot-tunable from shadow data; index updates are in-band (dispatcher routes every turn anyway).

**Per-model (CPU-quant, GPU-quant) pairing** is a first-class parameter (drives reverse-teleport
quality direction; = the quant-asymmetric IQ2-draft/Q4-verify idea generalized across the stack).

**Autopilot ownership.** Decide now / actuate later: **Phase 1** autopilot shadow-measures → produces
the **vetted allowlist** (its own deliverable); **Phase 2** autopilot gets a *bounded* actuator — select
among the allowlist, behind `orchestrator_stack.py` + the 3 gates. Never "deploy any server." CPU-lane
provisioning is inherently low-risk (RAM/cores abundant) and can be managed more liberally than the
tightly-gated GPU residency (the danger was VRAM *scarcity*).

## Open — pending E5 (do not freeze until the sweep lands)
- Is the CPU side **"N NUMA quarters"** or **"1 full pool"**? (E5 iso-concurrency decides.)
- Are **workload-class lanes** real (a low-K latency lane vs high-K throughput lane)? If no crossover, the dispatcher stays simple.
- `K_gpu` and per-instance `-np` sizing.
- Residency-scheduler home: autopilot's Phase-2 actuator vs a distinct orchestrator-runtime component.

### GAP (filed 2026-07-29, fable-auditor via claude-gpu-lane) — GPU **host threads** are an implicit consumer with no slot

This design models the GPU as a **placement target** and `q0..q3` as the CPU resource set. It does
not model the CPU threads the GPU lane's own **host submission threads** occupy (measured shape:
8 threads, currently logical 184-191). Today they are an **implicit consumer**: they consume CPU
threads with no slot, no lease and no epoch, so the daemon's quiesce-drain machinery cannot cover
them, and the lane's true CPU footprint is invisible to the fabric that is supposed to arbitrate it.

**This needs zero parallel machinery** — the ratified frame already fits: extend the resource set
(`q0..q3` **+ `gpu-host`**) and give the lane's host threads a slot-shaped roster entry with a
lease, exactly like any other tenant. Leases sit above the flock per the contract, so the existing
axioms hold unchanged.

Recorded now, **built later**: this is the durable home for whichever host-thread reservation wins
(a `gpu-host` region name, or a static SMT carve on the hosting quarter), and that choice is not
due until the lane-residency verdict. The point of filing it now is that **the fabric must not be
finalised without it** — a resource set that omits a known consumer will read as complete.

⚠ Do not assume the reservation lands on `q3`: the MI210 is **NUMA node 1**-attached
(sysfs `numa_node=1`), so today's 184-191 placement is already cross-node and device-local
candidates were never measured. See `gpu-serving-tie-in-program.md` → **P2-5j**, which must run
before any carve is minted.

- [ ] Model GPU host threads as a fabric slot (`gpu-host`) — design only, gated on the residency verdict

## Task list (all GATED — post-v7-promotion + post-E5; nothing starts before then)
- [x] Architecture designed + reconciled against the live placement fabric ✅ 2026-07-20
- [ ] **Consume E5** — set the CPU (N,K) provisioning + resolve the lanes question from the sweep
- [ ] **Model-keyed capability records replace role-keyed NUMA/spec config** (operator-directed 2026-07-23; the model-side completion of the ratified optionality principle). Today `NUMA_CONFIG` + spec/launch recipes are keyed by ROLE (frontdoor's entry encodes the 35B's half-wins result; worker_general's encodes gemma's interleave/MTP quirks), so a model swap under a role is a bespoke lineup event (2026-05-08 worker swap precedent). Invert into per-model capability cards — model+quant → {optimal solo shape, NUMA-splitting potential, per-shape `-np` optima (E5 R4 rows are the first population), ctx/KV config, spec-dec recipe + accept rates, platform-labeled top specs, policy quirks} — with role entries and WP-12 fleets holding REFERENCES only. Payoffs: (a) model swap = flip the reference + §H recert, nothing else — this also yields the missing model-swap-under-role runbook (alias runbook + `new-model` skill are partial today); (b) contention-matrix rows indexed by (model_a, model_b, shape-pair) instead of role+instance become REUSABLE across swaps — the §H recert shrinks to never-measured pairs only (the derived `placement_overlap`/topology_hash layer is already deterministic recompilation; only the measured throughput verdicts are physical facts of the model stack).
- [ ] **Design the GPU-as-placement-target** extension to `ConcurrencyAwareBackend`/`NUMA_CONFIG` (GPU instance in the fabric)
- [ ] **Layer-2 residency-actuator verb** on `orchestrator_stack.py` (allowlisted load/evict + kill-switch) + the swap protocol (session-handover drain)
- [ ] **Teleport-to-GPU** = the re-prefill-from-transcript variant of the existing migration transaction
- [ ] **Tracked-session index** (Option 3 predicate) wired to the router/escalation signals
- [ ] **Layer-3** autopilot residency policy: shadow-measure → vet allowlist (Phase 1) → bounded auto-select (Phase 2)
- [ ] **N-dwell / hysteresis** for GPU swaps (extend the parent's anti-thrash with `N ≥ C·(1−X)/X`)

## Key files / cross-links
- Parent (reuse): `src/backends/concurrency_aware.py` (`ConcurrencyAwareBackend`), `ContentionGate`, `scripts/server/stack_numa.py` (`NUMA_CONFIG`), the KV-migration transaction (WP-3/WP-4), `src/metrics/migration_counters.py` — all in [within-role-placement-state-machine.md](within-role-placement-state-machine.md).
- Lifecycle: `epyc-orchestrator/scripts/server/orchestrator_stack.py` (Layer-2 actuator home).
- Parameterizing input: [batched-decode-measurement.md](batched-decode-measurement.md) **E5**.
- Related: [mi210-big-model-and-acceleration-roadmap.md](mi210-big-model-and-acceleration-roadmap.md) (teleport AXA / residency ladder), [architect-model-selection-bench.md](architect-model-selection-bench.md) (GPU-only-architect deployment cost), [inference-acceleration-index.md](inference-acceleration-index.md) (dispatch).

## Reporting
On any phase: flip its `- [ ]`, record the measured constant (E5 provisioning, C for N-dwell, allowlist
contents) with a MEASUREMENT stamp. No stack/production change lands without the operator + the 3 gates.

## Fabric optionality/robustness contract (OPERATOR-RATIFIED 2026-07-23 — "couldn't agree MORE"; governs the fabric design session)

**Optionality principle**: role→slot binding is POLICY DATA, never code — every topology in the
escalation option space (A-D, eval-tower-verification.md), every parallelism layout, every
residency arrangement must be expressible as configuration. Data can be swept; code is a
strategic decision forever.

**Robustness invariants (2026-07-22/23 campaign lessons, promoted to axioms)**:
1. One fact per physical resource — breaker/lock/health/residency on the SLOT, realized-probed,
   never per-role copies (ESC-8 / 90x-churn, extended to devices).
2. Realized-first truth — device↔model map from probing, never launch intent (the manifest lesson;
   a stale "GPU holds architect" record is a future phantom-lineup outage).
3. Fail-closed residency — unverifiable teleport ⇒ slot UNKNOWN, excluded from placement (REL-1
   applied to placement).
4. No mid-decode preemption; session-handover is the only migration primitive (proven).

**Conversion rule (strategic→sweepable boundary)**: a fabric parameter is autopilot-sweepable IFF
bounded ∧ reversible ∧ protocol-measurable ∧ gate-protected. Static remainder: device inventory,
per-device quant artifacts, safety envelopes, the residency-capable model set. DESIGN DISCIPLINE:
build every parameter to satisfy the four properties from birth so conversion is a flag flip.

**Declared instances of this contract (2026-07-27)**: the contract above is not specific to GPU
residency — it is the general **resource-admission blueprint**, and two subsystems already
implement it independently:

| Element | Orchestrator CPU placement | Session bus (agent dispatch) |
|---|---|---|
| Resource set | CPU regions `q0..q3` | lanes `cpu/gpu/none`, slot-shaped roster |
| Exclusive claim | `src/runtime/cpu_region_lock.py` (`LOCK_EX` per region, union acquire, LIFO release) | task claim + `lease_expires_ts` + epoch fencing |
| Co-residency policy as data | `orchestration/contention_matrix.yaml` (ratio, `verdict`, `default_floor`, `topology_hash`) | `contention_class` + `config.yaml` |
| Admission gate | `src/scheduling/contention_gate.py` `evaluate()`/`admit()` | coordinator-daemon eligibility rule |
| Typed defer reasons | `src/scheduling/placement.py` `QueueReason` | `queue.jsonl` status enum |

Consequences already acted on, tracked as R1/R3 in
[session-bus-thin-dispatcher.md](session-bus-thin-dispatcher.md) §Rider:

- **Axiom 1 forbids a second occupancy notion.** Benchmarks previously took no region lock at all
  while orchestrator dispatch did — three disjoint exclusion domains over the same cores. Closed
  2026-07-27 via `epyc-orchestrator/scripts/region-lock`, a wrapper over the *same*
  `cpu_region_lock()`. Observing holders is not exclusion (TOCTOU); only acquiring is.
- **Axiom 4 shapes every reclaim path.** Lease revocation and priority preemption are
  quiesce-and-drain at a boundary, reusing the swap protocol above — never forcible. A held
  `flock` cannot be revoked by a third party in any case, so lease authority must sit in an
  advisory layer above it, with the flock remaining liveness truth (axiom 1).

**Unification remains deferred** behind this handoff's existing triggers (a local-model
long-horizon main, or the slot fabric landing "everything is a slot"). What converges now is
vocabulary and data shape, not implementations — bounded, reversible, and gate-protected per the
conversion rule.

**Inputs required before the full design session** (per the design-session discipline for
NUMA/concurrency complexity): E5 NUMA×batch mapping, teleport break-even measurements, and the
architect-bench GPU-arm results (the first heterogeneous binding candidate).

## 2026-08-09 — async generation/execution split (research-intake Stage-2b, HYPOTHESIS)

- [ ] **HYPOTHESIS ONLY — asynchronous separation of generation from candidate execution.**
  OpenMLE-Evo ([intake-1024](../../research/intake_index.yaml), dive-verified) runs generation and
  sandbox execution as independent queues, and intake-940's dive measured the claimed step-time
  speedup at 1.91x. **That win exists because their generation runs on a GPU while execution runs
  elsewhere.** On a CPU-bound box the two contend for the same cores and the mechanism inverts into
  contention — which is precisely what the co-residency and region-claim discipline exists to prevent.
  **This is explicitly NOT a portable win.** The single condition under which it could transfer is a
  genuine heterogeneous split: generation resident on the MI210, candidate execution on CPU. Evaluate
  only as part of a binding-candidate design session, never as an assumed speedup, and note the
  measured figure is from a source whose headline claims intake-940 largely overturned.
