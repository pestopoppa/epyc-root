# TQ3 / TurboQuant Quantization — Monitor List

**Status**: monitoring / stop-list active for current sub-2-bit candidate reruns (do NOT merge TQ3_1S — see rationale below)
**Created**: 2026-04-01 (via research intake)
**Updated**: 2026-07-20 (July steering supersedes the old broad speed-probe loop; PR #21089 monitoring remains)
**Categories**: quantization, hardware_optimization

> **⚠ STEERING (2026-07-19) — deprioritize the sub-2-bit breadth probes.** Bonsai-8B/27B `Q1_0`,
> Ternary `Q2_g64`, and Ternary `Q2_0` were probed on experimental-v7 and are **speed-only,
> quality-blocked or broken-load** (Q1_0 6/8 instruction-format; Q2_g64 6/8 + empty `<think>`;
> Q2_0 won't load — 498/498 tensors short, noncanonical packing). **Do NOT keep running speed
> reruns on these.** Reopen ONLY on a *specific* quality path: a producer/transcode fix for the
> Q2_0 layout, or a prompt/template fix with a hypothesis for the instruction-format miss. Full
> results + verdicts: [`../../docs/reference/model-probe-scoreboard.md`](../../docs/reference/model-probe-scoreboard.md).
> Freed cycles → operator-gated v7 promotion work (OP-2 / P-GPU-1 / AXA-2 / GLM accept-control).

## Status as of 2026-04-21

Backburner monitoring. PR #21038 remains merged and auto-enabled in production v3 (confirmed 2026-04-17). PR #21089 (TBQ3_0/TBQ4_0 CPU KV cache kernels) still open — no movement since last review. ChunkKV proposal unchanged. TQ3_1S rejection stands (immaturity + wrong target; see rationale below). Next revisit: when PR #21089 receives maintainer review or lands.

## Why NOT to Merge TQ3_1S

1. **Immature**: 3 commits, 1 contributor, no peer review, no CPU kernels, undocumented conversion tool
2. **Wrong target**: Only benchmarked on Qwen3.5-27B vs Q4_0. No Q4_K_M comparison. No Qwen2.5 tests. Author warns smaller models are "much less forgiving"
3. **We don't need VRAM savings**: Our EPYC 9655 setup has ample RAM/VRAM. Q4_K_M fits comfortably. Bottleneck is throughput, not capacity
4. **Upstream going different direction**: ggerganov himself is working on Hadamard rotation for existing quant types (PR #21038) — no new types needed
5. **MoE risk**: WHT rotation creates ~367K ghost activations per forward pass, shattering sparse routing. Not applicable to dense Qwen2.5-Coder-32B but relevant for Qwen3.5 hybrid

## What to Monitor Instead (High Priority)

### PR #21038 — ggerganov's Hadamard Rotation ✅ LANDED
- **What**: Applies WHT rotation to ALL existing KV cache quant types (Q4_0, Q5_0, Q8_0 etc.)
- **Impact**: Q4_0 KV cache PPL improves 25-77% on small models. Q8_0 with rotation matches FP16 on reasoning benchmarks
- **Why it matters**: Free quality improvement — no model re-quantization needed, just rebuild llama.cpp
- **Status**: ✅ MERGED upstream as commit `744c0c731` (2026-04-01). Auto-enables in `production-consolidated-v3` when KV types are quantized. `--kv-hadamard` flag removed from orchestrator config (was our prior custom WHT impl, now redundant).
- **URL**: https://github.com/ggml-org/llama.cpp/pull/21038

### PR #21089 — CPU TurboQuant KV Cache (TBQ3_0/TBQ4_0)
- **What**: 3-bit and 4-bit KV cache quantization with CPU kernels
- **Impact**: 5.2x KV cache compression with minimal PPL loss. Extends effective context length
- **Status**: CLOSED UNMERGED upstream 2026-06-02 (GitHub PR metadata checked 2026-07-29); no TBQ code entered the local production tree.
- **URL**: https://github.com/ggml-org/llama.cpp/pull/21089

### ChunkKV (arXiv:2502.00299) — Training-Free KV Compression
- **What**: Chunk-level KV cache compression preserving semantic structure. No retraining required
- **Impact**: Retains 12% of KV cache matching full cache quality. 26.5% throughput improvement via layer-wise index reuse
- **Why it matters**: Works on existing pretrained models — directly applicable to our stack
- **URL**: https://arxiv.org/abs/2502.00299

#### 2026-07-29 feasibility assessment

**Disposition: technically implementable as an experimental llama.cpp candidate; do not treat it as
an existing-server toggle or a production patch.** ChunkKV selects complete contiguous chunks from
the observed-query attention matrix, retains a recent observe window, and reuses selected indices
across adjacent layers. The paper evaluates chunk sizes 3–30 and reports 10 as its robust default
([paper §3.2–3.3](https://arxiv.org/html/2502.00299#S3),
[§4.4](https://arxiv.org/html/2502.00299#S4)). Its published quality and throughput figures are
observations on different models/runtimes, not an EPYC decision claim.

The production tree already contains the adjacent substrate: `src/llama-kv-compress.cpp` is compiled
and the server's `POST /slots/{id}?action=compact` path performs idle-slot Expected-Attention eviction.
That is **not a faithful ChunkKV implementation**. Expected Attention derives a future-attention proxy
from raw K/V; ChunkKV requires the actual attention scores from the final prefill queries. Summing the
existing per-token proxy into chunks would be a useful *ChunkEA* derivative, but must not be reported
as reproducing the paper. The server also deliberately leaves evicted positions gapped because its
prompt/checkpoint state tracks logical positions independently; eviction creates reusable KV capacity,
not an allocated-buffer shrink or immediate logical-context extension.

If scheduled, start from fresh production on `llama.cpp-experimental`, never the frozen production
tree: (1) capture the bounded observe-window attention scores at prefill, (2) implement ordered
top-k chunk selection plus recent-window protection, (3) reuse indices only behind a per-model
ablation, and (4) compare Full KV / current Expected Attention / faithful ChunkKV on a long-context
retrieval and quality suite with the same cache budget. This is an experimental-kernel feature and
needs its own operator-approved measurement window; no implementation or model run is authorized
during the E5 host hold.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-246 | llama.cpp-tq3 — TQ3_1S Weight Quantization | medium | worth_investigating (monitor) |
| intake-245 | MSA: Memory Sparse Attention | low | not_applicable (training-only) |
| intake-828 / 829 | BitNet (2310.11453) / b1.58 (2402.17764) — foundational ternary; bitnet.cpp TQ1_0/TQ2_0 already integrated in the epyc-llama fork | medium | already_integrated |

## Action Items

- [x] Watch PR #21038 for merge — ✅ LANDED 2026-04-01 as commit `744c0c731`, auto-enables in v3
- [x] Evaluate PR #21089 when merged — test TBQ3_0 KV cache on Qwen2.5-Coder-32B context extension ✅ 2026-07-29 — upstream closed the PR unmerged on 2026-06-02 (no `mergedAt`; last update 2026-06-03), and the local tree contains no #21089/TBQ commit. No build, benchmark, or runtime action was taken. Reopen only for a new upstream PR or a merged successor.
- [x] Read ChunkKV paper — assess if implementable in llama.cpp ✅ 2026-07-29 — experimental-only
  feasibility memo above: the required existing substrate is server-side Expected-Attention eviction,
  but a faithful ChunkKV port requires observed-prefill attention capture and ordered chunk selection;
  do not equate the two.
- [ ] Prototype faithful ChunkKV only on a fresh `llama.cpp-experimental` tree after an
  operator-approved long-context measurement window; compare it with Full KV and the existing
  Expected-Attention compactor at equal cache budgets before considering promotion.
- [ ] Revisit TQ3_1S weight quant only if: upstream adopts + multi-model benchmarks + Q4_K_M comparison + CPU kernels

---

## Research Intake Update — 2026-05-21

### AngelSlim toolkit + sub-2-bit weight quantization track

- **[intake-590] AngelSlim toolkit (arxiv:2602.21233)** — Tencent Hunyuan model-compression toolkit. CC-BY-4.0 (per paper) / custom proprietary (per GitHub README) — license inconsistency to resolve before code adoption. Bundles four un-indexed Tencent techniques: Sherry (1.25-bit, intake-591), Tequila (ternary QAT, intake-593), DAQ (delta-aware PTQ, intake-594), SpecExit (intake-592). Verdict: cherry-pick the algorithms + the upstream llama.cpp PR; do NOT adopt the toolkit wholesale (vLLM/SGLang/transformers-first runtime focus).
- **[intake-591] Sherry — 1.25-bit hardware-efficient ternary quantization (arxiv:2601.07892, ACL 2026)** — 3:4 fine-grained sparsity packs 4 weights into 5 bits (power-of-two-aligned 1.25 bpw, SIMD-compatible). Introduces "Arenas" annealing residual synapse to prevent weight-trapping / representational collapse during QAT. LLaMA-3.2-1B: zero accuracy loss vs SOTA ternary baselines, 25% bit savings, 10% speedup on Intel i7-14700HX. AngelSlim/Hy-MT1.5-1.8B-1.25bit-GGUF release is the public reference artefact (440 MB, claimed 1.5x decode speedup).
- **Concrete upstream path**: llama.cpp PR #22836 (STQ1_0 kernel) — sub-2-bit weight quant kernel from Tencent. This is the directly mergeable artefact into our `epyc-llama` fork. Watch consolidated HERE as of 2026-06-12 (formerly on [`llama-cpp-kernel-push-rebase`](../completed/llama-cpp-kernel-push-rebase.md), now archived).
- **[intake-593] Tequila — Trapping-free Ternary Quantization (arxiv:2509.23809)** — QAT method that identifies "deadzone trapping" failure mode and repurposes deadzone-trapped weights as dynamic biases. Claims >4% ARC gain over SOTA ternary, within <1% of FP, 3.0x speedup. Limitation: training-time only — adoption requires Tencent-released Tequila-trained checkpoints (none verified today) or in-house QAT cycle. Deferred.
- **[intake-594] DAQ — Delta-Aware Quantization (arxiv:2603.22324)** — Data-free PTQ preserving post-training deltas (RL / DPO / instruction-tune) via Sign-Preservation-Rate and Cosine-Similarity-of-ΔW metrics instead of reconstruction-error minimization. Claims to recover style-specific capabilities lost under standard PTQ. Limitation: tested in FP8 only at abstract time, where standard PTQ already near-lossless. The load-bearing question (does DAQ help at INT4 / INT2?) is unanswered. Becomes relevant only if/when we move below Q4_K_M. Deferred.

### Delta from this handoff's KV-cache scope

This handoff (`tq3-quantization-evaluation`) tracks **KV-cache** quantization (TurboQuant, TQ3_1S, ChunkKV). The AngelSlim track is **weight** quantization. The portable artefact for both is the same `epyc-llama` rebuild infrastructure but the kernels and PRs are independent. Sub-2-bit weight quant gets its own coordination point: [[angelslim-techniques-evaluation]].

### Caveats (Tier 2b)

- **Sherry is QAT, not PTQ** (correction logged 2026-05-21). Sherry trains on ~10B tokens of UltraFineWeb-style data and cannot be applied to an arbitrary pretrained worker the way GPTQ/AWQ/Q4_K_M can. The STQ1_0 llama.cpp kernel (PR #22836) is generic inference, but real adoption is gated on Tencent (or another party) releasing Sherry-QAT'd checkpoints of a stack-relevant base model. Today only Hy-MT1.5-1.8B and HY-1.8B-2bit are public Sherry-QAT'd weights.
- Sherry evaluated only to 3B params on Intel i7-14700HX (laptop class). Generalization to 7B-122B class on EPYC 9655 (12-channel DDR5, BW-bound regime per `feedback_cpu_decode_bw_bound`) is unverified — the 10% speedup pattern may not transfer.
- All Tequila / DAQ accuracy claims are Tencent self-reported with no third-party reproduction at intake time. ACL 2026 acceptance lifts Sherry credibility specifically (intake-591 credibility=4); intake-593/594 remain credibility=1.

### Action Items (added 2026-05-21; STQ1_0 watch consolidated here 2026-06-12)

- [ ] **Monitor llama.cpp PR #22836 (STQ1_0 kernel) for merge — SINGLE OWNER: this handoff** (consolidated from `llama-cpp-kernel-push-rebase`, archived to [`../completed/llama-cpp-kernel-push-rebase.md`](../completed/llama-cpp-kernel-push-rebase.md) 2026-06-12). On merge: cherry-pick into the next `production-consolidated-v5` (or successor) branch alongside any other pending kernel work.
- [ ] When STQ1_0 lands: llama-bench AngelSlim/Hy-MT1.5-1.8B-1.25bit-GGUF on EPYC 9655 canonical baseline (taskset -c 0-95 -t 96 -fa 1; per `feedback_canonical_baseline_protocol`); compare decode t/s vs Q4_K_M equivalent. If positive at kernel level, note scaling Sherry to worker-class models is gated on a QAT pipeline we do not have (only Hy-MT1.5-1.8B / HY-1.8B-2bit are public Sherry-QAT'd weights).
- [ ] Defer Tequila + DAQ until QAT or sub-4-bit deployment is in scope; not actionable today

## Research Intake Update — 2026-07-02

### New Related Research
- **[intake-756] "NVIDIA Qwen3.6-27B-NVFP4"** (HF model card; official NVFP4 4-bit-float checkpoint)
  - **Relevance:** A concrete, official-NVIDIA **FP8-parity accuracy table** for a two-level block-scaled FP4 format — a useful *external bar* for our CPU 4-bit path (Q4_K_M / TQ3) and a comparison point vs MXFP4. NVFP4 = FP4 E2M1 elements, block_size 16, per-block FP8 E4M3 scale + per-tensor FP32 scale (finer block + higher-precision scale than MXFP4's 32/E8M0). Only transformer-block linears are quantized; attention linears + **KV cache stay FP8**.
  - **Reported results:** near-lossless vs FP8 — MMLU Pro 86.3 (FP8 86.1), GPQA Diamond 85.5 (86.0), AIME 2025 92.7 (93.1), IFBench 65.5 (65.1); ~2.5× memory (16→4 bits/param), ~22 GB weights.
  - **Delta from current approach / verdict = not_applicable (operator-review flagged):** NVFP4 is **GPU-native** (Blackwell/Hopper + vLLM), **not GGUF/llama.cpp-loadable**, and MI210 (gfx90a) has **no FP4/FP8 tensor path** — matching the intake-339 (gemma-4 NVFP4) precedent. Creative uses preserved: (a) the checkpoint's **Apache-2.0 BF16 source is freely re-quantizable to GGUF Q4_K_M/TQ3** for CPU (unsloth already ships Qwen3.6-27B-GGUF, tracked under qwen36-27b-cpu-feasibility); (b) use the FP8-parity table as a target — *does our CPU 4-bit path match FP8 as tightly?*; (c) MTP-head-preserved NVFP4 siblings mirror our MTP direction.
  - **Open question for TQ3 eval:** is a two-level (block FP8 + tensor FP32) scale worth emulating in a CPU K-quant variant, or is the accuracy delta below our decision-gating threshold?


## Research Intake Update — 2026-07-14

### New Related Research — lossless weight-compression sub-area (new to the corpus)
Three URLs plus reference-chasing opened a sub-area the compendium had **no** prior entry for: **lossless, entropy-coded weight compression** (exploiting the highly-skewed BF16 *exponent* distribution). All neighbors to date (TQ3 intake-246, TurboQuant intake-191, REAP intake-181) are **lossy**. Verdict across the cluster: **worth_investigating / adopt_patterns — NOT deployable at our operating point** (all yield ~11–12 bits/weight, ~2.5× larger than production Q4_K_M ~4.5 bpw).

- **[intake-815] "Lossless Model Compression Experiment"** (blog, brianbell-x)
  - Relevance: medium — directionally aligned with our BW-bound decode thesis; a 12-bit GEMV prototype ran at **0.733× BF16 time on an A40** (decode-on-the-fly can beat dense BF16 when bandwidth-bound).
  - Key technique: K15 sign-exponent encoding + byte-split; bit-exact over all 59,509 tensors of GLM-5.2 753B (30.168% smaller, lossless).
  - Delta from current approach: lossless ~11–12 bpw does **not** beat our lossy Q4_K_M footprint; GPU microbenchmark only, CPU decode untested.
- **[intake-816] "ZipNN: Lossless Compression for AI Models"** (arxiv:2411.05239, IBM/MIT-IBM/BU; credibility 4)
  - Relevance: medium — reference lossless-NN method; ~33% BF16 savings, bit-exact; the exponent-skew insight is the core idea.
  - Delta: framed as a **storage/download** optimization (>1 EB/month HF traffic), not inference-time bandwidth; decode ~1.2–2.5 GB/s would compete with our decode bandwidth.
- **[intake-817] "DFloat11 / Dynamic-Length Float"** (arxiv:2504.11651; credibility 4)
  - Relevance: low — bit-exact BF16 → ~11 bpw with a **GPU/CUDA-only** on-the-fly decode kernel; no CPU path, MI210 would need a full HIP port.
  - Delta: ~11 bpw is ~2.4× larger than Q4_K_M; headline 1.85–38.83× gains are vs BF16+CPU-offload, not vs on-GPU lossy quant.
- **[intake-818] "ZipServ: Hardware-Aware Lossless Compression"** (arxiv:2603.17435; verdict adopt_patterns; credibility 4 [audit-corrected from 3])
  - Relevance: low deploy / real conceptual — **fixed-length** (branch-free) exponent code + a **"load-compressed, compute-decompressed" fused GEMM** keeping weights compressed in the bandwidth-critical path. (ASPLOS'26 acceptance declared in the arXiv Comments field — same author-declared basis as ZipNN's IEEE Cloud and DFloat11's NeurIPS 2025.)
  - Delta: NVIDIA-Tensor-Core-locked, benchmarked only vs FP16; 1.51× lossless footprint is dominated by our lossy Q4_K_M.

### Transferable patterns (for a future CPU/ROCm bit-exact path only)
1. The BF16 **exponent distribution is the entire compressibility budget** — a fixed-length ~3-bit exponent code (ZipServ) avoids variable-length serialization stalls.
2. "**Load-compressed, compute-decompressed**" — keep weights compressed on the bandwidth-critical path and decode into registers.

### New outstanding tasks
- [ ] Decide (operator): is lossless exponent-coding worth a CPU/AVX-512 spike **only** as (a) staging/download savings for **full-precision FP16/BF16 source checkpoints retained for re-quantization** (NOT already-quantized GGUFs — those are near-max-entropy and compress negligibly, so the ~238GB UD-IQ2 GLM staging artifact is *not* a beneficiary), or (b) is lossy Q4/Q8 dominance decisive enough to close the lossless-weight thread? Default lean: close for inference, note for storage logistics only if we keep BF16 sources on the 120GB-SSD/3.7TB-raid host. If the storage direction is ever taken, track it under `model-stack-update-pipeline-audit.md` (staging / re-quantization logistics), not here — tq3's scope is lossy quant for the inference path.


## Research Intake Update — 2026-07-16

### New Related Research — PrismML Bonsai-27B + foundational BitNet papers
Batch intake (8 URLs + 3 reference-chased papers). The Bonsai family extends intake-384 (Ternary Bonsai 8B) to 27B; two foundational BitNet papers were genuine index gaps (0 prior matches) despite their descendants being tracked.

- **[intake-820] "Bonsai 27B" announcement** (prismml.com blog) + **[intake-821] Bonsai-27B whitepaper** (24pp PDF, fully parsed) + **[intake-822] Bonsai-demo repo**
  - Relevance: PrismML's post-training binary/ternary weight transform, now at 27B (Qwen3.6-27B base). Self-reported: ternary 80.5 avg @1.71 bpw / 5.9 GB, 1-bit 76.1 @1.125 bpw / 3.9 GB vs FP16 85.0. Ships **GGUF Q1_0/Q2_0 via a PrismML llama.cpp fork (`prism` branch)** with prebuilt CPU/CUDA/Vulkan/ROCm/Metal binaries across 27B/8B/4B/1.7B — materially more EPYC-testable than the intake-384 blog was.
  - Key deltas vs intake-384: adds a 4-bit KV-cache quant with a claim that low-bit weights confer near-lossless KV-quant tolerance (~12–15× less output forward-KL on-policy vs FP16-KV); adds the DSpark speculative drafter; first Bonsai carrying CoT/tool-use intact at 27B; claims the code-gen weakness is fixed (coding 82–86 retained).
  - **✅ Source-claim VERIFIED (2026-07-16 deep-dive):** the claim is correct. **Q1_0 (the 1-bit Bonsai format) is upstream** — llama.cpp PR #21273 by PrismML (`khosravipasha`), merged 2026-04-06 ("support inference for … 1-bit Bonsai models which are native in Q1_0") — and `GGML_TYPE_Q1_0` (type 41) **is already in production-consolidated-v6**. **Q2_0** (PrismML's distinct new ternary type, group-128, *not* upstream TQ1_0/TQ2_0 — see llama.cpp discussion #22019) merged upstream **2026-07-07** (PR #24448 CPU / #25419 Metal; CUDA #25707 open) — **after** the v6 cutover (2026-06-26), so it is **not** in v6. intake-384's 2026-04-17 "Q1_0 not upstreamed" note was already stale when written.
  - Caveat: custom kernels target MLX + CUDA; EPYC production is AVX-512 CPU + MI210 (gfx90a). The GGUF *formats* (Q1_0/Q2_0) and the KV-tolerance / DSpark *patterns* are portable; the kernels are not drop-in. credibility 0–1 (vendor self-report, no independent corroboration). Verdict worth_investigating. `backlog-roi-audit-2026-07-14` already declined pulling the 8B into this watch; the 27B does not change that unless a GGUF + EPYC kernel path is confirmed.
- **[intake-828] BitNet (arxiv:2310.11453)** — the seminal 1-bit-from-scratch / BitLinear paper. Verdict **superseded** by its own ternary successor b1.58 (which EPYC already supports via TQ1_0/TQ2_0). credibility 4. Kept as canonical reference.
- **[intake-829] BitNet b1.58 (arxiv:2402.17764)** — THE 1.58-bit ternary paper underpinning this whole thread. credibility 4, worth_investigating. **Load-bearing distinction:** b1.58 is train-from-scratch QAT (FP16 parity only ≥3B); Bonsai (intake-821) is a POST-training transform. We have no from-scratch pretraining pipeline, so b1.58's headline result is not directly reproducible — its value is as the reference framing the PTQ-transform vs pretrained-ternary axis for the tq3 / AngelSlim / Sherry / Tequila evaluations.

### New outstanding tasks
- [x] Verify the "Q1_0 merged upstream / Q2_0 migrating" claim (intake-822): **VERIFIED** — Q1_0 upstream (PR #21273, already in v6); Q2_0 upstream 2026-07-07 (PR #24448), NOT in v6 (post-cutover). Both PrismML-authored; Q2_0 ≠ upstream TQ1_0/TQ2_0 (discussion #22019). ✅ 2026-07-16
- [x] Bonsai-27B Q1_0 quiet-host CPU+MI210 quality/prompting gate executed on experimental v7: corrected completion-mode runner passed 6/8 strict-output probes (`ok`, minified JSON, simple math on both devices) but failed the six-word instruction probe on both devices. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/bonsai_q1_quality_gate/bonsai_q1_quality_clean_20260717T0755Z/summary.json`. Verdict: loadable/partially coherent, **not role-ready**. ✅ 2026-07-17
- [x] Ternary Bonsai Q2_g64 quiet-host CPU+MI210 quality/throughput follow-up executed on experimental v7: strict gate passed 6/8 only, failing the short-instruction probe on both devices. Raw p512/tg128 control measured MI210 `25.69` prompt / `10.53` decode t/s and CPU `25.27` prompt / `8.39` decode t/s. A realistic MI210 structured-copy CLI pair showed `ngram-mod` improves generation `9.8 -> 22.9` t/s, but this is speed-only because output retained empty `<think>` tags. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/ternary_q2_g64_quality_gate/ternary_q2_g64_quality_20260717Tcodex/summary.json` and `throughput_observation.json`. Verdict: acceleration-interesting, **not role-ready**. ✅ 2026-07-17
- [x] Bonsai-8B Q1_0 current-build MI210 throughput probe executed on experimental v7 `d1e5a20eb`: `/mnt/raid0/llm/tmp/v7-bonsai8b-gpu-bench-current-20260718T141319Z/` used `llama-bench -dev ROCm0 -ngl 99 -fa on -p 2048,8192 -n 1024 -r 3` after relinking the HIP bench target. Results: `pp2048 2349.46 ± 1.11 t/s`, `pp8192 1750.72 ± 0.41 t/s`, `tg1024 38.37 ± 0.01 t/s`; post-run ROCm showed `0%` VRAM and no KFD PIDs. This is speed-only observation evidence; it does not override the Bonsai-27B quality/prompting gate or make Bonsai role-ready. ✅ 2026-07-18
- [x] Bonsai-8B Q1_0 current-build MI210 context repeat executed on experimental v7 `6a8dd5ea6`: `/mnt/raid0/llm/epyc-inference-research/data/bonsai_current_v7/bonsai8b_mi210_context_6a8dd5ea68_20260719T052624Z/summary.json` measured `pp512 2414.00`, `pp4096 2062.67`, `pp16384 1284.44`, `tg1024 36.74 t/s`; cleanup verified no KFD PIDs. This supersedes the older `/tmp` artifact for current-tip speed context but remains speed-only and does not make Bonsai role-ready. ✅ 2026-07-19
- [x] Bonsai-27B Q1_0 current-v7 MI210 `llama-bench` context probe executed on experimental v7 `d1e5a20eb`: `/mnt/raid0/llm/epyc-inference-research/data/bonsai_current_v7/bonsai27_q1_mi210_llama_bench_20260718T150243Z/` used `-dev ROCm0 -ngl 99 -fa on -p 2048,8192 -n 1024 -r 2`. Results: `pp2048 798.59 ± 0.40 t/s`, `pp8192 759.19 ± 1.72 t/s`, `tg1024 11.24 ± 0.00 t/s`. This confirms the local 27B Q1 path remains decode-slow on MI210 and is speed-only evidence; the 6/8 quality gate still blocks role readiness. ✅ 2026-07-18
- [x] Ternary Bonsai Q2_g64 current-v7 MI210 `llama-bench` context probe attempted on experimental v7 `d1e5a20eb`: `/mnt/raid0/llm/epyc-inference-research/data/bonsai_current_v7/ternary_bonsai_q2_g64_mi210_llama_bench_20260718T150707Z/` used `-dev ROCm0 -ngl 99 -fa on -p 2048,8192 -n 1024 -r 2`, emitted only `pp2048 25.68 ± 0.01 t/s`, then remained CPU-bound with `0%` GPU and no decode row until manually terminated. Treat as a current bench-path/acceleration failure and partial speed observation, not quality evidence. ✅ 2026-07-18
- [x] Ternary Bonsai Q2_g64 current-v7 MI210 short-instruction retry executed: `/mnt/raid0/llm/epyc-inference-research/data/ternary_q2_g64_quality_gate/ternary_q2_g64_mi210_short_instruction_current_v7_20260718T151711Z/summary.json` returned `prevents overfitting, ensures generalization, measures true performance.` instead of exactly six lowercase words. This confirms the instruction-following blocker survives the current v7 binary. ✅ 2026-07-18
- [x] Ternary Bonsai Q2_0 raw GGUF layout verifier completed: `/mnt/raid0/llm/epyc-inference-research/data/bonsai_current_v7/ternary_bonsai_q2_layout_contract_20260718Tcodex.json` parses header/tensor-info without `gguf-py` tensor reshape or llama.cpp model loading. Result: Q2_0 has `498/498` Q2_0 tensors short under current-v7 standard 18-byte/block `Q2_0`; sibling Q2_g64 has `0/498` mismatches. ✅ 2026-07-18
- [ ] Parked operator-review candidate (re-scoped 2026-07-19): the GGUFs already EXIST and are public (`prism-ml/Bonsai-27B-gguf` Q1_0 ~3.8 GB; `prism-ml/Ternary-Bonsai-27B-gguf` Q2_0 ~7.17 GB). The **1-bit Q1_0** variant is v7-loadable and partially coherent, but the first CPU+MI210 strict-output gate failed instruction-format compliance; reopen only on a named prompt/template/protocol fix, not broader speed or generic quality churn. The **ternary Q2_g64** variant is acceleration-interesting with MI210 `ngram-mod` on structured-copy tasks, but also failed strict quality and is not role-ready; reopen only on a named quality/protocol fix. The **ternary Q2_0** headline variant is verifier-confirmed noncanonical under current v7; reopen only after an explicit producer/export fix, transcode, or compatibility-loader decision, not ordinary CPU/MI210 smoke retry. NB: quality is self-reported **and independently contested** (gibberish/hallucination/tool-call-collapse reports; no third-party reproduction of the 80.49 avg) — treat as a footprint/density experiment, not a quality win. Append every reopened probe to `docs/reference/model-probe-scoreboard.md`.

## Research Intake Update — 2026-07-21 (QTIP trellis quantization — and we already ship the stubbed kernels)

- **[intake-873] "QTIP: Quantization with Trellises and Incoherence Processing"** (arxiv:2406.11235; Tseng/Sun/Hou/De Sa, Cornell RelaxML) — credibility 4; surfaced by expansion from **[intake-872]** (exllamav3/EXL3, which is a streamlined QTIP variant).
  - Relevance: trellis-coded quantization is a **distinct algorithm family absent from our entire low-bit track** (TQ3/TurboQuant, Sherry, Tequila, DAQ, PrismML are all scalar or ternary). It reaches effective quantization dimension >100 via a bitshift/LFSR trellis with *computed* rather than stored codebooks (1MAD/3INST), on top of Hadamard incoherence processing — the same primitive we already validated and landed for KV cache.
  - **The integration cost is unusually low: our v6 fork ALREADY CONTAINS the iqk trellis kernel family, stubbed out as `return false` because the registry showed zero usage** (see completed `iqk-port.md`). QTIP is the paper that family implements; ik_llama.cpp exposes it as IQ1_KT/IQ2_KT/IQ3_KT/IQ4_KT (1.75-4.0 bpw), using integer 3INST-style arithmetic chosen specifically because 16-bit integer dot products are ~2x faster on CPUs without native fp16.
  - Reported: Llama-2-70B @ 2 bit Wikitext2 3.78 vs QuIP# 3.91 vs AQLM 3.94; Llama-3-70B @ 2 bit 4.97 vs QuIP# 5.77 (largest margin). Decode throughput on par with QuIP# (25.8 vs 25.9 tok/s, RTX 4090).
  - **Three reasons to measure rather than adopt.** (1) The paper **never benchmarks against llama.cpp/GGUF quants** and reports **no CPU number of any kind** — so "QTIP beats IQ-quants at equal bpw" is unsupported in the direction we care about. (2) Our own strongest counter-datapoint: `kv-cache-quantization.md` records TurboQuant full-fix at 573 tok/s vs Hadamard+q4_0 at 1279 tok/s on EPYC 9975 — **2.2x slower**; compute-per-weight dequant has historically lost to plain q4_0 on AVX-512. QTIP's computed codes are cheaper than codebook lookup, so this is suggestive, not dispositive. (3) Zero-shot accuracy at 2 bit is within noise of QuIP# on 3 of 4 tasks — the advantage is concentrated in perplexity, not downstream task quality.
  - Also note exllamav3's own author concedes GGUF i-quants "hold up well" against SOTA formats, so the headroom over what we already run is modest.

- [ ] Operator-review candidate (bounded measurement, NOT a deployment): rebuild on `llama.cpp-experimental` with the iqk trellis kernels un-stubbed and `llama-bench` IQ4_KT/IQ3_KT against production Q4_K_M under the canonical baseline protocol, paired with a correctness/garbage check. Production `production-consolidated-v6` is FROZEN — experimental branch only. Gating question is narrow: does per-weight Viterbi decode cost exceed the bandwidth it saves at our operating point? [intake-873]
- [x] Coordinate the sub-2-bit angle with [angelslim-techniques-evaluation.md](angelslim-techniques-evaluation.md) rather than opening a parallel track. ✅ 2026-07-29 — ownership is now explicit: this handoff retains KV-cache/TurboQuant/trellis investigation; AngelSlim retains QAT weight-quant/STQ1_0 and its public reference artifacts. Both remain experimental-only and deployment-deferred; they share rebuild infrastructure, not a benchmark or promotion claim. [intake-873]

## Deep-Dive Correction — 2026-07-21 (Trellis is NOT a flag flip; but our IQ-quant kernels ARE stubbed under a model we deploy)

Supersedes the trellis actionable in the 2026-07-21 intake section above. Verified against the canonical tree 2026-07-21.

**The trellis bench is 3-6 days, not a flag flip.** The stub is real (`ggml/src/ggml-cpu/iqk/iqk_stubs.cpp:35`), but four things are missing and they compound:
1. `iqk_gemm_ktquants.cpp` is **not in the build** — `ggml/src/ggml-cpu/CMakeLists.txt:55-61` lists only `iqk_mul_mat / iqk_gemm_kquants / iqk_gemm_legacy_quants / iqk_quantize_min / iqk_stubs / iqk_dispatch`.
2. The `block_iq2_kt` / `block_iq4_kt` structs **do not exist in our tree** (only in `/mnt/raid0/llm/ik_llama.cpp/ggml/src/ggml-common.h:670,682`), so the file cannot compile here.
3. The types are synthetic casts OUTSIDE the enum (`GGML_TYPE_IQ2_KT ((ggml_type)153)` … `IQ1_KT 158`) while `ggml.h:433` has `GGML_TYPE_COUNT = 43`. No `type_traits` row ⟹ `ggml_blck_size`/`ggml_row_size` index out of bounds ⟹ **a KT GGUF cannot load at all**. Same OOB class that commit `715383cde` already had to fix for ik-only types.
4. Honoring ik's IDs 153-158 against a dense `type_traits` array ripples into CUDA/HIP per-type tables; the alternative is a sparse shim. Most underestimated item.
Plus: no CUDA/ROCm path, so KT is CPU-only and the MI210 cannot participate.

**And the bpw arithmetic kills the GLM use case.** From ik's static asserts: `block_iq2_kt` = `QK_K/4 + QK_K/64` = 68 B/256 weights = **2.125 bpw**, versus **IQ2_XXS at 2.0625 bpw** — which is what GLM-5.2 actually uses. Trellis is *larger*: zero bandwidth saved, arithmetic added. It is a **quality-at-equal-bpw play mis-framed as a speed play**. Against Q4_K_M the saving is ~17.5%, but our own iqk data (+7.9-8.8% on Q4_K, ~0% on Q8_0) shows we are NOT fully BW-saturated at 4-bit, so added per-weight arithmetic eats into it rather than riding free. ik's own author states KT quants are "generally slower for token generation on CPU due to likely compute bottleneck". Mechanism differs from the TQ3 failure (computed codes vectorize; TQ3's codebook gathers did not — 573 vs 1279 t/s, 2.2x) but the outcome likely rhymes.

**THE ACTUAL CHEAP WIN — and it is the condition `iqk_stubs.cpp:11-12` explicitly warned about.** GLM-5.2 UD-IQ2_M's tensor histogram is `F32 709 | Q8_0 476 | Q5_K 313 | IQ2_XXS 148 | Q6_K 82 | IQ3_XXS 71 | IQ4_XS 4 | IQ2_S 2 | Q2_K 2`. But `iqk_typeA_supported` (`iqk_dispatch.cpp:58`) lists ONLY Q4_K/Q5_K/Q6_K/Q2_K/Q3_K/Q8_0/Q4_0/Q5_0/Q4_1/Q5_1 — **every IQ type is excluded**, and `iqk_set_kernels_iquants` is a `return false` stub (`iqk_stubs.cpp:26`). So `GGML_IQK=1` on GLM-5.2 accelerates attention and shared experts and does **nothing for the 221 routed-expert tensors that dominate both decode bandwidth and prefill FLOPs.**

Unlike KT this needs **none** of the hard parts: `IQ2_XXS=16`, `IQ3_XXS=18`, `IQ2_S=22` are already native v6/v7 enum values (no enum growth, no `type_traits` change, no GGUF change, no requant, no download), and the real kernels are already vendored and complete — `iqk_gemm_iquants.cpp` (202KB) has `set_kernels` cases at `:2760-2791` and the prefill convert path `iqk_convert_iq{2_xxs,2_s,3_xxs}_q8_k_r8` at `:2810-2813`. The known OOB hazard (converters returning ik-only `Q8_K_R8`) already has its `iqk_row_size()` fix landed.

- [ ] **STEP 1 (~1 day, do first):** add `iqk_gemm_iquants.cpp` to `CMakeLists.txt:55-61`, delete the two `return false` lines at `iqk_stubs.cpp:26,31`, add IQ2_XXS/IQ3_XXS/IQ2_S cases to `iqk_typeA_supported` (`iqk_dispatch.cpp:58`). Leave IQ4_XS on the native path (only 4 tensors; no case in the ik file). Expect **prefill-dominant, decode-modest** gains by the iqk pattern — GLM prompts run 3-12K tokens and its measured decode (2.49 t/s no-spec, 5.33 with MTP) is deep in the BW-bound regime. MUST be on `llama.cpp-experimental`; `production-consolidated-v7` is FROZEN.
- [ ] **STEP 2 (gate, needs operator inference approval):** measure IQ4_KT vs Q4_K_M and IQ2_KT vs IQ2_XXS **inside `/mnt/raid0/llm/ik_llama.cpp` as a scratch measurement instrument** — the reference implementation is already on disk, so the whole speed/quality decision can be made without porting anything into v7. Not a second serving binary; a bench harness.
- [ ] **STEP 3 (only if Step 2 wins):** the 3-6 day port. **Decision-flipper:** IQ4_KT must reach >=95% of Q4_K_M tg128 under the canonical protocol AND show a measurable PPL/eval win. Slower than 95% ⇒ DROP permanently — 17.5% fewer bytes that decode slower is strictly dominated.
- NOTE: no IQ*_KT GGUF exists under `/mnt/raid0/llm`, and public KT producers (ubergarm, ik-community) cover the giant MoEs (DeepSeek-V3/R1, Kimi-K2.x, GLM-4.5/4.6/4.7), NOT the models we serve. Viterbi is the *encoding* cost only — decode runs the trellis LCG forward — so self-quantizing is hours on 192 cores plus an imatrix, not prohibitive, but it is not free either.
- NOTE: `/mnt/raid0/llm/llama.cpp-experimental` is a proper worktree on `experimental-v7-refresh-20260716` @ `8bb53c520`, **3 ahead / 0 behind** production — correctly fresh-pulled. It is currently DIRTY with in-flight GDN/CONCAT work, so trellis/iquant work needs its own branch off it, not a merge into that state.

### Ownership moved — 2026-07-21

Both the IQ-quant un-stub and the KT/trellis sequencing now live in **[iqk-iquant-enablement.md](iqk-iquant-enablement.md)** (tasks B1-B5 and T1-T3 respectively), so there is one owner and one ordering. The analysis above stands; the executable tasks moved.

Two corrections to the section above, from the tensor-header parse: the whitelist covers **five** native types (IQ2_XXS, IQ2_XS, IQ2_S, IQ3_XXS, IQ3_S), not three — matching exactly what `iqk_gemm_iquants.cpp` implements in both its kernel and converter switches. And the change benefits **all four** IQ-quant registry models, not GLM-5.2 alone; **Qwen3-Next-80B i1-IQ2_M gains the largest share (433 of 807 tensors, 54%)**.
