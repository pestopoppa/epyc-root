# Handoff: Hybrid SSM Speculative Decoding — Slot-Promotion Reopener

**Status**: Phase 0 falsification scheduled. Reopener of closed work via NEW mechanism (intake-490 slot-promotion + DFlash-style NUMA-parallel verify).
**Created**: 2026-04-28
**Source**: intake-490 (PyTorch SGLang blog, Dec 2025) "Hybrid Models Meet SGLang: More than Full Attention"
**Pre-production push gate**: Phase 0 GO/NO-GO verdict required before MoE-Spec Phase 3 follow-up "production registry integration" lands in `model_registry.yaml`. See [`moe-spec-cpu-spec-dec-integration.md`](moe-spec-cpu-spec-dec-integration.md) gate blockquote at top.

**Categories**: speculative_decoding, ssm_hybrid, kv_cache, hardware_optimization
**Workstream**: Inference Acceleration → Reopened Tracks
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md) Reopened Tracks section

---

## Reopener gates (closure-inflation policy compliance)

The 6 closed handoffs listed in the "Falsified-under-prior-assumption" table below all closed under a single shared assumption that intake-490 falsifies. Per `feedback_closure_inflation.md`, reopening requires:

> Enumerate which gates were met under the prior assumption, AND identify a NEW gate UNMET under the new assumption. Closure-inflation pattern #1 (extrapolating one falsification to "all paths exhausted") is forbidden.

### Prior assumption (under which the 6 handoffs closed)

> "Spec-dec on Delta Net hybrids is bandwidth-/state-bound regardless of draft mechanism — verification batch = N × single-token cost. The 75% Delta Net layers are sequential regardless of batch size, so multi-token verification batches always cost N× single-token decode."

This is `ssm-hybrid-acceleration.md` line 379: *"fundamental limitation: 75% Delta Net layers process tokens sequentially regardless of batch size, making ALL draft-verify paradigms net-negative on hybrid models"*.

### New assumption (intake-490)

> "Per-candidate state slots + DFlash-style NUMA-parallel single-token verify break the verification-wall serialization. Each NUMA quarter verifies ONE candidate as a single-token decode (not a K-token batch). The recurrent layers' sequential nature is preserved per-token, but K candidates are now wall-clock-parallel across 4 NUMA quarters."

The mechanism is **slot promotion**, not state cloning. Per the SGLang blog (verbatim):

> "Each draft token receives a private cache slot with its own SSM state. When a sequence of draft tokens is accepted, simply promote the last accepted slot to become the new main state. Snew = Sparent + vnew·knew^T."

This is architecturally compatible with Delta Net because the Delta Net update is deterministic from a parent state plus new inputs (k, v, β, g). It is incompatible with our prior `clone_cell` approach which paid 450 MB clone cost per path (failure mode documented in `ssm-checkpoint-speculation.md`).

### Gates met under prior assumption (preserved)

| Gate | Under prior assumption | Status |
|---|---|---|
| A: External draft + freeze-recurrent net positive on 1×96t hybrid | tested | MET (+5.4% on Qwen3.5-9B per `hsd-hierarchical-self-speculation.md`) |
| B: External draft survives NUMA 4-way (4×48t) | tested | NOT MET (-12.5% to -27% per S3 sweep in `ssm-hybrid-acceleration.md`) |
| C: Multi-token batched verification cost is ~1× single-token | tested | NOT MET (2-token batch = 3-4× single-token decode confirmed across MTP, tree, MoE-self-draft) |

### Gate unmet under new assumption (target of this handoff)

| Gate | Under new assumption | Status |
|---|---|---|
| D: Per-candidate Delta Net state allocation (slot promotion) is feasible in our llama.cpp fork without re-engineering ggml graph | NEVER TESTED | Phase 0 target |

If gate D fails (HIGH risk OR >2 weeks wall-clock), the closure is scoped specifically to "slot-promotion in our fork's graph builder is too expensive to implement" — it does NOT generalize to "hybrid spec-dec on CPU is dead". A different implementation path (e.g., bypassing ggml at the spec-dec layer, or per-context virtual-state layering) could still be tested separately.

---

## Falsified-under-prior-assumption table

All 6 closed handoffs cited here remain valid as historical record under their prior assumption. They are NOT reopened; they are referenced as the specific evidence body that motivated the prior assumption.

| Handoff | Prior verdict | Specific claim that becomes potentially overturnable under slot-promotion |
|---|---|---|
| [`ssm-hybrid-acceleration.md`](../completed/ssm-hybrid-acceleration.md) | "All hybrid accel net negative" (line 379, 7 approaches × 0 wins) | The serialization wall is what made all 7 approaches fail. Slot-promotion + per-NUMA verify changes the per-candidate cost model from N× single-token to 1× single-token (per NUMA quarter). |
| [`mtp-speculative-decoding.md`](../completed/mtp-speculative-decoding.md) | "0.56× throughput on hybrid (78.5% acceptance, 2-token batch = 3-4× cost)" | The 78.5% acceptance is a known floor. Under slot-promotion + per-NUMA verify, 2-token verification = 1× single-token cost (each token verified on a separate NUMA quarter). At 78.5% acceptance × 1× cost = ~1.5-1.7× speedup, not 0.56×. |
| [`tree-speculation-numa-drafting.md`](../completed/tree-speculation-numa-drafting.md) | "Tree ≈ linear at 48t; NUMA 4-way is the real win" | The tree-overhead-vs-gain calculation assumed multi-token batched verify cost. Slot-promotion + NUMA-parallel changes the calculation. Plus MAB tree-shape selector (sibling handoff) provides adaptive shapes the prior tree-spec evaluation did not test. |
| [`ssm-checkpoint-speculation.md`](../completed/ssm-checkpoint-speculation.md) | "clone_cell ~450 MB per path overhead exceeds tree benefit, -59.5%" | Slot-promotion stages only the (k, v, β, g) input deltas per candidate (~KB per slot), not the full 450 MB recurrent state clone. Three orders of magnitude lower per-candidate cost. |
| [`dflash-block-diffusion-speculation.md`](../completed/dflash-block-diffusion-speculation.md) | "Block diffusion AR-loss; CPU-incompatible" | This handoff's Phase 6 explicitly proposed NUMA-parallel verification on hybrid models as a reopener path. The SGLang slot-promotion mechanism is the missing primitive that makes that Phase 6 idea concrete. |
| [`v3-hybrid-ssm-regression.md`](../completed/v3-hybrid-ssm-regression.md) | "Uninitialized freeze_recurrent bug" (fixed) | Slot-promotion bypasses freeze_recurrent entirely — each candidate has its own state, so there is no shared state to freeze. The architectural lessons about hybrid memory handling apply but the freeze_recurrent flag is mooted by the new mechanism. |

---

## Phase 0 — Falsification (research, no benchmark)

### Step 0.1 — Read intake-490 PyTorch SGLang blog end-to-end (~1 hour)

URL: https://pytorch.org/blog/hybrid-models-meet-sglang-more-than-full-attention/

Capture:
- Per-token slot semantics: how is `S_new = S_parent + Δ` computed in their stack?
- Slot-promotion-on-accept protocol: what's the exact accept/reject decision flow?
- HybridReqToTokenPool: per-request state pool structure
- HybridLinearKVPool: layer-id remap to skip linear-attention layers
- MambaRadixCache: prefix-tree of snapshots (vs live state sharing)
- EAGLE-Tree compatibility: how does multi-path branching interact with slots?

Write findings into a "Mechanism summary" section in this handoff.

### Step 0.2 — Trace Delta Net state in our fork (~2 hours)

Files (in `/mnt/raid0/llm/llama.cpp-experimental/`):
- `src/models/delta-net-base.cpp` — recurrence implementation (`s_t = exp(g_t) * s_{t-1} + k_t ⊗ β_t * (v_t - s_{t-1}^T k_t)`); identify state read/write callsites
- `src/models/qwen35moe.cpp` — forward call site that invokes Delta Net layer
- `src/models/qwen3next.cpp` (if present) — Qwen3-Next forward
- `src/llama-context.cpp` — per-context state allocation in `llama_context::init`; identify the `delta_net_state` (or equivalent) bytes
- `src/llama-cparams.h` — params surface
- `common/speculative.cpp` — heap-spec accept/reject loop callsite for slot promotion hook

Capture:
- Where is the per-context Delta Net state allocated? Size in bytes per layer × n_layers?
- Is the state currently a single pointer per `llama_context`, or already organized by sequence/slot?
- How is the state mutated during forward? Direct pointer mutation, or via ggml graph nodes?
- Where would per-candidate slot allocation hook in?

### Step 0.3 — Verify Qwen3.6-35B-A3B architecture (~30 min)

The autonomous CPU agent benchmarks Qwen3.6-35B-A3B Q8 alongside Coder-30B and REAP-246B. Determine:
- Is Qwen3.6-35B-A3B hybrid Delta Net like Qwen3.5-35B-A3B / Qwen3-Next, or pure MoE like Qwen3-Coder-30B-A3B?
- Source: `src/models/` for the model architecture handler; or model registry/HF config

Affects whether this reopener applies to Qwen3.6-35B-A3B at all (if pure MoE: Workstream A MAB selector applies; this Workstream B does not).

### Step 0.4 — Phase 1 prototype scope estimate (~1 hour)

Produce LOC + risk + wall-clock estimate per file (table in Phase 1 below). Document any blocking concerns about ggml graph re-engineering needs.

---

## Phase 0 GATE

**PROCEED to Phase 1** iff: LOW or MEDIUM risk + ≤800 LOC + ≤2 weeks wall-clock.

**CLOSE via test** iff: HIGH risk OR >2 weeks wall-clock. Closure scoped to:
> "Per-candidate Delta Net slot allocation in our llama.cpp fork's current ggml graph builder requires N> 800 LOC / >2 weeks of engineering. The slot-promotion mechanism itself remains valid; CPU implementation is blocked by the graph builder's monolithic state-pointer assumption."

**Does NOT generalize to**: "hybrid spec-dec on CPU is dead" or "intake-490 mechanism is invalid". A different implementation path (e.g., bypassing ggml at the spec-dec layer; per-context virtual-state layering; forking the model loader to expose per-slot state) could still be tested separately.

CPU20 artifact bundle path: `data/cpu_optimization/2026-04-2X-hybrid-ssm-slot-promotion-phase-0/`. Phase 0 bundle is **mandatory even with no benchmark** — README states the falsification hypothesis, system-state captures the experimental fork build target, decision.md records the LOC/risk/wall-clock verdict explicitly with line-numbered file references.

---

## Phase 1 — Slot-promotion prototype (deferred behind Phase 0 gate)

### Files (in `/mnt/raid0/llm/llama.cpp-experimental/`)

| File | LOC est | Why |
|---|---|---|
| `src/llama-context.cpp` | +80 to +150 | Per-context slot alloc: `n_slots × delta_net_state_bytes`. For Qwen3.5-35B-A3B with ~62 MiB state and B=4 slots, this is ~248 MiB scratch. |
| `src/llama-cparams.h` | +8 to +15 | `n_spec_slots`, `delta_net_slot_promotion` flags |
| `src/models/delta-net-base.cpp` | +60 to +120 | Active-slot state read/write; recurrence reads from a slot pointer rather than the canonical state |
| `src/models/qwen35moe.cpp` | +20 to +40 | Thread slot id through forward call (and qwen3next.cpp if applicable) |
| `common/speculative.cpp` | +120 to +200 | Promote-slot semantics on accept; tree-aware slot bookkeeping |
| `common/arg.cpp` + `common/common.{h,cpp}` | +30 | `--spec-slots N` plumbing |
| `tools/server/server-context.cpp` | +40 to +80 | Slot lifetime alongside http slots |
| **Total** | **~360 to ~635 LOC** | MEDIUM-effort, justifies the explicit Phase 0 gate |

### Mechanism

```
For each speculation round:
  1. Drafter generates K candidates (heap-spec or tree, unchanged)
  2. For each candidate i in [0, K):
     - Load parent slot state (or canonical state for first candidate)
     - Compute delta: (k, v, β, g) for candidate's token
     - Write candidate's state to slot[i] via S_new = S_parent + Δ
     - Run verification forward pass using slot[i] state
  3. Reject/accept tokens via standard rejection-sampling math
  4. Promote longest-accepted-prefix's slot to canonical state
  5. Discard rejected slots (next round overwrites)
```

Phase 1 runs all K candidate verifications **sequentially on a single NUMA quarter**. Phase 2 parallelizes them across 4 NUMA quarters.

### Phase 1 gate

- **Acceptance**: ≥30% on Qwen3.5-35B-A3B with B=4 candidate slots
- **Throughput**: end-to-end ≥0% vs `p_split=0` linear baseline (1×96t single-NUMA)
- **Memory**: scratch ≤ 1 GB additional (B=4 × 62 MiB × layers headroom)
- **Bit-exact output**: verified against `p_split=0` baseline at temperature=0

CPU20 7-artifact bundle.

---

## Phase 2 — DFlash-style NUMA-parallel verify (deferred behind Phase 1)

Pin each of K candidate-slot verify passes to one NUMA node. Each quarter independently computes one slot's verify forward; reduce.

```
NUMA quarter 0: drafter (Qwen2.5-Coder-0.5B at 12 threads) generates 4 candidates
  ↓ broadcast (k, v, β, g) per candidate to slots 0-3
NUMA quarter 1: verify slot 0 (single-token decode through Delta Net + attention layers)
NUMA quarter 2: verify slot 1 (parallel)
NUMA quarter 3: verify slot 2 (parallel)
NUMA quarter 0: verify slot 3 (parallel after drafter)
  ↓ all 4 verifications complete in ~1× single-token-decode wall-clock
Promote longest-accepted-prefix's slot to canonical
Commit canonical state + KV deltas
```

### Phase 2 gate

Aggregate ≥1.3× over Phase 1 best (Phase 1 single-NUMA verify; Phase 2 must beat by NUMA-4-way ratio adjusted for verify serial fraction). Note this is single-instance-per-request gain, not aggregate-throughput-per-host gain — the 4-NUMA-aggregate framing of `numa-orchestrator-deployment.md` is traded for per-request latency.

If interactive (single-stream) workloads dominate: this is the right tradeoff.
If batch (multi-tenant) workloads dominate: the 4×48t NUMA aggregate of `numa-orchestrator-deployment.md` remains preferable.

### Phase 3 — Production decision

5-rep proper canonical sweep + 32-chunk PPL + interaction with MoE-Spec Phase 1 budget + interaction with MAB tree-shape selector if it landed.

Phase 3 gate: ≥10% over current 4×48t hybrid production (Qwen3.5-35B-A3B at 49.7 t/s aggregate per `inference-acceleration-index.md` line 86) on per-request latency, OR close via test.

---

## Cost model (rough projection — verify in Phase 0)

Per-NUMA-quarter single-token decode of Qwen3.5-35B-A3B Q4_K_M at 1×48t single-NUMA: ~12 t/s (per `ssm-hybrid-acceleration.md` S2 Config C results). That's ~83 ms per single-token decode.

For K=4 candidates verified in parallel on 4 NUMA quarters: 1× single-token cost = ~83 ms wall-clock.

With 70% per-token acceptance (MTP-1 floor: 78.5%), expected accepted length ≈ 2.5/round.

Drafter cost (Qwen2.5-Coder-0.5B at 1 NUMA quarter, 48 threads): ~50 ms for 4 tokens (rough, verify in Phase 0).

Net throughput: ~2.5 accepted tokens / (83 ms verify + 50 ms drafting) = ~19 tokens/sec **per request**.

Current baseline single-instance: 13.4 t/s on 1×96t Qwen3.5-35B-A3B (S2 Config B). **Projected gain: ~1.4× single-instance per-request latency.**

Aggregate-vs-NUMA-4-way framing trade-off:
- Current 4×48t aggregate: ~50 t/s aggregate across 4 concurrent requests = 12.5 t/s per request
- Slot-promotion + NUMA-parallel: ~19 t/s per request, but only 1 request at a time

For interactive workloads (frontdoor, single user typing) per-request latency matters. For batch (concurrent API calls) aggregate matters. **This is the wrong handoff for batch workloads.**

---

## CPU20 artifact bundle spec

Per phase: `data/cpu_optimization/2026-XX-YY-hybrid-ssm-slot-promotion-phase-{0,1,2,3}/`:
- `README.md` — phase purpose, hypothesis, gate criteria, prior-assumption falsification framing
- `system-state.txt` — for Phase 0 (no benchmark): `numactl --hardware`, `nproc`, branch HEAD, build target verification
- `process-pre.txt` / `process-post.txt` — for Phase 1+ benchmark phases
- `ld_debug.txt` — `LD_DEBUG=files` for libomp identity (Phase 1+)
- `results.csv` — Phase 1+: 5-rep × {p_split=0 linear, slot-promotion B=4} × {pp32, end-to-end}
- `decision.md` — gate met/unmet with measured numbers; closure or proceed verdict; explicit closure scope

Phase 0 bundle is mandatory even with no benchmark.

---

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| ggml graph rebuild required to support per-slot state pointer | HIGH | Phase 0 Step 0.2 explicitly investigates this; gate D can fail HIGH-risk if confirmed |
| Per-candidate state alloc duplicates 62 MiB × layers per slot, exceeds NUMA quarter memory budget on Qwen3-Next-80B | MEDIUM | Phase 0 Step 0.4 quantifies. May need to scope Phase 1 to Qwen3.5-35B-A3B only, defer Qwen3-Next-80B |
| Drafter quality: Qwen2.5-Coder-0.5B as drafter for Qwen3.5-35B-A3B (different architecture, different vocab) | MEDIUM | Use existing same-family Qwen3.5-0.8B if available; or train a small Mamba drafter (blocked on no-GPU stack — see `gpu-acceleration-path.md`) |
| Cost model assumes 70% acceptance — actual may be lower at K=4 with non-aligned drafter | MEDIUM | Phase 1 measures actual acceptance; Phase 1 gate is ≥30% acceptance |
| Per-NUMA-quarter Qwen3.5-35B-A3B single-token decode rate not yet measured at v5 PGO build | LOW | Phase 0 includes a confirmation benchmark step (~30 min) |
| Production push of MoE-Spec v5 PGO + REAP=40 lands before Phase 0 verdict | MEDIUM | Pre-prod gate blockquote on moe-spec handoff explicitly blocks this |

---

## Sources

- intake-490: PyTorch + SGLang Team, "Hybrid Models Meet SGLang: More than Full Attention", PyTorch blog Dec 2025
- intake-489: Zhong et al., "SpecMamba: Accelerating Mamba Inference on FPGA with Speculative Decoding", arxiv:2509.19873 — independent confirmation that SSM-rollback is the key algorithmic primitive (FPGA target, but algorithmic frame transfers)
- Closed handoffs (preserved record):
  - [`../completed/ssm-hybrid-acceleration.md`](../completed/ssm-hybrid-acceleration.md)
  - [`../completed/mtp-speculative-decoding.md`](../completed/mtp-speculative-decoding.md)
  - [`../completed/tree-speculation-numa-drafting.md`](../completed/tree-speculation-numa-drafting.md)
  - [`../completed/ssm-checkpoint-speculation.md`](../completed/ssm-checkpoint-speculation.md)
  - [`../completed/dflash-block-diffusion-speculation.md`](../completed/dflash-block-diffusion-speculation.md)
  - [`../completed/v3-hybrid-ssm-regression.md`](../completed/v3-hybrid-ssm-regression.md)
- Sibling reopener handoff: [`mab-tree-shape-selector.md`](mab-tree-shape-selector.md) (orthogonal axis, applies to pure-MoE)
- Closure-inflation policy: `feedback_closure_inflation.md` (memory)
- Reference: [`research/intake_index.yaml`](../../research/intake_index.yaml) intake-490 entry with verbatim mechanism quotes
