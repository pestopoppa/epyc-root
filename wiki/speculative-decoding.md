# Speculative Decoding

**Category**: `speculative_decoding`
**Confidence**: verified
**Last compiled**: 2026-04-30
**Sources**: 32 documents (3 deep-dives, 4 completed handoffs, 4 active handoffs, 21 intake entries)

## Summary

Speculative decoding accelerates autoregressive inference by drafting multiple candidate tokens cheaply, then verifying them against the target model in a single batch. The fundamental promise is that verification of N tokens can be cheaper than N sequential decodes -- but on our EPYC 9655 CPU stack, this promise is architecture-dependent: it holds for dense and pure MoE models but breaks catastrophically on hybrid recurrent architectures.

Our production experience spans the full spectrum. Tree speculation on Qwen2.5-Coder-32B (dense, f16) yields +15.8% throughput. External drafting with a 0.75B Qwen3-Coder model gives +55% on dense 32B targets. But every speculative approach tested on Qwen3.5 hybrid models -- MTP-1, tree speculation (Approaches 0, A, C), and DFlash -- results in net-negative throughput (-53% to -66%). The root cause is that 75% of layers in Qwen3.5 are Delta Net recurrent layers that process tokens sequentially regardless of batch size, making multi-token verification O(N) instead of O(1). This "verification wall" is the single most important finding in our speculative decoding research, and it applies equally to all draft-verify paradigms: autoregressive, tree, and block diffusion.

The frontier technique is DFlash (block diffusion speculation), which drafts 16 tokens in a single O(1) forward pass through a 0.5B drafter -- a genuine architectural advance over the linear O(N) cost of EAGLE-style autoregressive drafting. On GPU, DFlash achieves 6.49 accepted tokens per round on Qwen3-8B (greedy). However, our 21-commit llama.cpp C++ port (forward pass verified bit-exact against HuggingFace) demonstrated that DFlash is not viable on Q4_K_M quantized models: per-token acceptance drops to 27%, yielding only 1.4% block acceptance. The quantization noise in hidden state extraction degrades the conditioning signal beyond recovery. The autoregressive drafter wins decisively (36.5 vs 13.0 t/s). A complementary technique, DART, uses a single-layer drafter with a 100GB n-gram trie from the Dolma corpus to prune draft trees, boosting acceptance by +0.5-0.7 tokens -- feasible on our 768GB+ RAM but with lower base acceptance (3.67-3.76 vs DFlash's 6.49).

A separate line of research addresses reasoning efficiency without touching the draft-verify loop. The short-m@k paper demonstrates that shorter reasoning chains are up to 34.5% more accurate than longer ones within the same question, because correct reasoning proceeds efficiently while incorrect reasoning wanders (95-188 backtracks for correct vs 269-352 for incorrect). This yields a zero-cost "length alarm" heuristic: when a `<think>` block exceeds 1.5x the difficulty band budget, cancel and re-generate with a fresh seed. The full parallel approach (k concurrent streams, take the first m to finish) requires multi-slot infrastructure we currently lack, but the heuristic alone integrates cleanly with our existing difficulty-band system at near-zero implementation cost.

A promising new direction is calibration-based early exit (TIDE, intake-422/423). Unlike LayerSkip/SWIFT which require fine-tuning, TIDE trains tiny MLP routers (~0.5M params) on cosine similarity between hidden states at checkpoint layers -- calibration takes <3 minutes on 2000 samples. On GPU, this yields 6.6-8.1% throughput gains. On CPU at batch_size=1, the gain is projected at 15-25% because (a) there is no batch compaction overhead, (b) layer compute is the dominant cost, and (c) the router check is a trivial matmul. Our fork already has `n_layer_exit` support across 7 model architectures including qwen3moe (production); the deep dive maps a 3-phase implementation path from external router → per-token exit → GGUF-embedded routers. This directly addresses the HSD finding that static layer-skip yields near-zero acceptance -- the learned router prevents quality degradation by only exiting tokens that have genuinely converged.

The current state of the art for our stack is not speculative decoding at all -- it is NUMA 4-way parallel serving (4 independent model instances on 48 threads each), which delivers 6.7x aggregate throughput on the frontdoor role. Speculative decoding provides incremental gains on top (+17-21% from draft_max tuning, +2-5% from tree branching on large dense targets) but is no longer the primary acceleration lever. The opening provided by REAP expert pruning is significant, however: REAP-25B is pure MoE (`qwen3moe` arch), meaning speculative decoding works where the hybrid frontdoor previously made it impossible.

## Key Findings

- **Verification wall on hybrid recurrent models**: Multi-token verification on Qwen3.5 (75% Delta Net layers) costs approximately N times single-token decode. MTP-1 measured 0.56x throughput at batch-size 2. Tree speculation measured -53% to -66% across three implementation approaches (frozen multi-path, per-path sequential replay, checkpoint/clone-cell). DFlash projected approximately 0.3x (16 tokens at approximately 16x cost). The root cause is architectural: recurrent layers process tokens sequentially regardless of batch size, while GPU parallel scan hides this cost. [DFlash deep-dive](../research/deep-dives/dflash-dart-diffusion-speculation.md), [Tree speculation handoff](../handoffs/completed/tree-speculation-numa-drafting.md)

- **DFlash O(1) drafting is real but quantization kills acceptance**: DFlash generates 16 tokens in one forward pass via a 0.5B drafter conditioned on hidden states from 5 uniformly-sampled target layers. The drafter's cost is constant regardless of draft length -- fundamentally different from EAGLE-3's O(N) autoregressive cost. On GPU (f16), acceptance is 6.49 tokens per round. On our Q4_K_M stack, acceptance drops to 27% per token because quantized hidden states corrupt the conditioning signal. The DFlash handoff concluded after 21 commits with verified-correct C++ forward pass: not viable on Q4_K_M, autoregressive wins 36.5 vs 13.0 t/s. [DFlash deep-dive](../research/deep-dives/dflash-dart-diffusion-speculation.md), [DFlash handoff](../handoffs/completed/dflash-block-diffusion-speculation.md)

- **DFlash + tree speculation is composable and multiplicative**: DFlash's parallel logits at all 16 positions can build a tree (take top-k at each position) at O(1) cost -- the same as linear. In standard tree speculation, building the tree requires N sequential draft passes. Projected impact on large architect models: 2-4x base DFlash times 1.15 tree bonus equals 2.3-4.6x. The tree bonus is largest for the architect models (235B, 480B) where verification headroom is greatest. [DFlash deep-dive](../research/deep-dives/dflash-dart-diffusion-speculation.md)

- **DART trades drafter quality for speed + n-gram diversity**: DART uses a single transformer decoder layer (approximately 0.1B params, 3.5ms draft latency including n-gram lookup) conditioned on 3 target layers. Base acceptance is 3.67-3.76, lower than DFlash's 6.49, but the 100GB Dolma 3-gram trie boosts acceptance +0.5-0.7 via tree pruning. The trie is feasible on our 768GB+ system but represents a significant memory commitment for modest acceptance gains. DART's published training recipe is valuable reference for when DFlash publishes theirs. [DFlash deep-dive](../research/deep-dives/dflash-dart-diffusion-speculation.md)

- **Tree speculation is structurally sound but overhead-limited on CPU**: The tree construction and verification infrastructure was implemented across 8 phases. On 32B f16 targets, tree gives +15.8% (5.01 to 5.80 t/s). On Q4_K_M, tree equals or underperforms linear because Q4_K_M verification is 4-5x at N=64 (not near-free like f16 at 1.69x). NUMA 4-way delivers much larger gains (6-7x aggregate). [Tree speculation handoff](../handoffs/completed/tree-speculation-numa-drafting.md)

- **draft_max tuning gives free throughput**: Increasing `--draft-max` from 16 to 24-48 yields +17-21% across all production models with zero code changes. REAP-25B optimal is dm=24 linear (39.62 t/s). This was the single highest-ROI speculative optimization. [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

- **Shorter reasoning chains are more accurate (short-m@k)**: Within any given question, shorter reasoning chains are up to 34.5% more accurate (LN-Super-49B) and use 42-54% fewer tokens. Correct reasoning is concise; incorrect reasoning wanders with compounding per-token error. Deployable without parallelism: short-1@k (take single shortest) gives equal accuracy with 40% fewer thinking tokens and approximately 50% less wall-time. Finetuning on short chains yields +2.8% accuracy and -5.8% tokens. [short-m@k deep-dive](../research/deep-dives/short-mk-parallel-reasoning.md)

- **Length alarm integrates with difficulty bands**: Easy problems benefit most from length-based filtering (wrong/right token ratio 2x vs 1.3x for hard). Our band-adaptive budgets (easy=1,500, medium=3,500, hard=7,000) are well-calibrated. The addition: if generation exceeds 1.5x band budget, treat as failure signal and re-generate. Three-layer stack: conciseness prompting (shifts distribution left) + band budgets (caps right tail) + length alarm (actively selects shorter chains). [short-m@k deep-dive](../research/deep-dives/short-mk-parallel-reasoning.md)

- **NUMA parallelism could reopen hybrid speculation**: If 4 concurrent single-token decodes on separate NUMA nodes achieve >2.5x aggregate throughput, NUMA-parallel verification (N nodes times 1 token each, parallel) could break the sequential recurrent bottleneck. Each node needs its own model copy (approximately 20GB Q4_K_M). The project's existing concurrent execution tests showed aggregate throughput gains. [DFlash deep-dive](../research/deep-dives/dflash-dart-diffusion-speculation.md)

- **REAP-pruned models are speculation-compatible**: REAP-25B is pure MoE (`qwen3moe` arch), so all speculation approaches work. Optimal config: dm=24 linear at 39.62 t/s (101% of base 30B with dm=8). Tree hurts (30.83 t/s, 79%). Lookup is safe but doesn't help on short prompts (37.91 t/s). If the frontdoor shifts from hybrid Qwen3.5 to REAP-25B, speculation becomes viable for the highest-volume role. [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

## Actionable for EPYC

- **Deployed and validated**: NUMA 4-way parallel (6.7x frontdoor), draft_max 32-48 (+17-21%), external drafting with 0.75B Qwen3-Coder (+55% on dense targets), auto freeze-recurrent for hybrid speculation, REAP-25B with dm=24 (39.62 t/s)

- **Implement now**: Reasoning length alarm (Phase 0 of short-m@k). Approximately 80 lines in `src/graph/helpers.py`, integrates with existing `difficulty_signal.py` bands and `detect_think_block_loop()`. Zero infrastructure cost. Expected to improve accuracy on easy problems where the wrong/right token ratio is highest (2x). Estimated effort: 1 day

- **Worth investigating**: NUMA-parallel verification benchmark (2-3 day effort to determine if NUMA isolation can break the hybrid verification wall -- if aggregate/N > 0.6x individual, project DFlash viability with tau=6.49 and N-parallel verification). DFlash tree composition on f16 dense targets (multiplicative benefits for architect models). Sequential short-1@k for math/reasoning tasks (Phase 1, k=2-3 generations keep shortest, 2 days, gated behind feature flag)

- **Blocked/concluded (CPU)**: DFlash on Q4_K_M (concluded: 27% per-token acceptance, AR wins 36.5 vs 13.0 t/s). All tree/MTP approaches on hybrid models (concluded: -53% to -66%). Full short-m@k parallel generation (requires multi-slot infrastructure on architect models that we lack). DFlash training recipe not yet published

- **GPU reopener — vLLM DDTree+Dflash** (2026-04-15): Community benchmark reports **91 tok/s accepted** on Qwen3.5-27B AWQ with DDTree (tree verification) + Dflash (block diffusion drafting) on DGX Spark GB10, 96.4% acceptance rate. GPU parallel scan handles the Delta Net recurrent state that kills CPU speculation. DFlash paper reports τ=6.49 on Qwen3.5-35B-A3B (GPU). This is vLLM-native, not llama.cpp — the entire pipeline (diffusion drafting, tree verification, KV management) is GPU-optimized. Reproduction plan in [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md), blocked on DGX Spark acquisition.

- **Priority**: Low-to-medium on CPU (concluded). Potentially HIGH on GPU if DGX Spark is acquired — the 91 t/s community benchmark would make Dflash speculation the single most impactful GPU optimization. NUMA parallelism and KV cache optimization remain the primary CPU acceleration frontiers.

## 2026-04-28 Update — MoE-Spec deployable, MAB selector + slot-promotion reopener

**MoE-Spec verification-budget mechanism gate MET on pure-MoE targets** (Phase 1 prototype, autonomous CPU agent's session): `--moe-spec-budget N` aggregates routing softmax across the verification batch and shrinks the active-expert union. Phase 1 forward-pass measurements: Coder-30B Q4_K_M B=64 +7.3%, REAP-246B Q4_K_M B=40 +15.2% (both 5-rep proper canonical). Phase 2 v5 PGO end-to-end via llama-server attenuates significantly — REAP-246B end-to-end +3%, Coder-30B end-to-end +9% — because spec-dec round = drafter forward + target verification + accept-evaluation, and MoE-Spec only accelerates target verification (Amdahl ceiling). **Final verdict**: REAP-246B B=40 deployable; Coder-30B B=64 NOT deployable (varies wildly across builds + cache states + system noise). Production registry integration queued behind explicit pre-prod gate. Tracked at [`moe-spec-cpu-spec-dec-integration.md`](../handoffs/active/moe-spec-cpu-spec-dec-integration.md).

**MAB tree-shape selector (intake-491, EMNLP'25 §3.2)**: drop-in over heap-spec for pure-MoE targets, orthogonal compounding axis to MoE-Spec verification budget. Paper reports sequential 112.69 → MAB-optimized 138.22 t/s on Pythia-6.9B (+22.65% over sequential / +8.5% over best fixed shape). UCB1-style arm pull over a fixed pool of tree shapes; reward = accept_len/draft_len. End-to-end Amdahl ceiling applies (selector operates on the same verification step). Phase 0 falsification probe queued. Tracked at [`mab-tree-shape-selector.md`](../handoffs/active/mab-tree-shape-selector.md).

**Hybrid SSM spec-dec slot-promotion reopener (intake-490, PyTorch SGLang Dec 2025)**: per-candidate state slots via `S_new = S_parent + Δ(k,v,β,g)`; rejected slots discarded, accepted slot promoted. Architecturally compatible with Delta Net. Combined with DFlash-style NUMA-parallel single-token verify (one candidate per NUMA quarter), per-candidate cost drops from 450 MB clone (our prior `clone_cell` failure) to ~KB staged inputs AND verification wall-clock for K candidates drops from `K × single-token` to `1 × single-token` per quarter. Reopens the 6 closed SSM-hybrid handoffs under closure-inflation policy (gates A,B,C met under prior assumption; gate D unmet under per-candidate-slot assumption). Phase 0 research-only falsification queued. Tracked at [`hybrid-ssm-slot-promotion-spec-dec.md`](../handoffs/active/hybrid-ssm-slot-promotion-spec-dec.md). Cost model projects ~1.4× single-instance per-request latency on Qwen3.5-35B-A3B Q4_K_M if Phase 1 lands.

Together these three handoffs add three orthogonal compounding axes to spec-dec on EPYC: verification budget (MoE-Spec, deployable), tree topology (MAB selector, Phase 0), hybrid state model (slot-promotion, Phase 0).

## Updates — 2026-04-28

### MoE-Spec verification-batch mechanism (Phase 1+2 v5 PGO)

The `--moe-spec-budget N` mechanism — see [`moe-spec-cpu-spec-dec-integration.md`](../handoffs/active/moe-spec-cpu-spec-dec-integration.md) — aggregates routing softmax across the K-token verification batch, takes top-B over the aggregated distribution, and masks out-of-budget experts before `argsort_top_k`. Mechanism rationale: in a verification batch, the union of distinct experts selected across K tokens is a routing-policy-dependent superset of any single token's top-K. Reducing that union directly reduces DRAM expert-weight reads — the dominant decode cost on EPYC per CPU24 attribution.

Phase 1 forward-pass measurements (5-rep canonical, autonomous CPU agent's session):

| Model | Quant | Budget | pp32 baseline | pp32 MoE-Spec | Δ verify |
|-------|-------|--------|---------------|---------------|----------|
| Coder-30B | Q4_K_M | B=64 | 321.35 t/s | 344.70 t/s | +7.3% |
| REAP-246B | Q4_K_M | B=40 | 45.23 t/s | 52.11 t/s | +15.2% |

PPL drift (3-chunk WikiText-2 spot check): Coder-30B +6.7%, REAP-246B +23%. Drift is bounded by the assumption that out-of-budget experts contribute negligibly per-token; larger models have more diffuse routing and larger drift.

Phase 2 end-to-end via llama-server (v5 PGO build, mixed-batch regimen): REAP-246B B=40 +3.3% e2e, Coder-30B B=64 −2.6% e2e (within build/cache-state noise). The end-to-end attenuation is Amdahl-determined: a spec-dec round = drafter forward + target verification + accept-evaluation, and MoE-Spec only accelerates target verification. Drafter and accept-eval are unchanged.

**Final verdict**: REAP-246B B=40 deployable behind explicit env-gate `LLAMA_ARG_MOE_SPEC_BUDGET=40` for the REAP role only. Coder-30B B=64 NOT deployable — the mask-overhead vs total-compute ratio is marginal, and end-to-end measurements vary across builds and cache states beyond the gain margin. Defer Coder-30B to Phase 3 cleaner re-measurement after MAB selector lands.

The cause for the measured-vs-predicted gain is geometric: EPYC's L3 (~32 MB per CCD × 12 = 384 MB) is far below total expert-weight footprint (Coder 17 GB, REAP 138 GB at Q4_K_M). Cutting expert-union size directly reduces DRAM traffic. Larger models therefore have more headroom — REAP at +15.2% vs Coder at +7.3% is consistent with this attribution.

### Hybrid SSM slot-promotion reopener (intake-490) — CLOSED 2026-04-30, mechanism net-negative on Qwen3.6-35B + Qwen3-1.7B drafter

Handoff moved to [`completed/hybrid-ssm-slot-promotion-spec-dec.md`](../handoffs/completed/hybrid-ssm-slot-promotion-spec-dec.md). **Closure-inflation correction (preserved)**: the prior "speculation dead on hybrid SSM" claim was valid under the K-token-batched-verify cost model and is preserved as accurate in [`completed/ssm-hybrid-acceleration.md`](../handoffs/completed/ssm-hybrid-acceleration.md) for all 7 closed approaches (clone_cell, K-token-batch, MoE self-draft, attention-only draft, prefix prefetch, per-token speculation, multi-context replay). The reopener tested a fundamentally different cost model.

New mechanism from SGLang (PyTorch blog, Dec 2025): per-candidate state slots `S_new = S_parent + Δ(k,v,β,g)`, plus DFlash-style NUMA-parallel single-token verify (one candidate per NUMA quarter). The reopener implementation took dispatcher v0 (pass-through) to dispatcher v1 (functional K-parallel candidate verify) in commit `d45126db5` on `feature/cpu-ep-inter-process` (+386 LOC). All 7 sub-slices landed: alt-path selection from `speculation_tree::get_paths()`, one-shot primary→aux state sync at `SLOT_STATE_GENERATING`, sequential pre-decode aux state sync (race-free), parallel aux decode threads, per-ctx sample-and-accept reducer, winner-state commit with `slot.smpl` + `slot.spec_draft` rotation.

**Slice B.5 gate-check PASSED**: state-sync cost is 62.81 MiB/aux ctx (5.3× smaller than the brief's 330 MiB worst-case), 17.5 ms one-shot per request, ~5.8 ms per primary→aux pair on Q8 hybrid — well under per-token gate budget.

**Slice G canonical 3-prompt × 2-rep result on Qwen3.6-35B-A3B-Q8_0 + Qwen3-1.7B-Q8_0 drafter at v5 PGO build**: K=1 = 11.40 t/s mean, K=4 dispatcher v1 = 7.42 t/s mean — **K=4 is 35% slower**. Gate (≥1.3×) NOT MET.

**Slice G divergent-tree sensitivity sweep (4 (p_split, temp) configs × 5 prompts including creative + open-ended)**: dispatcher engages 62 times, but **primary wins 60/62 (97%)**. The 2 aux-winning rounds delivered just +1 marginal accepted token each. Per-round economics: ~22 ms K-parallel overhead vs 0.03 × 83 = 2.5 ms expected savings = **−20 ms/round net loss**.

**Important correction to canonical analysis**: the early "K-parallel verify hit count = 0" claim was an artifact of non-verbose log filter that suppressed DBG-level engagement messages. The dispatcher actively engages on canonical workload — it just loses 97% of the time.

**Why architectural pivot was abandoned**: pre-sweep, the 35% slowdown was attributed to thread-count penalty (primary 24t vs 96t). The sweep falsified that — the deeper issue is that aux paths verify the SAME tokens primary already verifies in 97% of rounds, even at p_split=0.001 + temperature=0.7. Threading reconfiguration would not change aux win-rate.

**Closure scope (per closure-inflation policy)**: mechanism is structurally net-negative for THIS drafter/target/workload class. Does NOT generalize to "K-parallel verify is dead" — different drafter models (larger drafter that produces alt branches more aligned with target sampling), different target models, different K values, and very different workload classes (long-form generation with frequent ambiguity) remain unevaluated.

**Operational disposition**: dispatcher v1 stays in tree as disabled-by-default (`--spec-numa-quarters` defaults to 1; `LLAMA_ARG_SPEC_NUMA_QUARTERS` env equivalent). Re-evaluate on different drafter/target pairs. The 6.10× ceiling probe that motivated this work measured AGGREGATE THROUGHPUT across independent slots (NUMA-quarter splitting for 4× concurrent inference), not per-request K-parallel verify gain — these are two different mechanisms; the aggregate-throughput one is already deployed in production via the orchestrator's 4×24t splits.

CPU20 bundles: [`2026-04-30-state-sync-cost-probe/`](../../epyc-inference-research/data/cpu_optimization/2026-04-30-state-sync-cost-probe/) (canonical 3×2 + state-sync probe), [`2026-04-30-divergent-tree-sweep/`](../../epyc-inference-research/data/cpu_optimization/2026-04-30-divergent-tree-sweep/) (4 configs × 5 prompts engagement probe).

### MAB tree-shape selector Phase 0 NO-GO (intake-491 §3.2)

Per [`mab-tree-shape-selector.md`](../handoffs/active/mab-tree-shape-selector.md). The paper-claimed +13.7% sequential→MAB-optimized result was falsified on EPYC at temperature=0 greedy: tree at p_split=0.05 produces BYTE-IDENTICAL outputs to linear p_split=0 (verifier collapses to greedy path) while adding wasted draft+verify overhead. End-to-end: Coder −18% mean (high variance ±48% CV), REAP +1.4% (within noise).

**Narrow closure scope**: MAB selector over the paper's arm pool cannot recover headroom that is structurally absent when the greedy verifier discards non-greedy branches. The closure does NOT generalize to:
- Sampling-temperature regime (where non-greedy branches might be accepted)
- Different arm pools (the paper's pool is heap-spec-derived; an arm pool tuned to EPYC's 96-core verifier could differ)
- Non-MoE targets (this was tested on Coder-30B and REAP-246B only)

This is a closure-inflation-policy-compliant gate enumeration: the paper's specific arm pool × greedy regime is closed. The general MAB selector technique remains open under different conditions.

### Amdahl ceiling for spec-dec end-to-end gain (cross-cutting)

Spec-dec round decomposes as: drafter forward + target verification + accept-evaluation. All three orthogonal axes added in 2026-04-28 (MoE-Spec budget, MAB tree topology, slot-promotion) target the verification step only, and inherit the same Amdahl ceiling. REAP +13.5% pp32 verify → +3% e2e because drafter+accept-eval are unchanged.

This means NUMA-4-way concurrent serving (~6.7× frontdoor aggregate, see [`large-moe-expert-parallelism.md`](../handoffs/active/large-moe-expert-parallelism.md)) remains the primary CPU acceleration lever. Spec-dec axes are stacking incremental gains on top of an already-saturated verification-step budget. To push past the Amdahl ceiling, future work would need to accelerate the drafter forward or accept-evaluation steps independently.

### Mamba Drafters EMNLP'25 Findings (intake-491)

External SSM drafter for Transformer target: Mamba-130M matches/beats much larger Pythia drafters at constant memory vs context length. Memory at 8k context: Mamba 52 GB vs EAGLE 72 GB total. The accompanying tree-based MAB optimizer (the §3.2 result above): sequential 112.69 → MAB-optimized 138.22 t/s on Pythia-6.9B / GSM-8K (paper).

Acceptance limitations (per the paper):
- Hidden-state backtracking: Mamba discards previous hidden states, complicating rejection recovery
- Tree-verification incompatibility: SSM sequential token processing precludes parallel path verification on the drafter side
- Hyperparameter sensitivity

Verdict: worth_investigating. The principle (SSM drafter for Transformer target) generalizes, but Pythia-6.9B / Mistral-7B target+drafter combos in the paper are too small to map directly onto our 30B / 246B stack. Bookmarked for future investigation when a larger SSM drafter checkpoint becomes available.

## Open Questions

- Can NUMA-isolated concurrent verification break the sequential recurrent bottleneck on Qwen3.5? If 4 NUMA nodes give >2.5x aggregate throughput, DFlash becomes interesting again on hybrid models
- What is DFlash's acceptance rate on f16 hidden states (no quantization noise)? The Q4_K_M failure may be specific to quantized conditioning -- f16 testing was not attempted before the handoff concluded
- Can DFlash + tree composition achieve the projected 2.3-4.6x on architect models (235B, 480B)? These are the highest-value targets due to slow baseline decode (300-800ms per token)
- Will DFlash publish training recipes enabling custom drafter training for our models? DART's published recipe is the interim reference
- Does the length alarm heuristic (Phase 0 short-m@k) interact with speculative decoding? Shorter reasoning chains may improve draft acceptance by reducing distribution shift over long sequences
- Can Qwen3.5 hybrid serving benefit from the Qwen3.5 serving recipe (intake-152) for MoE+Delta Net configuration tips? The recipe may offer incremental non-speculation gains
- Does REAP-25B's speculation compatibility compound with NUMA 4-way (4x15GB instances = 60GB, well within quarter-machine budget)?

## Related Categories

- [KV Cache Optimization](kv-cache.md) -- KV cache size determines context capacity; speculative decoding increases KV pressure (more tokens verified per round). KV compression enables larger speculation budgets and longer effective contexts
- [MoE Optimization](moe-optimization.md) -- REAP-pruned models change speculation viability fundamentally: pure MoE is spec-compatible, hybrid is not. REAP-25B at 15GB fits trivially in quarter-machine for NUMA
- [Quantization](quantization.md) -- Q4_K_M quantization degrades DFlash hidden state conditioning (27% vs 6.49 acceptance). KV quantization (Hadamard+q4_0) interacts with verification batch size. Weight quantization determines verification cost profile (f16: 1.69x at N=64, Q4_K_M: 4-5x)

## Source References

- [DFlash & DART Deep-Dive](../research/deep-dives/dflash-dart-diffusion-speculation.md) -- O(1) block diffusion drafting, DART n-gram pruning, portability assessment (13-20 day implementation), verification wall analysis, DFlash+tree composability, NUMA-parallel reopener
- [short-m@k Deep-Dive](../research/deep-dives/short-mk-parallel-reasoning.md) -- Shorter chains more accurate (+34.5%), length as failure signal, difficulty-stratified data, Phase 0-3 implementation path, cost analysis for single-server architecture
- [DFlash Handoff](../handoffs/completed/dflash-block-diffusion-speculation.md) -- 21-commit C++ implementation, forward pass verified correct, Q4_K_M 27% acceptance, concluded not viable on quantized models (36.5 vs 13.0 t/s)
- [MTP-1 Handoff](../handoffs/completed/mtp-speculative-decoding.md) -- Model-native MTP head, 0.56x on hybrid at batch-size 2, verification cost scales linearly with recurrent layers, CLOSED
- [Tree Speculation Handoff](../handoffs/completed/tree-speculation-numa-drafting.md) -- 8 phases across 12 days, +15.8% on f16 dense, NUMA 4-way discovery (6-7x), 3 hybrid approaches all net-negative, Phase 8B deferred (40% viability)
- [HSD Hierarchical Self-Speculation Handoff](../handoffs/completed/hsd-hierarchical-self-speculation.md) -- External draft +55% on dense 32B, HSD branch resampling +0.8%, freeze-recurrent auto-enable, self-spec not viable
- [REAP Handoff](../handoffs/completed/reap-moe-expert-pruning.md) -- 246B deployed, REAP-25B dm=24 at 39.62 t/s, pure MoE enables speculation
- [Inference Acceleration Index](../handoffs/active/inference-acceleration-index.md) -- Master coordination for all inference optimization work
- [intake-016](https://arxiv.org/abs/2211.17192) arXiv:2211.17192 -- Foundational speculative decoding (Leviathan et al.)
- [intake-129](https://arxiv.org/abs/2505.17813) short-m@k paper -- Parallel reasoning, length-accuracy correlation, difficulty-stratified analysis
- [intake-152](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html) Qwen3.5 serving recipe -- Hybrid MoE+Delta Net configuration tips for non-speculation optimization
- [intake-158](https://arxiv.org/abs/2602.06036) DFlash paper (arxiv:2602.06036) -- Block diffusion speculation, O(1) draft cost, tau=6.49
- [intake-159](https://arxiv.org/abs/2601.19278) DART paper (arxiv:2601.19278) -- N-gram-pruned parallel drafting, single-layer drafter, Dolma trie
- [intake-422](https://github.com/RightNow-AI/TIDE) TIDE: Token-Informed Depth Execution -- Calibration-trained MLP routers for per-token early exit without model fine-tuning; deep dive upgraded to adopt_patterns
- [intake-423](https://arxiv.org/abs/2603.21365) TIDE paper (arxiv:2603.21365) -- Post-training early exit, 6.6-8.1% GPU throughput gain, projected 15-25% CPU gain
- [TIDE deep-dive](../research/deep-dives/tide-calibration-router-early-exit.md) -- Implementation roadmap for calibration-router on fork's n_layer_exit infrastructure. **Note (2026-04-23): TIDE track deprecated after projection quality could not be solved with linear or bottleneck-adapter approaches; 1.76× speed confirmed but projection produces garbage on unseen prompts.**
- [Lucebox Hub deep-dive](../research/deep-dives/lucebox-hub-consumer-gpu-dflash.md) -- 2026-04-23: first public GGUF Q4_K_M port of DFlash on consumer RTX 3090 via llama.cpp fork with tree-mode support. 207 tok/s peak, 129.5 tok/s mean HumanEval (5.46× / 3.43× over AR). Resolves the "no llama.cpp / no GGUF" blocker in intake-158 on the GPU side only — CPU spec-dec on hybrid DeltaNet remains not viable (verification cost is sequential recurrence, not kernel-level).
- [Hazy Megakernel deep-dive](../research/deep-dives/hazy-megakernel-llm-inference.md) -- 2026-04-23: methodological parent of Lucebox's megakernel component; establishes 78% memory-bandwidth utilization as the GPU roofline target for any future inference engine.
- [Qwen3.6-27B CPU feasibility deep-dive](../research/deep-dives/qwen36-27b-dense-spec-dec-cpu-feasibility.md) -- 2026-04-24: **architecture clarification** — Qwen3.6-27B (released 2026-04-22) is NOT true dense; it is hybrid Gated-DeltaNet + Gated-Attention (3:1 GDN:attention; 64 layers = 48 GDN + 16 Gated-Attn). "Dense" refers to dense FFN (no MoE). **Same architecture class as Qwen3.5-27B → CPU spec-dec foreclosed by GDN verification wall.** Community 4090 numbers (5.9× over Ollama, 154 t/s peak) are GPU-only and do not transfer; bookmarked at `gpu-acceleration-path.md`. CPU evaluation tracked at `qwen36-27b-cpu-feasibility.md` covers throughput probe + coder A/B only, no spec-dec.
- [intake-455](https://huggingface.co/Qwen/Qwen3.6-27B) Qwen3.6-27B community spec-dec note (RTX 4090, ik_llama.cpp) -- Same-family 1.7B draft beats 4B distilled on net throughput (154 vs 85 t/s) despite lower acceptance — durable heuristic for future GPU spec-dec on dense-FFN models. CPU non-applicable.
- [intake-490](https://pytorch.org/blog/hybrid-models-meet-sglang-more-than-full-attention/) PyTorch SGLang blog (Dec 2025) -- Slot-promotion mechanism for hybrid SSM speculation; per-candidate state slots; the basis for the 2026-04-28 hybrid SSM spec-dec reopener
- [intake-491](https://arxiv.org/abs/2506.01206) Mamba Drafters for Speculative Decoding (EMNLP'25 Findings) -- §3.2 MAB tree-shape selector; +22.65% over sequential, +8.5% over best fixed shape on Pythia-6.9B; basis for the 2026-04-28 MAB selector handoff. Mamba SSM external drafter for Transformer target also documented but blocked on GPU rental for drafter training.
- [MAB tree-shape selector handoff](../handoffs/active/mab-tree-shape-selector.md) -- intake-491 §3.2 Phase 0/1/2/3 spec; pre-prod gate on MoE-Spec production registry integration
- [Hybrid SSM slot-promotion reopener handoff](../handoffs/completed/hybrid-ssm-slot-promotion-spec-dec.md) -- intake-490 reopener of 6 closed SSM-hybrid handoffs; CLOSED 2026-04-30 (mechanism net-negative on Qwen3.6-35B + Qwen3-1.7B drafter; dispatcher v1 in tree disabled-by-default; canonical 3×2 + 4-config × 5-prompt sweep showed primary wins 60/62 = 97% of K-parallel rounds)
- [MoE-Spec handoff](../handoffs/active/moe-spec-cpu-spec-dec-integration.md) -- Verification-budget mechanism deployable on REAP-246B B=40; Phase 1+2 measured 2026-04-28; pre-prod registry-integration gate active
