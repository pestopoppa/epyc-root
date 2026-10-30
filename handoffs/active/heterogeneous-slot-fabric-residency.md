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

**Scratch**: `/mnt/raid0/llm/tmp/codex-ni-20261027-hsf5p-repair-c5/`, `/mnt/raid0/llm/tmp/codex-ni-20261027-hsf-determinism-job/`, `/mnt/raid0/llm/tmp/codex-ni-20261027-hsf-restore-source-audit/`, `/mnt/raid0/llm/tmp/codex-ni-20261027-hsf-profile5/` · worktrees: none

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
  - [x] **HSF-3-SCHEMA-BOUNDARIES (NI05-32)** — add synthetic source-schema coverage/refusal cases for tap, progress and checkpoints alongside native exact/proxy positive controls. Report counters without inferring joins/enqueues/client brands; no live data, new grading class or distribution from fixtures.


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

2026-10-05 reviewed source boundary: NI10 explicit optional `x_client_class` validates and forwards self-reported metadata with `caller_supplied:x_client_class` provenance; omitted fields remain absent. App source is published at `099dc1af69cf`. Original CI 37325396069 verifies 1/1 ordinary capacity refusal and 17/17 synthetic request-to-record controls. NI32 source59e adds 12/12 native/exact/proxy and tap/progress/checkpoint schema controls; original CI37326107920 is TRUE Judged/Located. The preceding 8/12 failed fixture expectation remains FALSE unchanged; missing-ledger custody correctly refuses to report OK (SC73). Neither fixture result supplies live gap data. HSF-3 remains open pending ≥50 properly keyed/classed sessions per reported basis in each independent window; no percentile, client brand, TTL or inferred enqueue. Delivery tally **34/36**.

## Research intake 2026-10-20 — DeepInfer (research intake entries 2116–2142, see research/intake_index.yaml)

Operator-approved 2026-10-20 via research intake (plan sha256 recorded in the session's stage3_filing).

- [ ] **HSF-3.1 — Return-within-T curve per client class from the HSF-3 gap data (intake-2136#record).** For T in {3 min, 1 h, 24 h, 72 h, 7 d} report the fraction of sessions whose next call arrives within T, per role and client class, with n and a later-window replicate; zero inference. Consumers: tracked-session TTL, prefix-store retention, the DS41 window-state vs block-state tier choice (KPF-28). Vendor TTLs are a prompt, not a target.
  - *(2026-10-20, workspace-f8.)* NOT JUDGEABLE: 0 eligible session-keyed completion->next-enqueue pairs (10 session_created records in 122 progress files, no client class); no fractions reported; evidence /mnt/raid0/llm/tmp/analytics-20261020/HSF-3.1/REPORT.md.
  - *(2026-10-24, f8 sweep.)* Still NOT JUDGEABLE: 0 session-keyed dispatch.v1 records (108 ever, 10-21 13:02Z to 10-23 13:55Z, none with `session.key`; `client.class` `orchestrator_internal` 82, null 26). The live API (uvicorn :8000 pid 3663075, started 2026-10-23 16:19:44Z on `fd1a8941`, which contains 78f68032/249d7da5/058e674b) has written 0 records since: only `/health` traffic. Accrual 0/day, so no date can be projected. Waits on session-keyed traffic with `x_client_class` reaching the live API (OpenCode `/v1`, `/chat`/REPL, an autopilot run); >= 50 per basis in each of two windows. Rerun-ready: `nice -n 19 /usr/bin/python3 -I /mnt/raid0/llm/tmp/analytics-20261024/HSF-3.1/return_within_t.py --since 2026-10-23T16:19:44+00:00 --out /mnt/raid0/llm/tmp/analytics-20261024/HSF-3.1/results_since_api_start.json` (right-censoring and the two-window gate built in; synthetic positive control passed). Evidence `/mnt/raid0/llm/tmp/analytics-20261024/HSF-3.1/REPORT.md`.
- [x] **HSF-3.1a — add session-keyed completion->next-enqueue gap logging with client class**, prerequisite of HSF-3.1. (derived 2026-10-20 from /mnt/raid0/llm/tmp/analytics-20261020/HSF-3.1/REPORT.md) ✅ 2026-10-21
  - *(2026-10-21, noninf-offline.)* the same dispatch.v1 record (see WP-15.1 note, `src/backends/dispatch_log.py`) carries `session.key` (sha256[:16] of the session id; id not logged), `session.source`, `client.class` + provenance (`x_client_class` only; absent when the caller did not supply one), `ts_arrival`, `ts_end`; the gap is derived by the reader as next.ts_arrival - prev.ts_end per session.key (cross-worker, one flocked file). Also written by the passthrough route and by direct single-server backend calls (fleet state null; session from x_session_id / x-session-id / x-dynamo-session-id, class from x_client_class / x-client-class). Live after the next stack start; epyc-orchestrator main 78f68032. Logging only: HSF-3.1 itself stays open until >=50 keyed/classed sessions per class in two windows exist.
  - *(2026-10-21, noninf-offline.)* limits closed (epyc-orchestrator main 249d7da5, 058e674b; 162 tests green under region-lock): `client.class_source` = `header` (caller `x_client_class` / `x-client-class`, never overwritten) or `derived` (server-side: eval_batch->eval_harness, campaign->campaign, passthrough->external[:x-client-id], typed /v1 keys->v1_client, background priority->background, else orchestrator_internal); autopilot LocalPlannerProvider now sends `x_client_class: autopilot`; `RoundRobinBackend.infer_streaming` writes a `handed_off` record. Not tagged: `evolution_manager._invoke_local` (arbitrary URL), dtap eval endpoint client (derives via workload class). Live after next stack start.
- [ ] **HSF-4 — Reload-vs-re-prefill crossover per lineup model (intake-2119#record, intake-2214#record, intake-2216#record, intake-2220#record).** For each served model compute KV bytes/token and append-prefill FLOPs/token from config, express GB per PFLOP, and set against MI210 H2D (~28.9 GB/s measured plateau) and the CPU --cache-ram copy rate; add the agentic hit rate and append-length distribution from orchestrator session logs, reported PER ROLE as an uncached-prompt-length histogram (prompt_tokens - cached_prompt_tokens from serving_call.v1; dispatch.v1 prompt_chars for the fleet) with, at candidate tier cuts B in {1K, 2K, 4K, 8K, 16K, 64K}, the share of requests and of uncached tokens below B (alpha(B)) and the ceiling alpha(B)*(1 - 1/rho) with rho = measured full-vs-half shape-speed ratio (the 1K cut is the prefill-compute HOL scale, the 8K-16K cuts the KV-reservation scale; label which mechanism each cut speaks to), so DI-126 and the WP-15 tier arm read one table. Analytic plus log mining; output feeds the placement KV-recovery term.
  - *(2026-10-20, workspace-f8.)* analytic half done: KV 10.6-51 KiB/tok (q8_0), 0.7-9.6 GB/PFLOP, reload 60-820x cheaper than re-prefill, 27B H2D crossover ~6 tokens; 27B resumed hit rate 0.963 token-weighted, append p50/p90/p99 467/5362/16413 tokens; --cache-ram/slot-file source rate unmeasured, so the box stays open; evidence /mnt/raid0/llm/tmp/analytics-20261020/HSF-4/REPORT.md.
  - **CORRECTION (2026-10-22, workspace-f8 / locals-a; HSF-LB1).** The "reload 60-820x cheaper than re-prefill" line above is an analytic bandwidth-vs-FLOPs ratio (bytes over the 28.9 GB/s H2D plateau against prefill FLOPs); it prices the copy alone and is not an end-to-end restore cost. The measured end-to-end figure from the cache-idle-slots ON arm is a pre-eval stall (TTFT minus prompt_ms) of median 43.5 s at 20-29k cached tokens versus 1.0 s OFF (15 turns, ONE rep, confounded: the stall sits before prompt evaluation and its attribution among neighbour idle-saves, own prompt_load and draft resync is open, UFH14-LB7). Do not cite 60-820x as the restore speed-up; cite it only as the transfer-time bound. The compiled wiki line (`wiki/inference-serving.md`, HSF-4 analytic half) repeats the unqualified ratio and is corrected at the next wiki sweep.
  - *(2026-10-21, hsf4-wp15.)* log half done from llama-server logs (serving_calls has 19 rows; dispatch.v1 absent): 16,087 completed requests, logs 2026-09-22..10-20; rho=1.325 (prefill tok/s full 296 n=369 vs half 224 n=187, log-median, not a controlled matrix value). Frontdoor 35B (n=5,581): 90.1% of requests <1K, uncached tokens below 1K / 8K / 16K = 0.31 / 0.75 / 0.86, ceiling = alpha*0.245 = 0.076 / 0.183 / 0.211. GPU :8083 Qwen3.8-27B (n=5,488): 74% of tokens in requests >16K, ceiling only 0.063 at 16K, 0.220 at 64K. architect_general CPU :8074 Flash-Next (n=2,609): alpha(16K)=0.556, ceiling 0.136. 122B era (n=97) and :8085 (n=48) insufficient. Role = port+model era (logs carry no role field). Source-rate sub-term and a dispatch.v1/serving_call.v1 re-run stay open; evidence /mnt/raid0/llm/tmp/hsf4-wp15-20261021/hsf4_results.json.
  - *(2026-10-23, workspace-f8; `docs/design/hsf-4-results-20261023.md`.)* Source-rate sub-term, **GRAPHS DISABLED** (KPF-18-S1 remainder step 7, 27B on the :8083-shaped argv, L = 8k / 16k / 32k): tmpfs restore 8.26 / 9.27 / 6.15 GB/s (52.7 / 77.1 / 206.8 ms), cold-disk restore 4.12 / 4.10 / 3.06 GB/s (105.6 / 174.2 / 416.2 ms), tmpfs save 3.06 / 3.09 / 2.89 GB/s, disk save 1.59 / 1.73 / 0.80 GB/s, `--cache-ram` load stall 68.8 / 45.7 / 77.3 ms (the L = 8000 baseline stall of 37 ms is a 26x outlier, so that cell is unreliable). Against measured idle re-prefill (graphs ON) the copy is 103-301x cheaper and the crossover prefix is about 14 tokens (tmpfs) to 28 (cold disk). Copy and apply only: the largest single transfer (1.58 s) is 27x below the 43.5 s ON-arm stall, so it does not explain it (UFH14-LB7 owns that). Graphs: save/restore are hipMemcpy plus file I/O, not graph nodes, so an effect is unlikely for tmpfs/disk and possible but small for the stall-based `--cache-ram` figures; unmeasured, 7g is the test and was not decided here. serving_call.v1 / dispatch.v1 re-run: 478 / 481 rows exist but are all direct-lane scratch traffic (max prompt 3,370 tokens), so the per-role histogram keeps the 2026-10-21 log table. Not ticked.
  - [x] **HSF-4.G — re-quote the HSF-4/5 source-rate sub-term from the graphs-ON step-7 run (filed 2026-10-24, workspace-f8; the KPF-18-S1.7g rule).** KPF-18-S1.7g came out `graphs-sensitive`: 4 of 21 (L, mode) cells (VERDICT `/mnt/raid0/llm/tmp/f8-launchers-20261023/kpf18-s1-step7-graphs-on/VERDICT.json`, rule sha256 `79350337f034…`). So HSF-4/5 must use the graphs-ON numbers, all of them, from that run. The difference is attributed to graphs ON plus the knob plus the fresh load / step-7-only history jointly, NOT to HIP graphs alone. Next step: in `docs/design/hsf-4-results-20261023.md`, quote the ON medians (`VERDICT.json` → `step7_graphs_on_result`) as the source rates. Keep the OFF table labelled graphs-disabled, and retire the code-path judgement that the copies sit inside the 3-rep spread. ✅ 2026-10-24
    - *(2026-10-24, workspace-f8 sweep.)* `docs/design/hsf-4-results-20261023.md` re-quoted from the graphs-ON run (rule sha256 `79350337f034…` = PREDECLARATION.md = VERDICT `predeclaration_sha256`, no records excluded; graphs-sensitive cells: 8k and 16k cache_baseline, 32k disk_restore_cold (-80.6 ms), 32k cache_load (+6.0 ms)). ON source rates, L = 8k / 16k / 32k: tmpfs restore 8.58 / 8.50 / 7.29 GB/s (50.8 / 84.1 / 174.6 ms), cold-disk restore 3.92 / 3.94 / 3.79 GB/s, tmpfs save 3.21 / 3.19 / 3.17 GB/s, disk save 1.70 / 1.69 / 1.68 GB/s, `--cache-ram` save stall 111.0 / 160.5 / 189.2 ms, load stall 77.9 / 55.1 / 83.2 ms (the L = 8000 cache-ram baseline outlier recurs in the ON run, so the derived 8k cache-ram rates stay flagged unusable). Recomputed: re-prefill/restore 215-296x (tmpfs), 98-154x (cold disk); crossover 13 / 30 tokens; largest single transfer 758.5 ms, 57x under the 43.5 s stall. OFF table kept and labelled graphs-disabled; the code-path judgement is retired; the ON/OFF difference is attributed to graphs ON plus the knob plus the fresh load / step-7-only history jointly, not to HIP graphs alone. Parent HSF-4 stays open (per-role histogram has no usable sample; LB7 restore cost owed).
- [x] **HSF-5 — Cost a write-through host KV mirror for the MI210 np4 slots (intake-2126#record, intake-2140#record).** Bytes/token/layer, D2H time vs the 28.9 GB/s plateau and vs a 3% decode budget, the HIP-graph-capture interaction, and the handover cost it would remove vs slot-file save; include the mapped-host gather pattern (ROCm/mori UMBP, MIT) as the read side. Analytic only; decides whether the host-tier prototype trigger fires. ✅ 2026-10-24
  - *(2026-10-20, workspace-f8.)* analytic half done: KV mirror 34,840 B/tok (0.013% of link, 0.0128% serialized), recurrent 149.6 MiB must be checkpointed every >=19 tokens/slot (per-token 57.7% fails 3%), host mirror 14.3 GB (q8); D2H, disk and gather rates unmeasured, so the box stays open; evidence /mnt/raid0/llm/tmp/analytics-20261020/HSF-5/REPORT.md.
  - *(2026-10-24, workspace-f8 sweep; closes the box.)* [`docs/design/hsf-5-host-kv-mirror-costing-20261024.md`](../../docs/design/hsf-5-host-kv-mirror-costing-20261024.md) (calc `/mnt/raid0/llm/tmp/analytics-20261020/HSF-5/calc_20261024.py`). Inputs: D2H 28.20 GB/s from the same 2026-08-03 rocm-bandwidth-test receipt that gives the 28.9 GB/s H2D plateau (research `data/mi210-h2d-d2h/20260803T131500Z`), the graphs-ON step-7 rates (HSF-4.G) and the GPU-ZOS-1a step times (139.6 ms spec ON, 59.1 ms spec OFF). KV tail mirror 0.44% (ON) / 1.01% (OFF) of step time worst case with 128 serialized copies, 0.014% as one staged copy; the 149.6 MiB recurrent state fits 3% only as a checkpoint every 6 (ON) / 13 (OFF) steps (per step 15.9% / 37.7%). Handover cost removed at 8k / 16k / 32k: 130 / 218 / 395 ms vs tmpfs, 250 / 417 / 753 ms vs disk, 105 / 155 / 184 ms vs `--cache-ram`, each above its own 3-rep range. HIP graphs: a copy inside the captured graph breaks reuse (the destination moves every step); graph-safe = a scatter into the mapped host alias or a side-stream copy after the step event, no blocking wait in post_decode. Gather (mori UMBP) is restore-side only: reading host KV in place each step costs 154 ms/step at 32k. Decision rule DI-140 (`kv-unified-stack-rollout.md`): fits the decode budget AND removes measurable handover cost -> **the trigger FIRES** (AUTHOR readings of "fits"/"measurable" stated in the doc). Value is bounded per handover (0.1-0.75 s); handover frequency is unknown (HSF-3.1). Prototype filed below as HSF-5.P.
- [ ] **HSF-5.P — Host-pinned KV mirror prototype for the MI210 np4 slots (DI-140 fired 2026-10-24 by HSF-5; intake-2140#record).** On a fork `experimental/*` branch cut from the current champion tip: (a) a `hipHostRegister(Mapped)` host tier on the membind=3 node, about 14.3 GB, q8_0; (b) the KV tail write as a graph-safe scatter into the mapped alias, or a staged single D2H on a side stream after the step event, with no copy inside the capture and no blocking wait in `post_decode`; (c) a recurrent checkpoint every k = 6 steps per slot, replaying at most k steps at restore; (d) restore by bulk pinned H2D, with the UMBP `GatherFragmentsKernel` source-copied (MIT) for fragmented cells. Accept with the 3-step microbench in the HSF-5 doc (graphs ON, ABA, decode delta <= 3%, `graphs reused` unchanged, restore greedy-equivalent to a slot-file restore). Design it together with GPU-ZOS-2 (one-step-lag post_decode). (filed 2026-10-24, workspace-f8)
  - *(2026-10-24, workspace-f8; code done, box stays OPEN: acceptance not run.)* Prototype on fork `experimental/hsf-5p-host-kv-mirror-20261024` @ `14d0f7fa2` (champion `dcc853b55` + 22 files): (a) node-3 mbind host tier, pinned+mapped in 1 GiB pieces; (b) KV tail = one async side-stream copy per step after an event (no copy inside the capture, no host wait; `post_decode` untouched, so it composes with GPU-ZOS-2); (c) staggered recurrent checkpoint every k=6 steps, a lag save replays <= k; (d) restore = pinned staging + bulk H2D / mori `GatherFragmentsKernel` (source-copied @`37cdd8e9`, MIT header kept). Knob `--kv-host-mirror` (default off). CPU tests `tests/test-kv-host-mirror.cpp` + `tools/kv-mirror-bench`. Not yet compiled (no build outside a grant). Launchers + PREDECLARATION (sha256 `9de08e8f`) in `/mnt/raid0/llm/tmp/f8-launchers-20261024/hsf-5p/` (`hsf-5p-build`, `hsf-5p-microbench`: BACKLOG); belief write side wired (VB-HSF5P-WRITE). Waits on: a build-role grant for `hsf-5p-build`, then a GPU grant (mi210_0 + 184-191, >= 50 min).
  - *(2026-10-24, workspace-f8 wrap-up read-out; box stays OPEN: build gate verified, microbench not run.)* `hsf-5p-build` ended rc 0 (grant complete 14:29Z; `BUILD_OK` + `PASSED`); outputs `/mnt/raid0/llm/tmp/f8-launchers-20261024/hsf-5p/build/out/`, rule PREDECLARATION.md sha256 `9de08e8f6b6d6639b3f60ef3acd976099419c86da7b66ea9f57c9f0e48f23f70` (matches `PREDECLARATION.sha256`). Verified from the logs and the binaries, not from the marker: **B0 PASS** (`test-kv-host-mirror: all checks passed`, exit 0, CPU-only build). **B1 PASS**: worktree HEAD is `14d0f7fa2`; `strings` on the built libs finds `ggml_backend_kv_mirror_get_ops` in `libggml-hip.so`, `HSF-5.P kv host mirror ON` in `libllama.so`, `kv-host-mirror save:` in `libllama-server-impl.so`, control `graphs reused` present; negative control on `kernels/builds/gpu-20261023-dcc853b55-c3` has none of the three gate strings and the control string present (the gate can fail); `verify_ggml_linkage.sh` PASS (all ggml libs resolve inside `build-hip-hsf5p`); `llama-server` and `llama-kv-mirror-bench` built 14:28-14:29Z, after the commit. The box is one acceptance item (build AND the 3-step microbench with its G1-G4 gates), so it is not ticked; `hsf-5p-microbench` (GPU, mi210_0 + 184-191) is the only part left.
  - *(2026-10-24, workspace-58 wrap-up; box stays OPEN.)* Microbench `/mnt/raid0/llm/tmp/f8-launchers-20261024/hsf-5p/gpu/` VERDICT INCONCLUSIVE 15:44:52Z: G1 decode PASS, G2 graphs reused PASS, G3 restore PASS, G4 mirror engaged INCONCLUSIVE only because the libllama INFO enable line `HSF-5.P kv host mirror ON` was filtered from `server.B.log` (verbosity 3, 0 libllama INFO lines captured) although the save (tail_copies=874, replay_steps=6) and restore (device_bytes=298907648) lines are present. Fix adopted: `hsf-5p/AMENDMENT-G4-log-capture.md` (instrument-only; all 4 arms `--log-verbosity 4`; G1 evaluated with all arms at -lv 4; the 15:44Z INCONCLUSIVE stands), applied to `gpu/job.sh` (backup `job.sh.bak-ws58-g4log`), dry rc 0. Re-run booked on the GPU after v11-086-cpu (~10-25 00:00Z).
  - [x] **HSF-5.P-MB — run the predeclared 3-step microbench (-lv 4, G4 amendment) on the MI210** ✅ 2026-10-25 (workspace-58): VERDICT **FAIL**, ended 13:48Z rc 0. G1 decode FAIL: B 45.58 vs A mean 43.76 ms/token = **+4.17%** (A1 43.88, A2 43.64, A spread 0.55%) > 3% gate; G2 graphs reused PASS (737/742/737/737); G3 restore PASS; G4 mirror engaged PASS (enable line captured). Rule sha256 `9de08e8f6b6d6639b3f60ef3acd976099419c86da7b66ea9f57c9f0e48f23f70` verified. Evidence: research `data/hsf-5p/microbench-20261025/` (VERDICT.json, SHA256SUMS), raw `/mnt/raid0/llm/tmp/f8-launchers-20261024/hsf-5p/gpu/`. [no-belief: single-run predeclared gate; native adapter absent]
  - [ ] **HSF-5.P-NEXT — decide the host KV mirror's fate: investigate the +4.17% decode cost (which copy/sync/scatter term, graph-safe variants) or retire HSF-5.P.** The 3% acceptance is not met, so HSF-5.P stays open. Next step: attribute the 1.82 ms/token B-A gap from `out/arms.jsonl` waves and `server.B.log` before choosing.
    - *(2026-10-27, workspace-58 results harvest)* No attribution yet; five traced A1/B/A2 attempts all INVALID: P1 rocprofv3 export SIGKILLed (memory trace missing all arms); P2 HOLD interruption; P3 /proc PermissionError during A2 export; P4 A1 first-request token divergence (idx45 4619 vs 20572); P5 B restore control FAIL (B saved/restored 4079 of 4116 tokens, continuation evaluates 38 vs 1 prompt tokens; A/A spread 1.83%), attribution_valid=false. HSF-ORIGINAL-IMAGE-DETERMINISM-1: 4 processes x 30 completions identical, divergence not reproduced (n=2/condition, no determinism claim). HSF-5P-REPAIR-C5 CPU+HIP builds rc0 (seal e87acfc5e), model-free save/restore parity 43/43/43; GPU-OPS native mirror PASS 429 cases / 1391627616 B (correctness only). G1 +4.17% vs gate <=3% unchanged. Artifacts `/mnt/raid0/llm/tmp/codex-ni-20261027-hsf-profile5/out/20261027T063913Z/`, `/mnt/raid0/llm/tmp/codex-ni-20261027-hsf-determinism-job/out/`, `/mnt/raid0/llm/tmp/codex-ni-20261027-hsf5p-repair-c5/`. [no-belief: invalid runs + correctness-only]
    - [x] **HSF-5.P-NEXT-RESTORE — explain the B-arm 37-token save shortfall (4079 vs 4116) under mirror ON and confirm the C5 live-save repair closes it before any PROFILE-6.**
      - *(2026-10-28, workspace-58 results filing; ticks the box.)* `codex-hsf5p-restore-r11-20261028` (codex-wrap-checks, GPU mi210_0 + q3 184-191, scheduled 1500 s row, ended rc0 complete 22:50:01Z; manifest class **diagnostic**, equality only, no timing, quality or promotion claim) against predeclared rule `/mnt/raid0/llm/tmp/hsf5p-r11-repair-20261028/PREDECLARATION.md` (three save/erase/restore/continuation checks in one server process; saved = erased = restored = continuation cache_n, all positive, and written bytes = read bytes). Result `runs-official/20261028T224917927087Z/restore-{0,1,2}.jsonl`: all three checks n_saved = n_erased = n_restored = cache_n = **4116** (the 37-token shortfall 4079 vs 4116 is gone), continuation prompt_n = 1 (was 38), written = read bytes in each check (740,054,204 / 938,916,368 / 938,916,368), first-response and continuation tokens identical across the three checks, draft 55/55 accepted. Restore state valid: same PID 3085832 for all 35 residency samples (kfd true, VRAM >= 51.3 GB own, sampled during the requests 22:49:42-22:49:59Z), repaired C5 HIP build `codex-hsf5p-repair-c5/build-hip-hsf5p` with `verify_ggml_linkage.sh` PASS and `libggml-hip.so` mapped, model hashes recorded (27B Q8_0 `a680f44a`, DFlash2 `7f1c9a31`), server reaped (`cleanup.txt`); the row's own normal (162.6 s, 2 fresh processes) and forced-cutoff (rc 75) smokes passed beforehand on pinned source manifest `615b3bd2`. Rule fully met, so **PASS (correctness-only)**. Scope limits: timing fields (save_ms / restore_ms / decode rate) are recorded but the run alternated no arms and is not a quiet-q3 baseline, so they carry no claim; this does not attribute the +4.17% decode cost, does not close HSF-5.P, and PROFILE-6 stays DEFERRED pending operator go. Observation, not a rule failure: the first save in a process wrote 740,054,204 B vs 938,916,368 B for saves 2 and 3 (same 4116 tokens; same 740,054,204 in both smoke processes), unexplained. `retention_consumer.py` keeps raw slot file (939 MB `slots/hsf5p-B.bin`) for reaping. [belief: cc]
      - [x] **HSF-5.P-NEXT-RESTORE-FU1 — explain why the first slot save in a fresh server process writes 740,054,204 B but saves 2 and 3 write 938,916,368 B for the same 4116 tokens (mirror ON, C5 repair); confirm both are valid restores (they are: read = written and continuation cache_n 4116) and whether the 198.9 MB delta is lazily-populated checkpoint state.** Source/log inspection first (`server.log` in the r11 run dir); no new compute unless the log is silent. ✅ 2026-10-29 — the logs answer it: one extra context checkpoint (below). [belief: cc]
        - 2026-10-29 (ws58 filer A; log inspection, plus the replicate `codex-hsf5p-restore-r3-20261028` rc0 00:25:29Z on the `codex-hsf5p-repair-c5` HIP build, binary sha256 `802a3e0c…`, source `bd35948cc`): r3 reproduces r11 exactly against its predeclared diagnostic rule (equal positive saved/erased/restored token counts and equal saved/restored bytes) -> met: 3/3 checks n_saved = n_erased = n_restored = cache_n = 4116, written = read 740,054,204 / 938,916,368 / 938,916,368 B. Cause of the delta, from `save_slot_ch` in both server logs: save 1 appends **2** context checkpoints (379.299 MiB), saves 2 and 3 append **3** (568.949 MiB); one checkpoint is 189.650 MiB = 198,862,438 B, which matches the 198,862,164 B delta to the rounding of the logged MiB. The first prefill creates checkpoints at n_tokens 3509 and 4017, and the mirror's checkpoint count grows across checks in one process (`ckpts=6/6` -> `11/11` -> `16/16`). So the delta is checkpoint count, not lazily populated state, and both sizes restore validly (read = written, continuation cache_n 4116). Evidence `/mnt/raid0/llm/tmp/codex-hsf5p-restore-r3-20261028/runs/20261029T002447178189Z/{RESULT.json,server.log}` and `/mnt/raid0/llm/tmp/hsf5p-r11-repair-20261028/runs-official/20261028T224917927087Z/server.log`. [belief: cc]
    - [ ] **HSF-5.P-NEXT-PROFILE-6 — re-run traced A1/B/A2 attribution on the repaired C5 build once its branch is published.**
    - [ ] HSF-5.P-NEXT phase 2 GPU profile (mirror off/on/off, rocprof): PROFILE-1 rc1 2026-10-26 21:47Z (memory exports SIGKILLed; all 3 arms INCOMPLETE). An offline recovery of the raw memory records (A1/B/A2) is derived-only with completeness UNKNOWN, not a measurement. PROFILE-2 (180 s export reserve per arm) was stopped at 23:29Z by the ws58 night whole-host HOLD, an owner scheduling error, not a job fault. Next: a fresh successor id after the HOLD lifts (~10-27 03:45Z). Launcher dirs: `/mnt/raid0/llm/tmp/cal-1026/hsf-5p-next-profile-{1,2}/`. Owner: codex-ni (launcher), ws58 (calendar). [checkpoint ws58-20261026-2335] PROFILE-3 2026-10-27: `PermissionError(13)` (Yama ptrace_scope=1, non-ancestor /proc reads). PROFILE-4 (04:21Z rc1): first-request divergence A1 vs A2 at warmup token 45 (4619 vs 20572), INCOMPLETE; determinism job (06:10Z rc0) 4/4 identical, divergence not reproduced. PROFILE-5 (06:53Z rc1): restore-state INVALID (B saved/restored 4079 vs erased 4116, replay_tokens=37), no attribution. Full record: `docs/design/hsf-5p-host-kv-mirror-findings-20261027.md`.
    - *(2026-10-27, workspace-58; box stays OPEN.)* Evidence and revival checklist: [`docs/design/hsf-5p-host-kv-mirror-findings-20261027.md`](../../docs/design/hsf-5p-host-kv-mirror-findings-20261027.md). Restore mechanism source-proven (lag save uses the latest valid checkpoint; R=C+1=M+1-replay_tokens; 4116-37=4079; `server.B.log:1820`); decode-cost attribution, 90/50 vs 55/55 draft internals and determinism cause NOT established. Decision: repair on current champion now, GPU testing deferred.
    - [x] HSF-5.P-REPAIR-C5 (codex-ni, T2): port the mirror onto C5 `c72ec82f5`, save drains to the live position, opt-in knob default OFF, model-free restore round-trip test. No model inference/benchmark (model-free GPU-OPS validation authorized 07:36). Spec: findings doc section 6. — accepted C5 CPU/HIP builds and model-free GPU-OPS validation (429 cases; 1,391,627,616 D2H-poison/H2D bytes; CSV SHA-256 `442f99d366d79206d6cdfa7e0c0e082e2475e8f0f59972eb60de9ba50cd454a6`). Source seal `e87acfc5ee0fb855eab9e821d8201d1bfa6bdc21c97d078a63f6757b6b042083`; owner confirmed private fork push `bd35948cc073f78c23baf3ccc1e9e0c698cd64dd` after cutoff. This does not close HSF-5.P or authorize promotion. [belief: cc]
    - [ ] HSF-5.P-NEXT GPU attribution (P6), DEFERRED pending operator go: run per the REVIVAL CHECKLIST in the findings doc section 7.

### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **HSF-LB1 — Correct the reload-cheaper-than-reprefill note with the measured end-to-end restore cost (pre-eval stall median 43.5 s at 20-29k cached tokens, one rep, confounded), and add the preceding tool name and finish_reason to dispatch.v1 so session gaps can be keyed by tool (intake-2398, intake-2411#record).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / locals-a.)* Both halves done. Correction note: HSF-4 sub-bullet above. dispatch.v1: branch `f8/locals-a-orch-20261022` (unmerged, not pushed), commit `28ed886f`: records now carry `preceding_tool` (passthrough derives it from the request body: chat last `tool` message resolved through `tool_call_id`, or /v1/responses `function_call_output` resolved through `call_id`), `turn_trigger` (`tool_result` / `user` / null) and `finish_reason` (the upstream stop signal on passthrough, `completion_reason` on the fleet and direct lanes; fleet/direct take `preceding_tool` from a staged caller field when a caller sets it, else null). 3 new tests plus the dispatch/passthrough/fleet suites (107) pass. Live only after merge and API reload.

- 2026-10-28 HIL15 s1 co-tenancy disclosure (workspace-58, NI draft): the private HIL15 s1 grant names CPUs 24-47. Earlier pair32/33 preparation (tests, read-only hash/ledger activity: 172,223,893,080 bytes of EXL3 shards read, peak GitNexus RSS 2,561,828 KiB; no inference, no GPU) overlapped it; pair work stopped 04:25:21.524Z. The assumption that the YaRN s1 exception covered this distinct grant was wrong. Outputs diagnostic only; validity assessment belongs to the owning refactor session. Separately, the HIL15 s1 shared-venv incident is refactor-owned (see progress 2026-10-28-workspace-58). Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261028-coordination/pair32-overlap-exact.txt`, `pair32-hil-0338.txt`. [no-belief: incident disclosure, no measurement]


### 2026-10-30 05:30 original HSF and YaRN event filing

HSF PROFILE-6 R12's original whole-host event ended 05:14:53Z rc75 before A1/B/A2 because the unchanged 150 GiB floor plus 16 GiB normal trace reserve was unavailable. Three later grants made the same refusal; at 05:30:23Z the owner withdrew its ungranted waiter and verified its captured PID and sleep child dead, without changing the floor. The prior separate B-only 32,768-context control completed in 190.393s with trace/restore and cleanup; its full 42-member archive is 730,699,910 bytes, SHA-256 `464ad36b04f7c83ef3ce6acc56dc823b2bce2bab925b18be0ec4aaf3518703b7`. It is not a full-context or attribution result. [Original events and custody](../../artifacts/compute/results-filing-20261030-0530.json). [belief: cc]


### 2026-10-30 06:00 native entry and split-storage checkpoint

- HSF13 split-storage successor was real-smoke qualified and published, then keeper accepted05:52:45Z. B-only32,768-context native control completed112.06s,25/25 positive during-request GPU residency samples, rc0/writer/drain; native control is retained on Micron with individual member hashes. Full normal A1/B/A2 at393,216 context and its16GiB native-output budget are unchanged; real RAID metadata reserves128MiB above150GiB. The normal grant opened05:53–06:33Z and launcher started05:54:14Z; this grant alone does not establish native completion.
  - [belief: cc] [Native/source evidence](../../artifacts/compute/results-filing-20261030-0600.json).


At05:58:40Z HSF13 normal A1 had completed warmup, six four-stream waves and restore. All211 during-driver samples recorded KFD and positiveVRAM; latest serving sample52.18GB. Serving had drained while the captured profiler process remained live in native trace export. Full A1/B/A2 remains incomplete; grant ownership is not substituted for native evidence. Canonical launcher log now hardlinks the actual keeper stdout inode. [Live native proof](../../artifacts/compute/results-filing-20261030-0600.json). [belief: cc]
