# Kolinko Effort Engine — Deep Dive

**Created**: 2026-05-08
**Source intake**: intake-528
**Source URL**: <https://kolinko.eu/effort/>
**Companion repo**: <https://github.com/kolinko/effort> (MIT, last code commit `46f5269` 2024-04-25, last push 2024-07-01 = `about.html` only)
**Author**: Tomasz Kolinko (single-person Warsaw-based project, 228 GitHub stars, 5 issues total — #5 still open on Mac-only compilation)
**Status**: This is a "decided NOT to pursue" deep dive — written to make the engineering judgment explicit and reusable, not to prepare a port.

## TL;DR

Effort/bucketMul is a 2024 Apple-Silicon Metal/Swift implementation of a real-time-tunable structured-sparse vector-matrix multiplication. The kernel achieves **50–70% of M2 Pro memory bandwidth** at 50% effort and ~2× that at 25% effort — competitive with Apple's MPS GEMV in the Apple-Silicon native FP16 niche where it was hand-tuned. Three portable algorithmic ideas survive a careful read; none are worth the implementation cost on EPYC given our current production stack (Q4_K_M / Q8_0 / TQ3 + MTP drafters), but they are genuinely interesting and worth recording for future cross-reference.

The author honestly concedes via their own KL-distance test that bucketMul **does not beat plain quantization on quality-per-speed**. No third party has produced a CPU / GGML / vLLM port in the 25 months since release. Modern dense and small-MoE models (Llama-3.x / Mistral-NeMo / Qwen3 / Gemma 4) exhibit **far less activation/weight sparsity** than the OPT-class models on which the dynamic-sparsity literature was built — the regime to which Effort belongs is structurally eroded on the targets we actually run.

## What I actually read

Source-of-truth files audited for this deep dive (versus the high-level blog read in the original intake):

| File | Bytes | What it taught me |
|---|---|---|
| `bucketMul.metal` | 8,318 | The whole runtime path: `findCutoff32` (binary-search bisection), `prepareDispatch` (atomic counter scan), `bucketMul` (one-thread-per-output-column gather), `bucketIntegrate` (SIMD reduce). |
| `bucketMul.swift` | 3,413 | The host-side dispatch: `probesCount=4096` hardcoded, `maxDispatchSize=458752`, `mulGroups=32`, `tmpMulVec=[32×16384]`. Effort goes in as `q = (probesCount-1)·(1-effort)` — i.e., absolute count of weights to KEEP, not a percentage. |
| `convert.swift` | 12,677 | Layout precomputation: probes are extracted, weights transposed, sorted-abs per row, bucketized into `[inDim·bSize, outDim/bSize]`, stats `(row, min, max, mean)` computed per bucket. **Q8 packing format `[SvvvvvPPP]`**: 1 sign + 4 value + 3 position. Outliers: top 2% / bottom 1% percentile stored separately for Q8. |
| `convert.metal` | (key kernels) | **`getProbes` is `probes[i] = w[i + i·cols]` — a stride-sample of W, NOT input·W.** This is the most important undocumented finding. |
| `gpu.html` | (blog) | Why bucket size = 16: the position is encoded in the **bottom 4 bits of the FP16 weight** (`as_type<ushort>(w) & 15`). Bucket 32 would need 5 bits → can't fit FP16 mantissa. Bucket 8 → only 3 bits, less precision in sorting → needs higher effort for same quality. |
| `pesky.html` (re-read) | (blog) | Author's own 2024-04-21 update: KL-distance metric "okay-ish. The algorithm seems to not win against Quantization yet." |
| `LICENSE` | 1,071 | MIT (no constraint for our use; not a legal blocker — just an engineering one). |
| Repo metadata | — | Created 2024-03-26, last code commit 2024-04-25 (`46f5269`), final push 2024-07-01 was `about.html` only. **No code change in 24+ months.** |

## Algorithm reconstructed precisely

### Pre-compute (`bucketize` in `convert.swift:209`)

For each weight matrix W with `w.cols = inDim ≥ 4096` and `w.rows = outDim`:

1. **Probes**: extract a 4096-element vector via `probes[i] = w[i + i·cols]` — a stride-`cols+1` diagonal sample of W. **Cost: O(4096) reads, no multiplication.** This is the most important and least-documented design choice: the probes are *raw weight samples used as a per-row magnitude proxy*, not a precomputed activation expectation. The cutoff calculation will use `|probe[i] · v[i]|` as a quick heuristic for "is row i contribution above threshold?".
2. **Transpose + sort**: each row of Wᵀ is sorted by `|w|` descending, indices preserved.
3. **Bucketize**: split each sorted row into chunks of `bSize` (16 for FP16, 8 for Q8). For FP16, the position-within-bucket (4 bits) is **packed into the FP16 mantissa LSBs** of the value itself — so the in-memory weight is the FP16 value with its bottom 4 bits replaced by the position. Decoded at runtime via `as_type<ushort>(w) & 15`. Effective FP16 mantissa drops from 10 bits to ~6 bits (with sign and exponent intact). Author notes the precision is "okay" because each bucket already covers a narrow magnitude range.
4. **Stats**: per bucket compute `(row_id, min, max, mean)` as half4 in `binStats`. Used at runtime to decide whether the whole bucket can be skipped.
5. **Q8 variant**: per-bucket-slice `(minRange, diff)` derived from 5%/95% percentiles. Outliers (>98% percentile or <1% percentile of `|w|`) stored separately. Format per weight: `[S vvvv PPP]` = 1 sign + 4 value + 3 position bits. Quality story: per-bucket range is much tighter than tensor-wide range, so 4 value bits suffice.

### Runtime (per matmul, per token)

1. **`findCutoff32`** (1024 threads): binary-search the cutoff threshold `c` such that `|{i : |probe[i]·v[i]| > c}| ≈ effort`. Bisection over 100 iterations max, terminates at `±3` count tolerance or `|max−min| < 1e-5`. **Returns one float.** Uses a `CUTOFF_SCALE = 100000` multiplier to dodge half-precision underflow on `wq`/`wv` projections where probes can be ~3·10⁻⁵.
2. **`prepareDispatch`** (one thread per `chunkSize=4` buckets): iterate per-bucket `binStats`, evaluate `cutoff < CUTOFF_SCALE · mean · |v[i % rowsCount]|`. If true, **atomically bump `dispatchCount`** and append `(v_val, bucket_id × cols)` to the dispatch list. **The atomic on `dispatchCount` is the dispatch-build's serialization point.** The Metal kernel batches the atomic in groups of `idxIncr=1` (so every survivor pays one atomic) — author's "minor non-determinism" note is exactly this race ordering.
3. **`bucketMul`** (one thread per output column × 32 multiplication groups): each thread maintains a register-allocated `float myVal[16]`. Walks the dispatch list in `STEP=4` chunks: fetch `(v_val, base)`, read `weights[base + bucketID]`, extract position from `& 15`, accumulate via the branchless `for(i=0;i<16;i++) myVal[i] += (pos==i) ? v : 0`. **Branchless gather emits 16 conditional moves per inner step** — looks expensive on paper but hot in registers.
4. **`bucketIntegrate`** (SIMD-group reduce): sum the 32 partial vectors in `tmpMulVec` via `simd_sum`.

**Total kernel launches per matmul: 4** (cutoff, dispatch, mul, integrate). Plus a `roundUp` + `zeroRange32` patch that pads the dispatch size to a multiple of 2048 to dodge subtle off-by-`STEP·bucketSize` errors at boundary effort levels — a hint that the dispatch boundary handling is fragile.

### Why bucket size 16 is forced

| Bucket size | Position bits needed | Fits in FP16 LSBs | Speed (per author) | Sorting precision |
|---|---|---|---|---|
| 8 | 3 | yes (only 3 bits stolen) | slower elsewhere → net flat | worse, needs higher effort for same quality |
| **16** | **4** | **yes** | **best** | **good — same as paper benchmarks** |
| 32 | 5 | no — would need separate index storage | 2× slower | better still |

So the design choice is forced by FP16 mantissa width AND by an empirical "myVal array storage" cliff. From `gpu.html:131-142`: "increasing size of myVal (say to 32) lowers the speed of operation twice; keeping the size intact, but using just a fraction of the values speeds up the operation twice — if you change `& 15` to `& 7`, or modify underlying data to be in a smaller range, you will get a performance boost. Where is myVal stored and at what form? It won't fit the registers, it doesn't go to device memory, so I guess some sort of an intermediate cache?"

This is the author's own acknowledged mystery. The `myVal[16]` is most likely SIMD-group-private register memory on Apple GPU (28 KB per simdgroup on M2/M3), and changing its size pushes it across spill boundaries. **This is an Apple-GPU-specific cliff** and would not directly translate to AVX-512 zmm registers on Zen 5.

### What's broken in the released version (per author)

- **Mistral**: works at 100% effort, KL-equivalent to baseline. Below 100%, "okay-ish" per author's own KL-distance — does not beat plain quantization.
- **Mixtral**: garbage after a few tokens. Author "cannot find the bug" since porting from Mistral.
- **Q8**: "produces total garbage", suspected to be inference-engine bug rather than kernel.
- **Long context**: attention path not optimised; degrades fast.
- **15 ms / token wrapper overhead** at all effort levels (even 0%), independent of the matmul. Author can't isolate the cause; suspects `commandQueue` dispatch / hazard tracking. Caps end-to-end TPS at **~60 tps on M2 Pro**, regardless of what the kernel achieves.

## Comparison to closely related work

| Work | What it does | Where Effort sits relative to it |
|---|---|---|
| **Deja Vu** (Liu et al., NeurIPS 2023, arXiv 2310.17157) | Sparse activations predicted by lightweight predictor (separate small NN). | Effort uses **no predictor** — just `mean(\|w\|) · \|v[i]\|` as proxy. Cheaper but sloppier. Effort's "probes are diagonal weight samples" trick is novel vs Deja Vu's learned approach. |
| **PowerInfer** (Song et al., SOSP 2024, arXiv 2312.12456) | Hot/cold neuron classification for GPU+CPU split inference. | Effort doesn't classify hot/cold statically; the sort is **per-row**, not per-neuron. PowerInfer requires offline neuron analysis; Effort's bucketize requires only sort + stats. |
| **LLM in a Flash** (Alizadeh et al., arXiv 2312.11514, intake-169) | Sparsity-aware loading from flash storage; row-column bundling. | Closest prior in our index. Both target Apple Silicon + sparsity-aware data placement. LLM-in-a-Flash optimises I/O; Effort optimises compute under DRAM. The "skip trailing rows at load time" idea in Effort is a poor man's load-time pruning version of LLM-in-a-Flash's bundling. |
| **Wanda** (Sun et al., ICLR 2024, arXiv 2306.11695) | Pruning by `\|activation\| × \|weight\|` at calibration time. | Effort is **dynamic Wanda**: same scoring metric, applied per token instead of once at calibration. Wanda is well-validated; Effort dynamizes the same idea but inherits all its quality/sparsity-rate caveats. |
| **SparseGPT** (Frantar & Alistarh, ICML 2023, arXiv 2301.00774) | One-shot Hessian-based pruning. | Effort uses no Hessian, no second-order info. Cheaper, lower quality at same sparsity. |
| **TEAL / activation sparsity** (multiple 2024 papers) | Threshold-based activation sparsity at runtime. | Effort's `prepareDispatch` cutoff IS a threshold mechanism — same family. |
| **MegaBlocks** (intake-467 in our index, arXiv 2211.15841) | Sparse expert dispatch via blocked-CSR-COO indexing. | Different problem: MegaBlocks routes batched MoE tokens to experts. Effort routes within a single dense matmul. The "indexing scheme over sparse blocks" pattern is structurally similar. |

**Bottom line**: Effort sits in the dynamic-activation-sparsity family, alongside Deja Vu / PowerInfer / Wanda-applied-dynamically / TEAL. The novel parts are not the algorithmic class but the data-layout tricks (positional LSBs, bucket sort, probe-as-diagonal-sample) and the runtime ergonomics (real-time effort dial, load-time row drop). It is not a state-of-the-art quality method and the author publicly concedes this.

## Three portable artefacts

Of everything in Effort, three ideas are genuinely portable and not redundant with what we already have. None individually justifies a handoff stub, but they are worth recording for future cross-reference.

### Artefact 1: load-time trailing-bucket skip ("ad-hoc distillation by mmap")

**The idea**: Once a weight matrix is laid out as sorted-by-importance buckets, the trailing 10–30% of buckets are by construction the least important. **Drop them at mmap time** — no model conversion, no calibration. Author claims "the model may not even notice" at 20–30%.

**EPYC fit**: ~0%. We use Q4_K_M / Q8_0 / TQ3 via standard ggml repack formats. None has a "trailing bucket" concept because none sorts within blocks by importance — K-quants block-quantize 32 / 64 weights and store per-block scale + zero-point with no within-block reordering. To realize this artefact on our stack, we would need a **new repack format** (`Q4_K_BUCKETED` or `FP16_BUCKETED`) — comparable cost to landing a new K-quant.

**Where it could matter on our stack**: if for a *different reason* we ever build a sorted-bucket repack format (e.g., for shape-specialized GEMV per-block early-exit), the trailing-bucket skip is a free additional dial. **Re-surface trigger**: a sorted-bucket repack lands in `cpu-shape-specialized-gemv-decode.md` for some other reason, then add trailing-skip.

### Artefact 2: per-token "effort dial" as a quality-budget primitive

**The idea**: Expose a single scalar `effort ∈ [0, 1]` to the inference API that proportionally reduces compute. The caller can dial up/down at every token without recomputing model state.

**EPYC fit**: ~10%. We currently have **zero** per-token compute-budget primitives. Compute-effort is decided per-model (which model in the registry routes the question), not per-token. Three handoffs in our active set could compose with a per-token effort dial:

| Handoff | Composition |
|---|---|
| `routing-intelligence.md` | Currently chooses a model per request. An effort dial would let it choose a model + an effort level — finer-grained and possibly cheaper than swapping models. |
| `per-request-reasoning-budget.md` | Already has the budget abstraction at the reasoning-step level. An effort dial would push the budget down to per-matmul. |
| `decision-aware-routing.md` | Same — finer-grained delegation. |

But: an effort dial only *makes sense* if the underlying matmul kernel actually supports proportional compute reduction. **None of our ggml/llama.cpp kernels do** — they either run the full matmul or skip it entirely (via MoE expert dispatch). Implementing kernel-level effort would mean either (a) the bucketized-repack route from Artefact 1, or (b) a coarser layer-level effort (skip layers? — falsified for hybrid models in `mtp-speculative-decoding.md`). **Re-surface trigger**: any of the three routing/budgeting handoffs activates AND we have a kernel that supports effort.

### Artefact 3: probe-as-diagonal-sample for cheap row-magnitude estimation

**The idea**: For any sparsity-prediction work, you can estimate "is row i of W likely to contribute meaningfully to W·v?" via `|w[i, i] · v[i]|` (single weight × single input element) as a proxy for `|W[i,:] · v|` (full row dot product). Cost: O(1) per row vs O(d) per row.

**EPYC fit**: ~5%. We have no active sparsity-prediction work — the closest is `decision-aware-routing.md`, which routes at the request level not the matmul level. **The probe trick is most valuable as a comparison point against Deja Vu's learned predictor** if we ever evaluate dynamic-sparsity methods. **Re-surface trigger**: dynamic-sparsity literature re-enters scope.

## Why not pursue this on EPYC

A direct port to ggml/llama.cpp would cost roughly **1 staff-month** (new repack format, new GEMV kernel for the bucket layout, AVX-512 implementation of the branchless gather, dispatch-list management, integration tests, cross-arch validation). Compare against:

| Lever | Status (May 2026) | Expected gain |
|---|---|---|
| **CPU2 8×8 Q8_0 AVX-512BW kernel** | LANDED | +31.8% @ 1t, +1–3% @ 12–96t (BW-saturated); proven |
| **wdata-aware MUL_MAT coalescing** | Phase 0 design done | Q/K/V chain barrier reduction, est +5–10% |
| **CPU18 MegaBlocks blocked-CSR-COO MoE indexing** | Designed, not implemented | Per-expert padding/drop elimination on MoE |
| **Gemma 4 31B + MTP drafter (intake-527)** | Production-viable, +198% measured (7.05 → 21.02 t/s on EPYC) | **2.98× drafter speedup landed, no new repack** |
| **Effort/bucketMul port** | Hypothetical | Author concedes vs. quantization. Best honest case at 25% effort with proper FP16 storage = 2× weight read reduction, but adds 4 kernel launches per matmul + atomic dispatch contention. On CPU with 460 GB/s aggregate BW + ~10 GB/s/core OMP scheduling overhead, the launch tax likely overwhelms. **Realistic upside: 1.2–1.5× at 30–50% quality cost vs. Q4_K_M.** Below MTP's 2.98× and below CPU2's already-shipped 31.8% at 1t. |

The opportunity cost is the binding constraint. There is no scenario in which Effort beats the existing roadmap on quality-per-staff-hour.

## Staleness signals (additive to the original intake)

- **Last code change 2024-04-25** (`46f5269`); only 5 issues ever filed; issue #5 (open) is *"Compilation out of MacOS"* — i.e., **nobody has even tried to port to Linux**, let alone CPU/ggml.
- **No academic citations**: searching arXiv and Semantic Scholar for "bucketMul" returns no follow-up papers. The most recent "Show HN" thread (id=40067677) is the only public discussion record.
- **No third-party fork has shipped** any port (vLLM, MLX, llama.cpp, transformers).
- **Author's other GitHub work since 2024-07-01 is unrelated** (no Effort-derivative project).
- **Sparsity headroom on the targets we run** (Llama-3.x, Mistral-NeMo, Qwen3, Gemma 4) is far below the OPT-class numbers Deja Vu / PowerInfer were calibrated on — independently confirmed by NimbleEdge's 2025 white paper and the ICLR 2025 SLLM workshop materials.

## Verdict refinement

**Original intake-528 verdict**: `worth_investigating` — kept.
**Deep-dive refinement**: `worth_investigating` for the **three portable artefacts** as discrete cross-reference targets, not for a port. The deep-dive itself functions as the closure record: any future "should we look at Effort?" question is answered by this file.

### Re-surface triggers (machine-readable, copied into intake-528 verdict_justification)

- A sorted-bucket repack format lands in our ggml fork for an unrelated reason → revisit Artefact 1 (trailing-bucket skip).
- `routing-intelligence.md` / `per-request-reasoning-budget.md` / `decision-aware-routing.md` activates AND we have a kernel that supports proportional effort → revisit Artefact 2 (effort dial composition).
- Dynamic-activation-sparsity (Deja Vu / PowerInfer / TEAL family) re-enters scope → revisit Artefact 3 (probe trick) AND the full algorithm.
- An Apple-Silicon backend re-enters scope (currently not a deployment target).

## Open questions deferred

These came up in the audit and would matter only if a re-surface trigger fires. Recording so the next session doesn't have to rediscover them.

1. **Does `myVal[16]` actually live in registers on Apple GPU, or in threadgroup memory?** Author doesn't know. Resolving would clarify the Apple-vs-EPYC portability ceiling — if it's threadgroup memory (32 KB per simdgroup on M2), the AVX-512 zmm equivalent would be 16 zmm regs per thread on Zen 5 = ~512 bytes/thread, plenty for `float[16]`.
2. **What's the actual KL-divergence-vs-quantization curve?** Author claimed "okay-ish" but never published. We could in principle reproduce on Apple Silicon — but would require Apple hardware we don't have and don't plan to acquire.
3. **Is the probe-as-diagonal-sample cost-effective vs. an actual 1-token activation probe?** An activation probe (run `v` through, take max) costs O(d) per matmul. Effort's diagonal probe costs O(1). The quality gap between them is unmeasured.
4. **Could the CPU2 8×8 AVX-512BW kernel be modified to accept a "block mask" input** (one bit per 8-element block, skip if zero) to deliver Effort-like dynamic sparsity without changing the storage format? This would be a much cheaper path than a full bucketized repack and could ride the existing kernel infrastructure. **Open question — not pursued in this deep dive.**
