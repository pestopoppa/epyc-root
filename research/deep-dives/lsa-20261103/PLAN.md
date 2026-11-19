# D-LSA transplant feasibility and proposed filing — 2026-11-03

Stage 1/2 evidence collected; Stage 3 proposal, awaiting operator approval. No handoff or production changes applied. Three agents: 2 gpt-6.1-sol/high and 1 gpt-6.1-sol/medium. Source claims mean verified author reports, not local reproduction. Independent second reader confirmed frozen-base conversion, hybrid layer placement, timing scope and serving restrictions. Broader per-claim numerical anchor review remains bounded to the named tables; no independent replication found in the current contradiction search.

## Decision

Qwen3.8-27B is already demonstrated by the authors and has released PCA/distilled maps. Our work is a backend transplant and controlled validation, rather than new whole-model training. Qwen3.6-35B-A3B is a plausible extension with the same attention family, but needs its own teacher capture and maps. Never reuse 27B maps on 35B.

Both local GGUFs are hybrids: 27B has 48 GDN + 16 global attention trunk layers; 35B has 30 GDN + 10 global attention layers. Their query/KV head counts are 24/4 and 16/2, head dimension256; both use quarter-head RoPE. MoE FFNs and recurrent state stay intact. MTP is outside these trunk counts and requires a separate compatibility gate. Primary config evidence: https://huggingface.co/Qwen/Qwen3.8-27B/raw/main/config.json and https://huggingface.co/Qwen/Qwen3.6-35B-A3B/raw/main/config.json, retrieved 2026-11-03; local GGUF headers and frozen source corroborate the split.

The paper's 72.4x prefill and 42.5x decode gains time one attention module at10M, with prefill timing only the final32768-query chunk. Table3 whole-model H200 TP8/DCP8 gains reach9.21x TTFT and2.87x TPOT, with regressions at shorter lengths. None transfers to one MI210 or CPU. Lower TTFT/TPOT is better; quality/recall higher is better. Flat is still asymptotically quadratic; tree gives subquadratic indexing, but the evaluated single-request tree mode uses flat decode. Begin with flat.

LSA retains full KV storage. Derived BF16 attention KV alone is64KiB/token (27B) and20KiB/token (35B), about61.0GiB and19.1GiB at one million decimal tokens, excluding weights, GDN state, allocator and index. Thus one64GB MI210 cannot reproduce the authors'27B BF16 million-token setup. Budget shorter contexts or explicitly design and validate quantized KV/offload; CPU's large RAM permits larger storage but bandwidth and irregular gathers matter. These are engineering costs and capacity constraints, not an applicability decline.

As released, Qwen integration requires BF16 KV, page size1, no speculative decoding, no prefill context parallelism and no attention DP; prefill CUDA graphs must be disabled. Our Q8 KV and DFlash2/MTP serving path needs explicit implementation and correctness gates. CUDA/CuTe kernels require a gfx90a/CPU implementation; start with an inspectable reference and reuse existing sparse-row contracts. Do not import NVIDIA binaries or modify frozen production. D-LSA trains small projections with frozen base; N-LSA is a separate native-training design and is not needed for this transplant.

## Difficulty and cost envelope

Planning estimates, not measured quotes: reference-map reader and flat CPU prototype roughly1–2 engineer-weeks; full CPU+gfx90a experimental backend and request/cache lifecycle roughly4–8 engineer-weeks; quantized-KV plus speculative rollback/MTP integration another2–6 engineer-weeks, with overlap possible. The35B capture/PCA adapter is roughly1–2 additional engineer-weeks. Unknown GPU-hour cost for distillation must be measured with a small frozen pilot: the paper's352M tokens and48k sampled-query steps do not establish our cost. Full sparse continued training is a fallback option, not the default prerequisite. Quality recovery or backend debugging may exceed these ranges.

## Bounded deciding screen and six controls

Question: at production-relevant lengths, does flat semantic selection improve complete request latency enough to justify a port while preserving useful task quality? Implementation precedes a run-ready manifest; no inference is launched by this intake.

1. Freeze model/GGUF/source/map/tokenizer hashes, exact rendered token IDs, seeds, context extension, KV dtype, backend, device topology and effective configuration. Select32 development prompts across code retrieval, multi-hop reasoning, document QA and agent-history continuation, at8k/32k/128k/native262k where capacity permits. Freeze32 disjoint held-out prompts before tuning. Keep every item in the denominator; unavailable cells are explicit invalid results.
2. Baseline: current exact-model dense global attention with identical context scaling, precision and batching; compare all-keys oracle, PCA-flat and distilled-flat. Match speculation off initially in both arms; current production recipe is a separate baseline before activation. Avoid crediting quantization or disabling speculation to LSA.
3. Persist per-item raw outputs, prompt token IDs, scores, selected-index budgets, TTFT, TPOT, peak memory, index/clustering time and effective configuration. Capture own PID residency and ggml linkage during GPU runs. Keep full failure/invalid/timeout/abstention counts.
4. Tune only development data; evaluate held-out once, and repeat timing in a later reserved window. Report individual task groups and model/device/length cells, never pool away regressions.
5. Predeclare screening quality guard: no new failures on exact retrieval sentinels and no more than one additional failure per32 held-out items relative to dense, reported as a screening rule, not equivalence proof. Seek at least10% end-to-end TTFT reduction with TPOT regression no worse than5% at a useful length; timings need enough repeats to distinguish this from spread. Start3 paired timing repetitions, cap7 if direction unresolved. Inconclusive cells stay inconclusive.
6. Stop on answer or futility: parity defect stops affected arm; capacity fault records invalid and stops that cell; exhausted timing cap does not authorize more unbounded runs. Broader training/tree/concurrency reproduction triggers only after quality and end-to-end crossover pass for a target cell. Run concurrency1 first, then production-shaped concurrency4 only when memory permits. Current screen is diagnostic, not a formal promotion/significance gate.

## Ownership, scope and dependencies

Inspected scope: two source trees, four conversion comparators, current target metadata, qwen35/qwen35moe global-attention dispatch, long-context, architecture-readiness, ROCm and belief owners at root49854e2606; not a full inventory of every attention backend. Consumers: direct27B/35B serving; evidence evaluator; prospective routing/concurrency and kernel promotion; policy/production freeze. No consumer receives duplicate work merely for visibility. Existing DSA sparse kernels and KV row gathers are dependencies, not proof LSA already exists. Existing literature adapter covers intake evidence; the experiment needs producer-side native capture. Independent implementation lanes are map/capture and backend reference; empirical execution waits for capture plus reference parity.

## Work packets

| Packet | Action | Owner |
|---|---|---|
| P1 | Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210. | handoffs/active/long-context-program.md |
| P2 | Add frozen-teacher capture for Qwen3.6-35B-A3B and generate model-specific PCA projections for its ten global layers, with exact GQA/head aggregation and RoPE-free coordinate tests; run the same bounded screen and estimate full distillation only from a timed extraction/training pilot. | handoffs/active/model-architecture-readiness.md |
| P3 | Implement experimental CPU AVX512 and gfx90a flat-index selection plus indexed exact attention using existing row-gather contracts where suitable; retain full KV and validate request isolation, causal masks, partial clusters, slot reuse and dense fallback. Quantized-KV and MTP/DFlash2 parity require separate integration gates before serving activation. | handoffs/active/rocm-kernel-authoring.md |
| P4 | Before the first conversion screen, register its native result producer in scripts/vidya/adapters/README.md and project complete raw-run identity, effective configuration, failures and decision records through the existing measurement ladder; require a planning-context canary, without inventing a new grading rule. | handoffs/active/vidya-belief-substrate-program.md |
| P5 | Repair intake validation of historical handoff references after the approved backlog folds: resolve old filenames only through an unambiguous committed fold mapping to an existing owner and Track heading; reject unknown, ambiguous and dangling targets. Apply the same resolution to index and cross-reference-map checks, add focused moved/missing/ambiguous tests, and require the full intake validator to exit zero before closing this campaign. | handoffs/active/knowledge-pipelines.md |
| M1 | Tree hierarchy only after flat indexing dominates measured useful-context latency; no active task. | handoffs/active/long-context-program.md |
| M2 | Native training only after an explicit training objective or demonstrated frozen-map recovery need; no active task. | handoffs/active/long-context-program.md |

Screen controls also require budget-matched oracle top-k and positional/window-only selection, attention-mass/top-key recall, and held-out documents excluded from PCA fitting. These diagnose whether semantic selection adds value beyond locality. Distilled35B training starts only after a timed teacher-capture pilot and a held-out PCA result justify it. Quantized KV and speculative serving are separate paired arms, with draft acceptance and prefix rollback correctness recorded before activation.

## Verified sources and wave close-out

Three bounded waves closed: seed/configuration verification; reference selection; deep verification of four conversion comparators. No new sources are left selected and undived. Remaining source discovery is outside this completed scope, not a missing-software blocker. Stage1 expansion4/10.

### intake-2622 — Latent Sparse Attention: Towards Subquadratic Ultra-Long Context Attention

https://arxiv.org/abs/2610.42147 — revision arXiv:2610.42147v1; 2026-10-30; CC BY 4.0; read depth FULL.

- D-LSA learns separate low-dimensional query/key index projections, with the base model frozen. The attention itself still uses original Q/K/V over selected indices. It directly converts Qwen3.8-27B in this paper; Qwen3.6-35B-A3B is not an evaluated model. Evidence: https://arxiv.org/html/2610.42147v1#S3.SS3.
- Equation (1): k_idx=k_attn W_K; q_idx=sum_h q_attn,h W_Q; index vectors L2-normalized. All query heads share one index list. Qwen3.8 indexing reads only the RoPE-free 75% of each head. PCA leading key directions initialize both projections and also supply the training-free variant. Evidence: https://arxiv.org/html/2610.42147v1#S3.SS3.
- Equation (2) minimizes forward KL(A_teacher || A_indexer) over long-range eligible keys. Teacher softmax is normalized per head then averaged. Actual training retains/renormalizes teacher top-2048 keys, while indexer softmax spans all eligible keys. Per-layer temperature is calibrated before training and used only in distillation. Evidence: https://arxiv.org/html/2610.42147v1#S4.SS1.
- Distillation uses 352M document tokens, documents 16k–1M, 48k steps with 128 sampled queries per document-step, LR3e-4. Only projections and temperature train. No subsequent whole-model sparse fine-tuning was performed. This is not evidence of full-model retraining being necessary. Evidence: https://arxiv.org/html/2610.42147v1#S4.SS1.
- LongDocs covers seven domains. 13.1% of distillation tokens are in-house agent traces; public sources include Common Pile releases, The Stack Python/Java repositories, and Open-SWE-Traces. Each sequence stays within one document; 2% held out. The 1M length gets quadruple ordinary-length token allocation and ~one-third total mix. Evidence: https://arxiv.org/html/2610.42147v1#A3.
- D-LSA Qwen settings: index dimension64; pool4; cluster block512; average bucket8/max16; long-range budget4096 plus4 sinks and512-token window; top1024 buckets. Ward merging stops at64 buckets per block. Selected buckets expand into token indices without deleting the stored KV cache. Evidence: https://arxiv.org/html/2610.42147v1#S4.SS1.
- Only tree search gives the indexer O(T log T) prefill / O(log T) centroid scoring per query at constant beam. Flat search remains asymptotically quadratic in prefill. Once constructed each cluster block is immutable. Tree uses bottom-up bucket hierarchy and beam search. Evidence: https://arxiv.org/html/2610.42147v1#S3.SS2.
- At 10M Qwen tokens D-LSA flat scores RULER63.9 vs full-attention59.9, PaperTrail29.1 vs19.8. This is authors’ task evidence beyond advertised model context, not proof of uniformly preserved reasoning or scientific-work quality at10M. Evidence: https://arxiv.org/html/2610.42147v1#S4.SS2.
- On GLM tree loses more accuracy beyond1M: RULER55.8 vs flat66.8 at10M. Training-free PCA remains close to distilled flat on Qwen, but trails distilled flat on GLM. Evidence: https://arxiv.org/html/2610.42147v1#S4.SS2.
- The headline Qwen72.4x prefill/42.5x decode and GLM22.7x/4.6x compare a single global attention module on H200 at10M. Prefill times only the last32768-query chunk, decode one request-step with CUDA graph and amortized clustering. They are not whole-model speedups. Evidence: https://arxiv.org/html/2610.42147v1#S4.SS3.
- Qwen end-to-end H200 TP8+DCP8 at10M: flat TTFT9.21x and TPOT2.87x against full attention. Baseline4582.2s TTFT/32.1ms TPOT. At512k flat TTFT1.03x/TPOT0.87x; at1M1.51x/1.00x. On B300 flat at512k0.68x/0.63x,1M0.96x/0.73x,10M5.73x/1.46x. Ratios below1 are regressions. Evidence: https://arxiv.org/html/2610.42147v1#S4.SS3.
- Reported whole-model latencies are medians of3 requests, one request at a time,256 output tokens. Tree runs flat search during single-request decode. Scaling beyond10M to100M is an extrapolation; tree prefill is predicted to overtake flat only beyond10M. Evidence: https://arxiv.org/html/2610.42147v1#S4.SS3.
- N-LSA is a separate native-training design: no index projections, one KV head, per-bucket score=max_h(normalized q_h dot centroid), stop gradient through selection, NTP-only learning. It adds no parameters and uses no positional encoding in evaluated models. It is not the conversion path for existing Qwen models. Evidence: https://arxiv.org/html/2610.42147v1#S3.SS4.
- N-LSA evidence is ~0.5B hybrid24 layers (6 attention,18 Gated DeltaNet),100B tokens at4k plus12B at128k. Flat search only. At128k validation loss1.085 equals full attention, attention forward/backward1.6x, whole decay phase1.24x, layer peak memory6.8GiB vs5.8GiB. Larger-model/tree training remains untested. Evidence: https://arxiv.org/html/2610.42147v1#S4.SS4.
- LSA preserves the full KV cache, so storage still grows linearly with context. At10M GLM each CP8 rank holds1.25GiB of the10GiB per-layer KV cache plus the complete246MiB bucket cache. Replicating the bucket cache trades memory for communication. Evidence: https://arxiv.org/html/2610.42147v1#S3.SS3.
- Evaluation uses subsets: MMLU-Pro2000, MATH500100, LongBench-v2 60, RULER100 prompts/task through1M then20/task beyond. PaperTrail has3 domains,90 scored questions repeated3x, and fabricated trails embedded in recent scientific papers. It is a controlled retrieval/linking benchmark, not observed autonomous scientific research. Evidence: https://arxiv.org/html/2610.42147v1#A5.SS1.
- PaperTrail10M contains some papers posted up to6 weeks before model release, while through5M papers postdate both releases. Thus the main-text almost-all-unseen framing is defensible but absolute no-training-exposure at10M is not established. Evidence: https://arxiv.org/html/2610.42147v1#A4.
- Qwen10M evaluation changes context handling with YaRN factor40 (42 for PaperTrail). Such results combine sparse attention and context extension; native context is not10M. Evidence: https://arxiv.org/html/2610.42147v1#S4.SS1.
- The paper describes CuTe DSL kernels specifically for H200/B300 and a Triton implementation not tied to these GPUs. This does not establish tested MI50/gfx906 correctness or speed. Such a backend is a build/validation task, not a technical reason to decline the approach. Evidence: https://arxiv.org/html/2610.42147v1#A6.SS1.
### intake-2623 — Latent Sparse Attention reference implementation

https://github.com/Prefrontal-AI/latent-sparse-attention — revision 97b82d695b74ca341965a16bbc2a951c8b0c567a; read depth PARTIAL.

- The released Qwen path preserves recurrent layers and changes global attention selection; its current integration requires BF16 KV and refuses speculative decoding. Evidence: src/lsa/sglang/models/qwen3_5/backend.py:125-134,265-305.
- Published Qwen3.8-27B PCA/distilled projection artifacts cover 16 full-attention layers; Qwen3.6 requires separate model-specific projections. Evidence: README.md:210-230; release d-lsa-weights-v1; safe artifact ZIP/pickletools inspection.
### intake-2624 — SeerAttention: Learning Intrinsic Sparse Attention in Your LLMs

https://arxiv.org/abs/2410.13276 — revision 2410.13276v4; read depth PARTIAL.

- Learns pooled block attention gates through frozen-model self-distillation. Gate ground truth uses customized FlashAttention max-pooling rather than materializing dense attention maps. Evidence: https://arxiv.org/html/2410.13276v4#S3.SS2.
- Reported gate recipe: RedPajama64k chunks,500 steps, batch16, LR1e-3 cosine,40 A100 hours. This is a separate method/model recipe, not a cost estimate for D-LSA. Evidence: https://arxiv.org/html/2410.13276v4#S4.SS0.SSS0.Px2.
- Appendix A.2 initializes gates through self-distillation before whole-model YaRN fine-tuning with cross-entropy plus gate loss. Evidence: https://arxiv.org/html/2410.13276v4#A1.SS2.
### intake-2625 — HashAttention: Semantic Sparsity for Faster Inference

https://arxiv.org/abs/2412.14468 — revision 2412.14468v2; 2025-06-03; read depth PARTIAL.

- Independent learned Q and KV mappings produce32-bit Hamming signatures; bitwise scores still scan cached token signatures before sparse token attention. Evidence: https://arxiv.org/html/2412.14468v2#S4.SS1.
- Training labels use high isolated-token contribution accounting for attention weight and value magnitude, rather than D-LSA averaged-attention KL. Uses classification/BCE and top64 labels. Evidence: https://arxiv.org/html/2412.14468v2#S4.SS2.
- Quality evaluation distinguishes generic training (up to16x token reduction) from task-specific tuning (up to32x). CPU-resident cache/ultra-long offloading not evaluated. Evidence: https://arxiv.org/html/2412.14468v2#S5.SS1.
### intake-2626 — InfLLM-V2: Dense-Sparse Switchable Attention for Seamless Short-to-Long Adaptation

https://arxiv.org/abs/2509.24663 — revision 2509.24663v1; 2025-09-29; read depth PARTIAL.

- Reuses dense QKV with no new trainable parameters; unions selected and local blocks into single attention output and drops compressed-attention output. Parameter-free multistage pooling selects blocks. Evidence: https://arxiv.org/html/2509.24663v1#S3.SS2.
- Trains8B standard GQA model with32 query heads/2 KV heads, head dimension128; long-sequence fine-tuning5B tokens across0–32k with four balanced length bands. Evidence: https://arxiv.org/html/2509.24663v1#S3.SS3.
- Dense/sparse mode can switch by length to avoid selector overhead. Official recipe has GQA group16; Qwen38/36 groups6/8 differ and require adaptation. Evidence: https://arxiv.org/html/2509.24663v1#S3.SS4.
### intake-2627 — MoBA: Mixture of Block Attention for Long-Context LLMs

https://arxiv.org/abs/2502.13189 — revision 2502.13189v1; 2025-02-18; read depth PARTIAL.

- Parameter-free mean-key block gate chooses top blocks and attends within them; dense/sparse layer modes can change during training. Evidence: https://arxiv.org/html/2502.13189v1#S2.SS2.
- Reported Llama3.1-8B continuation grows128k→256k→512k→1M; after1M continuation MoBA active100B tokens, block4096/top12. No evidence this cost is needed for D-LSA. Evidence: https://arxiv.org/html/2502.13189v1#S3.SS2.
- MoBA/full training and layer hybrids control sparse-training fidelity;10M is performance scaling evidence with block-size changes, not10M task accuracy proof. Evidence: https://arxiv.org/html/2502.13189v1#S3.SS3.

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| RI-LSA-1 | intake-2622 | Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210. | P1 / LSA-SCREEN-1 |
| RI-LSA-2 | intake-2622 | Add frozen-teacher capture for Qwen3.6-35B-A3B and generate model-specific PCA projections for its ten global layers, with exact GQA/head aggregation and RoPE-free coordinate tests; run the same bounded screen and estimate full distillation only from a timed extraction/training pilot. | P2 / LSA-MOE-1 |
| RI-LSA-3 | intake-2623 | Implement experimental CPU AVX512 and gfx90a flat-index selection plus indexed exact attention using existing row-gather contracts where suitable; retain full KV and validate request isolation, causal masks, partial clusters, slot reuse and dense fallback. Quantized-KV and MTP/DFlash2 parity require separate integration gates before serving activation. | P3 / LSA-PORT-1 |
| RI-LSA-4 | intake-2623 | Before the first conversion screen, register its native result producer in scripts/vidya/adapters/README.md and project complete raw-run identity, effective configuration, failures and decision records through the existing measurement ladder; require a planning-context canary, without inventing a new grading rule. | P4 / LSA-EVIDENCE-1 |
| RI-LSA-5 | intake-2623 | Repair intake validation of historical handoff references after the approved backlog folds: resolve old filenames only through an unambiguous committed fold mapping to an existing owner and Track heading; reject unknown, ambiguous and dangling targets. Apply the same resolution to index and cross-reference-map checks, add focused moved/missing/ambiguous tests, and require the full intake validator to exit zero before closing this campaign. | P5 / LSA-INTAKE-XREF-1 |
| RI-LSA-PAPER-1 | intake-2622 | Reproduce Qwen38 released PCA and distilled maps in experimental backend at exact source/model/map revisions; benchmark dense versus flat at actual EPYC context/concurrency mix before extrapolating10M gains. | P1 / LSA-SCREEN-1 |
| RI-LSA-PAPER-2 | intake-2622 | Implement Qwen36 MoE-aware frozen-teacher capture adapter and generate its own PCA baseline before distillation; validate GQA normalization/head aggregation and 75% RoPE-free flattening against current repo adapter. | P2 / LSA-MOE-1 |
| RI-LSA-PAPER-3 | intake-2622 | Separate memory feasibility, attention-module timing, TTFT, decode latency, and task fidelity. Keep complete KV retained unless an independently evaluated cache-compression layer is added. | P1 / LSA-SCREEN-1 |
| RI-LSA-PAPER-4 | intake-2622 | Use flat first; require tree-specific accuracy study and sufficiently long context/concurrency before claiming tree benefit. Consider dense fallback at short context after measured crossover. | P1 / LSA-SCREEN-1 |
| RI-LSA-PAPER-5 | intake-2622 | Port/reference-check Triton indexer and sparse gather-attention on experimental ROCm backend; use exact selected-index oracle/captured QKV tests and incremental benchmark checkpoints. | P3 / LSA-PORT-1 |
| RI-LSA-PAPER-6 | intake-2622 | If distilled map misses quality target, compare longer-domain-specific distillation and optional sparse continued training against parameter-free switchable-attention alternatives. | P2 / LSA-MOE-1 |
| RI-LSA-REPO-1 | intake-2623 | Decide whether released distilled/PCA maps retain useful attention and task quality at production rotation, Q8weights/Q8KV, before a long port. | P1 / LSA-SCREEN-1 |
| RI-LSA-REPO-2 | intake-2623 | Reduce full-attention CPU work at long contexts without dense scan of skippedKV; decide net end-to-end gain against current MTP baseline. | P3 / LSA-PORT-1 |
| RI-LSA-REPO-3 | intake-2623 | Establish gfx90a correctness/crossover at actual batch/context and Q8KV before porting NVIDIA microarchitecture optimizations. | P3 / LSA-PORT-1 |
| RI-LSA-REPO-4 | intake-2623 | Determine same technique utility on deployed35B-A3B without altering MoE routing or GatedDeltaNet. | P2 / LSA-MOE-1 |
| RI-LSA-REPO-5 | intake-2623 | Make useful sparse serving compatible with current27B DFlash2 and35B MTP; avoid per-request cache corruption or draft rejection regressions. | P3 / LSA-PORT-1 |
| RI-LSA-REPO-6 | intake-2623 | Only build hierarchy if measured flat selector dominates at actual context/concurrency or context objective expands. | M1 |
| RI-LSA-REPO-7 | intake-2623 | Keep distinct from retrofit; only relevant if EPYC chooses to train an attention architecture. | M2 |
| RI-LSA-REPO-8 | intake-2623 | Any port screen emits native run artifacts and source adapter registration so observed results can enter current decision loop. | P4 / LSA-EVIDENCE-1 |
| RI-LSA-LIT-1 | intake-2624 | Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen. | P1 / LSA-SCREEN-1 |
| RI-LSA-LIT-2 | intake-2625 | Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen. | P1 / LSA-SCREEN-1 |
| RI-LSA-LIT-3 | intake-2626 | Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen. | P1 / LSA-SCREEN-1 |
| RI-LSA-LIT-4 | intake-2627 | Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen. | P1 / LSA-SCREEN-1 |

## Validation and Stage-4 close-out to apply after approval

Full validator currently fails with1648 existing missing-handoff-reference errors after recent folds. New entries and the v2 plan have no new schema/structural failures in the differential check. Intake is not complete or fully validated. P5 is a concrete repair to execute as part of approved Stage4: edit only the validator and focused tests using committed fold provenance, without manufacturing alias handoffs or suppressing missing references. GitNexus is stale and its refresh was denied by CPU admission; symbol impact for intake_index is unavailable. Current diff is additive research/checkpoint documentation with no executable/production blast radius. P5 requires its own symbol impact check before code editing.

Apply exactly the five proposed task lines, execute the scoped validation repair, retain the comparator findings in the long-context owner, update dispositions, reconcile the checkpoint with exact plan SHA256, render dive digests and confirm wiki scanner discovery, update progress and agent log, regenerate index state and require both validators exit0. No index row additions or stubs are needed. No kernel build, inference, reload or promotion is authorized by this filing. Artifact audit: clean; research scratch is source-only and no benchmark result is claimed.

## Stage-3 filing payload

```json
{
  "format_version": 2,
  "entry_updates": [
    {
      "id": "intake-2622",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/long-context-program.md",
        "handoffs/active/model-architecture-readiness.md",
        "handoffs/active/rocm-kernel-authoring.md",
        "handoffs/active/vidya-belief-substrate-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "This approved filing would route scoped conversion findings to the named owners; no reproduction or deployment implied."
      ]
    },
    {
      "id": "intake-2623",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/long-context-program.md",
        "handoffs/active/model-architecture-readiness.md",
        "handoffs/active/rocm-kernel-authoring.md",
        "handoffs/active/vidya-belief-substrate-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "This approved filing would route scoped conversion findings to the named owners; no reproduction or deployment implied."
      ]
    },
    {
      "id": "intake-2624",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/long-context-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "This approved filing would route scoped conversion findings to the named owners; no reproduction or deployment implied."
      ]
    },
    {
      "id": "intake-2625",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/long-context-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "This approved filing would route scoped conversion findings to the named owners; no reproduction or deployment implied."
      ]
    },
    {
      "id": "intake-2626",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/long-context-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "This approved filing would route scoped conversion findings to the named owners; no reproduction or deployment implied."
      ]
    },
    {
      "id": "intake-2627",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/long-context-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "This approved filing would route scoped conversion findings to the named owners; no reproduction or deployment implied."
      ]
    }
  ],
  "opportunity_reviews": {
    "P1": {
      "project_objective": "Decide whether sparse selection improves native EPYC long-context serving without losing task fidelity.",
      "implementation_ref": "llama.cpp ffc1bac82 src/models/qwen35.cpp build_layer_attn and qwen35moe.cpp; upstream LSA 97b82d695b74",
      "gap": "Current model graph has global attention and recurrent layers but no verified LSA selector/maps or integrated measurement producer.",
      "operational_change": "Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.",
      "benefit_direction": "Lower TTFT/TPOT and bytes read at fixed task quality; account for retained KV and index memory.",
      "owner": "handoffs/active/long-context-program.md",
      "execution_conditions": "Experimental trees only; P4 capture before empirical runs; P3 reference implementation before P1/P2 screens; no production reload or promotion. Full training/tree/activation follows observable screen success.",
      "closure_basis": "Concrete deciding implementation and screen retained; no production or full-training claim."
    },
    "P2": {
      "project_objective": "Decide whether sparse selection improves native EPYC long-context serving without losing task fidelity.",
      "implementation_ref": "llama.cpp ffc1bac82 src/models/qwen35.cpp build_layer_attn and qwen35moe.cpp; upstream LSA 97b82d695b74",
      "gap": "Current model graph has global attention and recurrent layers but no verified LSA selector/maps or integrated measurement producer.",
      "operational_change": "Add frozen-teacher capture for Qwen3.6-35B-A3B and generate model-specific PCA projections for its ten global layers, with exact GQA/head aggregation and RoPE-free coordinate tests; run the same bounded screen and estimate full distillation only from a timed extraction/training pilot.",
      "benefit_direction": "Lower TTFT/TPOT and bytes read at fixed task quality; account for retained KV and index memory.",
      "owner": "handoffs/active/model-architecture-readiness.md",
      "execution_conditions": "Experimental trees only; P4 capture before empirical runs; P3 reference implementation before P1/P2 screens; no production reload or promotion. Full training/tree/activation follows observable screen success.",
      "closure_basis": "Concrete deciding implementation and screen retained; no production or full-training claim."
    },
    "P3": {
      "project_objective": "Decide whether sparse selection improves native EPYC long-context serving without losing task fidelity.",
      "implementation_ref": "llama.cpp ffc1bac82 src/models/qwen35.cpp build_layer_attn and qwen35moe.cpp; upstream LSA 97b82d695b74",
      "gap": "Current model graph has global attention and recurrent layers but no verified LSA selector/maps or integrated measurement producer.",
      "operational_change": "Implement experimental CPU AVX512 and gfx90a flat-index selection plus indexed exact attention using existing row-gather contracts where suitable; retain full KV and validate request isolation, causal masks, partial clusters, slot reuse and dense fallback. Quantized-KV and MTP/DFlash2 parity require separate integration gates before serving activation.",
      "benefit_direction": "Lower TTFT/TPOT and bytes read at fixed task quality; account for retained KV and index memory.",
      "owner": "handoffs/active/rocm-kernel-authoring.md",
      "execution_conditions": "Experimental trees only; P4 capture before empirical runs; P3 reference implementation before P1/P2 screens; no production reload or promotion. Full training/tree/activation follows observable screen success.",
      "closure_basis": "Concrete deciding implementation and screen retained; no production or full-training claim."
    },
    "P4": {
      "project_objective": "Decide whether sparse selection improves native EPYC long-context serving without losing task fidelity.",
      "implementation_ref": "llama.cpp ffc1bac82 src/models/qwen35.cpp build_layer_attn and qwen35moe.cpp; upstream LSA 97b82d695b74",
      "gap": "Current model graph has global attention and recurrent layers but no verified LSA selector/maps or integrated measurement producer.",
      "operational_change": "Before the first conversion screen, register its native result producer in scripts/vidya/adapters/README.md and project complete raw-run identity, effective configuration, failures and decision records through the existing measurement ladder; require a planning-context canary, without inventing a new grading rule.",
      "benefit_direction": "Lower TTFT/TPOT and bytes read at fixed task quality; account for retained KV and index memory.",
      "owner": "handoffs/active/vidya-belief-substrate-program.md",
      "execution_conditions": "Experimental trees only; P4 capture before empirical runs; P3 reference implementation before P1/P2 screens; no production reload or promotion. Full training/tree/activation follows observable screen success.",
      "closure_basis": "Concrete deciding implementation and screen retained; no production or full-training claim."
    },
    "P5": {
      "project_objective": "Decide whether sparse selection improves native EPYC long-context serving without losing task fidelity.",
      "implementation_ref": "llama.cpp ffc1bac82 src/models/qwen35.cpp build_layer_attn and qwen35moe.cpp; upstream LSA 97b82d695b74",
      "gap": "Current model graph has global attention and recurrent layers but no verified LSA selector/maps or integrated measurement producer.",
      "operational_change": "Repair intake validation of historical handoff references after the approved backlog folds: resolve old filenames only through an unambiguous committed fold mapping to an existing owner and Track heading; reject unknown, ambiguous and dangling targets. Apply the same resolution to index and cross-reference-map checks, add focused moved/missing/ambiguous tests, and require the full intake validator to exit zero before closing this campaign.",
      "benefit_direction": "Lower TTFT/TPOT and bytes read at fixed task quality; account for retained KV and index memory.",
      "owner": "handoffs/active/knowledge-pipelines.md",
      "execution_conditions": "Experimental trees only; P4 capture before empirical runs; P3 reference implementation before P1/P2 screens; no production reload or promotion. Full training/tree/activation follows observable screen success.",
      "closure_basis": "Concrete deciding implementation and screen retained; no production or full-training claim."
    },
    "M1": {
      "project_objective": "Decide whether sparse selection improves native EPYC long-context serving without losing task fidelity.",
      "implementation_ref": "llama.cpp ffc1bac82 src/models/qwen35.cpp build_layer_attn and qwen35moe.cpp; upstream LSA 97b82d695b74",
      "gap": "Current model graph has global attention and recurrent layers but no verified LSA selector/maps or integrated measurement producer.",
      "operational_change": "Retain observable trigger only; no immediate tree/native-training backlog.",
      "benefit_direction": "Lower TTFT/TPOT and bytes read at fixed task quality; account for retained KV and index memory.",
      "owner": "handoffs/active/long-context-program.md",
      "execution_conditions": "Experimental trees only; P4 capture before empirical runs; P3 reference implementation before P1/P2 screens; no production reload or promotion. Full training/tree/activation follows observable screen success.",
      "closure_basis": "Current deciding question is frozen-base conversion at deployed context. Tree follows measured indexer dominance; native training follows an explicit training objective or demonstrated recovery need."
    },
    "M2": {
      "project_objective": "Decide whether sparse selection improves native EPYC long-context serving without losing task fidelity.",
      "implementation_ref": "llama.cpp ffc1bac82 src/models/qwen35.cpp build_layer_attn and qwen35moe.cpp; upstream LSA 97b82d695b74",
      "gap": "Current model graph has global attention and recurrent layers but no verified LSA selector/maps or integrated measurement producer.",
      "operational_change": "Retain observable trigger only; no immediate tree/native-training backlog.",
      "benefit_direction": "Lower TTFT/TPOT and bytes read at fixed task quality; account for retained KV and index memory.",
      "owner": "handoffs/active/long-context-program.md",
      "execution_conditions": "Experimental trees only; P4 capture before empirical runs; P3 reference implementation before P1/P2 screens; no production reload or promotion. Full training/tree/activation follows observable screen success.",
      "closure_basis": "Current deciding question is frozen-base conversion at deployed context. Tree follows measured indexer dominance; native training follows an explicit training objective or demonstrated recovery need."
    }
  },
  "opportunity_scan": [
    {
      "scan_id": "S1",
      "source_ref": "intake-2622#record",
      "implementation_ref": "llama.cpp ffc1bac82 src/models/qwen35.cpp build_layer_attn and qwen35moe.cpp; upstream LSA 97b82d695b74",
      "mechanism": "Frozen-base semantic selection with released Qwen maps",
      "consumer": "27B serving",
      "application": "Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-LSA-1"
      ],
      "basis": "Selected source mechanisms compared with actual hybrid graph and serving restrictions; validation repair comes from observed repository reference failures."
    },
    {
      "scan_id": "S2",
      "source_ref": "intake-2622#record",
      "implementation_ref": "llama.cpp ffc1bac82 src/models/qwen35.cpp build_layer_attn and qwen35moe.cpp; upstream LSA 97b82d695b74",
      "mechanism": "Model-specific frozen QK projections",
      "consumer": "35B MoE serving",
      "application": "Add frozen-teacher capture for Qwen3.6-35B-A3B and generate model-specific PCA projections for its ten global layers, with exact GQA/head aggregation and RoPE-free coordinate tests; run the same bounded screen and estimate full distillation only from a timed extraction/training pilot.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-LSA-2"
      ],
      "basis": "Selected source mechanisms compared with actual hybrid graph and serving restrictions; validation repair comes from observed repository reference failures."
    },
    {
      "scan_id": "S3",
      "source_ref": "intake-2623#record",
      "implementation_ref": "llama.cpp ffc1bac82 src/models/qwen35.cpp build_layer_attn and qwen35moe.cpp; upstream LSA 97b82d695b74",
      "mechanism": "Sparse index lists with exact original QKV attention",
      "consumer": "CPU/GPU attention graph",
      "application": "Implement experimental CPU AVX512 and gfx90a flat-index selection plus indexed exact attention using existing row-gather contracts where suitable; retain full KV and validate request isolation, causal masks, partial clusters, slot reuse and dense fallback. Quantized-KV and MTP/DFlash2 parity require separate integration gates before serving activation.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-LSA-3"
      ],
      "basis": "Selected source mechanisms compared with actual hybrid graph and serving restrictions; validation repair comes from observed repository reference failures."
    },
    {
      "scan_id": "S4",
      "source_ref": "intake-2623#record",
      "implementation_ref": "llama.cpp ffc1bac82 src/models/qwen35.cpp build_layer_attn and qwen35moe.cpp; upstream LSA 97b82d695b74",
      "mechanism": "Producer-time capture of experiment warrants",
      "consumer": "Planning context",
      "application": "Before the first conversion screen, register its native result producer in scripts/vidya/adapters/README.md and project complete raw-run identity, effective configuration, failures and decision records through the existing measurement ladder; require a planning-context canary, without inventing a new grading rule.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-LSA-4"
      ],
      "basis": "Selected source mechanisms compared with actual hybrid graph and serving restrictions; validation repair comes from observed repository reference failures."
    },
    {
      "scan_id": "S5",
      "source_ref": "intake-2623#record",
      "implementation_ref": ".claude/skills/research-intake/scripts/validate_intake.py:473-488,626-674; committed fold-list-1a/1b.json",
      "mechanism": "Committed fold provenance for persistent source cross-references",
      "consumer": "Intake validator",
      "application": "Repair intake validation of historical handoff references after the approved backlog folds: resolve old filenames only through an unambiguous committed fold mapping to an existing owner and Track heading; reject unknown, ambiguous and dangling targets. Apply the same resolution to index and cross-reference-map checks, add focused moved/missing/ambiguous tests, and require the full intake validator to exit zero before closing this campaign.",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-LSA-5"
      ],
      "basis": "Selected source mechanisms compared with actual hybrid graph and serving restrictions; validation repair comes from observed repository reference failures."
    },
    {
      "scan_id": "RI-LSA-PAPER-1",
      "source_ref": "intake-2622#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Reproduce Qwen38 released PCA and distilled maps in experimental backend at exact source/model/map revisions; benchmark dense versus flat at actual EPYC context/concurrency mix before extrapolating10M gains.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Reproduce Qwen38 released PCA and distilled maps in experimental backend at exact source/model/map revisions; benchmark dense versus flat at actual EPYC context/concurrency mix before extrapolating10M gains.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-PAPER-1"
      ],
      "basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding."
    },
    {
      "scan_id": "RI-LSA-PAPER-2",
      "source_ref": "intake-2622#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Implement Qwen36 MoE-aware frozen-teacher capture adapter and generate its own PCA baseline before distillation; validate GQA normalization/head aggregation and 75% RoPE-free flattening against current repo adapter.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Implement Qwen36 MoE-aware frozen-teacher capture adapter and generate its own PCA baseline before distillation; validate GQA normalization/head aggregation and 75% RoPE-free flattening against current repo adapter.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-PAPER-2"
      ],
      "basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding."
    },
    {
      "scan_id": "RI-LSA-PAPER-3",
      "source_ref": "intake-2622#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Separate memory feasibility, attention-module timing, TTFT, decode latency, and task fidelity. Keep complete KV retained unless an independently evaluated cache-compression layer is added.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Separate memory feasibility, attention-module timing, TTFT, decode latency, and task fidelity. Keep complete KV retained unless an independently evaluated cache-compression layer is added.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-PAPER-3"
      ],
      "basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding."
    },
    {
      "scan_id": "RI-LSA-PAPER-4",
      "source_ref": "intake-2622#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Use flat first; require tree-specific accuracy study and sufficiently long context/concurrency before claiming tree benefit. Consider dense fallback at short context after measured crossover.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Use flat first; require tree-specific accuracy study and sufficiently long context/concurrency before claiming tree benefit. Consider dense fallback at short context after measured crossover.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-PAPER-4"
      ],
      "basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding."
    },
    {
      "scan_id": "RI-LSA-PAPER-5",
      "source_ref": "intake-2622#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Port/reference-check Triton indexer and sparse gather-attention on experimental ROCm backend; use exact selected-index oracle/captured QKV tests and incremental benchmark checkpoints.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Port/reference-check Triton indexer and sparse gather-attention on experimental ROCm backend; use exact selected-index oracle/captured QKV tests and incremental benchmark checkpoints.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-PAPER-5"
      ],
      "basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding."
    },
    {
      "scan_id": "RI-LSA-PAPER-6",
      "source_ref": "intake-2622#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "If distilled map misses quality target, compare longer-domain-specific distillation and optional sparse continued training against parameter-free switchable-attention alternatives.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "If distilled map misses quality target, compare longer-domain-specific distillation and optional sparse continued training against parameter-free switchable-attention alternatives.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-PAPER-6"
      ],
      "basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding."
    },
    {
      "scan_id": "RI-LSA-REPO-1",
      "source_ref": "intake-2623#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Decide whether released distilled/PCA maps retain useful attention and task quality at production rotation, Q8weights/Q8KV, before a long port.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Decide whether released distilled/PCA maps retain useful attention and task quality at production rotation, Q8weights/Q8KV, before a long port.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-REPO-1"
      ],
      "basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding."
    },
    {
      "scan_id": "RI-LSA-REPO-2",
      "source_ref": "intake-2623#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Reduce full-attention CPU work at long contexts without dense scan of skippedKV; decide net end-to-end gain against current MTP baseline.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Reduce full-attention CPU work at long contexts without dense scan of skippedKV; decide net end-to-end gain against current MTP baseline.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-REPO-2"
      ],
      "basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding."
    },
    {
      "scan_id": "RI-LSA-REPO-3",
      "source_ref": "intake-2623#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Establish gfx90a correctness/crossover at actual batch/context and Q8KV before porting NVIDIA microarchitecture optimizations.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Establish gfx90a correctness/crossover at actual batch/context and Q8KV before porting NVIDIA microarchitecture optimizations.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-REPO-3"
      ],
      "basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding."
    },
    {
      "scan_id": "RI-LSA-REPO-4",
      "source_ref": "intake-2623#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Determine same technique utility on deployed35B-A3B without altering MoE routing or GatedDeltaNet.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Determine same technique utility on deployed35B-A3B without altering MoE routing or GatedDeltaNet.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-REPO-4"
      ],
      "basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding."
    },
    {
      "scan_id": "RI-LSA-REPO-5",
      "source_ref": "intake-2623#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Make useful sparse serving compatible with current27B DFlash2 and35B MTP; avoid per-request cache corruption or draft rejection regressions.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Make useful sparse serving compatible with current27B DFlash2 and35B MTP; avoid per-request cache corruption or draft rejection regressions.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-REPO-5"
      ],
      "basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding."
    },
    {
      "scan_id": "RI-LSA-REPO-6",
      "source_ref": "intake-2623#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Only build hierarchy if measured flat selector dominates at actual context/concurrency or context objective expands.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Only build hierarchy if measured flat selector dominates at actual context/concurrency or context objective expands.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-LSA-REPO-6"
      ],
      "basis": "Flat scan becomes material bottleneck after sparse read is effective, or user chooses ultra-long multi-million context; paper tree decode wins only at verylong1request and can lose taskquality. Usebf16nodes ongfx90a initially; paperFP8node optimization needs separate numerical andhardware support proof."
    },
    {
      "scan_id": "RI-LSA-REPO-7",
      "source_ref": "intake-2623#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Keep distinct from retrofit; only relevant if EPYC chooses to train an attention architecture.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Keep distinct from retrofit; only relevant if EPYC chooses to train an attention architecture.",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-LSA-REPO-7"
      ],
      "basis": "An explicit native-model training objective or failure of frozen-map retrofit that warrants model training; paper100Bpretrain+12Bdecay not required for D-LSA."
    },
    {
      "scan_id": "RI-LSA-REPO-8",
      "source_ref": "intake-2623#record",
      "implementation_ref": "qwen35/qwen35moe global-attention path and current Q8-KV/speculation recipe",
      "mechanism": "Any port screen emits native run artifacts and source adapter registration so observed results can enter current decision loop.",
      "consumer": "Hybrid model serving and evaluation",
      "application": "Any port screen emits native run artifacts and source adapter registration so observed results can enter current decision loop.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-REPO-8"
      ],
      "basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding."
    },
    {
      "scan_id": "L1",
      "source_ref": "intake-2624#record",
      "implementation_ref": "llama.cpp ffc1bac82 qwen35 global attention path",
      "mechanism": "Learns pooled block attention gates through frozen-model self-distillation. Gate ground truth uses customized FlashAttention max-pooling rather than materializing dense attention maps.",
      "consumer": "Long-context screen design",
      "application": "Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-LIT-1"
      ],
      "basis": "Comparator provides a design control/caveat, not a requirement to reproduce a separate model or all training regimes."
    },
    {
      "scan_id": "L2",
      "source_ref": "intake-2625#record",
      "implementation_ref": "llama.cpp ffc1bac82 qwen35 global attention path",
      "mechanism": "Independent learned Q and KV mappings produce32-bit Hamming signatures; bitwise scores still scan cached token signatures before sparse token attention.",
      "consumer": "Long-context screen design",
      "application": "Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-LIT-2"
      ],
      "basis": "Comparator provides a design control/caveat, not a requirement to reproduce a separate model or all training regimes."
    },
    {
      "scan_id": "L3",
      "source_ref": "intake-2626#record",
      "implementation_ref": "llama.cpp ffc1bac82 qwen35 global attention path",
      "mechanism": "Reuses dense QKV with no new trainable parameters; unions selected and local blocks into single attention output and drops compressed-attention output. Parameter-free multistage pooling selects blocks.",
      "consumer": "Long-context screen design",
      "application": "Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-LIT-3"
      ],
      "basis": "Comparator provides a design control/caveat, not a requirement to reproduce a separate model or all training regimes."
    },
    {
      "scan_id": "L4",
      "source_ref": "intake-2627#record",
      "implementation_ref": "llama.cpp ffc1bac82 qwen35 global attention path",
      "mechanism": "Parameter-free mean-key block gate chooses top blocks and attends within them; dense/sparse layer modes can change during training.",
      "consumer": "Long-context screen design",
      "application": "Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen.",
      "disposition": "covered",
      "ledger_ids": [
        "RI-LSA-LIT-4"
      ],
      "basis": "Comparator provides a design control/caveat, not a requirement to reproduce a separate model or all training regimes."
    }
  ],
  "actionable_additions": [
    {
      "ledger_id": "RI-LSA-1",
      "source": "intake-2622",
      "action": "Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.",
      "terminal_mapping": "P1 / LSA-SCREEN-1"
    },
    {
      "ledger_id": "RI-LSA-2",
      "source": "intake-2622",
      "action": "Add frozen-teacher capture for Qwen3.6-35B-A3B and generate model-specific PCA projections for its ten global layers, with exact GQA/head aggregation and RoPE-free coordinate tests; run the same bounded screen and estimate full distillation only from a timed extraction/training pilot.",
      "terminal_mapping": "P2 / LSA-MOE-1"
    },
    {
      "ledger_id": "RI-LSA-3",
      "source": "intake-2623",
      "action": "Implement experimental CPU AVX512 and gfx90a flat-index selection plus indexed exact attention using existing row-gather contracts where suitable; retain full KV and validate request isolation, causal masks, partial clusters, slot reuse and dense fallback. Quantized-KV and MTP/DFlash2 parity require separate integration gates before serving activation.",
      "terminal_mapping": "P3 / LSA-PORT-1"
    },
    {
      "ledger_id": "RI-LSA-4",
      "source": "intake-2623",
      "action": "Before the first conversion screen, register its native result producer in scripts/vidya/adapters/README.md and project complete raw-run identity, effective configuration, failures and decision records through the existing measurement ladder; require a planning-context canary, without inventing a new grading rule.",
      "terminal_mapping": "P4 / LSA-EVIDENCE-1"
    },
    {
      "ledger_id": "RI-LSA-5",
      "source": "intake-2623",
      "action": "Repair intake validation of historical handoff references after the approved backlog folds: resolve old filenames only through an unambiguous committed fold mapping to an existing owner and Track heading; reject unknown, ambiguous and dangling targets. Apply the same resolution to index and cross-reference-map checks, add focused moved/missing/ambiguous tests, and require the full intake validator to exit zero before closing this campaign.",
      "terminal_mapping": "P5 / LSA-INTAKE-XREF-1"
    },
    {
      "ledger_id": "RI-LSA-PAPER-1",
      "source": "intake-2622",
      "action": "Reproduce Qwen38 released PCA and distilled maps in experimental backend at exact source/model/map revisions; benchmark dense versus flat at actual EPYC context/concurrency mix before extrapolating10M gains.",
      "terminal_mapping": "P1 / LSA-SCREEN-1"
    },
    {
      "ledger_id": "RI-LSA-PAPER-2",
      "source": "intake-2622",
      "action": "Implement Qwen36 MoE-aware frozen-teacher capture adapter and generate its own PCA baseline before distillation; validate GQA normalization/head aggregation and 75% RoPE-free flattening against current repo adapter.",
      "terminal_mapping": "P2 / LSA-MOE-1"
    },
    {
      "ledger_id": "RI-LSA-PAPER-3",
      "source": "intake-2622",
      "action": "Separate memory feasibility, attention-module timing, TTFT, decode latency, and task fidelity. Keep complete KV retained unless an independently evaluated cache-compression layer is added.",
      "terminal_mapping": "P1 / LSA-SCREEN-1"
    },
    {
      "ledger_id": "RI-LSA-PAPER-4",
      "source": "intake-2622",
      "action": "Use flat first; require tree-specific accuracy study and sufficiently long context/concurrency before claiming tree benefit. Consider dense fallback at short context after measured crossover.",
      "terminal_mapping": "P1 / LSA-SCREEN-1"
    },
    {
      "ledger_id": "RI-LSA-PAPER-5",
      "source": "intake-2622",
      "action": "Port/reference-check Triton indexer and sparse gather-attention on experimental ROCm backend; use exact selected-index oracle/captured QKV tests and incremental benchmark checkpoints.",
      "terminal_mapping": "P3 / LSA-PORT-1"
    },
    {
      "ledger_id": "RI-LSA-PAPER-6",
      "source": "intake-2622",
      "action": "If distilled map misses quality target, compare longer-domain-specific distillation and optional sparse continued training against parameter-free switchable-attention alternatives.",
      "terminal_mapping": "P2 / LSA-MOE-1"
    },
    {
      "ledger_id": "RI-LSA-REPO-1",
      "source": "intake-2623",
      "action": "Decide whether released distilled/PCA maps retain useful attention and task quality at production rotation, Q8weights/Q8KV, before a long port.",
      "terminal_mapping": "P1 / LSA-SCREEN-1"
    },
    {
      "ledger_id": "RI-LSA-REPO-2",
      "source": "intake-2623",
      "action": "Reduce full-attention CPU work at long contexts without dense scan of skippedKV; decide net end-to-end gain against current MTP baseline.",
      "terminal_mapping": "P3 / LSA-PORT-1"
    },
    {
      "ledger_id": "RI-LSA-REPO-3",
      "source": "intake-2623",
      "action": "Establish gfx90a correctness/crossover at actual batch/context and Q8KV before porting NVIDIA microarchitecture optimizations.",
      "terminal_mapping": "P3 / LSA-PORT-1"
    },
    {
      "ledger_id": "RI-LSA-REPO-4",
      "source": "intake-2623",
      "action": "Determine same technique utility on deployed35B-A3B without altering MoE routing or GatedDeltaNet.",
      "terminal_mapping": "P2 / LSA-MOE-1"
    },
    {
      "ledger_id": "RI-LSA-REPO-5",
      "source": "intake-2623",
      "action": "Make useful sparse serving compatible with current27B DFlash2 and35B MTP; avoid per-request cache corruption or draft rejection regressions.",
      "terminal_mapping": "P3 / LSA-PORT-1"
    },
    {
      "ledger_id": "RI-LSA-REPO-6",
      "source": "intake-2623",
      "action": "Only build hierarchy if measured flat selector dominates at actual context/concurrency or context objective expands.",
      "terminal_mapping": "M1"
    },
    {
      "ledger_id": "RI-LSA-REPO-7",
      "source": "intake-2623",
      "action": "Keep distinct from retrofit; only relevant if EPYC chooses to train an attention architecture.",
      "terminal_mapping": "M2"
    },
    {
      "ledger_id": "RI-LSA-REPO-8",
      "source": "intake-2623",
      "action": "Any port screen emits native run artifacts and source adapter registration so observed results can enter current decision loop.",
      "terminal_mapping": "P4 / LSA-EVIDENCE-1"
    },
    {
      "ledger_id": "RI-LSA-LIT-1",
      "source": "intake-2624",
      "action": "Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen.",
      "terminal_mapping": "P1 / LSA-SCREEN-1"
    },
    {
      "ledger_id": "RI-LSA-LIT-2",
      "source": "intake-2625",
      "action": "Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen.",
      "terminal_mapping": "P1 / LSA-SCREEN-1"
    },
    {
      "ledger_id": "RI-LSA-LIT-3",
      "source": "intake-2626",
      "action": "Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen.",
      "terminal_mapping": "P1 / LSA-SCREEN-1"
    },
    {
      "ledger_id": "RI-LSA-LIT-4",
      "source": "intake-2627",
      "action": "Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen.",
      "terminal_mapping": "P1 / LSA-SCREEN-1"
    }
  ],
  "steering_reconciliation": [
    {
      "seq": 1,
      "stage": 1,
      "verbatim": "Run the research intake skill ont eh following sources: https://arxiv.org/html/2610.42147v1, https://github.com/Prefrontal-AI/latent-sparse-attention. Accept all deep dives and literature expansions for up to three stage 2 waves. I'm interested to udnerstand how hard/feasible it would be for us to custom transplant this attention algo on our models (specifically Qwen-3.8-27B and Qwen-3.6-35B-A3B",
      "disposition": "planned",
      "plan_ref": "P1",
      "reason": "Conversion feasibility and controlled decision screen are proposed in P1/P2; the three-wave research selection is executed."
    }
  ],
  "outcome_reviews": {
    "RI-LSA-1": {
      "required_outcome": "Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.",
      "review_status": "preserved",
      "review_basis": "Task preserves the operational result and has an experimental execution gate; current production remains frozen.",
      "task_refs": [
        {
          "owner": "handoffs/active/long-context-program.md",
          "task_id": "LSA-SCREEN-1",
          "task_text": "- [ ] **LSA-SCREEN-1 \u2014 Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-2": {
      "required_outcome": "Add frozen-teacher capture for Qwen3.6-35B-A3B and generate model-specific PCA projections for its ten global layers, with exact GQA/head aggregation and RoPE-free coordinate tests; run the same bounded screen and estimate full distillation only from a timed extraction/training pilot.",
      "review_status": "preserved",
      "review_basis": "Task preserves the operational result and has an experimental execution gate; current production remains frozen.",
      "task_refs": [
        {
          "owner": "handoffs/active/model-architecture-readiness.md",
          "task_id": "LSA-MOE-1",
          "task_text": "- [ ] **LSA-MOE-1 \u2014 Add frozen-teacher capture for Qwen3.6-35B-A3B and generate model-specific PCA projections for its ten global layers, with exact GQA/head aggregation and RoPE-free coordinate tests; run the same bounded screen and estimate full distillation only from a timed extraction/training pilot.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-3": {
      "required_outcome": "Implement experimental CPU AVX512 and gfx90a flat-index selection plus indexed exact attention using existing row-gather contracts where suitable; retain full KV and validate request isolation, causal masks, partial clusters, slot reuse and dense fallback. Quantized-KV and MTP/DFlash2 parity require separate integration gates before serving activation.",
      "review_status": "preserved",
      "review_basis": "Task preserves the operational result and has an experimental execution gate; current production remains frozen.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-kernel-authoring.md",
          "task_id": "LSA-PORT-1",
          "task_text": "- [ ] **LSA-PORT-1 \u2014 Implement experimental CPU AVX512 and gfx90a flat-index selection plus indexed exact attention using existing row-gather contracts where suitable; retain full KV and validate request isolation, causal masks, partial clusters, slot reuse and dense fallback. Quantized-KV and MTP/DFlash2 parity require separate integration gates before serving activation.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-4": {
      "required_outcome": "Before the first conversion screen, register its native result producer in scripts/vidya/adapters/README.md and project complete raw-run identity, effective configuration, failures and decision records through the existing measurement ladder; require a planning-context canary, without inventing a new grading rule.",
      "review_status": "preserved",
      "review_basis": "Task preserves the operational result and has an experimental execution gate; current production remains frozen.",
      "task_refs": [
        {
          "owner": "handoffs/active/vidya-belief-substrate-program.md",
          "task_id": "LSA-EVIDENCE-1",
          "task_text": "- [ ] **LSA-EVIDENCE-1 \u2014 Before the first conversion screen, register its native result producer in scripts/vidya/adapters/README.md and project complete raw-run identity, effective configuration, failures and decision records through the existing measurement ladder; require a planning-context canary, without inventing a new grading rule.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-5": {
      "required_outcome": "Repair intake validation of historical handoff references after the approved backlog folds: resolve old filenames only through an unambiguous committed fold mapping to an existing owner and Track heading; reject unknown, ambiguous and dangling targets. Apply the same resolution to index and cross-reference-map checks, add focused moved/missing/ambiguous tests, and require the full intake validator to exit zero before closing this campaign.",
      "review_status": "preserved",
      "review_basis": "Task preserves the operational result and has an experimental execution gate; current production remains frozen.",
      "task_refs": [
        {
          "owner": "handoffs/active/knowledge-pipelines.md",
          "task_id": "LSA-INTAKE-XREF-1",
          "task_text": "- [ ] **LSA-INTAKE-XREF-1 \u2014 Repair intake validation of historical handoff references after the approved backlog folds: resolve old filenames only through an unambiguous committed fold mapping to an existing owner and Track heading; reject unknown, ambiguous and dangling targets. Apply the same resolution to index and cross-reference-map checks, add focused moved/missing/ambiguous tests, and require the full intake validator to exit zero before closing this campaign.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-PAPER-1": {
      "required_outcome": "Reproduce Qwen38 released PCA and distilled maps in experimental backend at exact source/model/map revisions; benchmark dense versus flat at actual EPYC context/concurrency mix before extrapolating10M gains.",
      "review_status": "preserved",
      "review_basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding.",
      "task_refs": [
        {
          "owner": "handoffs/active/long-context-program.md",
          "task_id": "LSA-SCREEN-1",
          "task_text": "- [ ] **LSA-SCREEN-1 \u2014 Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-PAPER-2": {
      "required_outcome": "Implement Qwen36 MoE-aware frozen-teacher capture adapter and generate its own PCA baseline before distillation; validate GQA normalization/head aggregation and 75% RoPE-free flattening against current repo adapter.",
      "review_status": "preserved",
      "review_basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding.",
      "task_refs": [
        {
          "owner": "handoffs/active/model-architecture-readiness.md",
          "task_id": "LSA-MOE-1",
          "task_text": "- [ ] **LSA-MOE-1 \u2014 Add frozen-teacher capture for Qwen3.6-35B-A3B and generate model-specific PCA projections for its ten global layers, with exact GQA/head aggregation and RoPE-free coordinate tests; run the same bounded screen and estimate full distillation only from a timed extraction/training pilot.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-PAPER-3": {
      "required_outcome": "Separate memory feasibility, attention-module timing, TTFT, decode latency, and task fidelity. Keep complete KV retained unless an independently evaluated cache-compression layer is added.",
      "review_status": "preserved",
      "review_basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding.",
      "task_refs": [
        {
          "owner": "handoffs/active/long-context-program.md",
          "task_id": "LSA-SCREEN-1",
          "task_text": "- [ ] **LSA-SCREEN-1 \u2014 Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-PAPER-4": {
      "required_outcome": "Use flat first; require tree-specific accuracy study and sufficiently long context/concurrency before claiming tree benefit. Consider dense fallback at short context after measured crossover.",
      "review_status": "preserved",
      "review_basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding.",
      "task_refs": [
        {
          "owner": "handoffs/active/long-context-program.md",
          "task_id": "LSA-SCREEN-1",
          "task_text": "- [ ] **LSA-SCREEN-1 \u2014 Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-PAPER-5": {
      "required_outcome": "Port/reference-check Triton indexer and sparse gather-attention on experimental ROCm backend; use exact selected-index oracle/captured QKV tests and incremental benchmark checkpoints.",
      "review_status": "preserved",
      "review_basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-kernel-authoring.md",
          "task_id": "LSA-PORT-1",
          "task_text": "- [ ] **LSA-PORT-1 \u2014 Implement experimental CPU AVX512 and gfx90a flat-index selection plus indexed exact attention using existing row-gather contracts where suitable; retain full KV and validate request isolation, causal masks, partial clusters, slot reuse and dense fallback. Quantized-KV and MTP/DFlash2 parity require separate integration gates before serving activation.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-PAPER-6": {
      "required_outcome": "If distilled map misses quality target, compare longer-domain-specific distillation and optional sparse continued training against parameter-free switchable-attention alternatives.",
      "review_status": "preserved",
      "review_basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding.",
      "task_refs": [
        {
          "owner": "handoffs/active/model-architecture-readiness.md",
          "task_id": "LSA-MOE-1",
          "task_text": "- [ ] **LSA-MOE-1 \u2014 Add frozen-teacher capture for Qwen3.6-35B-A3B and generate model-specific PCA projections for its ten global layers, with exact GQA/head aggregation and RoPE-free coordinate tests; run the same bounded screen and estimate full distillation only from a timed extraction/training pilot.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-REPO-1": {
      "required_outcome": "Decide whether released distilled/PCA maps retain useful attention and task quality at production rotation, Q8weights/Q8KV, before a long port.",
      "review_status": "preserved",
      "review_basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding.",
      "task_refs": [
        {
          "owner": "handoffs/active/long-context-program.md",
          "task_id": "LSA-SCREEN-1",
          "task_text": "- [ ] **LSA-SCREEN-1 \u2014 Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-REPO-2": {
      "required_outcome": "Reduce full-attention CPU work at long contexts without dense scan of skippedKV; decide net end-to-end gain against current MTP baseline.",
      "review_status": "preserved",
      "review_basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-kernel-authoring.md",
          "task_id": "LSA-PORT-1",
          "task_text": "- [ ] **LSA-PORT-1 \u2014 Implement experimental CPU AVX512 and gfx90a flat-index selection plus indexed exact attention using existing row-gather contracts where suitable; retain full KV and validate request isolation, causal masks, partial clusters, slot reuse and dense fallback. Quantized-KV and MTP/DFlash2 parity require separate integration gates before serving activation.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-REPO-3": {
      "required_outcome": "Establish gfx90a correctness/crossover at actual batch/context and Q8KV before porting NVIDIA microarchitecture optimizations.",
      "review_status": "preserved",
      "review_basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-kernel-authoring.md",
          "task_id": "LSA-PORT-1",
          "task_text": "- [ ] **LSA-PORT-1 \u2014 Implement experimental CPU AVX512 and gfx90a flat-index selection plus indexed exact attention using existing row-gather contracts where suitable; retain full KV and validate request isolation, causal masks, partial clusters, slot reuse and dense fallback. Quantized-KV and MTP/DFlash2 parity require separate integration gates before serving activation.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-REPO-4": {
      "required_outcome": "Determine same technique utility on deployed35B-A3B without altering MoE routing or GatedDeltaNet.",
      "review_status": "preserved",
      "review_basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding.",
      "task_refs": [
        {
          "owner": "handoffs/active/model-architecture-readiness.md",
          "task_id": "LSA-MOE-1",
          "task_text": "- [ ] **LSA-MOE-1 \u2014 Add frozen-teacher capture for Qwen3.6-35B-A3B and generate model-specific PCA projections for its ten global layers, with exact GQA/head aggregation and RoPE-free coordinate tests; run the same bounded screen and estimate full distillation only from a timed extraction/training pilot.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-REPO-5": {
      "required_outcome": "Make useful sparse serving compatible with current27B DFlash2 and35B MTP; avoid per-request cache corruption or draft rejection regressions.",
      "review_status": "preserved",
      "review_basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding.",
      "task_refs": [
        {
          "owner": "handoffs/active/rocm-kernel-authoring.md",
          "task_id": "LSA-PORT-1",
          "task_text": "- [ ] **LSA-PORT-1 \u2014 Implement experimental CPU AVX512 and gfx90a flat-index selection plus indexed exact attention using existing row-gather contracts where suitable; retain full KV and validate request isolation, causal masks, partial clusters, slot reuse and dense fallback. Quantized-KV and MTP/DFlash2 parity require separate integration gates before serving activation.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-REPO-6": {
      "required_outcome": "Only build hierarchy if measured flat selector dominates at actual context/concurrency or context objective expands.",
      "review_status": "closed-with-basis",
      "review_basis": "Flat scan becomes material bottleneck after sparse read is effective, or user chooses ultra-long multi-million context; paper tree decode wins only at verylong1request and can lose taskquality. Usebf16nodes ongfx90a initially; paperFP8node optimization needs separate numerical andhardware support proof.",
      "task_refs": []
    },
    "RI-LSA-REPO-7": {
      "required_outcome": "Keep distinct from retrofit; only relevant if EPYC chooses to train an attention architecture.",
      "review_status": "closed-with-basis",
      "review_basis": "An explicit native-model training objective or failure of frozen-map retrofit that warrants model training; paper100Bpretrain+12Bdecay not required for D-LSA.",
      "task_refs": []
    },
    "RI-LSA-REPO-8": {
      "required_outcome": "Any port screen emits native run artifacts and source adapter registration so observed results can enter current decision loop.",
      "review_status": "preserved",
      "review_basis": "Exact proposed task retains this source-derived outcome; detailed controls and activation conditions remain binding.",
      "task_refs": [
        {
          "owner": "handoffs/active/vidya-belief-substrate-program.md",
          "task_id": "LSA-EVIDENCE-1",
          "task_text": "- [ ] **LSA-EVIDENCE-1 \u2014 Before the first conversion screen, register its native result producer in scripts/vidya/adapters/README.md and project complete raw-run identity, effective configuration, failures and decision records through the existing measurement ladder; require a planning-context canary, without inventing a new grading rule.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-LIT-1": {
      "required_outcome": "Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen.",
      "review_status": "preserved",
      "review_basis": "Screen includes dense/PCA/distilled arms and length-dependent crossover; further comparator implementations trigger only if the flat selector fails its quality or overhead budget.",
      "task_refs": [
        {
          "owner": "handoffs/active/long-context-program.md",
          "task_id": "LSA-SCREEN-1",
          "task_text": "- [ ] **LSA-SCREEN-1 \u2014 Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-LIT-2": {
      "required_outcome": "Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen.",
      "review_status": "preserved",
      "review_basis": "Screen includes dense/PCA/distilled arms and length-dependent crossover; further comparator implementations trigger only if the flat selector fails its quality or overhead budget.",
      "task_refs": [
        {
          "owner": "handoffs/active/long-context-program.md",
          "task_id": "LSA-SCREEN-1",
          "task_text": "- [ ] **LSA-SCREEN-1 \u2014 Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-LIT-3": {
      "required_outcome": "Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen.",
      "review_status": "preserved",
      "review_basis": "Screen includes dense/PCA/distilled arms and length-dependent crossover; further comparator implementations trigger only if the flat selector fails its quality or overhead budget.",
      "task_refs": [
        {
          "owner": "handoffs/active/long-context-program.md",
          "task_id": "LSA-SCREEN-1",
          "task_text": "- [ ] **LSA-SCREEN-1 \u2014 Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    },
    "RI-LSA-LIT-4": {
      "required_outcome": "Retain the verified conversion comparator and dense-fallback caveat in the bounded sparse-selection screen.",
      "review_status": "preserved",
      "review_basis": "Screen includes dense/PCA/distilled arms and length-dependent crossover; further comparator implementations trigger only if the flat selector fails its quality or overhead budget.",
      "task_refs": [
        {
          "owner": "handoffs/active/long-context-program.md",
          "task_id": "LSA-SCREEN-1",
          "task_text": "- [ ] **LSA-SCREEN-1 \u2014 Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.**",
          "acceptance": "Reference parity and complete controlled result records decide feasibility separately per model and device; no missing or failed item silently removed."
        }
      ]
    }
  },
  "proposed_tasks": [
    {
      "owner": "handoffs/active/long-context-program.md",
      "task_text": "- [ ] **LSA-SCREEN-1 \u2014 Build a disabled-by-default flat D-LSA reference selector for the sixteen Qwen3.8 global layers using pinned released PCA/distilled maps; preserve GDN, QK normalization, RoPE and output gates, validate selected-index and all-keys oracle parity, then run the bounded paired screen below on CPU and MI210.**"
    },
    {
      "owner": "handoffs/active/model-architecture-readiness.md",
      "task_text": "- [ ] **LSA-MOE-1 \u2014 Add frozen-teacher capture for Qwen3.6-35B-A3B and generate model-specific PCA projections for its ten global layers, with exact GQA/head aggregation and RoPE-free coordinate tests; run the same bounded screen and estimate full distillation only from a timed extraction/training pilot.**"
    },
    {
      "owner": "handoffs/active/rocm-kernel-authoring.md",
      "task_text": "- [ ] **LSA-PORT-1 \u2014 Implement experimental CPU AVX512 and gfx90a flat-index selection plus indexed exact attention using existing row-gather contracts where suitable; retain full KV and validate request isolation, causal masks, partial clusters, slot reuse and dense fallback. Quantized-KV and MTP/DFlash2 parity require separate integration gates before serving activation.**"
    },
    {
      "owner": "handoffs/active/vidya-belief-substrate-program.md",
      "task_text": "- [ ] **LSA-EVIDENCE-1 \u2014 Before the first conversion screen, register its native result producer in scripts/vidya/adapters/README.md and project complete raw-run identity, effective configuration, failures and decision records through the existing measurement ladder; require a planning-context canary, without inventing a new grading rule.**"
    },
    {
      "owner": "handoffs/active/knowledge-pipelines.md",
      "task_text": "- [ ] **LSA-INTAKE-XREF-1 \u2014 Repair intake validation of historical handoff references after the approved backlog folds: resolve old filenames only through an unambiguous committed fold mapping to an existing owner and Track heading; reject unknown, ambiguous and dangling targets. Apply the same resolution to index and cross-reference-map checks, add focused moved/missing/ambiguous tests, and require the full intake validator to exit zero before closing this campaign.**"
    }
  ]
}
```
