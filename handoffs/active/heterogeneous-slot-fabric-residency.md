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

> **Correction 2026-09-24 (conversation-stack session):** the premise below, that the orchestrator already stores the transcript, is
> false for `/v1`. `x_session_id` is recorded only (orch `src/api/models/openai.py:192-202`), and the session store has no
> messages table (`src/session/sqlite_store.py:123-257`). A session-keyed conversation store is filed as
> [`conversation-stack.md`](conversation-stack.md) CS-15. Until it lands, v1 teleport depends on client-resent history.

**Teleport = re-prefill (v1).** Transcript-only (the orchestrator already stores it → **no KV
plumbing**). Quant-asymmetric teleport makes a *copied* KV wrong (computed from different weights), so
re-prefill regenerates correct KV at the target quant. **KV-copy = v2**, long-context only — and
**near-moot** because our GPU residents are **GDN-hybrids with O(1) KV**. **KV-in-RAM offload** buys
capacity but is not free (HBM ~1.6 TB/s vs PCIe Gen4 H2D 28.89 GB/s measured 2026-08-03, epyc-inference-research/data/mi210-h2d-d2h/20260803T131500Z/, ~55×) — negligible for O(1)-KV residents,
severe only for a full-attention/long-context model (dense-27B, bench-gated).

**Prefill placement rule — candidate (2026-09-26, research intake; design-only, inputs unmeasured).** For an over-HBM MoE whose weights stay DRAM-resident (one weight copy; the GPU never holds the model), send a prompt of length L to a GPU streaming path only if T_gpu(L) < T_cpu(L). Here T_cpu(L) = L / R_cpu(L) (CPU prefill rate at length L, on the served artifact and the production recipe) and T_gpu(L) ≥ S / B_h2d, with B_h2d = 28.89 GB/s measured (34.6 ms per streamed GB). S is what the path streams. For llama.cpp op-offload (the path we have), S = ceil(L/ub) × W_offloaded, because offloaded weights are re-sent every ubatch (hypothesis; PF1 tests it). For a stream-once-per-prompt design (1810's SLP; no code released), S = W_experts once. Consequence: -ub is a first-class knob of the rule, not a detail. Do NOT carry 1810's 4K switch: it is a policy on a PCIe 5.0 link whose bandwidth the paper never states (intake-1810#01). Precondition: a GPU slot is free to host the streaming instance, which is a Layer-2 decision; Layer 1 can only route to an instance that already exists. Inputs are bench-class (llama-bench) until a serving-class confirmation exists.

**Designated CPU fallback (generalizes "CPU copy").** Every GPU model has a fallback: its **own CPU
copy** for dual-resident models; a **substitute model** (122B-Q4 / 35B) for a **GPU-only** model
(dense-27B, ~4.4 t/s on CPU → no viable self-home). This is what keeps availability continuous.

**Swap protocol (evict A → load B) — respects no-mid-decode-preemption:**
1. **Quiesce** — dispatcher flips A's GPU slots to *draining*; new A-traffic routes to A's CPU fallback (spillover). Instant flag flip.
2. **Drain at turn boundaries** — each in-flight A session migrates to its CPU fallback **when its current decode completes (session-handover)** — NOT forced mid-decode. Slots free as sessions hand over. (For dual-resident A, this is a reverse-teleport; quality delta follows A's (CPU,GPU) quant pair — 122B up, frontdoor neutral, worker mild-down — always correct.)
3. **Reclaim + load B** — free A's VRAM, load B into HBM (the expensive seconds). **The CPU grid serves continuously throughout** (HBM load touches only the GPU).
4. **Admit to B** — dispatcher marks B resident; routes/teleports B-eligible sessions to it.
Fail-safe: CPU-fallback floor (no outage), no in-flight loss, **abortable until B is healthy** (kill-switch = revert to all-CPU), atomic routing epoch, rate-limited by hysteresis.

> **Amendment 2026-09-26 (research intake; intake-1819#1, intake-1819#7, intake-1819#10):** step 2's "drain at turn boundaries" is necessary, not sufficient. A call boundary inside a live agent session is exactly where a model's window closes on a pending return: Talaria measured it on its own Aegaeon-like round-scheduler ablation (disabling session-prefill raises p50 session completion time from 189 s to 623 s), not on Aegaeon. Reclaim model A only at SESSION quiescence — no tracked A session completed a call within the last τ (τ from HSF-3). When a swap cannot wait (kill-switch, regime change), first `POST /slots/{id}?action=save` for every idle A slot holding a tracked session; production v10 permits a save only on an idle slot (server-context.cpp:2593-2596 @ffc1bac8). The save pays off only when the session returns to the same GGUF/quant (the recovery term under the tracked-session index task); otherwise it re-prefills. Do not rely on `--cache-ram`: that host prompt cache is in-process and dies with the evicted server. Axiom 4 unchanged; no kernel change.

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
  - Card fields (2026-09-26, intake-1787#01, #03): `swap_cost_hot_s` {median, interval, n, receipt refs; filled by
    HSF-1} and `partial_offload_curve` {`-ngl` fraction → decode t/s}. Both are per (model, device), because offload
    sensitivity is model- and device-specific. They are model-keyed, never role-keyed.
- [ ] **Design the GPU-as-placement-target** extension to `ConcurrencyAwareBackend`/`NUMA_CONFIG` (GPU instance in the fabric)
  - Spillover measurement arm (2026-09-26, intake-1817#4; design only, inherits this task's gate): when Layer-1 spillover is measured, include a partial-offload arm — under deep GPU queueing, route a fraction r of NEW sessions whole-request to the designated CPU fallback (no KV handoff; re-prefill per the teleport rule, :73-78) and report TTFT, TPOT and completed requests/min against GPU-only at matched load, with P-GPU-1 device-state capture and the codified CPU recipe. Dynamo's PR ratios are author-reported with no hardware, load or r-control stated; they are not a prior. Reuse DAR-LAT-3's driver (`scripts/benchmark/selection_loadsweep_ab.py`, decision-aware-routing.md); the CPU-speech collision (kv-unified-stack-rollout.md KVU-11b) and MEAS-6 host coupling are in scope. Belief kernel: VB-SPILL-TTFT (activation record).
- [ ] **Layer-2 residency-actuator verb** on `orchestrator_stack.py` (allowlisted load/evict + kill-switch) + the swap protocol (session-handover drain)
- [ ] **Teleport-to-GPU** = the re-prefill-from-transcript variant of the existing migration transaction
- [ ] **Tracked-session index** (Option 3 predicate) wired to the router/escalation signals
  - KV-recovery term and single session table (2026-09-26, intake-1819#5, intake-1819#11): when a tracked session returns and its GPU home is draining or evicted, the placement cost of its next call adds an explicit recovery term — 0 (slot still warm), slot-file restore (same GGUF/quant only; dual-resident pairs are quant-asymmetric, :74-76, so a cross-device restore is invalid), or full re-prefill on the CPU fallback priced by R_cpu(L) (mi210-big-model-and-acceleration-roadmap.md PF1) — so the fallback is never treated as free because it has spare slots. Talaria's router data show load-only placement reopening models and losing KV. This index is the ONE per-session state table: identity comes from harness-selection-and-integration.md HS-16's resolver, idle expiry from HSF-3, and kv-unified-stack-rollout.md KVU-14 reads it rather than building a second table (Axiom 1).
- [ ] **Layer-3** autopilot residency policy: shadow-measure → vet allowlist (Phase 1) → bounded auto-select (Phase 2)
  - Policy prior (2026-09-26, intake-1789#02):
    - When a swap to model B fires, admit queued and tracked B-eligible sessions as ONE group before any swap back.
    - The bound `swap_group_max` is policy data: bounded, reversible, sweepable per the conversion rule. Do not
      import Aegaeon's constant.
    - Session quiescence only (the 2026-09-26 swap-protocol amendment after :91), under the existing drain protocol
      (:86-91). This amortizes C over the group without preemption.
  - Regime-change input (2026-09-26, intake-1815#1, intake-1815#4): report each role's routed-traffic share (final role from the DAR-LAT-2 selection receipts, decision-aware-routing.md; admission-ledger dispatch counts) beside its allocated compute (device, NUMA instance count), and flag a role whose share and allocation diverge under sustained load. RouterWise's only material placement losses are whole-device-per-model isolation under skewed load at a small device budget; a load- or size-proportional fixed rule recovers most of its searched optimum (predicted score from profiled curves, not measured). Regime-change timescale only (Layer 2/3, minutes); never a per-request placement signal; no new telemetry (Axiom 1, :218).
- [ ] **N-dwell / hysteresis** for GPU swaps (extend the parent's anti-thrash with `N ≥ C·(1−X)/X`)
- [ ] **Prefill placement rule — fill R_cpu(L) and R_gpu(L, ub) from mi210-big-model-and-acceleration-roadmap.md PF1, then decide whether Layer 1 gets a length threshold** (design only; blocked on PF1)

## Key files / cross-links
- Parent (reuse): `src/backends/concurrency_aware.py` (`ConcurrencyAwareBackend`), `ContentionGate`, `scripts/server/stack_numa.py` (`NUMA_CONFIG`), the KV-migration transaction (WP-3/WP-4), `src/metrics/migration_counters.py` — all in [within-role-placement-state-machine.md](within-role-placement-state-machine.md).
- Lifecycle: `epyc-orchestrator/scripts/server/orchestrator_stack.py` (Layer-2 actuator home).
- Parameterizing input: [batched-decode-measurement.md](batched-decode-measurement.md) **E5**.
- Related: [mi210-big-model-and-acceleration-roadmap.md](mi210-big-model-and-acceleration-roadmap.md) (teleport AXA / residency ladder), [architect-model-selection-bench.md](architect-model-selection-bench.md) (GPU-only-architect deployment cost), [inference-research-index.md](inference-research-index.md) (dispatch).

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
  sandbox execution as independent queues, and intake-940#record's dive measured the claimed step-time
  speedup at 1.91x. **That win exists because their generation runs on a GPU while execution runs
  elsewhere.** On a CPU-bound box the two contend for the same cores and the mechanism inverts into
  contention — which is precisely what the co-residency and region-claim discipline exists to prevent.
  **This is explicitly NOT a portable win.** The single condition under which it could transfer is a
  genuine heterogeneous split: generation resident on the MI210, candidate execution on CPU. Evaluate
  only as part of a binding-candidate design session, never as an assumed speedup, and note the
  measured figure is from a source whose headline claims intake-940#record largely overturned.

## Research Intake Update — 2026-09-26 (orchestration prior art: slot record, swap cost C, residency declines; intake-1783/1787/1789)

**Slot-record fields, schema only (c3-A2).** DAR-LAT-1 in decision-aware-routing.md is the single runtime
implementation; this handoff owns the schema. The fields use proposal-003 semantics (intake-1783#01), internal only:
- `queued` ← `llamacpp:requests_deferred`, falling back to ledger waiting.
- `running` ← `llamacpp:requests_processing`, falling back to ledger in_flight, cross-checked against `/slots` busy.
- `kv_occupancy` = Σ(n_prompt_tokens+n_decoded)/Σ n_ctx over processing slots (intake-1783#07).
- Every field carries a source label.
- KV is reserved at launch (contention rider :193), so `kv_occupancy` is context-fill, never memory pressure. For
  GDN-hybrid residents only the attention layers' KV scales with tokens; do not route on it for them.
- EPYC-only fields beside the three: `device_class`, `numa_node`/`cpuset`, residency state incl. `UNKNOWN`, co-tenant
  count, measured prompt/predicted t/s.
- No upstream home for those fields (intake-1817#2, intake-1817#3): at Dynamo 81a9871a a CPU decode worker is an untyped decode worker — ModelRuntimeConfig has no CPU/GPU/XPU field, the default worker cost has no device or throughput term, and CPU bias is possible only through hand-set taints — and the Planner budgets in GPUs. Keep `device_class` and measured t/s as EPYC fields; do not wait for an upstream contract.
- Not an exporter and not an EPP feed: fronting with a GAIE EPP is declined (dynamic-stack-concurrency.md, 2026-09-26).

- [ ] **HSF-1 — Write a launch-phase receipt on every production GPU launch; it is the measured swap cost C per
  (model, MI210).**
  - Written from orch @fb7871ea `orchestrator_stack.py` (GPU path :1259-1275) to
    `orchestration/reports/launch_phase/<role>-<UTC>.json`.
  - Timer from stderr: process start → `load_model` → `model loaded` → health → first token.
  - Also: effective argv, binary + kernel-store digest, GGUF sha256, `fincore` page-cache fraction before exec, and
    outcome class.
  - Fit rule: once each of ≥3 model sizes has ≥5 hot receipts (page-cache fraction ≥0.99; colder launches counted
    and labelled), fit C = a + size/b (intake-1787#03, intake-1789#04). Holdout is leave-one-model-out.
  - Write per-model C into the capability card (:151) and replace the illustrative C=20 s in N-dwell (:95-96).
  - Cold/post-reboot C stays gated (mi210-big-model-and-acceleration-roadmap.md:296).
  - Plan approval 2026-09-26 authorizes HSF-1 and HSF-3 only (passive instrumentation and a log read); the rest of this list stays GATED.
- [ ] **HSF-2 — Add `--metrics` to CPU llama-server launch argv in the next stack-change package.** Today it is set
  only on the GPU path (orch @fb7871ea `orchestrator_stack.py:1267`; live :8074 argv has none), so `queued`/`running` fall back
  to the ledger on CPU roles. Bundle with the next signed stack change; never an ad-hoc relaunch.
- [ ] **HSF-3 — Measure the per-session inter-call gap distribution from existing logs (zero inference).** Gap = model response complete → next enqueue for the same session, per role and per client class (OpenCode `/v1` harness, `/chat`/REPL, autopilot). Sources: inference-tap structured events (`request_keys.x_session_id`; orch `src/llm_primitives/inference.py:1198-1200`), progress-log session events (`orchestration/repl_memory/progress_logger.py:768-800`) and `/chat` session checkpoints (`src/session/sqlite_store.py:184`). Step 0 prices the source: count sessions carrying a session key plus completion and next-enqueue timestamps; a class with <50 such sessions is recorded as a gap and deferred to HS-4 P0.4/HS-14 runs. Publish p50/p90/p99 with n per class and a later-window replicate. Consumers: τ in the swap-protocol amendment (:93), the tracked-session TTL (:102), HS-16's idle-retention TTL, dynamic-stack-concurrency.md G5's gap lengths, kv-unified-stack-rollout.md KVU-14's forced-resume timeout. Talaria's τ=1 s is sized to its own sub-second p90 and is NOT carried (intake-1819#4, intake-1819#12). Plan approval 2026-09-26 authorizes this item. Belief kernel: VB-GAP-DIST.
  2026-10-05 source boundary: prospective native pair wiring is implemented and 21 fixtures pass. One claimed serving-call journal census has 19 records missing session keys, zero eligible pairs and no tuple; this does not price all listed sources or establish a distribution. [Original census custody](../../progress/2026-10/2026-10-05-ni10-gap-census.md). Read-only [schema mapping](../../progress/2026-10/2026-10-05-hsf3-source-map-ni32-proposal.md) finds tap/progress/checkpoint contracts independently lack the exact completion/enqueue/class pairing fields; no raw tap or database census occurred.
  - [ ] **HSF-3-SCHEMA-BOUNDARIES (NI05-32)** — add synthetic source-schema coverage/refusal cases for tap, progress and checkpoints alongside native exact/proxy positive controls. Report counters without inferring joins/enqueues/client brands; no live data, new grading class or distribution from fixtures.


**Trigger (prose, no checkbox):** if HSF-1 has <5 hot receipts per model after 30 days, request a bus-granted GPU
window for a 5-launch series per model, with residents drained under the swap protocol by the stack-owning session.

**DECLINED — token/step-level GPU model multiplexing, Aegaeon-style (C5-A2; intake-1789#01, #03, #07).**
- It is mid-decode preemption, which axiom 4 forbids.
- It needs engine internals llama-server lacks: in-process component reuse, a host KV pool, IPC-event KV sync, and
  in-flight slot KV save (production v10 defers save/restore while a slot is processing, server-context.cpp:2593-2596).
- Prefetch-hiding needs VRAM for a second model beyond the ~58 GB 2-resident set (:65-66).
- The authors concede static multiplexing at strict SLOs, and the CPU fallback grid already absorbs the head-of-line
  blocking Aegaeon targets.
- Revisit only if a llama.cpp-experimental llama-server gains cooperative decode preemption
  (within-role-placement-state-machine.md:31).
- Talaria's cold-pool mechanisms (session-prefill mid-slot admission, bump-managed HBM, host KV registry, D2D weight staging) are declined on the same grounds: SGLang/VMM/CUDA-graph engine internals, and cold-pool decodes are time-sliced across rounds — mid-generation parking, which axiom 4 forbids. Talaria itself pins stable traffic to never-switching hot instances, which is our role shape and supports static residency (intake-1819#3, intake-1819#6, intake-1819#8).

**DECLINED — importing 2605.19593's absolute reload seconds or its "~2% overhead" into any EPYC cost model or dwell
calculation (C5-A5; intake-1787#02, #04).**
- Those figures come from single-request FP16 HF-Transformers on NVIDIA, with page-cache state unstated and a
  7,000-token-job denominator.
- Only the cost-model FORM transfers: a fixed penalty per (model, device). HSF-1 measures ours.

**DECLINED — a RouterWise-style joint placement+routing optimizer (2b-routerwise-A3; intake-1815#4, intake-1815#5).** Its own Figure 6 shows a sensible fixed allocation rule matching or nearly matching the searched setup in most cells (predicted score, not measured); its deployed comparison pits it against latency-blind routers on isolated placement; its fractional-compute knob (MPS caps) has no counterpart when the GPU footprint is fixed at launch (contention rider :192-194). Placement here is a gated Layer-2 or signed stack change. Reopen only if decision-aware-routing.md DAR-LAT-3 shows static-prior losses that track placement.
