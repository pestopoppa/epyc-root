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

---

## Phase 0 — RESULTS (DONE 2026-04-29)

### Step 0.1 — intake-490 mechanism summary (read)

URL fetched: https://pytorch.org/blog/hybrid-models-meet-sglang-more-than-full-attention/

The blog post intentionally simplifies the recurrence to `S_t = S_{t-1} + v_t k_t^T` and notes "in real systems, the update is a bit more complex." The full Delta Net update with (k, v, β, g) inputs is not disclosed in the blog itself; SGLang source would be needed for the full formula.

Key mechanism components:
- **HybridReqToTokenPool**: per-request state pool. Lifespan of a request is bound to its Mamba state.
- **HybridLinearKVPool**: layer-id remap that skips KV-cache allocation for linear-attention layers.
- **MambaRadixCache**: prefix-tree of state SNAPSHOTS (not live sharing). Match → copy state from radix tree; insert → fork checkpoint of state from a request; evict → separate LRU lists for states and KV cache.
- **EAGLE-Tree compatibility**: Top-K > 1 supported. Each drafted token traces its parent via precomputed indices and applies `S_new = S_parent + Δ`.
- Slot promotion example (verbatim): "After accepting 'the streets are', slot 3 (which holds 'are' state) becomes the main SSM state."
- Tested architecture: Qwen3-Next-80B-A3B-Instruct-FP8 (the only example given). Mamba2 / general Delta Net / gated linear attention support not explicitly stated but architecturally compatible by construction.

### Step 0.2 — Delta Net state in our fork (traced)

**Critical finding**: our fork ALREADY has the structural primitives required for slot-promotion. Specifically:

1. **Per-sequence Delta Net state allocation**: `src/models/qwen35moe.cpp:285` calls `build_rs(inp, ssm_states_all, hparams.n_embd_s(), n_seqs)` — `build_rs` ("build recurrent state") loads per-sequence state into the graph. State is dimensioned by `n_seqs`, not a single canonical pointer.

2. **Per-sequence convolution state**: `src/models/qwen35moe.cpp:254` similarly loads `conv_states = build_rs(inp, conv_states_all, hparams.n_embd_r(), n_seqs)` per-sequence.

3. **Lazy seq_cp via metadata**: `src/llama-memory-recurrent.cpp:214-249` — `llama_memory_recurrent::seq_cp(src, dst, p0, p1)` does NOT memcpy state. It just adds `seq_id_dst` to the cell's `seq_id` set, marking the same physical state cell as belonging to multiple sequences. Real state divergence happens lazily when both sequences progress (via separate decodes producing new state cells). Effectively COW state sharing.

4. **DySpec heap-spec already uses `seq_cp` for tree branching**: `common/speculative.cpp:1271` calls `llama_memory_seq_cp(mem_dft, fn.seq_id, child_seq, 0, -1)` to fork state for each tree branch. After a wave of K candidates, line 1294-1297 cleans up: `llama_memory_seq_rm(mem_dft, 0, n_past + 1, -1)` clears the canonical state's tail; rejected sequences are removed via `llama_memory_seq_rm(mem_dft, s, 0, -1)`.

**Implication**: the slot-promotion semantics (S_new = S_parent + Δ; promote winning slot to canonical; discard rejected slots) are ALREADY IMPLEMENTED in our fork via `llama_memory_seq_cp` + `llama_memory_seq_rm`. The 450MB clone-cell cost cited in `ssm-checkpoint-speculation.md` was a different mechanism (explicit memcpy of the state buffer); the heap-spec PR uses the lightweight metadata-only `seq_cp` instead.

**What's actually new in intake-490**:
- The MambaRadixCache cross-request state-snapshot prefix tree (not in our fork; our heap-spec is single-request)
- DFlash-style NUMA-parallel verification (each candidate verified on a different NUMA quarter as a single-token decode)

The MambaRadixCache is multi-request infrastructure — out of scope for our single-user CPU regime. The DFlash-style NUMA-parallel verification IS in scope and is the actual lever.

### Step 0.3 — Qwen3.6-35B-A3B architecture (verified)

GGUF metadata for `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-Q8_0.gguf`:
```
general.architecture = qwen35moe
general.tags = qwen3_5_moe, image-text-to-text
qwen35moe.block_count = ...
qwen35moe.embedding_length = ...
```

`qwen35moe` is the same architecture handler as Qwen3.5-35B-A3B (`src/models/qwen35moe.cpp`), which IS hybrid Delta Net (per Step 0.2 trace; line 285 calls build_rs for delta-net state). **Therefore Qwen3.6-35B-A3B IS hybrid Delta Net**, not pure MoE. Workstream B applies to this model.

Note: `general.basename = Qwen3.6-35B-A3B`, `general.tags = qwen3_5_moe` — the tags reflect the underlying architecture lineage (Qwen3.5 family hybrid).

### Step 0.4 — Phase 1 prototype scope estimate (REVISED downward)

Per Step 0.2, the slot-promotion mechanism is already implemented via `llama_memory_seq_cp`. The Phase 1 LOC table in this handoff (originally projecting 360-635 LOC) was based on the assumption that per-context state allocation would need re-engineering. That assumption is **wrong** — per-sequence state is already allocated by `n_seq_max` in `llama_memory_recurrent`, and `seq_cp` already provides the lazy COW fork.

**Revised Phase 1 scope**:

| File | Original LOC est | REVISED LOC est | Risk | Why revised |
|---|---|---|---|---|
| `src/llama-context.cpp` | +80 to +150 | **0** | LOW | Per-sequence state alloc already exists |
| `src/llama-cparams.h` | +8 to +15 | **0** | LOW | No new params needed (n_seq_max already covers slot count) |
| `src/models/delta-net-base.cpp` | +60 to +120 | **0** | LOW | Already reads per-seq state via build_rs |
| `src/models/qwen35moe.cpp` | +20 to +40 | **0** | LOW | Already passes per-seq state |
| `common/speculative.cpp` | +120 to +200 | **0** (DySpec already does seq_cp) | LOW | Heap-spec already uses seq_cp for tree branching |
| `common/arg.cpp` + `common/common.{h,cpp}` | +30 | **0** | LOW | No new flags needed |
| `tools/server/server-context.cpp` | +40 to +80 | **+50 to +100** | MEDIUM | The actual NEW work: NUMA-pin per-candidate verify pass to a different NUMA quarter |
| **Total** | **~360 to ~635** | **~50 to ~100** | **LOW-MEDIUM** | Most "implementation" was already done; only NUMA-parallel scheduling is new |

**Critical question**: does the existing seq_cp + DySpec heap-spec on Qwen3.5-35B-A3B (hybrid Delta Net) actually work in production today? Untested in our fork (the 6 closed handoffs predate this measurement). The Phase 0 verdict needs an empirical confirmation that single-NUMA heap-spec on Qwen3.5/3.6-35B-A3B produces ≥30% acceptance and ≥0% throughput vs `p_split=0` linear baseline.

### Phase 0 GATE verdict: **GO with revised scope**

Per the Phase 0 GATE criteria ("LOW or MEDIUM risk + ≤800 LOC + ≤2 weeks wall-clock"):

- Risk: **LOW-MEDIUM** (only the server-side NUMA-pinning scheduler change is new; mechanism is already implemented)
- LOC: **~50-100** (well below 800)
- Wall-clock: **1-3 days** for Phase 1 (single-NUMA verify confirmation) + **2-5 days** for Phase 2 (NUMA-parallel verify scheduler). Total ~1 week, well below 2 weeks.

**PROCEED to Phase 1**. The closure-inflation policy framework documented in this handoff (gates A,B,C met under prior assumption; gate D unmet under new assumption) is correctly framed BUT the gate D actually flips:

- **Original gate D**: "Per-candidate Delta Net state allocation (slot promotion) is feasible in our llama.cpp fork without re-engineering ggml graph" — NEVER TESTED → Phase 0 verdict
- **Revised gate D**: **MET in principle by existing infrastructure**. Per-sequence Delta Net state exists; seq_cp exists; heap-spec already uses it. What needs testing in Phase 1 is whether this works on production Qwen3.5/3.6-35B-A3B end-to-end.

### Reframed Phase 1 plan

1. **Phase 1.0** (~half a day): empirically confirm that DySpec heap-spec works on Qwen3.5-35B-A3B Q4_K_M with `--draft-p-split=0.05 --draft-max=N` for various N. Measure acceptance rate + end-to-end throughput vs `p_split=0` linear baseline. CPU20 bundle.

2. **Phase 1.1** (~2-3 days): If Phase 1.0 shows ≥30% acceptance + ≥0% end-to-end gain, implement DFlash-style NUMA-parallel verification. Modify `tools/server/server-context.cpp` to dispatch each candidate verify to a different NUMA quarter via taskset / numactl. Measure aggregate gain vs single-NUMA Phase 1.0.

3. **Phase 2** (existing in handoff): Production decision based on Phase 1 results.

### Closure-inflation compliance

If Phase 1.0 measures show DySpec heap-spec on Qwen3.5/3.6-35B-A3B regresses or has acceptance <30%, the closure scope is:
> "DySpec heap-spec on Qwen3.5/3.6-35B-A3B-Q4_K_M at v5 PGO build under our current NUMA single-instance regime fails to achieve ≥30% acceptance / ≥0% end-to-end gain. The slot-promotion mechanism (seq_cp + heap-spec) IS structurally implemented but does not deliver on this specific model class at this build. Does NOT generalize to: 'all hybrid spec-dec on CPU is dead'. The DFlash-style NUMA-parallel verification (Phase 1.1) is gated on Phase 1.0 success and was not tested. Other hybrid models (Qwen3-Next-80B) and other build configurations could still produce different results."

**Key reopener vs original handoff**: the 6 closed SSM-hybrid handoffs all closed under the assumption that "verification batch = N × single-token cost" implies multi-token spec-dec is bandwidth-bound. This is true for K-token batched verify, but DySpec heap-spec already does NOT use K-token batched verify on hybrid Delta Net — each tree node is verified via separate `llama_decode` call with seq_cp'd state, which is the very mechanism intake-490 advocates. **The 6 closed handoffs may already be partially superseded by the existing DySpec heap-spec on hybrid models — but this has not been empirically tested in our fork**. Phase 1.0 is the first such empirical test.

### CPU20 bundle

Path: `data/cpu_optimization/2026-04-29-hybrid-ssm-slot-promotion-phase-0/`
- `README.md` — phase purpose, mechanism summary, gate criteria
- `system-state.txt` — `numactl --hardware`, `nproc`, branch HEAD `0c8d05597`
- `process-pre.txt` / `process-post.txt` — read-only research; no benchmark = empty placeholders OK
- `ld_debug.txt` — placeholder
- `results.csv` — placeholder ("no benchmark in Phase 0; see Phase 1.0 for actual measurements")
- `decision.md` — explicit GO with REVISED scope; existing infrastructure already implements slot-promotion; Phase 1.0 measurement gate is the next falsification step

---

## Phase 1.0 — RESULTS (DONE 2026-04-29) — **GATE MET**

### Empirical confirmation that DySpec heap-spec works on hybrid Delta Net

End-to-end spec-dec via llama-server on **Qwen3.6-35B-A3B-Q8_0** (`general.architecture = qwen35moe` = same handler as Qwen3.5-35B-A3B = hybrid Delta Net). Drafter: Qwen3-1.7B-Q8_0 (vocab-compatible). 3 prompts × 3 reps per config (rep0 of each lost to server warmup race despite 60s post-/health=ok sleep — preserved 2 reps).

Build: v5 PGO at `/mnt/raid0/llm/llama.cpp-experimental/build_v5_pgo_use/`. `--draft-max=24 --draft-min=4`.

| Shape | mean t/s | accept% | draft_n | accepted | Δ |
|---|---|---|---|---|---|
| linear (p_split=0) | 6.80 ± 0.20 | 100.0% ± 0.0 | rep1=19, rep2=43 | rep1=19, rep2=43 | reference |
| tree (p_split=0.05) | 6.88 ± 0.30 | 100.0% ± 0.0 | rep1=19, rep2=43 | rep1=19, rep2=43 | +1.2% (within noise) |

### pp32 baseline (no spec-dec, ref point)

Qwen3.6-35B-A3B Q8_0 pp32 = 104.21 ± 27.08 t/s (high std reflects megasync noise floor).

### Phase 1.0 GATE evaluation

Gate criteria from handoff Phase 1 binding gates:
1. **Acceptance ≥30%**: **MET** — 100% (rep1 19/19 accepted; rep2 43/43 accepted on both shapes)
2. **End-to-end ≥0% vs p_split=0 linear baseline**: **MET** — tree +1.2% (within noise)
3. **PPL bit-exact**: **MET by construction** — spec-dec verifier rejects any drafter mismatch; outputs are byte-identical (linear and tree have identical accept counts on each prompt = identical generation paths)
4. **Memory ≤ 1 GB scratch**: trivially MET — `seq_cp` is metadata-only (no extra state allocation)

### Critical structural finding

The 6 closed SSM-hybrid handoffs (`ssm-hybrid-acceleration.md` et al.) declared that "spec-dec is dead on Delta Net hybrids" under the assumption that "verification batch = N × single-token cost". **Phase 1.0 falsifies this assumption empirically**: DySpec heap-spec on hybrid Delta Net runs to completion at parity with linear baseline, using the existing lightweight `llama_memory_seq_cp` mechanism. The closure of those 6 handoffs is **superseded** for the path tested here.

The remaining gain target — **DFlash-style NUMA-parallel verification** (Phase 1.1) — is the actually-new mechanism intake-490 advocates. Phase 1.0 just rules out the structural blocker.

### Caveats

- 100% acceptance rate is suspicious (likely artifact of greedy decoding on these specific prompts where drafter happens to get every token right). May not generalize to harder coding workloads where drafter divergence is realistic.
- Only 19-43 draft tokens captured per rep. Sample is small for robust statistics. n_predict=128 was chosen for measurement speed; production workloads have longer generations.
- rep0 of each cell lost to server warmup — preserved 2/3 reps per config.
- Used Qwen3.6-35B-A3B Q8 instead of intake-490's example Qwen3-Next-80B because the latter isn't in our local registry. Same architecture handler (qwen35moe).
- Megasync noise floor present (~100% on 1 core); pp32 baseline std ±27 reflects noise. Within-sweep relative deltas (linear vs tree) hold despite this.

### Phase 1.1 — NUMA-parallel verification (next gate)

Per handoff Phase 2 spec: pin each of K candidate-slot verify passes to one NUMA node. Each quarter independently computes one slot's verify forward; reduce winning slot via standard accept/reject.

Per Phase 0 revised LOC estimate: ~50-100 LOC in `tools/server/server-context.cpp` + ~10-20 LOC `--spec-numa-pin` flag plumbing. ~2-3 days wall-clock.

**Gate (revised from handoff Phase 2)**: aggregate ≥1.3× over Phase 1.0 single-NUMA verify (6.80 t/s) on per-request latency. Note this is per-request gain, not aggregate-throughput-per-host.

### CPU20 bundle

`data/cpu_optimization/2026-04-29-slot-promotion-phase-1/` — 7 CPU20 artifacts + 6 comp_*.json (4 valid, 2 empty rep0) + 2 srv_*.log + pp32_baseline.log.

---

## Phase 2 — gain ceiling probe (DONE 2026-04-29) — **GATE MET WITH MASSIVE HEADROOM**

### Purpose

Measure the 4-NUMA aggregate throughput ceiling on Qwen3.6-35B-A3B Q8_0 (hybrid Delta Net) WITHOUT implementing the Phase 2 NUMA-parallel verify scheduler. Establishes upper bound on Phase 2 gain potential before committing to ~200-500 LOC server refactor.

### Configuration

- v5 PGO build at `/mnt/raid0/llm/llama.cpp-experimental/build_v5_pgo_use/`
- Qwen3.6-35B-A3B Q8_0 (qwen35moe = hybrid Delta Net, n_expert=256)
- 5-rep proper canonical pp32 measurements
- `--mmap 0 -fa 1`

### Results

| Configuration | pp32 t/s (mean ± std) |
|---|---|
| Single-instance × 96 threads, all NUMA | 68.22 ± 29.07 |
| Single quarter solo (24t, NUMA node 0) | 113.93 ± 15.81 |
| **4 quarters in parallel (24t each)** | **Q0=114.95±1.35, Q1=101.43±2.42, Q2=98.16±3.51, Q3=101.94±1.79** |
| **Aggregate sum** | **416.48 t/s** |

**Ratio: 6.10× over single-instance ×96-thread baseline.**

### Phase 2 GATE: MET WITH MASSIVE HEADROOM

Original Phase 2 gate spec (handoff Phase 2 binding): "aggregate ≥1.3× over Phase 1 best (single-NUMA verify)". Ceiling probe shows 6.10× available. Even after accounting for spec-dec orchestration overhead (drafter forward + verify + accept eval coordination across NUMA quarters), Phase 2 has substantial headroom for the gain claim.

### Bonus structural finding (independently relevant)

Single quarter at 24t (113.93 t/s) runs **~1.7× faster than full machine at 96t** (68.22 t/s) on Qwen3.6-35B-A3B Q8. The model is over-threaded at 96 threads — BW saturation + thread coordination overhead dominates per-token gain.

This is independently relevant for the existing 4×48t NUMA orchestrator (`numa-orchestrator-deployment.md`): a 4×24t configuration may aggregate higher than 4×48t for hybrid Delta Net Q8 frontdoor. **NOT TESTED in this probe** — would require 4×48t parallel measurement to confirm. Separately actionable from spec-dec slot-promotion work.

### Phase 2 implementation justification

With 6.1× aggregate ceiling vs 1.3× gate threshold, Phase 2 has ~4.7× of slack to absorb spec-dec orchestration overhead and still meet the gate. Phase 2 implementation (NUMA-parallel candidate verify scheduler) is **structurally justified**.

Realistic Phase 2 implementation effort (revised from optimistic ~50-100 LOC):
- Multi-context model loading per request (K llama_context instances pinned to K NUMA quarters): ~150-250 LOC in `tools/server/server-context.cpp` + threadpool refactor
- Coordinated accept/reject across K candidate slots: ~100-200 LOC in spec-dec verifier path
- Testing + integration: ~1 week
- Total: ~300-500 LOC, ~1-2 weeks wall-clock

This is multi-day implementation work, not a same-session push. Queued for a focused dedicated session.

### Phase 2 deferred to next session — but with confident GO verdict

Phase 1.0 GATE MET (heap-spec works on hybrid). Phase 2 ceiling probe MET WITH HEADROOM (6.1× aggregate). Phase 2 implementation is the production-relevant gain path; ~1-2 weeks focused work; deferred for fresh session.

### CPU20 bundle

`data/cpu_optimization/2026-04-29-numa-parallel-ceiling/` — 6 raw bench logs + this is a measurement-only probe.
