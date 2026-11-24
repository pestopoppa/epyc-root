# Dive — tmblog — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/", retrieved: "2026-11-24", sha256: "d9396e86fb5a"}

Stage 2b wave 1 light dive. Bearing entry: exactpaper (intake-2872), ledger row A7. Expansion source for A7.

## 1. Stage-1 fields

- title: Defeating Nondeterminism in LLM Inference (Thinking Machines Lab, "Connectionism")
- authors: Horace He and others at Thinking Machines Lab
- date: Sep 10, 2025 (blog; no version). source_type: blog
- categories: inference_serving, hardware_optimization, benchmark_methodology
- novelty: medium. The mechanism (batch-size-dependent reduction order, not atomics) is stated here and then reused by exactpaper, divloc and x2605 as background; the per-op remedies are the new content.
- relevance: medium-high for A7 only. It is the cost model for a zero-floor audit arm; it does not change a served path.
- credibility_score: 1. +1 known contributor (Thinking Machines Lab); +0 date (about 14 months old, so not <=12 months and not >24); +0 commercial-bias adjustment (educational post); +0 corroboration (exactpaper's batch-invariant arm uses the same family of kernels, so it is a restatement of the remedy, not independent). Not peer-reviewed (+0).
- verdict: adopt_patterns. Adopt the per-op invariance rules (one reduction order per element regardless of batch width; fixed-size KV splits) as the design contract for a HIP audit arm. Do not adopt as a serving mode (the post's own numbers show 1.6-2.1x slowdown, section 3).

## 2. Key claims

0. **Only three ops need batch-invariant versions: RMSNorm, matmul, attention (CONFIRMED, with a CPU caveat).** Pointwise ops are assumed invariant; the post warns that some CPU kernels use vectorized intrinsics on part of an array and scalar on the rest with non-identical numerics. Anchor: page, section "How do we make kernels batch-invariant?", "Thus, we only need to worry about the 3 operations that involve reductions—RMSNorm, matrix multiplication, and attention".
1. **Atomics are not the cause; the loss of batch invariance is (PARTIAL for our stack, reattributed).** The post says the LLM forward pass has no atomic adds, so it is run-to-run deterministic, and the nondeterminism seen by a user comes from load-dependent batch size. In-house C21 contradicts the premise for the MI210 path: `mmq-q8-skinny.cu` flushes with f32 `unsafeAtomicAdd` ("Summation order across waves is not deterministic", 2-3 flushes per output element) and `mmq-q8-mf.cu:1454` also uses `unsafeAtomicAdd` (@ 98ff8a4). So on our GPU both mechanisms are live: run-to-run nondeterminism from atomics AND batch-width dependence. Anchor: page, section "When are atomic adds needed?", "the forward pass of an LLM involves no operations that require atomic adds".
2. **Remedies and their stated cost (CONFIRMED as stated by the authors).** (a) RMSNorm: data-parallel, one row per core; split reductions only appear at small batch and are best ignored. (b) Matmul: compile ONE kernel configuration for all shapes, no split-K; "we only lose about 20% performance compared to cuBLAS" and the loss concentrates at very small batch. (c) Attention: update KV cache and page table before the kernel so the reduction layout is independent of how many query tokens are in flight; use a FIXED SPLIT SIZE for split-KV (fix the size of each split, let the count vary), not a fixed split count. Anchors: page, section "Batch-invariant matrix multiplication", "So, the easiest way ... compile one kernel configuration and use that for all shapes"; section "Batch-invariant attention", "instead of fixing the # of splits, we fix the size of each split and then end up with a varying number of splits".
3. **Measured effect (CONFIRMED).** Qwen3-235B-A22B-Instruct-2507, 1000 completions at temperature 0 of one prompt, 1000 tokens: 80 unique completions, most common 78 times, first divergence at token 103 (992 vs 8 completions). With batch-invariant kernels all 1000 identical. Hardware for this experiment: NOT-FOUND-IN-SOURCE. Anchor: page, section "How nondeterministic are completions?", "we generate 80 unique completions, with the most common of these occuring 78 times".
4. **Throughput cost (CONFIRMED, small sample).** Qwen-3-8B on one GPU, 1000 sequences of 90-110 tokens: vLLM default 26 s, unoptimized deterministic 55 s, with improved attention kernel 42 s. That is 2.1x and 1.6x the default wall time (dive arithmetic). GPU model: NOT-FOUND-IN-SOURCE. Anchor: page, section "Performance", "vLLM default 26 Unoptimized Deterministic vLLM 55 + Improved Attention Kernel 42".
5. **Code availability (CONFIRMED, narrowed).** The library is `thinking-machines-lab/batch-invariant-ops` with a vLLM FlexAttention example, but the fixed-split-size attention "requires some internal FlexAttention changes that are not included in our code release". Anchor: page, section "Batch-invariant attention", "This requires some internal FlexAttention changes that are not included in our code release".

## 3. Reported results

- Qwen3-235B-A22B-Instruct-2507, temp 0, 1000 samples x 1000 tokens: 80 unique completions, modal count 78, first divergence token 103, "Queens, New York" 992 vs "New York City" 8; invariant arm 1000/1000 identical (hardware not stated).
- Qwen-3-8B, one GPU, 1000 requests of 90-110 output tokens: 26 s default; 55 s unoptimized deterministic; 42 s with improved attention kernel.
- Matmul: about 20% below cuBLAS with one tile configuration (Triton, no TMA); worse at very small batch from oversized instructions and low parallelism; "jigsaw" tile/wave quantization pattern.
- True on-policy RL (Qwen 2.5-VL 8B, RLVR on Bigmath): bitwise sampler/trainer parity gives flat 0 KL; not relevant to this stack.

## 4. Performance-principles table

| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| Per-row data-parallel RMSNorm (reduction order independent of batch) | YES, ALREADY TRUE: `norm.cu:347-370` launches one block per row, `blocks_num(nrows, nchannels, nsamples)`, block size chosen from `ncols` only (1536 -> 384, <1024 -> 256, else 1024), so the order is fixed per shape and independent of rows (@ 98ff8a4). Port cost 0, verify only | PARTIAL: CPU norm not read in this dive; `GGML_ROWEXACT_N` already forces single-row kernels for matmul (ggml-cpu.c:1505, 1712-1747 @ 98ff8a4) |
| One matmul kernel config for all n (no split-K, no shape-dependent tile) | PARTIAL, MAIN COST: dispatch changes reduction order with n. `calc_nwarps(type, ncols_dst, ...)` returns 4/2/1 warps by ncols_dst on the generic table and AK deliberately set nwarps=8 for CDNA2 Q8_0 bs=1 ("numerically-valid-not-bit-exact", `mmvq.cu:813-850`); skinny (n 5..16, stream-K atomics) and mmq-q8-mf/wvsk and MMQ take over at higher n; f16/bf16 route through hipBLAS (`ggml-cuda.cu:1712-1777`). Needs one pinned per-column reduction geometry for n=1..16 | YES, exists as opt-in: `GGML_ROWEXACT_N`, `LLAMA_SPEC_EXACT=row\|serial` (server-context.cpp:42-112, 1881 @ 98ff8a4); cost is speed |
| No atomic flush (fixed-order cross-wave combine) | PARTIAL: skinny's stream-K f32 atomic flush must be replaced by owner-ordered combine (the `mmq-q8-mf` family already documents WG-ordered sums); or set `GGML_HIP_Q8_SKINNY=0` (documented fallback "exactly as C6") | NO issue: CPU path has no atomic cross-thread flush in the matmul (not exhaustively read) |
| Fixed-size KV split for split-KV attention; KV written before kernel | PARTIAL: `fattn-common.cuh:1514-1594` chooses `parallel_blocks` from occupancy and n_kv (plus long-context override env), and the combine loop at :1339-1345 sums parts in index order, so the combine is deterministic for a given count but the COUNT varies with query width and context. Port: derive splits from a fixed KV-chunk length instead of from occupancy. vec vs tile/mma kernel choice by n must also be pinned (n=1 vs verify width) | PARTIAL: CPU flash-attn chunking uses thread-count-dependent chunk order (ops.cpp:10269 "fixed chunk order for fixed nth" per exactpaper dive); fixed for fixed nth, not for varying batch |
| Greedy tie-break determinism (not in this post) | n/a here; x2605 reports a top-k=1 race in LMDeploy. Check in-house device argmax tie rule | same |

## 5. In-house state

- No batch-invariant mode at C21 (exactpaper dive section 5, confirmed again by grep @ 98ff8a4). Closest: CPU `GGML_ROWEXACT_N`, `LLAMA_SPEC_EXACT=row|serial`.
- The width dependence is by design on GPU: `mmvq.cu:813-850` documents that CDNA2 bs=1 Q8_0 uses nwarps=8 and is "numerically-valid-not-bit-exact"; the 27B verify path at n>=5 goes to skinny (`GGML_HIP_Q8_SKINNY_MIN` default 5, MAX 16) which uses atomics. So width-1 vs width-W identity cannot hold on GPU by construction, which is consistent with SPEC-ID-NOISE-1 (GPU DFlash2 M1-M2 20/64 across launches; REDECODE_FAIL_CONFIRMED, `speculative-decoding.md:908 @ f74b175`).
- Attention: vec kernel with parallel_blocks (`fattn-vec.cuh:547` completion-counter atomic, fixed-order combine), stream-K fixup path for tiles (`fattn-common.cuh:1106-1270`).
- The served path reaches all of these; none is gated by a determinism flag.

## 6. Derived-actionables ledger

All rows refine exactpaper A7 ("estimate port cost of a GPU batch-invariant control arm"); none duplicates it.

| # | Task line | Owner (lane) | Compute | Stop / decision rule |
|---|---|---|---|---|
| T1 (refines exactpaper A7) | Write the per-op invariance census for the MI210 verify graph of 27B Q8_0 + DFlash2 at widths 1..16: for each op (rms_norm, mmvq, skinny, mmq-q8-mf/wvsk, hipBLAS bf16 drafter GEMM, fattn vec/tile, GDN tree kernel, argmax) record whether its reduction order depends on n or n_kv, whether it uses atomics, and the kernel route per width. Output: one table with the minimum code change per op | `rocm-kernel-authoring.md` (ACTIVE; per-op work there) | code/doc-only | Question: what is the smallest set of kernel changes that makes width-1 and width-W bit-equal on GPU. Stop-on-answer when every op has a classified verdict. Decision: if <=3 ops need change, open an implementation box for an audit-arm build; else keep margin classes only |
| T2 (refines exactpaper A7) | Probe the cheap lever first: rerun the SPEC-ID-NOISE-1 GPU A/A (same config, two launches, np1, 64 prompts) with `GGML_HIP_Q8_SKINNY=0` and report the launch-to-launch divergence count against the 20/64 baseline | `speculative-decoding.md` (SPEC-ID-NOISE follow-up under SPEC-ID-GATE-1) | GPU row (27B DFlash2, MI210) | Question: is the run-to-run drift from skinny's atomic flush. Stop-on-answer: 0/64 means atomics are the source and a fixed-order skinny is the minimal fix; >=1 means another source (fa parallel_blocks, hipBLAS, argmax) and T1 continues. Hypothesis only: the dive did not verify skinny is selected on every divergent position |
| T3 (refines exactpaper A7) | Prototype fixed-KV-chunk-length splitting in the vec flash-attn kernel behind an env flag (split count = ceil(n_kv / chunk)), keeping the existing index-order combine, and compare width-1 vs width-8 outputs bitwise on a fixed context | `rocm-kernel-authoring.md` | code, then a small GPU bitwise test | Question: does fixed-size splitting alone make attention n-invariant on gfx90a. Stop-on-futility if vec vs tile route still differs between n=1 and n=W (then pin the route too) |

Declines:
- Decline: adopting the post's full deterministic mode as a SERVING configuration. Reason specific to this entry: its own measurement is 1.6-2.1x wall time (26 s vs 42-55 s) and production here is speed-bound speculative decoding; the value is as an audit arm for identity gates only.
- Decline: the true on-policy RL section; no sampler/trainer pair is in the AutoKernel lane (not checked beyond lane greps).

## 7. Dive-surfaced sources

Index grepped unbounded (417,859 lines at f74b175): `defeating-nondeterminism` 0 hits (this entry); `batch-invariant-ops` 0 hits.
- github.com/thinking-machines-lab/batch-invariant-ops: ABSENT. Would supply reference Triton kernels for fixed-config matmul and RMSNorm. Would not change T1-T3 (the pattern is already stated; kernels are CUDA/Triton, not HIP). Decline; reopen only if T1 opens an implementation box.
- No other source surfaced.

## 8. Contradiction / adversarial pass

- Mechanism premise partly wrong for us: the post says LLM forwards have no atomics; our skinny and mq-q8-mf paths do. The post's remedies therefore do not suffice alone on this stack (atomic flush must also go).
- The post's strongest evidence is one prompt on one 235B model; hardware unstated. Overhead numbers are on an unoptimized FlexAttention path and a single 8B run; the authors call them not optimized.
- exactpaper (intake-2872) reports batch-invariant arms at 0.00% flips in vLLM, which is evidence the remedy works there; it uses the same kernel family and is not independent of this post.
- The post defines batch invariance per request vs concurrent requests, i.e. serving load. Our spec verify width is a different axis (draft width), but the same mechanism: the kernel route depends on row count.

## 9. Read depth

read_depth: FULL (entire page.txt, 38.9 KB). In-house kernels read: norm.cu launcher, mmvq.cu calc_nwarps comments, mmq-q8-skinny.cu header, fattn-common.cuh launch/combine, fattn-vec.cuh completion counter; not read: mmq-q8-mf/wvsk bodies, hipBLAS dispatch details, CPU norm/flash-attn bodies. lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit

artifact audit: clean
