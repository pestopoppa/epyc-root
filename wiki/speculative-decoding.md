# Speculative Decoding

**Category**: `speculative_decoding`
**Confidence**: verified
**Last compiled**: 2026-05-28
**Sources**: 34 documents (added 2026-05-28 DeepSeek-V4 MTP sidecar reference)

## Summary

Speculative decoding accelerates autoregressive inference by drafting multiple candidate tokens cheaply, then verifying them against the target model in a single batch. The fundamental promise is that verification of N tokens can be cheaper than N sequential decodes -- but on our EPYC 9655 CPU stack, this promise is architecture-dependent: it holds for dense and pure MoE models but breaks catastrophically on hybrid recurrent architectures.

Our production experience spans the full spectrum. Tree speculation on Qwen2.5-Coder-32B (dense, f16) yields +15.8% throughput. External drafting with a 0.75B Qwen3-Coder model gives +55% on dense 32B targets. But every speculative approach tested on Qwen3.5 hybrid models -- MTP-1, tree speculation (Approaches 0, A, C), and DFlash -- results in net-negative throughput (-53% to -66%). The root cause is that 75% of layers in Qwen3.5 are Delta Net recurrent layers that process tokens sequentially regardless of batch size, making multi-token verification O(N) instead of O(1). This "verification wall" is the single most important finding in our speculative decoding research, and it applies equally to all draft-verify paradigms: autoregressive, tree, and block diffusion.

The frontier technique is DFlash (block diffusion speculation), which drafts 16 tokens in a single O(1) forward pass through a 0.5B drafter -- a genuine architectural advance over the linear O(N) cost of EAGLE-style autoregressive drafting. On GPU, DFlash achieves 6.49 accepted tokens per round on Qwen3-8B (greedy). However, our 21-commit llama.cpp C++ port (forward pass verified bit-exact against HuggingFace) demonstrated that DFlash is not viable on Q4_K_M quantized models: per-token acceptance drops to 27%, yielding only 1.4% block acceptance. The quantization noise in hidden state extraction degrades the conditioning signal beyond recovery. The autoregressive drafter wins decisively (36.5 vs 13.0 t/s). A complementary technique, DART, uses a single-layer drafter with a 100GB n-gram trie from the Dolma corpus to prune draft trees, boosting acceptance by +0.5-0.7 tokens -- feasible on our 768GB+ RAM but with lower base acceptance (3.67-3.76 vs DFlash's 6.49).

A separate line of research addresses reasoning efficiency without touching the draft-verify loop. The short-m@k paper demonstrates that shorter reasoning chains are up to 34.5% more accurate than longer ones within the same question, because correct reasoning proceeds efficiently while incorrect reasoning wanders (95-188 backtracks for correct vs 269-352 for incorrect). This yields a zero-cost "length alarm" heuristic: when a `<think>` block exceeds 1.5x the difficulty band budget, cancel and re-generate with a fresh seed. The full parallel approach (k concurrent streams, take the first m to finish) requires multi-slot infrastructure we currently lack, but the heuristic alone integrates cleanly with our existing difficulty-band system at near-zero implementation cost.

A promising new direction is calibration-based early exit (TIDE, intake-422/423). Unlike LayerSkip/SWIFT which require fine-tuning, TIDE trains tiny MLP routers (~0.5M params) on cosine similarity between hidden states at checkpoint layers -- calibration takes <3 minutes on 2000 samples. On GPU, this yields 6.6-8.1% throughput gains. On CPU at batch_size=1, the gain is projected at 15-25% because (a) there is no batch compaction overhead, (b) layer compute is the dominant cost, and (c) the router check is a trivial matmul. Our fork already has `n_layer_exit` support across 7 model architectures including qwen3moe (production); the deep dive maps a 3-phase implementation path from external router → per-token exit → GGUF-embedded routers. This directly addresses the HSD finding that static layer-skip yields near-zero acceptance -- the learned router prevents quality degradation by only exiting tokens that have genuinely converged.

The current state of the art for our stack is not speculative decoding at all -- it is NUMA 4-way parallel serving (4 independent model instances on 48 threads each), which delivers 6.7x aggregate throughput on the frontdoor role. Speculative decoding provides incremental gains on top (+17-21% from draft_max tuning, +2-5% from tree branching on large dense targets) but is no longer the primary acceleration lever. The opening provided by REAP expert pruning is significant, however: REAP-25B is pure MoE (`qwen3moe` arch), meaning speculative decoding works where the hybrid frontdoor previously made it impossible.

## Key Findings

- **DeepSeek-V4-Flash ships an optional MTP sidecar that extends the self-drafting MoE pattern (2026-05-28).** The 3.6 GiB MTP-only GGUF side-file packages V4's multi-token-prediction head as a drafter for the V4 target, matching the broader "target family plus MTP sidecar" pattern already seen in Gemma4 and DeepSeek-V3-style work. It is a candidate reference only until `deepseek4` target loading and MTP sidecar API parity are verified in llama.cpp/ik_llama.cpp, followed by acceptance-rate measurement on EPYC workloads. Source: [moe-spec-cpu-spec-dec-integration.md](../handoffs/active/moe-spec-cpu-spec-dec-integration.md).
- **Peer-verifier speculation is not draft-target speculative decoding.** The Fortytwo-derived spike concerns same-tier peers scoring partial generations mid-stream, possibly using a Bradley-Terry-style accept/reject loop. That is mechanically distinct from small-drafter/large-target speculation and is currently a scoping spike only; the first gate is whether the backend exposes enough mid-stream control to prototype it without multi-week llama.cpp surgery. Source: [peer-verifier-speculation-spike.md](../handoffs/active/peer-verifier-speculation-spike.md).

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

**MAB tree-shape selector (intake-491, EMNLP'25 §3.2)** — **CLOSED 2026-04-29 with NO-GO** (framing revised 2026-04-29 evening via Remediation Phase C). Tested as drop-in over heap-spec for pure-MoE targets, orthogonal compounding axis to MoE-Spec verification budget. Paper reports sequential 112.69 → MAB-optimized 138.22 t/s on Pythia-6.9B; falsified on Qwen3-Coder-30B + DRAFT-0.75B drafter at v5 PGO build. Original Phase 0'' n=90 ("Coder -3.97% p=0.0125") was poisoned by missing OMP env stack baseline; Remediation Phase C re-tested under canonical at n=180 Coder + n=90 REAP: **Coder -1.34% NS, REAP -8.20% p<0.001**. Disposition unchanged (no-go); framing revised — Coder is actually within noise, not "definitive negative". REAP remains reliably negative. Tracked at [`completed/mab-tree-shape-selector.md`](../handoffs/completed/mab-tree-shape-selector.md).

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

### MAB tree-shape selector — DEFINITIVE NO-GO (intake-491 §3.2, CLOSED 2026-04-29)

Handoff moved to [`completed/mab-tree-shape-selector.md`](../handoffs/completed/mab-tree-shape-selector.md). Phase progression:

| Phase | Date | n | Verdict |
|---|---|---|---|
| Phase 0 | 2026-04-29 | 3 | NO-GO greedy temp=0 — verifier collapses tree to greedy (byte-identical output linear vs tree) |
| Phase 0' fixed-seed | 2026-04-30 | 9 | NO-GO temp=0.7 — fixed seed makes verifier deterministic (byte-identical output) |
| Phase 0' random-seed | 2026-04-30 | 9 | INCONCLUSIVE — Coder tree +9.6% vs linear, p≈0.23 (NS, low n) |
| Phase 0'' (broken OMP env) | 2026-04-29 morning | 90 paired | NO-GO claimed — Coder tree -3.97% (p=0.0125), REAP tree +0.34% (p=0.87) — *flagged later as poisoned baseline* |
| **Phase 0''-canonical (Remediation Phase C)** | **2026-04-29 evening** | **180 Coder + 90 REAP** | **NO-GO under canonical OMP recipe** — Coder -1.34% NS, REAP -8.20% p<0.001 |

The Phase 0' "+9.6%" was a low-n type-I error. The Phase 0'' "Coder definitive negative -3.97% p=0.0125" was itself an artifact of broken-OMP baseline contamination — under canonical recipe (`OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active numactl --interleave=all -- taskset ... -fa 1 --mmap 0`), Coder is actually within noise at twice the rep count. REAP regression IS real and highly significant. Phase 1 implementation (~245 LOC) NOT justified on either model.

**Closure scope** does NOT generalize to: different drafter (Pythia uncertainty profile differs), different arm pool (paper-shapes tuned for Pythia), multi-tenant/concurrent-slot workloads, architecturally different targets (dense, hybrid SSM — only MoE Q4_K_M tested at scale).

CPU20 bundles: [`2026-04-29-mab-tree-selector-phase-0/`](../../epyc-inference-research/data/cpu_optimization/2026-04-29-mab-tree-selector-phase-0/) (Phase 0 greedy), [`2026-04-30-mab-phase-0-prime-sampling/`](../../epyc-inference-research/data/cpu_optimization/2026-04-30-mab-phase-0-prime-sampling/) (Phase 0' fixed + random n=9), [`2026-04-29-mab-phase-0-prime-prime-replication/`](../../epyc-inference-research/data/cpu_optimization/2026-04-29-mab-phase-0-prime-prime-replication/) (Phase 0'' n=90, broken-OMP baseline), [`2026-04-29-remediation-phase-C-mab/`](../../epyc-inference-research/data/cpu_optimization/2026-04-29-remediation-phase-C-mab/) (Remediation Phase C n=180 Coder + n=90 REAP under canonical OMP recipe).

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

## Gemma 4 MTP Drafter — pure-CPU EPYC measured 2026-05-06

Google released pre-trained Apache-2.0-licensed MTP drafters for Gemma 4 (31B Dense, 26B-A4B MoE, E4B/E2B). Distinct from in-target NextN MTP (Qwen 3.5, GLM-4.x): the drafter is a **separate small model** of the `Gemma4AssistantForCausalLM` arch (4 layers, 1024 or 256 hidden, sliding+full attention, `num_kv_shared_layers=4` so the drafter's K/V comes from the target's banks). One architecture class spans all variants — they differ only in width.

ik_llama.cpp main does not support `gemma4_mtp` arch. PR #1744 (DRAFT, opened 2026-05-06 by Samuel/Radamanthys11) adds `LLM_ARCH_GEMMA4_MTP` + new `src/graphs/build_gemma4.cpp` + tensor mapping. Two patches were needed to actually run it on EPYC, both posted upstream:

1. **1-line gate fix** in `examples/server/server-context.cpp:35-39` (`params_use_gemma4_external_mtp`) — removed a chicken-and-egg precondition (`params.speculative.type == COMMON_SPECULATIVE_TYPE_MTP`) that's set as a *consequence* of the helper returning true. Without this fix, MTP gets disabled at slot init → NULL deref → segfault on first request. PR #1744 [comment 4388461769](https://github.com/ikawrakow/ik_llama.cpp/pull/1744#issuecomment-4388461769).
2. **4-line cosmetic Oops silencing** in `src/llama.cpp:2504-2515` — special-case the four top-level Gemma4Assistant tensor names (`mtp_pre_proj`, `mtp_post_proj`, `mtp_centroids`, `mtp_token_ordering`) in the size-accounting iteration. Loading is unaffected; warnings only. PR #1744 [comment 4388596615](https://github.com/ikawrakow/ik_llama.cpp/pull/1744#issuecomment-4388596615).

### Measured on EPYC 9655 canonical (96 threads, fa=1, no-mmap, OMP env stack, numactl --interleave=all, taskset -c 0-95)

| Variant | Baseline | + MTP draft-max=3 | Acceptance | Speedup | Verdict |
|---------|----------|-------------------|------------|---------|---------|
| **Gemma 4 31B Dense** Q4_K_M target + Q8_0 drafter | 7.05 t/s | **21.02 t/s** | 84.3% per-token (91/108), 100% per-batch (36/36) | **2.98×** | architect-tier candidate |
| **Gemma 4 26B-A4B MoE** Q4_K_M target + in-house Q8_0 drafter | 41.49 t/s | 44.12 t/s | 58.7% per-token (81/138), 73.9% per-batch (34/46) | 1.06× | tier X — slower than existing Coder-30B-A3B 49.1 t/s |
| (PR #1744 author's mixed-CPU/GPU bench, threads=24, ngl=99, batch=128) | 21.7 | 48.6 | 74% | 2.3× | reference |

### Two structural findings

**31B Dense pure-CPU 2.98× exceeds the PR mixed-CPU/GPU 2.3×** because the small ~500 MB drafter amortizes well against the slow BW-bound dense target on CPU; on GPU the target is already fast so the relative drafter cost is larger. **Pure CPU is the most-favorable substrate for MTP on dense models.**

**26B-A4B MoE + MTP only 1.06×** empirically confirms the lilting.ch contradicting-evidence finding (recorded in intake-527 `contradicting_evidence`): MoE batch=1 sees marginal gains because (a) the smaller 16/8-head drafter struggles to predict MoE expert routing (acceptance dropped 84.3% → 58.7%), and (b) the verifier loads up to K×8 distinct experts per K accepted tokens, eroding the bandwidth saving that makes MTP win on dense. **MoE batch=1 is a separate failure mode** from the Qwen 3.5 hybrid recurrent-verify wall (0.56× on Delta-Net) — both are MTP failure modes but with distinct mechanisms.

### Production status

- `gemma4_31b_q4km_mtp` registered in `epyc-inference-research/orchestration/model_registry.yaml` as Tier B (eval phase). Quality benchmark on the standard suite is the immediate open follow-up.
- `gemma4_26b_a4b_q4km_mtp` registered as Tier X (eval-only; not deployable). Drafter GGUF was converted in-house from `google/gemma-4-26B-A4B-it-assistant` HF safetensors (no community GGUF existed) — 840 MB BF16 → 441 MB Q8_0 via PR #1744 `convert_hf_to_gguf.py` + `llama-quantize`.
- Production use gates on PR #1744 merging to ik_llama.cpp main. Until then, runs from the `pr-1744` branch + our two patches; both registry entries pin `runtime_requirements.binary_dir` and `runtime_requirements.ld_library_path` accordingly.
- E4B / E2B multimodal MTP path deferred unless multimodal-pipeline E-series unification proceeds.

### Cross-references

- Handoff: [gemma4-mtp-drafter-evaluation.md](../handoffs/active/gemma4-mtp-drafter-evaluation.md) — full gate sequence + result tables + follow-up matrix
- Deep dive: [research/deep-dives/gemma4-mtp-drafter-deep-dive.md](../research/deep-dives/gemma4-mtp-drafter-deep-dive.md) — variant matrix, ik_llama.cpp PR table, EPYC implications
- Inference acceleration index: [Research Intake Update — 2026-05-06](../handoffs/active/inference-acceleration-index.md#research-intake-update--2026-05-06)
- Source: [intake-527](https://blog.google/innovation-and-ai/technology/developers-tools/multi-token-prediction-gemma-4/) — Google blog announcement, 2026-05-05

### Production deployment landed (2026-05-08)

**26B-A4B promoted to `worker_general`** despite the marginal 1.06× MoE-batch=1 speedup, on the strength of its quality lift over the prior occupant (Qwen3-Coder-30B-A3B Q4_K_M):

| Axis | gemma4-26B-A4B Q4_K_M MTP | Qwen3-Coder-30B-A3B Q4_K_M | Δ |
|---|---|---|---|
| Full-suite quality (rigorous Claude-as-Judge, /183) | 165 (90%) | 153 (84%) | +6pp |
| Tool_compliance (/27) | **26 (96%)** | 21 (78%) | +18pp |
| Tool_compliance tps | 60.7 | 44.7 | +36% |
| Median completion-token count per response | ~67 | ~120 | ~½ |

The +1.06× MTP alone wouldn't have justified a swap; the orthogonal quality + verbosity lift did. **The corollary**: when MoE-batch=1 cancellation degrades the speedup ratio, evaluate whether the underlying model is also a quality / output-shape upgrade — those two axes can dominate the spec-dec axis for routing decisions.

**Production launch tps measured higher than the original deep-dive bench** (76.5 t/s solo on full canonical instance, vs 44.12 t/s benchmarked at `mtp_speedup: 1.06`). The gap closes when launch params match the canonical recipe — the deep-dive bench used a subset of canonical settings; the production orchestrator now applies all of them.

**Eight launch params required** for ik_llama.cpp PR #1744 + gemma4 MTP — every one surfaced as a root-cause for the same `GGML_ASSERT(buf != NULL && "tensor buffer not set")` failure at `ggml-backend.cpp:236`:

1. `--spec-type mtp` — engages PR #1744 MTP code path (without it, `-md` is treated as standard spec decode and MTP draft tensors are loaded but never assigned to a backend buffer)
2. `--jinja` — gemma4's custom embedded chat template
3. `-np 1` — MTP fuses draft+target state across slots; `-np 2` ABA's on shared buffers
4. `-c 16384` — match registry `max_context`; smaller values cause MTP buffer mismatches
5. `--reasoning off` — gemma4 thinking-channel default ON; output otherwise lands in `reasoning_content` not `content`
6. `-ctk q8_0 -ctv q8_0` — registry-declared KV types
7. `--no-mmap` — canonical recipe (bulk-read on EPYC NUMA cold-cache)
8. **Strip `GGML_*` env block** + `OMP_DYNAMIC=false` + LLVM-20 libomp on `LD_LIBRARY_PATH` — production llama.cpp's `GGML_CCD_POOLS` / `GGML_CCD_WORK_DIST` / `GGML_BARRIER_LOCAL_BETWEEN_OPS` are tuned against a different ggml fork commit; ik_llama.cpp PR #1744 leaves MTP draft tensors unassigned when these are set. The other two are part of the canonical OMP recipe.

The `epyc-orchestrator/scripts/server/orchestrator_stack.py` worker_pool branch now applies all 8 via per-role `runtime_requirements` plumbing (binary override + LD_LIBRARY_PATH injection); other roles fall through to default. **Reference recipe**: memory `project_gemma4_mtp_launch_recipe`.

**31B Dense remains evaluation-only** despite its 2.98× speedup — the absolute 21 t/s is unviable for production worker workloads (vs 76 t/s on 26B-A4B).

**Cross-references**: [progress/2026-05/2026-05-08.md § session 2](../progress/2026-05/2026-05-08.md), commit `e205309` (epyc-orchestrator), commits `f106b7a`+`a295618` (epyc-inference-research), commit `0d131ea` (epyc-root).

### 2026-05-09 — ik_llama.cpp idle-spin caveat (9th launch-param fix)

After the swap landed and the stack was restarted, observed gemma4 worker_general pinning ~96 cores with **zero in-flight inference** and load average 97. Diagnosed via per-PID `/proc/<pid>/stat` delta sampling (per memory `feedback_ps_cpu_is_cumulative`): worker_general showed 95.13 cores busy in a 5s sample; all other servers at 0.00. User-confirmed via stop-test (`orchestrator_stack.py stop server_8072` → load 97 → ~5).

Root cause: **ik_llama.cpp PR #1744's gemma-mtp branch does NOT release OMP threads during idle slots when `OMP_WAIT_POLICY=active`**. Production llama.cpp's OMP integration releases correctly under `active`; ik_llama.cpp's fork point regresses this. The 96-thread OMP team busy-waits indefinitely between dispatches.

Fix: **9th required launch-param** for ik_llama.cpp PR #1744 + gemma4 MTP — `OMP_WAIT_POLICY=passive`. Wired in `orchestrator_stack.py:start_server` worker_pool branch under the `if binary_override:` guard, so it applies automatically to any future role using the binary_override path (gemma4-31B-MTP if rolled out, gemma4-E-series, etc.). Latency cost: a few µs first-token wakeup per request — negligible vs continuous 96-core idle waste under any non-saturated workload.

This makes the actual launch-param recipe for ik_llama.cpp PR #1744 + gemma4 MTP **9 items**, not 8 (the table above stays at 8 because OMP_WAIT_POLICY belongs in the env layer, not the cmd args). Reference: memory `feedback_ik_llamacpp_omp_idle_spin`.

**Cross-references**: [progress/2026-05/2026-05-09.md](../progress/2026-05/2026-05-09.md), commit `5eafe2f` (epyc-orchestrator).

### 2026-05-16 — passive override REVERTED, KMP_BLOCKTIME=10 is the correct fix

The 2026-05-09 `OMP_WAIT_POLICY=passive` override (commit `5eafe2f`) was reverted after smoke testing revealed passive **breaks MTP first-decode coordination**: every new request hangs forever with `llama_decode: failed to decode, ret = -3`, threads asleep on a futex but never woken by the MTP draft+target dispatch path.

Tried as direct source patches in ik_llama.cpp's `examples/server/server-context.cpp` at the `slots_idle()` transition:
- `omp_pause_resource(omp_pause_soft, omp_get_default_device())` — verified ignored by AOCC 5.0.0 libomp (95+ threads stayed in `R` state with `wchan=0` after the call)
- `omp_pause_resource_all(omp_pause_hard)` — same, ignored

**The correct fix is `KMP_BLOCKTIME=10` in the launch env** (LLVM libomp tunable; AOCC's libomp is LLVM-based and respects it). Workers busy-wait 10 ms before transitioning to a futex sleep — fast enough that MTP request dispatch still finds them warm (no first-token-latency regression), short enough that multi-second idle gaps don't waste cycles. `OMP_WAIT_POLICY=active` stays in the canonical recipe; KMP_BLOCKTIME tunes the idle transition, not the steady-state behavior.

| Metric | active alone (broken) | active + KMP_BLOCKTIME=10 |
|---|---|---|
| gemma4 idle cores busy (5s sample) | 95.05 | **0.00** |
| Threads state distribution | 95R / 5S | **100S** |
| Thread `wchan` | (userspace) | `futex_wait_queue` ✓ |
| gemma4 decode (solo) | ~109 t/s | **112 t/s** (no regression) |

Critically, **the spinning gemma4 OMP team was dragging concurrent inference on other roles** via L3/DRAM bandwidth contention even when renice=19 had been applied to gemma4's threads (renice fixes scheduler priority but not memory-subsystem contention). Post-fix:

| Role | With gemma4 spinning | With gemma4 KMP_BLOCKTIME=10 |
|---|---|---|
| frontdoor decode (thinking mode) | 7.21 t/s | **12.85 t/s** (+78%) |
| coder_escalation decode | 4.02 t/s | 12.34 t/s (+207%) |
| ingest_long_context decode | 10.46 t/s | 28.99 t/s (+177%) |

Wired in `orchestrator_stack.py:start_server` worker_pool branch under the same `if binary_override:` gate. The general pattern (AOCC libomp ignores standard OMP 5.0 pause API; KMP_BLOCKTIME is the supported tunable) applies to any future ik_llama.cpp-based role added via `runtime_requirements.binary_dir`.

**Reference memory**: `feedback_ik_llamacpp_omp_idle_spin` (updated with full resolution path).

### 2026-05-16 — TIDE dynamic early-exit was the inflated bench number (cost of correctness)

Bisect across 62 llama.cpp commits between 2026-04-24 and 2026-05-02 traced a frontdoor "regression" (16.4 → 12.45 t/s on Qwen3.6-35B-A3B Q8) to a single commit: **`2ffbdbbba` "fix: gate TIDE dynamic early exit on explicit --n-layer-exit flag"** (2026-05-02). The commit's rationale, verbatim:

> Commit 0a9e8e5bc unconditionally activated TIDE layer reduction in the server decode loop for all models. After 5 warmup tokens with 3 consecutive >80% confidence tokens, llama_set_n_layer_exit() was called, skipping the last ~5 layers of any model — including qwen35moe (Qwen3.6-35B-A3B) which does not wire n_layer_exit into its layer loop or recurrent state management. **This corrupted GatedDeltaNet state, producing garbage output (TemplateName, TargetException, WidgetItem token sequences)** on non-trivial prompts.

Reproduced verbatim on current binary with `--n-layer-exit 5..56` (re-enables TIDE per the fix's gating). Real bench prompt from `agentic.yaml:t1_q1_sequential` produces output like:

```
[{"tool": "grep_search",arguments {"htagTargetExceptionTargetExceptionTargetException...
TemplateNameTemplateName...lésãoárd可梦obilizedNametoweTemplateName
```

Sweep across `--n-layer-exit ∈ {5, 20, 40, 56}` caps at 16.7-17.6 t/s (always corrupted).

**The bench CSV at `epyc-inference-research/benchmarks/results/reviews/qwen36_q8_0_baseline.csv` (April 24, 25-30 t/s per question) was measured under TIDE-active conditions.** Claude-as-Judge scores were on factual correctness, not token-level integrity; corruption tends to appear in trailing tokens after the model emits a usable answer, so Judge scoring of 3/3 is consistent with corruption being present but tolerable for the leading answer text.

The correctness fix was correct. **Don't re-enable TIDE.** The orchestrator's RegistryLoader-driven launch path never passes `--n-layer-exit` for any production role today; TIDE is fully gated off by design.

**Residual gap**: even on the **April 20 binary (pre-TIDE entirely, head `81df3f7c`)** in total isolation (all other servers killed, 1068 GB free, fresh drop_caches), Qwen3.6-35B-A3B Q8 only delivers 12.13-12.48 t/s — not the 26 t/s recorded in the April 20 bench retest. CPU boost is correct. The 2x gap survives every config and binary lever tested. Most-plausible remaining cause: sustained multi-day uptime + cumulative throttle that `drop_caches` no longer fully restores (per memory `feedback_host_throttle_check`). Reboot test pending.

**Cross-references**: [progress/2026-05/2026-05-16.md](../progress/2026-05/2026-05-16.md), llama.cpp commit `2ffbdbbba`, bench CSV `epyc-inference-research/benchmarks/results/reviews/qwen36_q8_0_retest_fork_fix.json`.

### 2026-05-20 — Unified-model self-speculation (Nemotron-Labs-Diffusion)

NVIDIA released **Nemotron-Labs-Diffusion** (intake-576, no arXiv ID, tech report 2026-05-19, NVIDIA Nemotron Open Model License). Family: 3B/8B/14B (Base + Instruct) + VLM-8B. Backbone is **Ministral3 dense LLaMA-family** — no SSM, no Mamba, no Delta Net. Distinct from every prior block-diffusion-speculation entry in this wiki (DFlash, DART, Lucebox, Luce-Qwen3.6) because the drafter and verifier are **the same set of weights** — mode is selected at inference time by switching the attention pattern (causal → AR, block-bidirectional → diffusion, dual-stream → training).

Headline numbers (8B Instruct, batch=1, paper Fig. 9 + Tab. 10):

| Hardware / quant | AR | Linear SS | Speedup | Eagle3 | SOL |
|---|---|---|---|---|---|
| GB200 FP8 | 256 t/s | **851 t/s** | **3.32×** | 354 (1.38×) | 1471 (5.75×) |
| GB200 FP8 + custom CUDA | – | 1015 t/s | 3.97× | – | – |
| RTX Pro 6000 INT4-AWQ-Marlin | 80 | 525 | 6.56× | 211 (2.64×) | 989 (12.36×) |
| DGX Spark INT4-AWQ-Marlin | 41.8 | **112.5** | **2.69×** (INT4 vs INT4) | 43.2 (1.03×) | 223.1 (5.34×) |

Acceptance length on SPEED-Bench (k=31): **NLD-8B native 5.46 / LoRA-tuned 6.82 vs Qwen3-8B-Eagle3 2.75 / Qwen3-9B-MTP 4.24**. Gap to MTP widens to 8.69 vs 4.73 on the four diffusion-friendly categories (coding, math, reasoning, multilingual). **Quality**: 8B AR mode +0.86% avg over Qwen3-8B AR across 10 benchmarks — first diffusion LM to match AR-class accuracy (LLaDA, Dream, SDAR were 9–26 points below).

CPU portability prerequisites are materially better than DFlash: same-model drafter+verifier eliminates the cross-precision quantization drift that killed our DFlash CPU port at 27% acceptance; dense Ministral3 backbone has no recurrent-verify wall. **Port effort estimate: 15–25 days for Linear SS, 10–15 for diffusion-only** — comparable to DFlash but with more favorable architectural starting conditions. Critical unknowns before any port: (a) does Q4_K_M preserve the diffusion sampler's confidence-threshold sweet spot, (b) does Ministral3 load in our v4 llama.cpp fork, (c) does block-wise attention work as a causal-only approximation as a fast first cut. Two cheap pre-port audit tasks: Ministral3 conversion check (~1 h), AR-mode quality re-test on Q4_K_M (~4 h) — the latter validates the paradigm, NOT a worker-role candidacy (our worker_general is gemma4-26B-A4B Q4_K_M MTP; an 8B dense is the wrong size class).

Verdict: `worth_investigating`. Tracked in [`inference-acceleration-index.md`](../handoffs/active/inference-acceleration-index.md) + [`gpu-acceleration-path.md`](../handoffs/active/gpu-acceleration-path.md) (DGX Spark Day-0 candidate alongside DFlash) + [`gemma4-mtp-drafter-evaluation.md`](../handoffs/active/gemma4-mtp-drafter-evaluation.md) (Tab. 10 is the strongest single-paper evidence that "self-speculation > MTP" at low concurrency on dense models). Full deep dive at [`research/deep-dives/nemotron-labs-diffusion-tri-mode.md`](../research/deep-dives/nemotron-labs-diffusion-tri-mode.md). Tier 2b contradicting-evidence re-run scheduled 2026-06-20. Follow-up intake candidates: Set Block Decoding (arxiv:2509.04185, Meta FAIR — immediate prior art), Efficient-dlm (arxiv:2512.14067), TiDAR (arxiv:2511.08923), Fast-dllm (arxiv:2505.22618).

### New Findings (2026-05-27 — Peer-verifier same-tier speculation: NO-GO on EPYC, re-eval triggers documented)

- **Peer-verifier speculation is NOT draft-target speculation.** The Fortytwo Network's (unpublished) chunk-ranking pitch describes a same-tier mechanism: one leader model emits a chunk (e.g., 64–256 tokens, or up-to-newline/up-to-tool-call boundary); the remaining N−1 peers don't generate, they *score* the prefix+chunk via a single forward pass; if the swarm agrees, commit; on disagreement, switch leadership to the highest-scoring peer's continuation. Distinct mechanism from Medusa / EAGLE / draft-target speculation — there's no small drafter, just same-tier peer cross-verification.
- **NO-GO on current EPYC config — both backend and roofline gates fail.** `peer-verifier-speculation-spike.md` resolved 2026-05-27 by direct inspection of `LlamaServerBackend` + roofline math:
  - **Gate 1 (backend)**: native `/completion` path in `src/backends/llama_server.py:_build_payload` has no prefix-score request mode (no `n_predict=0` + per-prompt-position log-probs); no mid-generation handoff primitive; `save_slot`/`restore_slot` exist but the disk format is NOT portable across heterogeneous GGUFs (per `feedback_same_model_roles_share_server.md`). Adding the scoring half is ~1 day of wrapper work; the swap half is multi-week (likely upstream llama-server territory).
  - **Gate 2 (roofline)**: at N=3 26B verifiers (gemma4-26B-A4B band, leader at 76.5 t/s solo, prefill ~250 t/s), chunk=128: sequential verification = 1.67 + 3×0.51 = 3.20s/chunk → **40 t/s effective = 48% per-stream regression**. Parallel verification (peers share leader's 96-thread CPU) → ~38 t/s effective = 50% regression. Both schedules breach the 30% gate by 20-30 absolute points.
- **Re-evaluation triggers documented in the handoff** (any one flips the NO-GO):
  1. Fortytwo publishes the chunk-ranking method (replaces hypothesis-driven Variant 1 reconstruction with the actual mechanism — possibly cheaper than our roofline).
  2. DGX Spark or other unified-memory hardware arrives (changes prefill-to-decode ratio).
  3. RAO+ReDel substrate work (P#42) adds mid-stream-control primitives for an unrelated reason — drops Gate-1 cost from "multi-week" to "wire it up".
  4. Smaller specialist peers (e.g., 8B from swarm-dataset-distillation) replace the 26B verifiers — N=3 8B prefill at ~400 t/s shrinks per-chunk overhead from 0.51s to ~0.32s; combined with every-other-chunk verification (2× reduction), gets to ~18% regression — under the gate.
- **DAR-6 (request-time swarm-fanout) is NOT blocked by this NO-GO.** That covers the **published** post-hoc full-completion form (intake-615) and is independently buildable; scaffolding landed same session (default-off feature flag, no production routing change).

The spike is preserved in `handoffs/active/` (not archived) as a frozen reference for the four re-evaluation conditions. Negative results with concrete gating numbers and triggers are more useful than verdicts like "not practical" — the next reviewer can compare new evidence against the recorded gate thresholds in O(1).

Sources: [`handoffs/active/peer-verifier-speculation-spike.md`](../handoffs/active/peer-verifier-speculation-spike.md) · [`handoffs/active/decision-aware-routing.md`](../handoffs/active/decision-aware-routing.md) § DAR-6 · `research/intake_index.yaml` intake-614/615 · `epyc-orchestrator/src/backends/llama_server.py` · `progress/2026-05/2026-05-27.md`.

### New Findings (2026-05-27 evening — Cross-tokenizer SD, MTP-split feasibility, FastDraft gating)

Synthesis from 9-paper deep-dive (intake-617..624 + dedup against intake-042) supporting the new `gpu-drafter-mi200-investigation.md` handoff. Full text at [`research/deep-dives/2026-05-27-cross-tokenizer-specdec-and-mtp.md`](../research/deep-dives/2026-05-27-cross-tokenizer-specdec-and-mtp.md).

**Cross-tokenizer speculation is three algorithms, not one.** Timor et al. ICML 2025 (intake-617, arxiv:2502.05202) presents **SLEM** (string-level exact match with look-behind realign), **SLRS** (rejection sampling against $\psi(t) = \sum$ over all draft tokenizations canonicalizing to a target prefix — exponential, reference-only), and **TLI** (token-level intersection — $q'(x) = q(x)/\sum_{x \in T \cap D} q(x)$, masked renorm over shared vocab, no detokenize/retokenize). Headline up to 2.8× on long-context summarization; worst case −57% on matched-architecture pair where heterogeneous machinery is unneeded overhead. **TLI is the operational starting point** for any non-Qwen drafter contingency on our stack — cheapest hot path, integrates into existing rejection-sampling kernels with a single masked renormalization. Reference impl is HuggingFace Transformers PR #35029 (merged); llama.cpp port is critical-path engineering. This **falsifies our existing Chapter 01 § Tokenizer Compatibility Constraints text** (flagged for rewrite).

**MTP head-split for trunk-on-CPU/heads-on-GPU is architecturally bounded by what's shipped.** DeepSeek-V3 (intake-621) ships $D=1$ — per Eq. 21, the first MTP head hard-pins to the trunk's hidden state $h^0_i$, so chained-on-GPU has no chain. Gemma4's MTP (ik_llama.cpp PR #1744) is also $D=1$ — measured 76.9% acceptance on production traffic 2026-05-27 (`worker-explore-8072.log`, 472 release events, gate met). Per-token H2D of trunk hidden state is cheap (~14 KB at $d=7168$), so the split mechanically works, but it produces *one* extra drafted token per main step, not a multi-token chain. Gloeckle 2024 (intake-623, arxiv:2404.19737) is the architecturally correct version — **parallel** MTP heads with no inter-head dependency, $n=4$ → 2.74× speedup on code. But Meta released no checkpoints (500K GPU-hours trained, none shipped) and Llama-2 fine-tuning to add parallel heads "did not yield significant improvements" (their own quote). **Operationally: the architecture is right, the supply side is empty.**

**FastDraft (intake-624, arxiv:2411.11055) is the matched-vocab custom-drafter training pipeline.** ~10B tokens, <24h on 8× Gaudi-2, ~1-3 wall-clock days on modern accelerators (~1-3 weeks on a single dedicated MI210). Headline α=0.65 on HumanEval (code), only 0.31-0.37 on chat/summarization. Matched-vocab only; no Qwen, no MoE, no targets ≥10B in the paper. **Sweet spot for our stack is coder_escalation, not frontdoor.**

**The Gating Measurement — α(off-the-shelf drafter → target) on production traffic gates three independent optimization investments.** A single number — α(Qwen3-1.7B → Qwen3.6) at γ=3 on prod-mix traffic — gates: (a) cascade drafting / intake-042, gate α ≥ 0.7 (need geometric tail to exploit); (b) FastDraft custom training, gate α < 0.55 (off-the-shelf leaves acceptance on the table); (c) SpecDec++ adaptive-K / intake-620, gate optimal fixed K ≥ 4 AND per-position α-variance is high (structurally inapplicable at the gemma4 `--draft-max 2` regime where chunks are too short to truncate). These three are mutually exclusive — the same α value points to at most one as +EV; investing in two simultaneously is wasted effort. Persisted in three places: `gpu-drafter-mi200-investigation.md` § The Gating Measurement (specific thresholds + per-stage gate table), `research/deep-dives/2026-05-27-cross-tokenizer-specdec-and-mtp.md` § Action item #6 (rationale chain), and memory `feedback_measure_alpha_before_specdec_investment.md` (general principle).

**ZeTT (intake-618) and FVT (intake-622) are not realistic drafter sources for us.** Both recover *self-consistency* under tokenizer swap, not target-distribution alignment. Acceptance against a Qwen3.6-35B target after FVT- or ZeTT-ing a non-Qwen 1B would be bounded by the underlying capability gap and the matched-vocab small Qwen drafter beats them off the shelf. Keep on contingency shelf; do not block matched-vocab MI200 work on them.

Sources: [`handoffs/active/gpu-drafter-mi200-investigation.md`](../handoffs/active/gpu-drafter-mi200-investigation.md) · [`research/deep-dives/2026-05-27-cross-tokenizer-specdec-and-mtp.md`](../research/deep-dives/2026-05-27-cross-tokenizer-specdec-and-mtp.md) · `research/intake_index.yaml` intake-617..624 · `progress/2026-05/2026-05-27.md`.

## TiDAR CPU-mechanism correction + diffusion-LM port variant question (2026-05-28)

**Correction of an inverted reading.** Initial intake of TiDAR (arxiv:2511.08923, intake-633) scored it `superseded` by Nemotron-Labs-Diffusion (intake-576) and dismissed its "free token slots" mechanism as GPU-compute-slack-driven, therefore inapplicable to CPU. **The deep-dive 2026-05-28 inverted that finding.** TiDAR's plateau exists *because* weight + KV-cache fetch dominates per-step latency at batch=1 decode (paper Fig. 1) — that **is** our EPYC 9655 CPU regime (`project_cpu_decode_bw_bound`), not the inverse of it. The mechanism amortizes one weight-fetch over K drafted tokens per forward pass. On CPU each pass = one full weight scan, so TiDAR's one-pass pattern halves per-cycle weight traffic vs Nemotron Linear-SS (two-pass).

TiDAR is the architectural ancestor of Nemotron's *underperforming* Quad-SS mode. Quad-SS underperforms on GPU because FlexAttention kernels for the quadratic mask are unoptimized; **on CPU we write ggml ops either way, so the FlexAttention blocker does not carry over**. Revised: intake-633 verdict superseded → worth_investigating; novelty low → medium.

**Open question logged in Nemotron deep-dive §10**: evaluate a TiDAR-pattern one-pass variant alongside Nemotron Linear-SS in the §6 CPU port plan. User also proposed split-role hybrids (Variant C1 diffusion-think + AR-generate, C2 inverse). Promotion gate (matches the FLOPS-roofline audit decision rule exactly): **achieved FLOPS < 10% of ~9.2 TFLOPS FP32 socket theoretical AND achieved DRAM BW > 70% of ~614 GB/s socket theoretical** → diffusion variants have FLOPS margin. The roofline measurement that resolves this gate is itself a separate user-gated task ([`handoffs/active/cpu-decode-flops-roofline-audit.md`](../handoffs/active/cpu-decode-flops-roofline-audit.md)) which is blocked at DRAFT until Phase 0 calibrates the correct AMD Zen 5 perf counters (the initial draft prescribed Intel `fp_arith_inst_retired.*` events that this host rejects).

Sources: `research/intake_index.yaml` intake-633/634/635 + intake-576 (Nemotron successor) · [`research/deep-dives/nemotron-labs-diffusion-tri-mode.md` §10](../research/deep-dives/nemotron-labs-diffusion-tri-mode.md) · [`handoffs/active/cpu-decode-flops-roofline-audit.md`](../handoffs/active/cpu-decode-flops-roofline-audit.md) · `progress/2026-05/2026-05-28.md` §research-intake-batch.
