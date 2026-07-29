# MoE Optimization

**Category**: `moe_optimization`
**Confidence**: verified (CPU MoE findings) · observation (2026-07-06 MI210 GPU MoE-MTP numbers — single-run, no P-GPU-1 per MEASUREMENT.md)
**Last compiled**: 2026-07-20 (adds the reasoning∝active MoE law, the production-representative GLM expert-routing-skew result, the IQ2 GPU big-MoE residency ladder, and the slot-fabric residency model; earlier 2026-07-17 note: adds GLM-5.2 DSA-DENSE-MASK runtime classification + expert-routing-skew hypothesis + Hy3 MoE-verify-wall re-confirmation; ⚠️ 2026-07-06 GPU MoE-MTP-negative note added under the CPU-MTP-wall finding — human review)
**Sources**: 37 documents

## Compiled Update — 2026-07-20

New evidence pins down the MoE reasoning-vs-knowledge law and settles the offload/REAP viability gate for GLM-5.2 with a measured routing-skew profile. Confidence: `external` for the sparsity literature, `verified` for the routing-skew measurement, `observation` for all MI210 residency throughput.

### Key Findings (2026-07-20)

- **Reasoning ∝ ACTIVE FLOPs; knowledge/memorization ∝ TOTAL params; reasoning is non-monotonic in sparsity** (intake-859 `2508.18672`, cred 5). Denser overtakes once active-param counts grow; raising total experts at fixed top-k degrades reasoning while raising top-k mitigates it; neither test-time compute nor GRPO rescues over-sparsity — it is architectural. This makes a **large-total / moderate-active MoE (122B-A10B)** the literature-default architect (active⇒reasoning, total⇒knowledge) and the 35B-A3B (3B active) the reasoning floor; on a bandwidth-bound CPU, an MoE reaching dense-level quality at ~1/10 active FLOPs is exactly why MoE wins. A mid-size MoE can Pareto-dominate a larger one at 1/3 the memory (Gemma-4-E4B ≈ Gemma-4-26B-A4B — intake-862 `2604.07035`, cred 2). ([architect-model-selection-2026-07-20](../docs/reference/architect-model-selection-2026-07-20.md))
- **The expert-routing-skew profile (the cheap gate for offload/REAP) came back near-uniform on GLM-5.2.** Production-representative run: 19.1M selections, **global `top_32=15.19%`, entropy 0.9987, Gini 0.066**, with only weak layer-local skew (median layer `top_32=39.19%`; all 256 experts used every layer). → generic GLM hot-expert GPU residency / REAP is **NOT justified** by current workload evidence (near-uniform ⇒ PCIe-streaming-latency-bound if attempted); reopen only with a narrower role-specific corpus. REAP and offload are the *same* skew analysis, different action (permanently prune cold experts vs stream them). ([mi210-big-model-and-acceleration-roadmap](../handoffs/active/mi210-big-model-and-acceleration-roadmap.md))
- **IQ2 big-MoE GPU residency ladder is two-for-two viable** (observation-grade): 122B UD-IQ2_M = 43.7 t/s single / 148.7 agg@B32 (2.2× / ~8–9× over ~20 t/s CPU-Q4, PPL 5.02); Qwen3-Next-80B-A3B i1-IQ2_M = ~55.8 single / 265 agg@B32, and because it is a GDN-hybrid with O(1) KV, 32K context fits comfortably and it is compute-bound at B≈96–128. IQ2 residency **caps at ~122B**; GLM-5.2 (~238 GB even at IQ2) never fits GPU-only → offload/REAP is the only GLM path. AirLLM-style per-token weight streaming is the anti-pattern (PCIe 7–14× slower than DDR5); the HBM win exists only when weights *reside* in HBM. ([mi210-big-model-and-acceleration-roadmap](../handoffs/active/mi210-big-model-and-acceleration-roadmap.md))
- **The slot-fabric residency model treats GPU MoE residency as a slot operation.** VRAM (64 GB) is the only scarce resource; CPU+RAM dual-residency is free (1.1 TB), so every teleport-eligible model stays hot in RAM permanently. A realistic 2-resident set is one big GDN (122B-IQ2 ~40 GB) + one small (35B-A3B IQ4) ≈ 58 GB — two big IQ2 don't co-fit. A Layer-2 residency actuator is the only VRAM-touching op (allowlist + N-dwell hysteresis + kill-switch), and every GPU MoE has a designated CPU fallback (GPU accelerates, CPU guarantees). ([heterogeneous-slot-fabric-residency](../handoffs/active/heterogeneous-slot-fabric-residency.md))

### Open Questions (2026-07-20)

- Does a narrower *role-specific* corpus reveal a cacheable GLM hot-expert set that the production-representative profile averaged away?
- The GLM-5.2 endgame (expert-offload / REAP + IQ2-resident-experts + offload-cold-tail) remains operator-gated and unbuilt.
- Does dynamic IQ2 preserve the 122B-A10B's *reasoning* (not just knowledge)? The architect bench decides, and it re-gates the whole IQ2-residency-for-the-architect program.

### Source References (2026-07-20)

- [architect-model-selection-2026-07-20.md](../docs/reference/architect-model-selection-2026-07-20.md) — reasoning∝active / knowledge∝total MoE law + ranking implication.
- [mi210-big-model-and-acceleration-roadmap.md](../handoffs/active/mi210-big-model-and-acceleration-roadmap.md) — GLM routing-skew result, IQ2 residency ladder, AirLLM anti-pattern.
- [heterogeneous-slot-fabric-residency.md](../handoffs/active/heterogeneous-slot-fabric-residency.md) — GPU MoE residency as a slot operation + CPU-fallback guarantee.
- [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md) — CPU+GPU hybrid MoE expert-offload (`-ot exps=CPU` / `--n-cpu-moe`) machinery.
- intake-859 `2508.18672` (cred 5), intake-862 `2604.07035` (cred 2) — MoE sparsity/reasoning + deployment-aware Pareto-dominance.

## Summary

Mixture-of-Experts models are central to our EPYC 9655 inference stack. The frontdoor (Qwen3-Coder-30B-A3B, 3B active of 30B total), architect_general (Qwen3-235B-A22B), and architect_coding (REAP-246B, 50%-pruned from Qwen3-Coder-480B-A35B) are all MoE architectures. The fundamental characteristic of MoE for CPU inference is that only a fraction of parameters are active per token, but all expert weights must reside in memory for routing. This creates a unique optimization space distinct from dense model compression: reducing the number of stored experts directly reduces model file size and memory bandwidth requirements without affecting per-token active compute.

REAP (Router-weighted Expert Activation Pruning) is the breakthrough technique in this space. Published at ICLR 2026 by Cerebras, REAP permanently removes entire experts based on a saliency score that combines router gate values with expert output norms, computed in a single calibration forward pass over 128-512 samples. No fine-tuning, no gradient computation. The theoretical grounding is clean: expert merging (HC-SMoE, M-SMoE) creates irreducible error proportional to router policy variability because the merged expert loses the router's input-dependent control, while pruning preserves surviving experts unchanged. The empirical evidence is decisive: at 50% compression, REAP achieves 0.557 coding accuracy vs HC-SMoE's 0.379, and on creative writing, merging catastrophically collapses to 0.008 while REAP maintains 0.718.

We deployed REAP in production with striking results. The 480B architect_coding model was replaced by REAP-246B (50% pruning), achieving 82% quality on our Claude-as-Judge benchmark -- a 9 percentage point improvement over the unpruned model at deployment quantization. Throughput improved 14% (8.0 vs 7.0 t/s) and memory dropped 44% (139 vs 250 GB). The improvement is counterintuitive but consistent with findings across the ecosystem: removing noisy/redundant experts reduces routing confusion. Kimi-Linear at 30% pruning gained +10 on AIME25. Cerebras's own 480B at 25% outperforms base on 6/14 benchmarks. The 480B model has been deleted from our system.

The ecosystem around REAP is maturing rapidly. Cerebras has published 30 official pre-pruned models across 7 families (Qwen3-Coder, DeepSeek-V3.2, Kimi-Linear, MiniMax, GLM-4.x, Step-3.5-Flash, GLM-4.5-Air). Community practitioner 0xSero has produced systematic pruning sweeps across GLM-4.7, MiniMax-M2.1, DeepSeek-V3.2, and INTELLECT-3, with validated calibration recipes and stress testing methodology. The CerebrasResearch/reap repository (Apache 2.0) supports direct CLI pruning of all Qwen3 MoE models.

A critical practical finding emerged from 0xSero's stress tests: the "Goldilocks zone" for MoE pruning is 30-40%, not the intuitive 20-25%. At 20%, pruning destabilizes routing without triggering clean redistribution (repetition loops at low temperature on MiniMax-M2.1). At 30%, the router fully adapts to the reduced expert set. At 50%, degradation begins (2 loops in stress test). This counterintuitive result -- that removing more experts can produce better quality than removing fewer -- is one of the most practically important findings for deployment decisions.

Extending techniques include EvoESAP (non-uniform cross-layer budget allocation via evolutionary search), Router Knowledge Distillation (lightweight retraining of router weights post-pruning), and MoNE (replacing pruned experts with constant-vector "novice" approximations). For our Qwen3+REAP stack, EvoESAP is not useful (actually hurts at 25%, negligible at 50% -- the headline +19.6% was on a different model+criterion combination). Router KD is modestly beneficial (16/25 benchmarks improved) and worth the 2-hour investment only at 50%+. MoNE is lower priority than direct pruning (no REAP comparison in the paper, only tested up to 16B models).

A newer entrant is Leanstral (Mistral AI), a 119B MoE with 6.5B active parameters using DeepSeek V3-style architecture (MLA + 128 routed experts + 1 shared expert). Leanstral is a near-ideal REAP candidate: 95% of its parameters are routed expert weights. For specialized Lean 4 proof engineering, where expert activation patterns likely cluster on a subset of experts, aggressive pruning at 75% + Q4_K_M could shrink the model from 68 GB to approximately 20 GB with projected 40+ t/s on EPYC. The `deepseek2` architecture is fully supported in llama.cpp, and community GGUFs are available.

The 2026-07-02 refresh surfaces five threads that sharpen the MoE picture. (1) A GPU has finally landed (MI210 installed 2026-07-02), reopening the CPU+GPU hybrid-MoE offload path (`-ot "exps=CPU"` / `--n-cpu-moe`) where GPU handles attention + dense FFN while NUMA-distributed CPU handles routed experts — but the PCIe expert-transfer bottleneck (which DGX Spark's unified memory would have eliminated) remains the binding constraint. (2) MoE-Spec's budgeted-verification mechanism is proven (+15.2% forward-pass on REAP-246B at B=40) but now has NO live consumer — the REAP role was removed from the production stack and the frontdoor runs zero spec-dec, so there is nowhere to deploy it. (3) CPU speculative decoding is architecture-gated: dense models win (1.84-3.2x measured via MTP) while pure-MoE-A3B is the worst CPU-MTP case (≤1.06x even on GPU) because expert-union verification overhead, not draft quality, is the wall. (4) DeepSeek-V4-Flash — a 284B/13B-active MoE with a genuinely new attention architecture (CSA + HCA + indexer + compressor + manifold-constrained Hyper-Connections) — was ported via the antirez fork and provisionally FAILED the throughput gate (9.13 t/s vs an 18 t/s Q4 floor that itself needs V4-arch-aware recalibration to ~8-12 t/s). (5) A LongCat scaling-law result reframes n-gram embedding scaling as a sparsity axis orthogonal to MoE with a superior Pareto frontier at high sparsity — a pretraining choice, not retrofittable, but a fit for our 1.1 TB DDR5 node.

## Key Findings

### 2026-07-02 Refresh — hybrid-MoE offload, embedding-vs-experts, V4-Flash port result, CPU-MTP wall

- **CPU+GPU hybrid MoE offload reopens with the MI210 arrival (2026-07-02), but the PCIe expert-transfer bottleneck is the binding constraint.** The `-ot "exps=CPU"` / `--n-cpu-moe N` levers are production-ready in llama.cpp: attention + dense FFN stay on GPU while routed experts route to NUMA-distributed CPU RAM, exploiting our 192 threads + 1.1 TB budget for expert compute. PCIe latency (~64 GB/s bidirectional), not CPU compute speed, is the bottleneck. A two-tier expert cache (LRU-hot experts pinned in VRAM, cold experts in CPU RAM; llama.cpp issue #20757) shows 12-14 t/s vs 0.5-1 t/s for pure CPU offload in proof-of-concept — the most impactful pending feature for a discrete-GPU MoE setup, still unmerged. hipBLASLt grouped GEMM bundles MoE expert matmuls into one kernel launch for +29% (CDNA3+ only). [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md), [intake-310](https://huggingface.co/blog/Doctor-Shotgun/llamacpp-moe-offload-guide)

- **DGX Spark's unified memory would have eliminated the expert-offload PCIe bottleneck entirely — no Spark was acquired, so this remains the reference contrast, not a deployment.** On unified memory, expert weights are simply *there* (no CPU→GPU transfer): benchmarked MoE decode ~70 t/s single-chip (Gemma 26B MoE 69.9 t/s), obsoleting the entire `-ot "exps=CPU"` offloading paradigm for models that fit the 128 GB pool. The MI210 that did arrive is a discrete GPU, so the two-tier expert cache (not unified memory) is the relevant integration target. [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md)

- **N-gram embedding scaling is a sparsity axis orthogonal to MoE, with a superior Pareto frontier at high sparsity — but it is a pretraining choice, not retrofittable onto our production GGUFs.** The LongCat scaling-law paper establishes: (1) embedding-scaling beats expert-scaling on the high-sparsity Pareto; (2) width amplifies while depth diminishes the advantage; (3) embedding params should be ≤50% of total; (4) n-gram sub-table vocab must deviate from integer multiples of the base vocab (collision rule). LongCat-Flash-Lite realizes this as a 68.5B-total / 2.9-4.5B-active MoE with ~31.4B (46%) in n-gram-embedding tables. All numbers are GPU-measured (8×H800); the CPU probe of the deployed checkpoint closed negative (below). n-gram-embedding-in-host-DRAM is a genuine fit for our 1.1 TB / 460 GB/s node. [intake-758](https://arxiv.org/abs/2601.21204), [engram-conditional-memory.md](../handoffs/active/engram-conditional-memory.md)

- **The n-gram-augmented MoE family runs on CPU at production rates, but is dominated by our incumbent on this stack.** LongCat-Flash-Lite Q4_K_M measured 37.08 t/s decode (above the 15 t/s abandon threshold, below the 60 t/s escalate threshold) and 53.8% sentinel quality — dominated by gemma4-26B-A4B MTP (66.7%, faster) on both axes for the worker_general role. The family verdict is positive (n-gram-keyed memory works at MoE-scale on CPU); the checkpoint verdict is negative (better-tuned alternatives already deployed). Track A closed; a paper-faithful frozen-backbone retrofit (Track B) is a separate GPU-gated research bet. [engram-conditional-memory.md](../handoffs/active/engram-conditional-memory.md)

- **CPU speculative decoding on MoE is architecture-gated: pure-MoE-A3B is the worst case (≤1.06x even on GPU); dense wins (1.84-3.2x measured).** Every upstream MTP/EAGLE speedup is GPU; on MoE the expert-union verification overhead — not draft quality — is the wall. Clean-host measurements: gemma-4-31B dense MTP hit 1.84x on prose and 2.55-3.19x on structured/code output; Qwen3.5-9B dense MTP 1.97x at 87% draft accept. By contrast Qwen3.6-35B-A3B MoE MTP is "worth_investigating, low EV" (the 26B-A4B MoE measured only 1.06x). Corroborating: trimming the draft LM-head -85% in kernel time (FR-Spec, intake-740) yields only +1-3% end-to-end on bandwidth-bound decode. This is the same expert-verification-overhead mechanism MoE-Spec attacks from the verification-budget side. [speculative-decoding-mtp-refresh.md](../handoffs/active/speculative-decoding-mtp-refresh.md)

- **The MoE-verification wall reproduces on GPU too: for a GPU-resident MoE, PLAIN decode is the bar spec-dec must beat, and MTP does not clear it (2026-07-06, MI210, OBSERVATION).** On the Qwen3.6-35B-A3B frontdoor served fully on the MI210, single-stream decode is **~101 t/s PLAIN vs ~90 MTP** — MTP *loses* at every sampled temperature — because GPU-resident MoE plain decode already reads only ~active-expert bytes off 1.6 TB/s, so the draft+verify overhead isn't repaid (head-quant-independent; the loss is MoE-verify + GPU-resident overhead, not head dtype). This is the GPU analog of the CPU ≤1.06× pure-MoE wall above — MTP flips sign by **{arch × substrate}** (a win on GPU-*dense* and CPU-*dense*, a loss/wash on MoE-on-GPU). *Nuance:* after the MMVQ→MMQ verify-dispatch fix (`de447119f`) and a full output-temperature curve, MTP-on-GPU-MoE **converged to ~neutral (−1.6%) at production sampling temp 0.1–0.3** — the earlier "−12%" is stale — so it is a WASH (not worth enabling, no longer a reason to avoid); at batch the spec-dec benefit degrades toward zero regardless. Detail in [Speculative Decoding](speculative-decoding.md) and [Hardware Optimization](hardware-optimization.md). [fable5-window2-findings-05c, moe-aggregate-deployment-wins-brief]

- **MoE-Spec's budgeted-verification mechanism is proven but has NO live consumer as of 2026-06-12.** The `--moe-spec-budget N` lever (aggregate routing softmax across the verification batch, shrink the active-expert union before argsort_top_k) verified +15.2% pp32 forward-pass on REAP-246B Q4_K_M at B=40 and +3.3% end-to-end. But the REAP role was removed from the production stack, the Coder-30B B=64 result was not robust across builds/cache states, and the frontdoor runs zero spec-dec today — there is nowhere to deploy it. Reopen is chained to first enabling frontdoor spec-dec and measuring α(Qwen3-1.7B → frontdoor) on CPU. New catalog-only successors: DSpark ([intake-738], utilization-keyed adaptive verification depth — GPU-concurrency-specific, largely inert on our concurrency-1 CPU decode), Graft ([intake-742], training-free prune-then-graft draft tree — EAGLE-3-based + GPU adjacency), SpecDec++ ([intake-620], adaptive drafting-γ — composes with MoE-Spec's verification budget). [moe-spec-cpu-spec-dec-integration.md](../handoffs/active/moe-spec-cpu-spec-dec-integration.md)

- **DeepSeek-V4-Flash port attempt provisionally FAILED the CPU throughput gate; the 18 t/s floor needs V4-arch-aware recalibration.** Strategy B (run V4 on the antirez mainline-based fork as an auxiliary binary rather than translating 1347 LOC into ik_llama's older build-context API) executed 2026-05-30: download complete (153.32 GiB Q4), smoke PASS, but canonical decode clustered at 8-11 t/s (three independent measurements) against an 18 t/s Q4 floor — a **provisional FAIL**. The floor was calibrated by inverse-param-ratio from gemma4-26B-A4B without modeling V4's CSA/HCA/indexer/compressor overhead; the honest expected range is ~8-12 t/s, so the floor itself is the suspect number pending recalibration. V4 is a genuinely new architecture (hybrid Compressed-Sparse + Hierarchical Compressed Attention, manifold-constrained Hyper-Connections), 284B/13B-active, MIT-licensed, with an optional 3.6 GiB MTP-as-drafter sidecar. The larger DeepSeek-V4-Pro-DSpark (1.6T-total/49B-active, ~5.6× V4-Flash) is do_not_port — it blows the raid0 storage gate ([intake-739]). [deepseek-v4-flash-cpu-port.md](../handoffs/active/deepseek-v4-flash-cpu-port.md), [intake-637](https://huggingface.co/antirez/deepseek-v4-gguf)

### 2026-07-17 Refresh — GLM-5.2 DSA runs DENSE-MASK (sparse-compute unrealized); Hy3 re-confirms the MoE-verify wall

- **Generic DeepSeek Sparse Attention (DSA) LANDED upstream (#23346), but on GLM-5.2 it runs "DSA-DENSE-MASK": the Lightning Indexer/top-k engages yet final attention still scales with full KV — the 1M-context sparse-compute value is NOT yet realized.** The long-tracked draft #21149 is superseded; `LLM_ARCH_DEEPSEEK32` and `LLM_ARCH_GLM_DSA` are registered in v6, and experimental-v7 `3dee86a5a` closed a real gap where GLM loaded indexer tensors but was never wired to `llama_kv_cache_dsa` (it fell through to ordinary KV). Even after wiring, a source audit + runtime scaling classify it as dense-mask: the generic DSA path computes `indexer_score`/`ggml_top_k` and passes `top_k` to `build_attn`, but that helper builds a `kq_mask_top_k` over the **full** KV length and calls `build_attn_mha()` over full cached K/V — no sparse gather. Runtime confirms it: with fixed `indexer_top_k=32`, current-source GLM-5.2 UD-IQ2_M prompt throughput *declines* with context (`23.81 → 21.04 → 17.28 t/s` at `2.9K/5.9K/11.9K` tokens). So "DSA supported + indexer enabled" ≠ sparse compute; treating GLM's 1M-context claim as locally cheap requires a real top-k-gather final-attention path (the open D2 contribution) or backend evidence that masked rows are skipped. Sources: [glm51-reap-cpu-evaluation.md](../handoffs/active/glm51-reap-cpu-evaluation.md), [llama-cpp-dsa-contribution.md](../handoffs/active/llama-cpp-dsa-contribution.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md).
- **GLM-5.2 expert routing is near-uniform globally but has moderate layer-local hot sets — hypothesis-only, not decision-grade for offload/REAP.** A rebuilt-imatrix expert-count pass measured a near-uniform global aggregate (`top_32=17.1%`, normalized entropy `0.996`) but moderate layer-local concentration (median layer `top_32=55.6%`, max `70.5%`). The calibration corpus was tiny/repetitive, so this stays a hypothesis — do not unblock hot-expert GPU residency or REAP until a representative-workload profile repeats it. (GLM-5.2 at IQ2 is ~239 GB and never fits the MI210's 64 GB HBM, so any GPU path is expert-offload gated on exactly this skew profile.) Sources: [glm51-reap-cpu-evaluation.md](../handoffs/active/glm51-reap-cpu-evaluation.md).
- **Hy3 (Tencent 295B-total / 21B-active, 192-expert top-8 MoE with a native MTP head) re-confirms the MoE-A3B expert-verification wall rather than breaking it.** The community "88.2% acceptance" was a `p_min=0.75` confidence-gated number a maintainer flagged as invalid; TRUE ungated greedy acceptance is ≈41% (IQ2_M) / 47% (f16), matching official vLLM 46.7%. Because 21B-active/top-8-of-192 widens the verify-step expert union, decode is BW-bound and the author's own Metal M3 Max run is net-neutral (23.27 vs 23.21 t/s) — EPYC is predicted net-neutral too. CUDA/GB10 gains (+13% H200, +27–58% DGX Spark) are compute-bound only. This is a NEGATIVE datapoint for CPU-MTP, corroborating the ≤1.06× pure-MoE-A3B row above; RAM is a non-constraint (IQ2_M ~100 GB ≪ 1.1 TB), disk is the limiter → download one quant. Sources: [speculative-decoding-mtp-refresh.md](../handoffs/active/speculative-decoding-mtp-refresh.md).

### 2026-06-26 v6 cutover — MoE stack consolidated onto one kernel (production-consolidated-v6 + iqk); ik_llama deprecated

- **The production MoE serving stack was cut over 2026-06-26 onto a SINGLE kernel, `production-consolidated-v6`, which integrates ik_llama's `iqk_mul_mat` AVX-512 GEMM kernels (runtime-gated `GGML_IQK=1`).** This retires the prior two-kernel arrangement where the gemma MoE worker ran on a separate ik_llama.cpp binary; **ik_llama.cpp is now fully deprecated** (no second binary). The iqk kernels give ~+11% vs ik_llama on the gemma worker's quantized CPU decode. All MoE roles now share this kernel: the gemma-4-26B-A4B worker (external assistant-head MTP), the Qwen3.6-35B-A3B frontdoor/coder_escalation/worker_summarize (NEXTN self-draft, shared :8070 process), and the Qwen3.5-122B-A10B architect_general (NEXTN self-draft). References to `ik_llama.cpp` elsewhere on this page (e.g. the `deepseek4` support gate) now mean the consolidated v6 kernel.
- **Status (NOT verified production throughput):** v6+iqk cutover executed 2026-06-26 — config/governance converged (174 promotion-gate tests pass), canonical binary built; live throughput + garbage verification PENDING (operator deploy gate). Tracking: [v6-iqk-promotion.md](../handoffs/active/v6-iqk-promotion.md).

### DeepSeek-V4-Flash GGUF Heterogeneous MoE Quant Reference (2026-05-28)

- **DeepSeek-V4-Flash GGUF is a concrete asymmetric MoE quantization reference, now with a first (provisionally-failing) CPU throughput datapoint.** The antirez GGUF card packages a 284B-parameter `deepseek4` MoE with per-tensor-role precision: routed experts at very low precision, shared/attention/output tensors at higher precision, and router tensors preserved in F16. The Q2 and Q4 variants are reported at 80.8 GiB and 153.3 GiB on disk, respectively, which fit the EPYC host. As of the 2026-05-30 Strategy-B port attempt, the Q4 variant measured 8-11 t/s canonical CPU decode (provisional FAIL vs an 18 t/s floor that needs V4-arch-aware recalibration — see the 2026-07-02 refinding above). Still a transferable heterogeneous-MoE quant recipe; the `deepseek4` arch is a structural rewrite into ik_llama's older API, not a hand-merge. Sources: [large-moe-expert-parallelism.md](../handoffs/active/large-moe-expert-parallelism.md), [deepseek-v4-flash-cpu-port.md](../handoffs/active/deepseek-v4-flash-cpu-port.md).

### REAP Core Technique

- **REAP beats merging by a wide margin at all compression levels**: At 50%, REAP achieves 0.557 coding accuracy on Qwen3-30B-A3B vs HC-SMoE 0.379 and M-SMoE 0.413. On creative writing, HC-SMoE catastrophically collapses to 0.008 while REAP maintains 0.718. Theoretical explanation (Theorem 1 in the paper): merging creates irreducible error proportional to Var[r(x)] (router policy variability) because the merged expert cannot produce different outputs for different inputs -- the input-dependent routing is lost. Pruning preserves surviving experts unchanged, maintaining the router's discriminative ability. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **25% pruning is near-lossless and sometimes beneficial**: Qwen3-Coder-30B-A3B REAP-25B scores HumanEval 94.5 vs baseline 92.1 (+2.4), HumanEval+ 89.0 vs 87.8 (+1.2), MBPP 87.3 vs 87.6 (-0.3), LiveCodeBench identical (35.2). Paper-wide mean at 25% is -2.8% on coding. Cerebras 480B at 25% outperforms base on 6/14 benchmarks (agentic tasks up 1.8-2.9 pts). Kimi-Linear at 30% gains +10 AIME25. The mechanism: removing noisy/redundant experts reduces routing confusion, effectively performing implicit regularization. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **The Goldilocks zone is 30-40%, counterintuitively not 20-25%**: 0xSero's MiniMax-M2.1 stress tests across 4 temperatures times 6 prompt types: REAP-20% produced 1 repetition loop (deprecated), REAP-30% zero loops (recommended), REAP-40% zero loops (recommended), REAP-50% 2 loops (deprecated). Low temperature (0.0-0.2) exposes loop failures; temp >=0.7 masks them. `math_word` prompts are most vulnerable. Hypothesis: 20% removes just enough experts to destabilize routing without triggering clean redistribution, while 30% forces the router to fully adapt. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **Calibration data determines which capabilities survive**: If calibration data lacks code, code-specialized experts appear unused and get pruned, destroying coding ability. 0xSero's validated recipe (1,360 samples): 51% evol-codealpaca (code gen), 24% xlam-function-calling (tool use), 24% SWE-smith-trajectories (agentic coding). Cerebras uses a similar composition for Qwen3-Coder models. For our stack, custom calibration from production orchestrator workload (agentic coding + tool calls + multi-turn conversations) would be optimal. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **Gate renormalization (paper v2) improves accuracy**: Simple post-pruning router gate adjustment reduces mean accuracy loss from 2.6% to 1.9% across benchmarks. No re-training required. [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

- **REAP output is standard safetensors**: The pruned model is a standard HuggingFace checkpoint with fewer experts per MoE layer. Direct `convert_hf_to_gguf.py` produces valid GGUF. Standard `qwen3moe` architecture string -- no custom code, compatible with any llama.cpp build b6810+. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

### REAP Production Deployment

- **246B deployed as architect_coding, replacing 480B**: REAP-246B (50% pruning of Qwen3-Coder-480B-A35B): 82% quality on Claude-as-Judge (+9pp over unpruned at deployment quant), 8.0 t/s throughput (+14%), 139 GB memory (-44%). Math improved +3, thinking improved +5 -- removing noisy experts helped reasoning. Only IP suite regressed (prompt leakage, -3). The 480B model was deleted. Deployed since 2026-03-29. [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

- **REAP-363B (25% pruned 480B) is NOT compelling for single-model deployment**: 93% of 480B speed at 6.54 t/s, 31 GB savings irrelevant at 1.13 TB RAM. Tree and lookup both harmful (approximately -22%). REAP on large MoE is a GPU VRAM optimization; our CPU RAM budget is not the bottleneck. Only valuable in concurrent-model RAM budgeting scenarios. [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

- **REAP-25B GGUF available off-the-shelf**: bartowski's `cerebras_Qwen3-Coder-REAP-25B-A3B-GGUF` in 26 quant variants. Q4_K_M at 15.19 GB (vs approximately 18 GB base = -16% memory, same 3B active params). Downloaded and benchmarked: dm=24 linear at 39.62 t/s (101% of base 30B), baseline without speculation at 33.21 t/s (15% faster than unpruned baseline). [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md), [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

- **REAP replaces runtime expert reduction -- do NOT stack**: REAP permanently removes experts from the model file. Download the pre-pruned GGUF and skip `--override-kv n_expert` entirely. Stacking REAP with runtime expert reduction would double-prune and degrade quality. [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

### Extending Techniques

- **EvoESAP is not useful for Qwen3+REAP**: At 25% pruning, EvoESAP (non-uniform cross-layer budget via evolutionary search) actually hurts Qwen3 (Code Avg 0.580 vs 0.629 uniform REAP). At 50%, gains are only +0.010 Code Avg. The headline +19.6% MATH-500 result was ERNIE + Frequency criterion (weakest ranker), not REAP. REAP's uniform allocation is already near-optimal for Qwen3's 128-expert architecture. Not worth the 5-hour search cost. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **Router Knowledge Distillation: modest for REAP, worth 2h at 50%+**: Tested directly on Qwen3-30B-A3B at 62.5% retention (128 to 80 experts): 16/25 benchmarks improved but gains are small for REAP (the router already routes well post-pruning). Cost is only approximately 2h on A100 with 3000 samples and 0.04% of parameters updated. Larger gains for weaker compression methods (CFES, MoBE). Fine-grained MoEs with 128 experts (1.43T routing combinations) benefit most from re-training, so Qwen3 is in the right category. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **MoNE is lower priority than REAP**: Novice experts are constant vectors (mean expert output), not learned networks. Memory savings are essentially identical to REAP (expert FFN weights removed, novice overhead negligible). No direct REAP comparison in the paper. Only tested on models up to 16B. The "0.14 performance drop at 25%" claim was not from this paper (correction noted in deep dive). [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **Double compression pipeline (prune + quantize) achieves approximately 6.5x**: 0xSero demonstrated REAP 50% + AutoRound W4A16 on GLM-4.7: 700 GB to 92 GB, running at 375 tok/s prefill and 38.5 tok/s gen on 8x RTX 3090. The pipeline preserves standard HuggingFace safetensors at every step, so each stage uses standard tooling. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

### Leanstral and New MoE Architectures

- **Leanstral is a near-ideal REAP candidate**: 95% of its 119B parameters (116B of 122B) are routed expert weights (128 experts, 2048 FFN each). At 75% pruning (32 experts retained) + Q4_K_M, the model shrinks from 68 GB to approximately 20 GB with projected 40+ t/s on EPYC. The key hypothesis: Lean 4 proof engineering is extremely specialized -- if expert activation patterns cluster on 20-30 experts (plausible for a narrow domain), aggressive pruning has minimal quality impact. Needs profiling with `--moe-expert-stats` on representative Lean 4 workloads. [Leanstral deep-dive](../research/deep-dives/leanstral-architecture-analysis.md)

- **Leanstral uses DeepSeek V3 architecture (MLA + MoE)**: `deepseek2` architecture string in llama.cpp, fully supported. Multi-head Latent Attention (MLA) with 256 kv_lora_rank reduces KV cache requirements independently of expert pruning. 32 standard attention heads, 1024 q_lora_rank, 64 qk_rope_head_dim. Community GGUFs at `jackcloudman/Leanstral-2603-GGUF` (Q4_K_M approximately 68 GB, Q8_0 approximately 126 GB). Vision encoder (Pixtral) is dead weight for proof tasks and could be stripped. [Leanstral deep-dive](../research/deep-dives/leanstral-architecture-analysis.md)

- **Leanstral beats Claude on FLTEval at 15x lower cost**: pass@2 of 26.3 vs Claude Sonnet 4.6's 23.7, at $36 vs $549 per run. FLTEval tests repo-scale proof engineering (completing FLT PRs), not function-level verification. Complementary to Goedel-Code-Prover-8B which is a prover (takes goal, produces tactic proof) while Leanstral is an agent (uses lean-lsp-mcp tool, reads repo context). [Leanstral deep-dive](../research/deep-dives/leanstral-architecture-analysis.md)

### Hybrid Models and MoE

- **Qwen3.5 hybrid is NOT supported by REAP officially**: Only `Qwen3MoeForCausalLM` in the REAP model registry. 0xSero applied REAP to Qwen3.5-35B-A3B (intake-236) but PPL increased +39% at only 20% pruning vs near-lossless on pure MoE. Hybrid models with 75% recurrent layers are much less tolerant because MoE layers interact with recurrent state -- pruning experts disrupts the recurrent-attention interplay more severely. Custom model_util mapping would be needed. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **REAP-pruned models enable speculative decoding where hybrids cannot**: REAP-25B is pure MoE (`qwen3moe` arch), so all speculation approaches work (dm=24 linear at 39.62 t/s, lookup safe at 37.91 t/s, tree hurts at 30.83 t/s). If the frontdoor role shifts from hybrid Qwen3.5-35B-A3B to REAP-25B, speculation becomes viable for the highest-volume role in the orchestrator. [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

### GLM-5.1 REAP and Expert Pruning Thresholds

- **GLM-5.1-555B-A14B-REAP GGUF is the first 555B MoE with published GGUF benchmarks.** 325GB Q4_K_M, 14B active parameters from 192 experts (top-8 routing), 88% Terminal-Bench, 66% SWE-bench Pro, 0% repetition loops. CPU-deployable via llama.cpp. Evaluation handoff created: glm51-reap-cpu-evaluation.md. [intake-427]

- **Expert count threshold finding confirms 25-30% as the pruning sweet spot.** 192/256 experts (25% prune) = stable with 0% degeneration; 154/256 experts (40% prune) = BROKEN with 29% degeneration. This aligns with the Goldilocks zone finding from 0xSero's MiniMax-M2.1 stress tests, independently confirming that 25-30% pruning is near-lossless while 40%+ risks catastrophic quality collapse on large-expert-count architectures. [intake-427]

### Frontier GLM-MoE-DSA and Kimi-K2 Targets — DSA-gated, asymmetric storage (2026-06-20)

- **GLM-5.2 (754B GLM-MoE-DSA, MIT) is now the PRIMARY GLM target, superseding GLM-5.1-REAP.** Per user direction 2026-06-20, the flagship coding/agentic GLM under evaluation is `zai-org/GLM-5.2` via unsloth dynamic GGUF quants, not the REAP'd 555B/192-expert GLM-5.1 (now a fallback datapoint). It is a 754B MoE + Dynamic Sparse Attention model with a 1M-token context window. Vendor-self-reported benchmarks (AIME 2026 99.2, GPQA-Diamond 91.2, SWE-bench Pro 62.1, Terminal Bench 2.1 81-82.7) are **observations** per MEASUREMENT.md, usable for hypotheses but never to gate keep/deploy decisions. [intake-699], [GLM-5.x eval handoff](../handoffs/active/glm51-reap-cpu-evaluation.md)

- **The DSA cache/runtime gap, not storage, was the binding blocker for the entire GLM-5.x family.** That gap is now closed on current source: experimental-v7 `3dee86a5a` routes `LLM_ARCH_GLM_DSA` through `llama_kv_cache_dsa` and the DeepSeek32 DSA graph, and the current-source smoke returned `READY` with `Lightning Indexer enabled`. The remaining open work is sparse-compute profiling plus long-context quality, not basic wiring. [DSA contribution handoff](../handoffs/active/llama-cpp-dsa-contribution.md), [glm51-reap-cpu-evaluation.md], [intake-699]

- **GLM-5.2 escapes the storage gate via unsloth UD-IQ2; Kimi-K2.7-Code does not even at Q2_K — an asymmetric storage gate.** GLM-5.2's unsloth UD dynamic-quant ladder runs UD-IQ2_XXS/M ~238 GB and UD-Q2_K_XL 254 GB (vs Q4_K_M 466 GB, Q8_0 801 GB), so the IQ2 path fits the ~633 GB raid0 free with comfortable headroom. By contrast Kimi-K2.7-Code's GGUF set is Q4_K_M 620.7 GB / Q3_K_M 489.2 GB / Q2_K 373 GB — Q4_K_M is effectively non-viable against ~633 GB free, and even Q3_K_M (489 GB) leaves only ~144 GB. The "~480 GB headroom" figure earlier attached to Kimi was RAM, not disk. (Both fit the 1.1 TB RAM budget; the gate is disk, not memory.) [intake-699], [intake-703], [Kimi deferral addendum](../handoffs/completed/large-moe-expert-parallelism-completed-through-2026-05-28.md)

- **Kimi-K2.7-Code (~1T-total / 32B-active MoE) maps onto the deferred coder_escalation slot, but only its text path is fork-supported.** 384 experts (top-8 + 1 shared), 61 layers (1 dense), MLA attention, 256K context, coding-specialized. The model is now multimodal via a 400M MoonViT vision encoder (separate mmproj files), but **MoonViT is UNSUPPORTED in our fork** — there is no `moonvit` handling, so only the text path (deepseek2/MLA + kimi-k2 tokenizer) is plausibly runnable. CPU decode t/s on a ~1T MoE is unmeasured. Deferral stands behind storage + operator approval + a canonical CPU decode-t/s and coding-eval gate. [intake-703], [Kimi deferral addendum](../handoffs/completed/large-moe-expert-parallelism-completed-through-2026-05-28.md)

- **IndexShare cuts per-token FLOPs ~2.9x at 1M context by reusing one sparse-attention indexer across layers.** GLM-5.2 adds IndexShare (arXiv 2603.12201), which reuses the same sparse-attention indexer across every four sparse-attention layers rather than recomputing it per-layer. This is the only genuinely-new architectural technique in the GLM-5.2 point release (the 754B GLM-MoE-DSA base is otherwise carried over from GLM-5/5.1). It compounds the DSA value proposition that PR #21149 must unlock before any of it is realizable on CPU. [intake-699]

### Inter-process Expert Parallelism (CPU15 Phase 3, 2026-04-25)

After REAP made REAP-246B production-viable in absolute terms, the open question shifted to whether *single-stream* throughput on large MoE could exceed the 6.16 t/s Phase 0 baseline by sharding active expert compute across NUMA nodes. Phase 1/2 intra-process attempts (per-CCD expert sharding inside one llama.cpp process) all D3-failed: the fundamental limitation is ggml's sequential-per-op graph executor — even with sharding, all threads still execute op N together with global barriers, so per-NUMA parallelism isn't achievable inside one process. **Phase 3 escapes that constraint by running N independent llama.cpp processes connected via shared-memory IPC, each computing 1/N of experts at every MoE op.** The IPC primitive (`ep_dispatcher` library, [Phase 3.1 prototype](../../cpu-ep-prototype/)) achieves 0.73 μs RTT for 4 NUMA-pinned workers — ~200× under the viability threshold.

The integration into `llama.cpp-experimental:feature/cpu-ep-inter-process` landed 13 commits in one day: bootstrap fork at `ggml_cpu_init`, IPC harness inside `ggml_compute_forward_mul_mat_id`, expert slicing with parallel sum-reduce + merged broadcast, NUMA pinning, worker drone mode (workers skip non-MoE ops and receive src1+ids from master at each MoE op), multi-node pinning, lazy expert-tensor sharding (`ggml-ep-shard.{h,cpp}`), `GGML_EP_MASTER_ALL_NODES` for bandwidth-bound configs, plus a critical `#ifndef GGML_USE_OPENMP` guard fix that exposed earlier "throughput numbers" as measurement artifacts.

#### Production results

| Model | Total / Active | Baseline (96t, --numa distribute) | EP best | Δ | Verdict |
|-------|---------------|----------------------------------|---------|---|---------|
| gemma-4-26B-A4B-it Q4_K_M | 26B / 4B | 28.5 t/s | 30.3 (N=2 drone+shard) | +6% | Bit-exact ✓ |
| **Qwen3.6-35B-A3B Q8_0** | 35B / 3B | 9.93 t/s | **19.90** (N=2 drone+shard 48t) | **+100%** | Bit-identical PPL ✓ |
| REAP-246B-A35B Q4_K_M | 246B / 35B | 6.89 t/s | 0.1 (N=4 master-all-nodes) | −98% | EP doesn't help ✗ |
| MiniMax-M2.7 Q8_0 | 230B / 10B | 9.98 t/s | 7.72 (N=2 shard) | −23% | EP doesn't help ✗ |

The 32-chunk WikiText-2 PPL gate confirmed bit-identical perplexity between baseline and EP+drone+shard on Qwen3.6-35B-A3B (`[1]4.3289...[32]5.7225` in both runs). Visible token-level divergence in `llama-cli` was sampling-argmax jitter on FP-rounding-equivalent logits — the underlying probability distribution is identical.

#### Why EP wins on medium MoE and remains unresolved on >150B-class

**Wins on Qwen3.6-35B-A3B class** because compute, not bandwidth, dominates. With 3B active params and ~35 GiB Q8_0 model size, single-instance at 96t under-utilises the 4-NUMA bandwidth profile; EP at N=2 with each instance spanning 2 nodes lets master handle non-MoE compute fully while workers parallelise MoE — net 2× throughput.

**Current >150B outcome (REAP-246B / M2.7)**: EP regresses on measured configs, but aggregate-DDR saturation is not proven as the root cause. The strongest observed failure mode is thread oversubscription in master-all-nodes style configs (`96 + 24×3` threads on 96 physical cores), plus unresolved sync/imbalance effects. Root-cause closure now depends on CPU24 uncore/fabric counters and CPU23 regime coverage.

The fundamental issue: ggml's threadpool is fixed-size per process, so it can't dynamically resize between non-MoE phase (master-only active) and MoE phase (all instances active in parallel). Architectural fix would require dynamic threadpool resizing or phase-aware spin-parking — real engineering, deferred indefinitely.

#### Production deployment routing

| Total params | Mode | Reason |
|--------------|------|--------|
| < 50B MoE | EP N=2 drone+shard, 48t per instance | Compute-bound, parallelism wins |
| 50–150B MoE | EP N=2 drone+shard (validate first) | Likely benefits, bandwidth-edge |
| > 150B MoE | single-instance --numa distribute 96t (current) | EP regressions observed; attribution still open |
| Dense | single-instance | No MoE ops to parallelise |

#### Deferred memory and latency optimisations

- **Eager shard allocation (3.2(g.1))**: pre-allocate compact expert buffers at model-load time instead of lazily on first `mul_mat_id` call. Improves first-token latency on medium-MoE deployments. ~3-4 hours work.
- **`MADV_DONTNEED` on post-copy mmap pages (3.2(g.2))**: after `ggml_ep_shard_lookup` memcpys experts into the local anon buffer, `madvise(MADV_DONTNEED)` on the source mmap region releases the now-redundant page-cache pages. ~138 GB savings on REAP-246B-class. ~30 minutes work + PPL re-verify.

#### Architecture summary

The IPC machinery (`ep_dispatcher` 0.73 μs RTT, env-var bootstrap, NUMA pinning, drone mode, lazy shard) is **complete and correct**. The 13 commits constituting Phase 3.2 deliver a deployable EP capability for medium-MoE. For REAP-246B-class, treat closure as provisional pending CPU24 attribution rather than "bandwidth-saturation-closed."

[CPU15 handoff](../handoffs/active/large-moe-expert-parallelism.md), [progress 2026-04-25](../progress/2026-04/2026-04-25.md)

### MoE Serving and Offloading Research

- **Flash-MoE (intake-166)**: Pure C/Metal inference engine for Qwen3.5-397B on MacBook Pro -- relevant as reference for memory-efficient MoE serving on consumer hardware. The architecture insights about expert caching may inform our NUMA expert placement strategy. [intake-166](https://github.com/danveloper/flash-moe)

- **FlashMoE SSD offloading (intake-167)**: ML-based cache replacement for SSD-offloaded experts. Not directly applicable (our models fit in RAM) but relevant if we need to run models exceeding 768 GB. Cache replacement strategies for hot/cold experts could inform NUMA-aware expert placement. [intake-167](https://arxiv.org/abs/2601.17063)

- **SpecMoEOff (intake-168)**: Hides offloading latency by overlapping expert loading with speculative decoding. Interesting architecture but not applicable -- our models are fully RAM-resident. The principle of overlapping expert loading with drafting could be relevant for future ultra-large models. [intake-168](https://arxiv.org/abs/2508.21706)

## Updates — 2026-04-28

### Large-MoE as primary CPU target (2026-04-26 reframe)

Per [`large-moe-expert-parallelism.md`](../handoffs/active/large-moe-expert-parallelism.md). The single-instance vs concurrent gap on Coder-30B-A3B Q4_K_M is 2.13×: single-instance NPS4 best is 48.81 t/s vs concurrent 48×4t aggregate ~104 t/s. REAP-246B single-instance is 5.94 t/s and has no viable concurrent serving path due to NUMA memory contention.

Strategic reframe: shift the CPU-optimization target from 30B-class models (where concurrent NUMA-4-way already wins) to ≥100B sparse MoE where total params fit RAM but only a fraction are activated per token. Expert parallelism (EP) exploits the 4-way NUMA + 12-CCD topology to convert aggregate bandwidth to single-stream throughput — turning an aggregate-only win into a per-stream win.

### Inter-process EP Phase 3 results — honest baselines (2026-04-26)

Per [`large-moe-expert-parallelism.md`](../handoffs/active/large-moe-expert-parallelism.md). 13 commits on `feature/cpu-ep-inter-process` during the 2026-04-26 session, with honest `--mmap 0` canonical baselines that supersede the earlier warmed-baseline artifact (which had inflated Qwen3.6-35B-A3B to +100%):

| Model | Class | Honest baseline | EP best | Δ |
|-------|-------|-----------------|---------|---|
| Qwen3.6-35B-A3B Q8_0 | frontdoor | 17.0 t/s | 19.90 t/s | **+17%** |
| Gemma-4-26B-A4B Q4_K_M | medium | 28.5 t/s | 30.3 t/s | **+6%** |
| REAP-246B Q4_K_M | large | 6.89 t/s | regress | neutral / regress |
| MiniMax-M2.7 Q8_0 | large | 9.98 t/s | regress | neutral / regress |

The earlier +100% Qwen3.6-35B-A3B result was a measurement artifact — warmed page cache on the EP run vs cold on the baseline. The honest +17% is bit-identical PPL (32-chunk WikiText-2 verified).

REAP-246B and MiniMax-M2.7 (>150B) attribution is **open** pending CPU24 uncore counters. Not bandwidth-saturation-closed — earlier "exhausted" framing was closure-inflation. The leading hypothesis is thread oversubscription in master-all-nodes configs (96 + 24×3 threads on 96 physical cores) plus unresolved sync/imbalance effects.

**Drone mode**: workers skip non-MoE ops and receive src1+ids from master at each MoE op. PPL bit-identical on Qwen3.6-35B-A3B Q8_0 (32-chunk WikiText-2 verified).

**Production routing decision**:

| Total params | Mode | Reason |
|--------------|------|--------|
| < 50B MoE | EP N=2 drone+shard, 48t per instance | Compute-bound, parallelism wins |
| 50–150B MoE | EP N=2 drone+shard (validate first) | Likely benefits, bandwidth-edge |
| > 150B MoE | single-instance --numa distribute 96t | EP regresses; attribution open |

### MoE-Spec verification-batch CPU mechanism

Per [`moe-spec-cpu-spec-dec-integration.md`](../handoffs/active/moe-spec-cpu-spec-dec-integration.md) — see [speculative-decoding.md](speculative-decoding.md) for full mechanism description. The MoE-relevant points:

- Cache-aware, BW-bound mechanism: `--moe-spec-budget N` aggregates routing softmax across the verification batch and shrinks the active-expert union before `argsort_top_k`
- Verified +15.2% pp32 on REAP-246B Q4_K_M B=40 (Phase 1 forward-pass)
- End-to-end +3.3% on REAP-246B (Phase 2 v5 PGO; Amdahl-attenuated because drafter+accept-eval are unchanged)
- Mechanism rationale on EPYC: L3 (~32 MB per CCD × 12 = 384 MB) is far below total expert-weight footprint (REAP 138 GB at Q4_K_M). Per-batch top-B shortlist directly cuts DRAM expert-weight reads, the dominant cost per CPU24 attribution
- Final verdict: REAP-246B B=40 deployable behind env-gate; Coder-30B B=64 NOT deployable (mask-overhead/total-compute marginal, defer to Phase 3)

### Dynamic expert selection Phase 0 entropy probe NEGATIVE

Per [`moe-dynamic-expert-selection.md`](../handoffs/active/moe-dynamic-expert-selection.md). The entropy-gated K candidate (vary number of active experts per token based on routing entropy) was falsified at Phase 0: routing distribution on Coder-30B is bimodal, not high-entropy-tail-distributed, so an entropy threshold cannot select a low-K vs high-K regime cleanly. Pathfinder deprioritized as offline.

Other candidates remain queued for Phase 0 diagnostic-only probes (~3–4 hours total):
- **Dynamic-skipping**: per-token β threshold (skip expert evaluation when gate weight is below threshold)
- **OD-MoE lookahead**: 84–91% prediction accuracy for next-token expert set, enabling prefetch

Both Phase 0 are diagnostic — measure prediction accuracy / threshold curves, then decide whether to invest in implementation.

### Per-CCD / per-process expert sharding variants (Phase 1+)

Per [`large-moe-expert-parallelism.md`](../handoffs/active/large-moe-expert-parallelism.md). Two variants tracked under the EP umbrella:

- **Variant 1 — intra-process per-CCD**: reuses the CPU1 substrate (NPS4 + GGML_NUMA_WEIGHTS=1). Expert weights reorganized per-CCD so each CCD's threads pull from L3-local expert ranges. Composes with existing single-instance bandwidth wins.

- **Variant 2 — inter-process**: 4 instances (one per NUMA), with replicated attention/dense weights and expert dispatch via shared-memory IPC. This is the Phase 3 path that landed +17% on Qwen3.6-35B-A3B (above). Still has open attribution on >150B.

**Phase 3.4 candidate — 2DH ring-buffer**: port Tutel's 2DH (two-dimensional hierarchical) all-to-all (arxiv:2206.03382) to the CPU15 inter-process EP shared-memory ring for the 4-NUMA-node × 12-CCD topology. Target: reduce ~96 sync points/token to ~24, addressing the measured REAP-246B (-53% earlier baseline, neutral-regress now) and MiniMax-M2.7 (-23%) regressions on >150B MoE while attribution remains open.

## Actionable for EPYC

- **Deployed**: REAP-246B as architect_coding (50% prune of 480B). In production since 2026-03-29. 82% quality (+9pp), 8.0 t/s (+14%), 139 GB (-44%)

- **Ready to benchmark further**: REAP-25B Q4_K_M (15.19 GB, downloaded, initial benchmarks done). Run at temperatures 0.0/0.3/0.7 per 0xSero's loop-detection methodology. Test NUMA 4-way (fits trivially at 15 GB per quarter-machine). Verify quality gap vs frontdoor hybrid closes with 512+ max_tokens (Phase 2 showed 13pp gap was primarily truncation at 256 tokens)

- **Run REAP ourselves**: Use CerebrasResearch/reap CLI on Qwen3-Coder-30B-A3B at 25%/30%/40% with custom calibration from production orchestrator workload (agentic coding + tool calls + multi-turn). Convert each to GGUF Q4_K_M and benchmark. If 30-40% is safe on our workload, push to 50% + Router KD post-processing (2h investment)

- **Profile Leanstral expert activation**: Run Leanstral Q4_K_M with `--moe-expert-stats` on representative Lean 4 proof workloads. If activation clusters on 20-30 experts, REAP-75% is viable (68 GB to approximately 20 GB). Contingent on Lean 4 proving pipeline maturity

- **Apply REAP to architect_general**: Qwen3-235B-A22B is not in the official Cerebras inventory but is likely supported as Qwen3 family. Even 25% pruning would reduce from approximately 140 GB to approximately 105 GB Q4_K_M, potentially enabling better NUMA fit or concurrent loading

- **Priority**: MEDIUM. The big production win (246B deployment) is done. Further gains from REAP-25B quality validation, custom calibration, and Leanstral profiling are incremental. The highest-value next steps are in KV cache optimization (compaction and selection) rather than further MoE pruning

## Open Questions

- Does REAP-25B quality hold at low temperature (0.0-0.2) on our production workloads? The Goldilocks zone finding suggests low temp is the critical stress test for routing stability
- Can custom calibration from production orchestrator data improve over generic code datasets? Our workload mix (agentic coding, tool calls, multi-turn reasoning) differs from standard code benchmarks
- What is Leanstral's expert activation distribution on Lean 4 proofs? If highly clustered, REAP-75% is viable; if distributed, even 50% may degrade proof quality
- Does stacking REAP-25B with speculative decoding (dm=24) plus NUMA 4-way yield compound gains? 4x15GB instances = 60GB total, well within quarter-machine budget
- Can REAP be applied to Qwen3-235B-A22B (architect_general)? Not in Cerebras inventory but likely supported
- Will Cerebras publish REAP models for future Qwen3.5 hybrid architectures with improved hybrid tolerance?
- At what pruning level does Router KD become cost-effective? Currently "worth it at 50%+" but the exact crossover needs measurement on our models
- Can the double compression pipeline (REAP + quantization) be extended with KV cache compression for a triple stack (expert pruning + weight quantization + KV compression)?
- Does the two-tier expert cache (#20757) hold its 12-14 t/s proof-of-concept advantage on the MI210 discrete GPU with our largest MoE (246B-class attention footprint), and does it compose with hipBLASLt grouped GEMM or are they mutually exclusive paths?
- What is the correct V4-arch-aware throughput floor for DeepSeek-V4-Flash once CSA/HCA/indexer/compressor overhead is modeled — is the ~8-12 t/s measured range an acceptable operating point for an architect_general candidacy, or does the 18 t/s floor stand after recalibration?
- If frontdoor spec-dec is ever enabled, does MoE-Spec's +15.2% forward-pass gain survive on the frontdoor's actual verification batches, giving the mechanism a live consumer?
- Does the n-gram-embedding sparsity axis (embedding-scaling-beats-expert-scaling) ever justify a from-scratch pretraining or frozen-backbone retrofit on our node, given the CPU probe of the deployed LongCat checkpoint was dominated by gemma4-MTP?
- On CPU, is there any MoE architecture (vs dense) where MTP/spec-dec clears the expert-union verification wall, or is the ≤1.06x ceiling structural for pure-MoE decode?

## Related Categories

- [Speculative Decoding](speculative-decoding.md) -- REAP-pruned pure MoE models enable speculation where hybrid models cannot. REAP-25B at dm=24 achieves 39.62 t/s vs hybrid frontdoor at 19.6 t/s with no viable speculation
- [Quantization](quantization.md) -- REAP output is standard safetensors, directly compatible with GGUF quantization via `convert_hf_to_gguf.py`. Double compression pipeline (prune then quantize) achieves approximately 6.5x
- [KV Cache Optimization](kv-cache.md) -- MoE models have different KV patterns than dense; MLA (Leanstral's DeepSeek V3 architecture) reduces KV cache independently of expert pruning via low-rank latent attention
- [Hardware Optimization](hardware-optimization.md) -- NUMA 4-way parallelism delivers larger throughput gains than MoE pruning for models that fit in quarter-machine memory. REAP makes more models fit; the MI210 (2026-07-02) reopens CPU+GPU hybrid-MoE expert offload
- [Memory-Augmented Models](memory-augmented.md) -- n-gram-embedding-augmented MoE (LongCat-Flash-Lite / Engram) treats a deterministic lookup table as a sparsity axis orthogonal to routed experts; embedding-scaling can beat expert-scaling at high sparsity
- [Local Inference](local-inference.md) -- MoE serving via GGUF/llama.cpp: `deepseek4` V4-Flash port, `--n-cpu-moe` offload, per-role binary/spec-budget config live in the orchestrator launch path

## Source References

- [REAP Ecosystem Deep-Dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md) -- REAP algorithm and Theorem 1, Goldilocks zone (30-40%), 0xSero stress testing, calibration recipes, 30 Cerebras models, EvoESAP downgrade, Router KD assessment, MoNE rejection, double compression pipeline
- [Leanstral Architecture Analysis](../research/deep-dives/leanstral-architecture-analysis.md) -- 119B MoE (95% routed expert weights), MLA + DeepSeek V3 architecture, REAP candidacy at 75%, FLTEval results, CPU deployment estimates, complementary to Goedel-Code-Prover
- [REAP Handoff](../handoffs/completed/reap-moe-expert-pruning.md) -- 4-phase evaluation, 246B deployment (+9pp/+14%/-44%), REAP-25B benchmarks, 363B not compelling, answered 6 open questions, gate renormalization v2
- [GPU Acceleration Handoff](../handoffs/active/gpu-acceleration-path.md) -- Grouped GEMM for MoE on GPU (Stream-K, rocWMMA); CPU+GPU hybrid-MoE expert offload (`-ot "exps=CPU"` / `--n-cpu-moe`, two-tier expert cache #20757); MI210 installed 2026-07-02 reopening the discrete-GPU path; DGX Spark unified-memory contrast (not acquired)
- [MoE-Spec CPU Spec-Dec Integration Handoff](../handoffs/active/moe-spec-cpu-spec-dec-integration.md) -- Budgeted-verification `--moe-spec-budget N` mechanism (+15.2% forward-pass on REAP-246B B=40), now NO live consumer (REAP role removed, frontdoor zero spec-dec); catalog successors DSpark/Graft/SpecDec++
- [Speculative-Decoding / MTP Refresh Handoff](../handoffs/active/speculative-decoding-mtp-refresh.md) -- MoE-vs-dense CPU-MTP wall: dense 1.84-3.2x measured, pure-MoE-A3B ≤1.06x (expert-union verification overhead is the wall, not draft quality)
- [findings-05c lever × model-category matrix](../handoffs/active/fable5-window2-findings-05c-mi210-lever-category-matrix.md) -- MoE-on-GPU spec-dec verdict: frontdoor 35B-A3B single-stream PLAIN ~101 > MTP ~90 (PLAIN is the bar); MTP-on-GPU-MoE converged ~neutral at production temp (the −12% is stale); the {arch × substrate}-set spec-dec sign; MoE-aggregate FA-decode + bf16-for-aggregate config wins
- [MoE aggregate deployment wins brief](../handoffs/active/moe-aggregate-deployment-wins-brief.md) -- ⏸ production HOLD; MoE-on-GPU plain-decode aggregate levers (`-fa 1` at B≥8, bf16-for-aggregate); low-batch expert `mmid`→MMQ forcing net-negative (MMVQ is the correct sparse low-batch expert kernel)
- [DeepSeek-V4-Flash CPU Port Handoff](../handoffs/active/deepseek-v4-flash-cpu-port.md) -- Strategy-B port attempt: 284B/13B-active `deepseek4` MoE (CSA+HCA+indexer+compressor+manifold-HC), Q4 8-11 t/s provisional throughput FAIL vs 18 t/s floor (floor needs V4-arch-aware recalibration to ~8-12 t/s); ik_llama API-gap is a structural rewrite
- [Engram Conditional Memory Handoff](../handoffs/active/engram-conditional-memory.md) -- LongCat-Flash-Lite n-gram-augmented MoE (68.5B/2.9-4.5B-active, ~31.4B n-gram tables) CPU probe closed negative (37 t/s, 53.8% sentinel, dominated by gemma4-MTP); family viable, checkpoint not
- [intake-758](https://arxiv.org/abs/2601.21204) "Scaling Embeddings Outperforms Scaling Experts" (Meituan LongCat, arXiv 2601.21204) -- n-gram embedding scaling as a sparsity axis orthogonal to MoE with superior high-sparsity Pareto; embedding ≤50% of total; width amplifies / depth diminishes; scaling-law justification behind LongCat-Flash-Lite
- [intake-310](https://huggingface.co/blog/Doctor-Shotgun/llamacpp-moe-offload-guide) Doctor-Shotgun MoE offload guide -- `-ot "exps=CPU"` / `--n-cpu-moe` production-ready; PCIe latency is the bottleneck not CPU compute; two-tier expert cache 12-14 t/s vs 0.5-1 t/s pure offload
- [intake-637](https://huggingface.co/antirez/deepseek-v4-gguf) antirez/deepseek-v4-gguf -- 284B/13B-active `deepseek4` MoE, heterogeneous per-tensor-role quant (Q2 80.8 GiB / Q4 153.3 GiB), optional 3.6 GiB MTP-as-drafter sidecar
- [intake-738](https://github.com/deepseek-ai/DeepSpec/blob/main/DSpark_paper.pdf) DSpark (DeepSeek) -- semi-AR drafter + utilization-keyed adaptive verification depth; GPU-concurrency-specific, largely inert on concurrency-1 CPU decode; catalog-only, +26.7-30.9% accept-length vendor-reported
- [intake-742](https://arxiv.org/abs/2605.20104) Graft (arXiv 2605.20104) -- training-free prune-then-graft draft tree; MoE-Spec is tree-native so on-topic, but EAGLE-3-based + GPU adjacency; catalog-only until a CPU-refill variant is measured
- [intake-620](https://arxiv.org/abs/2405.19715) SpecDec++ (arXiv 2405.19715, COLM 2025) -- adaptive drafting-γ via per-token acceptance head; orthogonal-and-composable with MoE-Spec's verification budget (drafting side vs verification side)
- [intake-739](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-DSpark) DeepSeek-V4-Pro-DSpark -- 1.6T-total/49B-active MoE (~5.6× V4-Flash); do_not_port (blows raid0 storage gate + `deepseek4` unsupported); track FP4/FP8-mixed quant + on-policy distillation only
- [Lean Proving Pipeline Handoff](../handoffs/active/lean-proving-pipeline.md) -- Leanstral deployment context and Lean 4 integration
- [Inference Acceleration Index](../handoffs/active/inference-acceleration-index.md) -- REAP in context of broader inference optimization landscape
- [intake-181](https://arxiv.org/abs/2510.13999) REAP paper (arXiv:2510.13999, ICLR 2026) -- Core algorithm, pruning vs merging theorem
- [intake-183](https://github.com/0xsero) 0xSero GitHub -- 196 repos, community REAP practitioner, systematic sweeps
- [intake-184](https://huggingface.co/0xSero) 0xSero HuggingFace -- 28 REAP/AutoRound models, 216 followers
- [intake-185](https://github.com/CerebrasResearch/reap) CerebrasResearch/reap repository -- Apache 2.0, CLI for all Qwen3 MoE models
- [intake-186](https://huggingface.co/cerebras/Qwen3-Coder-REAP-25B-A3B) Cerebras pre-pruned Qwen3-Coder-REAP-25B-A3B -- 128 to 103 experts
- [intake-187](https://huggingface.co/bartowski/cerebras_Qwen3-Coder-REAP-25B-A3B-GGUF) bartowski GGUF quants -- 26 variants including Q4_K_M at 15.19 GB
- [intake-188](https://arxiv.org/abs/2603.06003) EvoESAP (arXiv:2603.06003) -- Non-uniform pruning, helps ERNIE not Qwen3
- [intake-189](https://arxiv.org/abs/2603.02217) Router Knowledge Distillation (arXiv:2603.02217) -- Lightweight router re-training
- [intake-190](https://arxiv.org/abs/2507.00390) MoNE (arXiv:2507.00390, ICLR 2026) -- Novice expert replacement
- [intake-235](https://mistral.ai/news/leanstral) Leanstral 119B (Mistral AI, Apache 2.0) -- MoE+MLA for Lean 4 proofs
- [intake-152](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html) Qwen3.5 serving recipe -- Hybrid MoE+Delta Net configuration
- [intake-166](https://github.com/danveloper/flash-moe) Flash-MoE -- Pure C/Metal inference for MoE on consumer hardware
- [intake-167](https://arxiv.org/abs/2601.17063) FlashMoE SSD offloading -- ML-based expert cache replacement
- [intake-168](https://arxiv.org/abs/2508.21706) SpecMoEOff -- Overlapping expert loading with speculation
- [intake-427] GLM-5.1-555B-A14B-REAP GGUF -- 325GB Q4_K_M, 14B active from 192 experts, 88% Terminal-Bench, 66% SWE-bench Pro, expert count threshold (25% safe / 40% broken)
- [intake-699](https://huggingface.co/unsloth/GLM-5.2-GGUF) GLM-5.2-GGUF (unsloth dynamic quants of zai-org/GLM-5.2) -- 754B GLM-MoE-DSA, MIT, 1M context, NOW the PRIMARY GLM target (supersedes GLM-5.1). DSA forward pass (PR #21149) is the gate, not storage; UD-IQ2 ~238 GB / UD-Q2_K_XL 254 GB / Q4_K_M 466 GB. New IndexShare indexer-reuse (arXiv 2603.12201) cuts per-token FLOPs ~2.9x at 1M ctx. Vendor benchmarks = observations.
- [intake-703](https://huggingface.co/mradermacher/Kimi-K2.7-Code-GGUF) Kimi-K2.7-Code-GGUF (mradermacher quants of Moonshot AI Kimi-K2.7-Code) -- ~1T-total/32B-active MoE (384 experts top-8 + 1 shared, MLA, 256K ctx). Q4_K_M 620.7 GB / Q3_K_M 489.2 GB / Q2_K 373 GB; storage near-blocker vs ~633 GB raid0 free. MoonViT vision encoder UNSUPPORTED in fork (text path only via deepseek2/MLA + kimi-k2 tokenizer).
- [GLM-5.x REAP CPU Evaluation Handoff](../handoffs/active/glm51-reap-cpu-evaluation.md) -- GLM-5.2 now primary; WAIT-DSA disposition; UD-IQ2 storage-viable path; GLM-5.1-REAP demoted to fallback
- [llama.cpp DSA Contribution Handoff](../handoffs/active/llama-cpp-dsa-contribution.md) -- PR #21149 DSA forward-pass blocker (Lightning Indexer + sparse fattn) gating the GLM-5.x family + DeepSeek-V3.2; multi-model-for-one-effort leverage. **2026-07-17 update:** superseded by landed generic-DSA #23346 (`deepseek32`+`glm-dsa` archs); GLM wired to `llama_kv_cache_dsa` on `3dee86a5a`; runtime GLM-5.2 classified **DSA-DENSE-MASK** (top-k engages, final attention still scales with full KV) → remaining D2 = a real sparse-gather final-attention path
- [progress 2026-07-17](../progress/2026-07/2026-07-17.md) -- GLM-5.2 DSA-DENSE-MASK runtime evidence + GLM cache/runtime wiring; GLM expert-routing skew (near-uniform-global / moderate-layer-local, hypothesis-only); Hy3 ungated-greedy acceptance ≈41–47% net-neutral CPU-MTP re-confirmation
- [Large-MoE EP Handoff (completed, Kimi addendum)](../handoffs/completed/large-moe-expert-parallelism-completed-through-2026-05-28.md) -- Kimi-K2 deferral row + 2026-06-20 K2.7-Code specifics (footprints, MoonViT unsupported, storage pre-gate)
- [intake-449] OpenAI Privacy Filter (huggingface.co/openai/privacy-filter) -- 2026-04-23: **aggressive small-MoE sparsity reference**. 128 experts with top-4 routing in a 1.5B-total / **50M-active (3.3%)** bidirectional encoder — ~2.6× sparser than our Qwen3.5/3.6-35B-A3B (8.6% active). 96% F1 on PII-Masking-300k. Not for deployment (PII task is off-roadmap), but design reference if `project_learned_routing_controller` upgrades from dense MLP to MoE router. [Deep-dive](../research/deep-dives/openai-privacy-filter-pii-preprocessor.md)
- [intake-467] MegaBlocks (arXiv:2211.15841, Stanford/MosaicML, MLSys 2023) -- 2026-04-26: foundational dropless-MoE via block-sparse grouped GEMM with **blocked-CSR-COO + transpose-indices** encoding. Eliminates capacity-factor padding/dropping. Anchors CPU18 backlog item: port the **indexing scheme** (not the GPU kernel) into CPU2's AVX-512BW Q8_0 expert-GEMM path for padding-free CPU MoE expert dispatch. Compounds with already-shipped CPU2 +31.8% (1t) / +1-3% (12-96t) wins.
- [intake-470] Tutel (arXiv:2206.03382, Microsoft Research, MLSys 2023) -- 2026-04-26: **2DH (two-dimensional hierarchical) all-to-all** aggregates intra-node small-message expert dispatches first, then inter-node exchange. Adaptive parallelism on a unified parameter layout. Anchors CPU19 backlog item: port 2DH to CPU15 inter-process EP shared-memory ring for the 4-NUMA-node × 12-CCD topology. Target: reduce ~96 sync points/token to ~24, addressing measured REAP-246B (-53%) and MiniMax-M2.7 (-23%) regressions on >150B MoE while attribution remains open. Phase 3.4 candidate in [`large-moe-expert-parallelism.md`](../handoffs/active/large-moe-expert-parallelism.md).
- [intake-471] Expert Choice Routing (arXiv:2202.09368, Google, NeurIPS 2022) -- 2026-04-26: **filed not_applicable**. Inverts dispatch (experts pick top-k tokens vs token picks top-k experts) for perfect load balance with no auxiliary loss. Three independent reasons: (1) training-time choice — our stack does no pre-training; (2) all production MoEs ship token-choice routers, cannot retrofit without retraining; (3) load-imbalance is largely absent on single-user CPU decode. Filed as literature reference only.

## 2026-05-04 Update — Probe B closes 122B-A10B + REAP-246B arch classes; opposite verdicts

### Qwen3.5-122B-A10B Q4_K_M — moe_q4_bw_bound_mbind_sensitive (NEW arch class)

Probe B (2026-05-04) closed the `architect_general` slot in v5 deployment draft (was `todo_or_undecided`). Single-instance 96t canonical, 4 configs × n=5:

| Config | avg t/s | σ % | Δ vs c0 | z |
|---|---|---|---|---|
| c0 default v5 | 12.041 ± 0.037 | 0.31% | baseline | — |
| c1 CPU1 stack | 12.065 ± 0.024 | 0.20% | +0.21% | 0.7 |
| **c2 mbind off** | **12.195 ± 0.051** | 0.42% | **+1.28%** | **3.0** |
| c3 c1+c2 | 12.048 ± 0.082 | 0.68% | +0.06% | 0.1 |

c2 (`GGML_NUMA_REPACK_INTERLEAVE=0`) wins +1.28% at z~3. CPU1 stack net-neutral; the two levers interact destructively (c3 = c1+c2 drops back to noise). Arch class: `moe_q4_bw_bound_mbind_sensitive`. Closest analogue is the Q8 frontdoor family (where mbind-off was +6%), distinct from Coder-30B "MoE Q4 sync-bound" (c1 wins +1.8%) and from REAP-246B "MoE Q4 DRAM-bound" (mbind-tolerant).

The mechanism: auto-mbind(MPOL_INTERLEAVE) on the CPU_REPACK buffer (Q8 8×8 NUMA fix, Session 15) is calibrated for some MoE classes but mildly hurts this one. With mbind disabled, weights spread via `numactl --interleave=all` first-touch — still distributed but via the kernel's default-interleave path. Mechanism still under investigation.

The bigger finding was production-wiring: 1× canonical 96t at 12.19 t/s vs production 2× cross-NUMA at 4.3 t/s/instance = **+184% per-request latency** unused. Wiring change LANDED in `epyc-orchestrator` commit `64101fd` (numa_instances 2→1, numa_ports `[8083,8183]→[8083]`).

Source: [data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/findings.md](../../epyc-inference-research/data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/findings.md), [findings_phase2.md](../../epyc-inference-research/data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/findings_phase2.md).

### REAP-246B-A35B Q4_K_M — moe_q4_dram_bound CONFIRMED

Probe B (2026-05-04) for `architect_coding` validates the v5 draft's existing `arch_class: moe_q4_dram_bound` + `env: {}` assignment. Same protocol as 122B:

| Config | avg t/s | σ % | Δ vs c0 | z |
|---|---|---|---|---|
| **c0 default v5** | **6.351 ± 0.003** | 0.05% | baseline | — |
| c1 CPU1 stack | 6.337 ± 0.005 | 0.08% | -0.23% | 2.49 |
| c2 mbind off | 6.361 ± 0.007 | 0.11% | +0.14% | 1.20 |
| c3 c1+c2 | 6.360 ± 0.005 | 0.09% | +0.14% | 1.40 |

All configs within ±0.25% — Probe B "all within ±2%" decision triggers "default v5". CPU1 stack mild distinguishable regression matches the existing CPU22 -0.8% noise observation. mbind-off non-significant uplift.

**Opposite verdict from 122B-A10B**: REAP is genuinely DRAM-bound; auto-mbind path is calibrated correctly for this class. The `moe_q4_dram_bound` v5 assignment stands.

Phase 2 wiring revalidation NOT pursued — RAM headroom precludes 4× per-NUMA-node (138 GB × 4 > per-node 290 GB budget); without a Phase 1 winning lever, Phase 2 has nothing to scale.

Source: [data/cpu_optimization/2026-05-04-reap246b-arch-probe/findings.md](../../epyc-inference-research/data/cpu_optimization/2026-05-04-reap246b-arch-probe/findings.md).

### Implication for arch-class taxonomy

Three distinct MoE Q4 sub-classes now empirically validated:

| Sub-class | Representative | Winning config | Why |
|---|---|---|---|
| **moe_q4_sync_bound** | Coder-30B-A3B | CPU1 stack (3-flag stable) +1.8% | barrier overhead is rate-limiting |
| **moe_q4_dram_bound** | REAP-246B-A35B | default v5 (no opt-in) | DRAM channels saturated; no software lever helps |
| **moe_q4_bw_bound_mbind_sensitive** | Qwen3.5-122B-A10B | mbind off (c2) +1.28% | auto-mbind calibration mismatched for this expert dispatch pattern |

The taxonomy is determined empirically per Probe B; do NOT assume a new MoE Q4 model fits one of these classes without measurement. The 35B-A3B is its own class (MoE Q8 BW-bound frontdoor, EP stack +17%).
