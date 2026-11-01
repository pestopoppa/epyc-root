# ws58 2026-10-31 dive record: w2_kern

Markdown rendering of `w2_kern.yaml` (the original is kept beside it) so the wiki scanner sees this dive. Intake IDs are as the dive recorded them; read them as `#record` references. Digit runs of 12+ digits are written grouped.

```yaml
# Wave w2, group kern. Sources: intake-2588 PTXBench, intake-2589 CAKE, intake-2590 AKV.
# CAKE (2608.12629) is referenced at research/intake_index.yaml:100117 (inside the block that awk attributes to intake-1218, whose own
# title/key_claims do not match; entry attribution of that line is unverified - it is NOT an entry of its own). Dedup: 2608.17379, 2608.12629,
# 2610.28577 and thu-nics/AKV have no own entry in the index (grep count 0 for 2610.28577; 2608.* only as that one reference).
entries:
- id: intake-2588
  verification: dive-verified
  read_depth: PARTIAL
  source_revision: 'arXiv:2608.17379v3 HTML sha256-12 e4ff90e61063, retrieved 2026-10-31 (v3 dated 28 Sep 2026)'
  source_text_path: scratch:dive-ws58-20261031/dive/w2kern/ptx.txt
  key_claims:
  - 'PTXBench scores LLM-written CUDA kernels with inline PTX (CUDA-PTX) on BF16 GEMM and attention (MHA fwd/bwd, causal) on H100 and B200 along three separate axes: functional correctness, runtime execution of the required PTX instruction family (via Nsight Compute SASS counts), and speedup vs frontier libraries (cuBLAS/cuDNN/FlashInfer). Kernels are written from scratch in an 8-call multi-turn loop (MiniPTXAgent).'
  - 'No evaluated model (Gemini 3.1 Pro, Claude Opus 4.8, GPT-5.6 xhigh, GLM-5.2, Qwen3.6-27B) consistently matches frontier libraries. Best library-relative figures in the text: GEMM on Blackwell 1.012x cuBLAS (Claude Opus 4.8) and 0.892x (Gemini 3.1 Pro). Attention backward success rates are low and executing the target instruction does not imply competitive speed. Qwen3.6-27B (the open model closest to our stack) produces no correct Hopper kernel.'
  - 'CORRECTED (stage-1 framing "Triton vs PTX token efficiency" is NOT in the paper): the paper compares Triton vs CUDA-PTX on Fast_p/peak speedup, not tokens. Triton is more reliable on attention, especially B200 (Gemini: Triton 0.514x on MHA-Bwd vs 0.198x CUDA-PTX; no correct CUDA-PTX MHA-Bwd-Causal kernel vs 0.437x Triton). On H100 GEMM peaks are close (0.991x vs 0.962x). With GPT-5.6 Sol some CUDA-PTX single-kernel peaks exceed Triton. Conclusion: high-level DSLs stay useful on new architectures.'
  - 'The only token-cost number is agent-harness vs plain refinement: Antigravity (Gemini 3.1 Pro) uses 3.32-5.06x the median total tokens of multi-turn refinement and is WORSE on all four attention workloads (e.g. MHA-Bwd 0.053x vs 0.240x; MHA-Bwd-Causal 0.000x vs 0.166x), better only on GEMM (0.583x vs 0.505x). Same direction for Codex/GPT-5.6 Sol (appendix, not read in full).'
  - 'Correctness method: shape+dtype check then torch.allclose with atol=rtol=1e-2; CUPTI latency (median of 50 iterations after 10 warmup); a memory-safety/sanitizer step inside an isolated profiling service; including cuBLAS/cuDNN headers is auto-fail. They explicitly did NOT run Compute Sanitizer racecheck (cost >1000x native; false negatives remain). Runtime-instruction check uses NCU predicate-enabled thread-execution counts; static SASS presence is not accepted; NCU failures count as unknown (conservative).'
  - 'Failure modes: without the 20k-30k-token architecture knowledge pack (parameters, PTX wrappers, layout/sync/memory-consistency contracts) the model rarely uses the requested PTX (Table 4 ablation: params alone gives 26.0% correct turns and zero target-instruction successes; adding the contract adds 18.7 points of target-instruction correctness over templates alone). Fixit SFT (Qwen3.6-27B LoRA, Gemini 3.1 Pro repair teacher) shifts failures from compilation to runtime/numerical errors and generalises unevenly; weaker reasoning teacher (Qwen itself) solves only GEMM vs all five problems with GLM-5.2 rationales.'
  reported_results:
  - 'Abstract / Sec 4.2: GEMM Blackwell 1.012x cuBLAS (Opus 4.8), 0.892x (Gemini 3.1 Pro)'
  - 'Sec 4.3: Gemini H100 GEMM peak Triton 0.991x vs CUDA-PTX 0.962x; B200 MHA-Bwd 0.514x Triton vs 0.198x CUDA-PTX; MHA-Bwd-Causal 0.437x Triton vs no correct CUDA-PTX'
  - 'Table 3 (H100, 8 evaluator requests, median of 4): refinement 0.505/0.584/0.560/0.240/0.166x vs Antigravity 0.583/0.425/0.413/0.053/0.000x (GEMM/MHA-Fwd/Fwd-Causal/Bwd/Bwd-Causal); token ratio 3.32/5.06/3.90/3.73/3.52x'
  - 'Sec 4.5 Table 4: params-only 26.0% turn correctness, 0 target-instruction; contract adds 38.5% target-inst correctness (18.7 points over templates alone)'
  - 'Sec 5.3: s1 Triton transfer MHA-Fwd-Causal 0.238x to 0.632x, MHA-Bwd-Causal 0.043x to 0.331x while turn correctness falls on every workload'
  - 'Sec 5.4 / Table 5: retrieved repair notes alone give zero correct MHA kernels; correctness appears only when the fixed kernel is also in the prompt'
  - 'Sampling scale: four 8-turn trajectories x 3 prompt variants per cell (N=32 per cell in the main plots); single seed family, no error bars on Table 1'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'Abstract + Sec 2.1/2.2/A.2 describe the three axes and loop.'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'Abstract sentence; Sec 4.2 numbers; Qwen row in Table 1 is all dashes and Sec 4.2 text states no correct Hopper kernel.'}
  - {claim_index: 2, verdict: PARTIAL, evidence: 'Triton-vs-PTX comparison exists (Sec 4.3, Fig 3, Fig 13) but on Fast_p/peak, not token efficiency; token efficiency premise NOT-FOUND.'}
  - {claim_index: 3, verdict: CONFIRMED, evidence: 'Table 3 and Sec 4.4.'}
  - {claim_index: 4, verdict: CONFIRMED, evidence: 'Sec 2.2 and A.1.'}
  - {claim_index: 5, verdict: CONFIRMED, evidence: 'Sec 4.5, 5.3, Table 4.'}
  claim_anchors:
  - {claim_index: 1, locator: 'v3 abstract', quote: 'No evaluated model consistently matches frontier libraries across the suite.'}
  - {claim_index: 2, locator: 'v3 Sec 4.3', quote: 'high-level kernel languages remain useful for producing correct kernels on new architectures'}
  - {claim_index: 3, locator: 'v3 Sec 4.4', quote: 'Antigravity has a higher median on GEMM, while multi-turn refinement has a higher median on all four attention workloads.'}
  - {claim_index: 4, locator: 'v3 Sec 2.2', quote: 'compares values using torch.allclose with atol=rtol=1e-2'}
  - {claim_index: 4, locator: 'v3 App A.1', quote: 'We did not apply NVIDIA Compute Sanitizer’s racecheck because it is too slow'}
  - {claim_index: 5, locator: 'v3 Sec 5.3', quote: 'It also shifts failures from compilation toward runtime and numerical errors'}
  - {claim_index: 5, locator: 'v3 Sec 2.1', quote: 'without this context, the model rarely uses the requested PTX'}
  claim_corrections:
  - {claim_index: 2, effect: narrowed, note: 'Brief asked about Triton vs PTX token efficiency; paper measures correctness/speed distributions only. The only token figure is agent-harness vs refinement (3.32-5.06x).'}
  depends_on: []
  dive_corrections: 'Stage-1 framing about token efficiency of Triton vs PTX is not in the source. Real result: Triton wins on reliability for attention on new hardware, direct PTX occasionally wins single-kernel peak. The strongest transferable facts for AK are (a) the three-axis separation (correct vs mechanism-executed vs fast), (b) allclose at 1e-2 is the only value gate and racecheck was consciously skipped, (c) a plain multi-turn refinement loop beat a general coding-agent harness on attention at 1/3-1/5 the tokens. NVIDIA-only (H100/B200, nvcc, NCU, CUPTI); nothing was run on AMD.'
  reader_should_conclude: 'Cite as evidence that frontier LLMs do not reliably match vendor libraries when forced to hand-write architecture-specific kernels, that instruction-executed verification is a separate gate from correctness, and that knowledge-pack context is the dominant lever. Do NOT cite for Triton-vs-PTX token efficiency, and do not carry NVIDIA speedup numbers to gfx90a.'
  not_read: 'Appendix tables 9/10, A.3 profiling-service detail, A.5-A.7 prompt text, Fig 14, Sec 5.1-5.2 recipe-ablation detail beyond the sentences quoted.'
- id: intake-2589
  verification: dive-verified
  read_depth: PARTIAL
  source_revision: 'arXiv:2608.12629v1 HTML sha256-12 18aca4f8c7fe, retrieved 2026-10-31 (submitted 12 Aug 2026)'
  source_text_path: scratch:dive-ws58-20261031/dive/w2kern/cake.txt
  key_claims:
  - 'CAKE ("Compiler-Agent co-design for Frontier Kernel Evolution", NVIDIA/CMU, Ye, Chen, Ceze et al.) is an NVIDIA-GPU (Ampere-Blackwell) kernel-agent harness whose agents author a typed, hardware-explicit schedule IR (Cake IR; roles, declared resources, barriers, pipelines) instead of raw CUDA/PTX; lowering derives barrier addresses, phase bits, descriptors; the compiler returns localized diagnostics instead of a pass/fail bit.'
  - 'Harness stages: generate structurally distinct candidates, filter by IR construction checks, verifier hard gates (program safety = synchronization/ordering/memory hazards; hardware conformance; data consistency; schedule semantics) and a calibrated cost model BEFORE GPU time, then evaluate survivors against an external oracle with on-GPU correctness and CUPTI timing (L2 flushed); evidence is routed to candidate, verifier, cost model, or IR vocabulary.'
  - 'Matched clean-start Flash-KMeans on B200, 3 runs per arm, GPT-5.6-sol xhigh, 80M-token budget: Cake IR median best 1.144x [1.041,1.205] of tuned FlashML vs direct CUDA/PTX 0.928x [0.852,1.151]; plateau reached 3/3 vs 0/3; median active evolve time 1.89 h vs 3.73 h.'
  - 'Beyond the benchmark: agent-generated Kimi Delta Attention prefill reaches 2.05x geomean over official FlashKDA on six B200 BF16 shapes (bitwise correct on its validation contract, verified in Kimi-K3 serving under SGLang, FlashInfer PR #4262); dispatcher-backed KNN/KMeans families improve 1.42x-2.12x across more than 400 shapes; four kernel changes are upstream PRs.'
  - 'The harness is itself evolved: recurring failures (sanitizer reports, correctness mismatches, debugging logs) become verifier rules, IR primitives, cost-model calibrations, gated by corpus tests because an un-validated verifier rule can reject valid kernels. Numerical check compares outputs across different shapes and input distributions; final acceptance is end-to-end in the target framework.'
  reported_results:
  - 'Abstract / Table 2: Flash-KMeans 1.144x [1.041,1.205] (Cake IR) vs 0.928x [0.852,1.151] (CUDA/PTX); plateau 3/3 vs 0/3; active evolve 1.89 [1.02,2.33] h vs 3.73 [3.59,4.34] h; Cake IR mean crosses baseline by 55M tokens (Fig 5)'
  - 'Sec 5.1: KDA prefill 2.05x geomean vs FlashKDA (6 B200 shapes); KDA decode 1.14x geomean vs upstream FlashInfer over 30 shapes'
  - 'Abstract: KNN/KMeans dispatcher families 1.42x-2.12x across more than 400 shapes'
  - 'n = 3 runs per arm, one model, one workload for the controlled comparison; ranges overlap (CUDA/PTX max 1.151 > Cake IR min 1.041)'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'Abstract, Sec 2.2.'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'Sec 3.1 Table 1 and Sec 4.'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: 'Table 2 and abstract; note ranges overlap and n=3.'}
  - {claim_index: 3, verdict: CONFIRMED, evidence: 'Abstract and Sec 5.1.'}
  - {claim_index: 4, verdict: CONFIRMED, evidence: 'Sec 3.1, 3.2.'}
  claim_anchors:
  - {claim_index: 1, locator: 'v1 Sec 4', quote: 'generate structurally distinct Cake IR'}
  - {claim_index: 2, locator: 'v1 Sec 5 trajectory', quote: 'with median active evolve time of 1.89 versus 3.73 hours.'}
  - {claim_index: 4, locator: 'v1 Sec 3.2', quote: 'verifier rule without corpus validation can reject valid kernels.'}
  claim_corrections:
  - {claim_index: 2, effect: narrowed, note: 'Headline 1.144x vs 0.928x is a median of 3 runs on one workload with overlapping min/max; supports "typed IR + pre-compile verifier helps the agent", not a general speedup.'}
  depends_on: []
  dive_corrections: 'Brief did not know what CAKE is: it is an NVIDIA agent+compiler co-design paper, not a cache or caching technique. It is referenced in the index only as an id inside another entry (index line 100117). No public repo link found in the text read (only FlashInfer PRs for generated CUDA). All baselines and hardware are NVIDIA B200; no AMD result.'
  reader_should_conclude: 'Cite for the design pattern: give the kernel agent a typed representation plus cheap static verifier gates (synchronization/memory hazards) and a cost model that filter candidates before GPU time, and turn recurring failures into permanent checks under corpus tests. Do not cite the 1.144x/2.05x numbers as portable; do not claim code availability.'
  not_read: 'Appendices A-D (IR catalog, Table 3 architecture coverage, D.x per-kernel evolution), Sec 6 dispatcher detail, Sec 5 reproduction-of-known-kernels tables.'
- id: intake-2590
  verification: dive-verified
  read_depth: PARTIAL
  source_revision: 'github.com/thu-nics/AKV @ c567a42 (2026-10-21); paper arXiv:2610.28577v1 HTML sha256-12 720743b692be, retrieved 2026-10-31 (submitted 20 Oct 2026)'
  source_text_path: scratch:dive-ws58-20261031/dive/w2kern/akvp.txt
  key_claims:
  - 'AKV / "Cache Engineering for Agents" (Tsinghua NICS; Tianyu Fu is also the C2C first author) lets the agent harness directly control the ACTIVE KV cache of a long agent loop with two extra cache operations beyond append: drop (exclude selected messages KV, typically old tool responses, from future attention) and repos (re-rotate retained keys with RoPE so positions are compacted), without editing the text trajectory and without re-prefilling retained context.'
  - 'CORRECTED: it is NOT cross-agent KV transfer and not C2C-style semantic communication; it is single-agent cache editing. The README/paper tie to C2C is only shared authorship/lab (README Related Projects).'
  - 'Serving challenge: cache state is history-dependent (same token prefix can have different KV under different drop/append orders), so plain prefix matching is insufficient. AKV (built on SGLang) uses a stateless OpenAI-compatible request with drop_message and reposition fields, an extended radix tree keyed by token plus operation history, drop-aware eviction, and segment-batch attention to restore evicted segments in one prefill pass.'
  - 'Agent results (3 models: MiniMax-M2.7, GPT-OSS-120B, MiroThinker-1.7-Mini; 4 benchmarks BCP, xbench-DS, GAIA-Text, SWE-Verified): rolling-drop of tool-response KV (keep latest 12) lowers cost 27.7% vs threshold-triggered summarization (Standard) and 21.9% vs lower-threshold Text Engineering, and raises average success 1.3-2.1% over Standard per model; cost is an API-price-table estimate from active tokens (Groq / MiniMax / Qwen3-30B-A3B rates), with repos charged at cache-hit rate, not measured spend.'
  - 'Serving results (GPT-OSS-120B, Top-80 SWE-Verified, 8x A800 80GB BF16, 4 prefill + 4 decode GPUs, TP4): at peak-throughput settings AKV (C=14) vs Standard (C=12) gives 1.18x output and 1.53x input throughput and 1.36x mean / 1.51x P95 request latency speedups. RSI-searched policies cut cost a further 7.1% (held-out; iterations 3 and 6 are 15.6% and 17.8% below Standard on 100 held-out BCP tasks). repos lifts BCP pass rate 55% to 62% by removing a position limit.'
  - 'Limits stated by the authors: supported architectures are softmax-attention text models (Qwen, Qwen2/2.5, Qwen3 incl MoE, GPT-OSS, MiniMax-M2 family); extending to linear-attention models is future work. Dropping reasoning KV hurts pass rate vs tool-response-only drop.'
  reported_results:
  - 'Abstract / Sec 1: -27.7% cost, +1.7 points avg score vs threshold summarization; 1.2x output throughput, 1.5x P95 latency; RSI -7.1%'
  - 'Sec 5.2: cost -27.7% vs Standard, -21.9% vs Text Engineering; success +1.3-2.1% and +0.9-8.7% vs the two baselines'
  - 'Table 2 (Sec 5.2): 1.36x mean, 1.51x P95 latency; 1.53x input, 1.18x output throughput at respective peak settings'
  - 'Sec 5.3 ablation: repos raises BCP 55% to 62%; dropping reasoning cache lowers pass rates'
  - 'Fig 14 (introduction): KV cache reads are 82.4% of total API cost in their accounting'
  - 'Table 7 (GPT-OSS-20B): AKV avg pass rate 45.2%, avg cost 4.8 cents'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'Abstract and Sec 3.'}
  - {claim_index: 1, verdict: OVERTURNED, evidence: 'Stage-1 expanded_from framing as C2C follow-up with cross-agent KV is not in README or paper; link is shared authorship only.'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: 'Abstract, Sec 4, README System section.'}
  - {claim_index: 3, verdict: PARTIAL, evidence: 'Numbers confirmed; cost is price-table-derived and uses summarization baselines, so it measures the avoided summarization/re-prefill economics, not llama.cpp slot behaviour.'}
  - {claim_index: 4, verdict: CONFIRMED, evidence: 'Sec 5.2 Table 2 text, Sec 5.3.'}
  - {claim_index: 5, verdict: CONFIRMED, evidence: 'README Supported Models; Limitations paragraph.'}
  claim_anchors:
  - {claim_index: 0, locator: 'arXiv:2610.28577v1 abstract', quote: 'agents can proactively use'}
  - {claim_index: 2, locator: 'v1 Sec 1', quote: 'the same token prefix and retained positions can result in different cache states under different cache operation histories.'}
  - {claim_index: 3, locator: 'v1 Sec 5.2', quote: 'AKV also reduces inference cost by 27.7% relative to Standard and 21.9% relative to Text Engineering'}
  - {claim_index: 4, locator: 'v1 Sec 5.2', quote: 'Input and output throughput are 1.53'}
  - {claim_index: 5, locator: 'v1 Limitations', quote: 'extending serving support to linear attention models remain future work.'}
  claim_corrections:
  - {claim_index: 1, effect: reattributed, note: 'AKV is single-agent KV drop/reposition cache editing in a serving engine; no cross-model or cross-agent KV transfer. Do not cite as C2C evidence.'}
  depends_on: []
  dive_corrections: 'Stage-1 expansion premise (cross-agent KV) overturned. Substance is more relevant than expected for the orchestrator agent loop (tool outputs dominate context; summarization/trim invalidates the prefix), but the mechanism needs mid-sequence KV removal plus RoPE position shift, which llama.cpp already has as llama_memory_seq_rm and seq_add for full-attention models and which is unsafe for recurrent/hybrid GDN memory. Gains are measured on SGLang with A800 BF16 and price-table costs; nothing was measured on llama.cpp.'
  reader_should_conclude: 'Cite for the idea and for the history-dependence correctness hazard (prefix match is not enough once KV is edited). The 27.7%/1.5x numbers are SGLang + API-price accounting versus summarization baselines; they are not a predicted gain for llama-server and not for hybrid/linear-attention models.'
  not_read: 'Appendices A.1.1 kernel details, A.3 (segment-batch attention math beyond summary), A.4 cost breakdowns, A.5 concurrent work, Table 1 per-cell numbers, repo code beyond file listing and README (akv/system/sglang/srt/context_system/* not read).'
new_entries:
- id: intake-2588
  arxiv_id: '2608.17379'
  url: https://arxiv.org/abs/2608.17379
  source_type: paper
  title: 'PTXBench: Evaluating and Adapting LLMs for GPU Kernel Optimization with Architecture-specific PTX'
  categories: [hardware_optimization, benchmark_methodology, autonomous_research, tool_implementation]
  novelty: medium
  relevance: medium
  discovered_via: expansion
  expanded_from: intake-2555
  verdict: adopt_patterns
  ingested_date: '2026-10-31'
  authors: [Genghan Zhang, Yixin Dong, Chengze Fan, Zhichen Zeng, Yueming Yuan, Shaowei Zhu, Kunle Olukotun]
  key_claims: ['see entries record intake-2588']
  techniques: [instruction-executed verification via NCU SASS counts, architecture knowledge pack in prompt, multi-turn refinement vs coding-agent harness, repair-conditioned SFT (Fixit), Fast_p with target-instruction restriction]
  reported_results: ['see entries record intake-2588']
  cross_references: {chapters: [], handoffs: [agentic-rocm-kernel-authoring.md, autokernel-research-loop.md], experiments: [], intake_entries: [intake-2555]}
  recommended_actions: ['see ledger rows KERN-1, KERN-2']
  credibility_score: 4
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: 'NVIDIA-only (H100/B200). Authors from Stanford/CMU/RadixArk. Code announced at github.com/zhang677/PTXBench (not cloned). Venue unknown (preprint, v3).'
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: 'arXiv:2608.17379v3 HTML sha256-12 e4ff90e61063'
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2589
  arxiv_id: '2608.12629'
  url: https://arxiv.org/abs/2608.12629
  source_type: paper
  title: 'CAKE: Compiler-Agent Co-Design for Frontier Kernel Evolution'
  categories: [hardware_optimization, autonomous_research, tool_implementation, agent_architecture]
  novelty: high
  relevance: high
  discovered_via: expansion
  expanded_from: intake-2555
  verdict: adopt_patterns
  ingested_date: '2026-10-31'
  authors: [Zihao Ye, Yingyi Huang, Hongyi Jin, Bohan Hou, Junru Shao, Zhongming Yu, Jinqi Chen, Meghan Cowan, Shiyi Cao, Shanli Xing, Hanfeng Chen, Vinod Grover, Tianqi Chen, Luis Ceze]
  key_claims: ['see entries record intake-2589']
  techniques: [typed hardware-explicit schedule IR, pre-compile verifier hard gates, calibrated cost model for candidate filtering, failure-to-verifier-rule compiler evolution, dispatcher-backed shape generalisation]
  reported_results: ['see entries record intake-2589']
  cross_references: {chapters: [], handoffs: [autokernel-research-loop.md, agentic-rocm-kernel-authoring.md, autokernel-rebuild-program.md], experiments: [], intake_entries: [intake-2555]}
  recommended_actions: ['see ledger rows KERN-3, KERN-4']
  credibility_score: 3
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: 'NVIDIA authors, NVIDIA-only targets, controlled comparison n=3. No repository link seen in the sections read.'
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: 'arXiv:2608.12629v1 HTML sha256-12 18aca4f8c7fe'
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2590
  arxiv_id: null
  url: https://github.com/thu-nics/AKV
  source_type: repo
  title: 'AKV: Cache Engineering for Agents (thu-nics/AKV)'
  categories: [kv_cache, agent_architecture, inference_serving, context_management]
  novelty: medium
  relevance: medium
  discovered_via: expansion
  expanded_from: intake-2559
  verdict: worth_investigating
  ingested_date: '2026-10-31'
  authors: [Tianyu Fu, Ruoxi Wang, Zihan Min, Zhongqi Ren, Zhihao Li, Tengxuan Liu, Shengxu Mu, Hanling Zhang, Yu Wang]
  key_claims: ['see entries record intake-2590']
  techniques: [KV drop of old tool responses, RoPE reposition of retained keys, history-aware radix tree, drop-aware eviction, segment-batch attention restore, cache-as-tool, recursive self-improvement of cache policies]
  reported_results: ['see entries record intake-2590']
  cross_references: {chapters: [], handoffs: [kv-prefix-fork-and-paged-attention.md, context-folding-progressive.md, tool-output-compression.md, streaming-llm-baseline.md], experiments: [], intake_entries: [intake-2559]}
  recommended_actions: ['see ledger rows KERN-5, KERN-6']
  credibility_score: 3
  contradicting_evidence: null
  referenced_arxiv_ids: ['2610.28577']
  notes: 'Companion paper arXiv:2610.28577 (title-checked on abs page: "Cache Engineering for Agents"); the paper is the same artifact family, filed here as the repo entry because the assigned source was the repo. Apache/other license not checked (LICENSE file present). SGLang-based; Rust build step.'
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: 'thu-nics/AKV @ c567a42'
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
ledger:
- row: KERN-1
  entries: [intake-2588]
  action: 'Add an instruction-executed gate to the AMD kernel-authoring path: when a candidate claims a mechanism (MFMA use, LDS staging, buffer/global load width), require a rocprof instruction-mix counter or ISA-disassembly execution check on the real workload before the claim counts; record failed profiling as unknown, not pass. Counter names to be confirmed on gfx90a (not asserted here).'
  grounding: 'handoffs/active/agentic-rocm-kernel-authoring.md (oracle/correctness gates, C5-3 correctness oracle at ~L888) has correctness + timing but no mechanism-executed axis; PTXBench Sec 2.2 shows correctness without target-instruction execution is common (Table 4: 26.0% correct, 0 target-inst).'
  owner: handoffs/active/agentic-rocm-kernel-authoring.md
  posture: cheap-screen-now
  benefit: 'Prevents AK keeps whose speedup is from a generic fallback rather than the intended mechanism; must stay correct: the check is a gate on claims, not a speed filter.'
  decision_rule: 'Screen: replay 10 existing AK keeps through the counter check (read-only, no new kernels). Promote to a standing gate if >=1 keep fails to execute its claimed instruction family; drop if all 10 pass and counters cost >2x a normal timed run.'
  reason: 'Cheap, read-only, and transfers the one portable idea of PTXBench.'
- row: KERN-2
  entries: [intake-2588]
  action: 'Compare AK candidate generation as plain multi-turn refinement vs agent-harness mode on token cost per accepted keep (PTXBench: agent harness cost 3.3-5.1x tokens and was worse on attention). Use existing AK run logs only; no new compute.'
  grounding: 'handoffs/active/autokernel-research-loop.md and autokernel-orchestrator-actor-backend.md use agent actors; no per-keep token accounting row found in the sections grepped.'
  owner: handoffs/active/autokernel-orchestrator-actor-backend.md
  posture: knowledge-only
  benefit: 'Informs actor budget allocation; not a basis to change the loop without our own data.'
  decision_rule: 'Revisit only if AK run logs already carry token counts per iteration; otherwise no work.'
  reason: 'One NVIDIA benchmark with 4 trajectories per cell; the direction is useful, the magnitude is not transferable.'
- row: KERN-3
  entries: [intake-2589, intake-2588]
  action: 'Close the verified AK gate gaps (no race detector, race_detector_id=None; no edge-value inputs; NMSE-only oracle) with a CAKE-style pre-GPU static filter tier: run the cheapest hazard/legality checks (LDS barrier ordering, wave64/exec-mask hazards from the sibling Volta symbolic executor in w1_kern) before a candidate consumes GPU time, and add an edge-value input family (zeros, denormals, +-inf, max-magnitude, sign-cancellation) to the correctness oracle. PTXBench explicitly skipped racecheck as >1000x cost; CAKE shows pre-compile hazard gates are the practical substitute.'
  grounding: 'out/w1_kern.yaml header L11-12 (wave-1 dive: execution/t0_provider.py:305-307 and :3662, race_detector_id=None; only race control is repetition to bit-identity, AKX-ALL-9; no edge-value families; NMSE oracle). agentic-rocm-kernel-authoring.md ~L748 shows the oracle surface is test-backend-ops max_nmse_err on init_tensor_uniform inputs.'
  owner: handoffs/active/autokernel-research-loop.md
  posture: primitive-now
  benefit: 'Fewer wasted GPU slots and fewer silently-wrong keeps; correctness must not regress: every new rule must pass the existing keep corpus (CAKE: an un-validated verifier rule can reject valid kernels).'
  decision_rule: 'Edge-value family: run over all existing keeps read-only; if any keep fails, treat as a defect and reopen that keep. Static filter: promote only if it rejects >=1 historically bad candidate and rejects 0 historical keeps.'
  reason: 'Two independent sources (CAKE gates, PTXBench skipped racecheck) point to the same missing tier; the edge-value part needs no new tooling.'
- row: KERN-4
  entries: [intake-2589]
  action: 'Failure-to-rule loop for AK: after each rejected batch, classify the failure reason and, when a class recurs (>=3), have an agent propose a permanent static check or oracle input, merged only under corpus tests of all prior keeps (CAKE Sec 3.2).'
  grounding: 'handoffs/active/autokernel-rebuild-program.md / autokernel-research-loop.md record abstention batches (e.g. AK-SERIAL-26 stopped with 36 abstention batches, research-loop L41) with no mechanism for turning repeated failures into new gates.'
  owner: handoffs/active/autokernel-rebuild-program.md
  posture: monitor
  benefit: 'Compounding gate quality; must stay correct via corpus-validated merges.'
  decision_rule: 'Start when KERN-3 lands a first static rule; stop if rules reject any historical keep twice.'
  reason: 'Depends on KERN-3 existing; premature otherwise.'
- row: KERN-5
  entries: [intake-2590]
  action: 'Bounded probe: tool-result KV drop+shift on a pure full-attention role in llama-server, using existing llama_memory_seq_rm + seq_add (as in the streaming-llm / context-shift path), on a recorded orchestrator agent trace. Measure (a) tokens re-prefilled per turn versus the current re-rendered-history path, (b) answer parity on a replayed trace with the tool results actually dropped vs summarized/trimmed. Restrict to non-hybrid models; hybrid GDN memory is unsafe for seq_rm/seq_add.'
  grounding: 'src/backends/llama_server.py:789 sends cache_prompt and id_slot is used on /completion only (serving_calls.py:739); streaming-llm-baseline.md already has seq_rm/seq_add context-shift controls (632ce0f92); autokernel-champion-aggregate.md CH-21 (L1058) documents that seq_add does not shift the recurrent tail and seq_rm on a recurrent tail can fail silently, so hybrid roles (Qwen3.5/3.6/3.8 family) are excluded; gemma4-26B worker is the candidate non-hybrid role.'
  owner: handoffs/active/context-folding-progressive.md
  posture: cheap-screen-now
  benefit: 'Lower per-turn prefill/TTFT in long tool loops without losing intermediate rounds; must stay correct on answer parity and positional coherence after shift.'
  decision_rule: 'Promote to a design pass only if (a) >=30% fewer re-prefilled tokens per turn on the trace AND (b) parity within noise on the replayed answers; otherwise record NO-GO and stop. Pair with context-folding arms rather than a new program.'
  reason: 'Mechanism exists in llama.cpp today; AKV supplies the policy design (rolling drop of latest-N tool results, reposition on a schedule) and the ablation (do not drop reasoning KV).'
- row: KERN-6
  entries: [intake-2590]
  action: 'Record the history-dependence correctness rule for any future KV-editing serving feature: a slot/prefix index keyed only by token prefix (src/inference/prefix_index.py) must also key on the drop/shift operation history, or mark the slot unmatchable after an edit. Add this as a constraint note on KPF-27 prefix index and slot save/restore (slot files restore tokens, not edit history).'
  grounding: 'src/inference/prefix_index.py (token-prefix index bound to id_slot via timings.id_slot, L78, L1328); kv-prefix-fork-and-paged-attention.md P2/KPF-22..27.'
  owner: handoffs/active/kv-prefix-fork-and-paged-attention.md
  posture: knowledge-only
  benefit: 'Avoids silently reusing a stale KV state after edit; no change until KERN-5 shows value.'
  decision_rule: 'Activate only if KERN-5 promotes.'
  reason: 'AKV names the exact failure (same tokens, different KV) that would break our prefix index.'
- row: KERN-7
  entries: [intake-2590]
  action: 'Decline porting AKV server (SGLang, Rust build, softmax-attention only) as a serving path; keep as design reference only. Hybrid/linear-attention models (our main Qwen line) are unsupported by the authors and by llama.cpp seq ops.'
  grounding: 'README Supported Models list; paper Limitations; CH-21 at autokernel-champion-aggregate.md:1058.'
  owner: handoffs/active/kv-prefix-fork-and-paged-attention.md
  posture: decline
  benefit: 'Avoids a parallel serving stack on an unmeasured gain.'
  decision_rule: 'Revisit if a non-hybrid champion role becomes the dominant agent-loop model.'
  reason: 'Technical constraint is real (recurrent state), so the workaround is KERN-5 in llama.cpp, not a port.'
dive_surfaced_sources:
- {source: 'https://github.com/zhang677/PTXBench (companion code, announced in PTXBench v3)', settles: 'whether the NCU target-instruction check and FlashInfer-Trace profiling service are reusable for an AMD instruction-executed gate', bears_on: intake-2588, recommend: 'ingest-and-dive'}
- {source: 'arXiv:2610.28577 (Cache Engineering for Agents; abs page title-checked)', settles: 'the AKV paper itself is the companion of intake-2590; covered in this dive from HTML but has no separate intake entry', bears_on: intake-2590, recommend: 'ingest-and-dive: file as its own paper entry so the repo and paper can be cited separately'}
- {source: 'FlashInfer PRs 4262/4279/4274/4287 (CAKE-generated kernels)', settles: 'whether CAKE-produced kernels are independently reproducible by upstream maintainers', bears_on: intake-2589, recommend: 'decline: NVIDIA-only kernels, no gfx90a bearing'}
artifact_audit: clean
```
