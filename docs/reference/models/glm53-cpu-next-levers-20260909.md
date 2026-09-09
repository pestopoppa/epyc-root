# GLM53 CPU reprofile: next high-value work

Completed September 9, 2026, using the canonical 48-thread CPU recipe, the same
six-shard UD-Q4_K_XL model, and native MTP with draft maximum 3. The primary
matched pair uses experimental source `c463f601b`, including the narrow
long-prefill repair `7c78663de`. No performance kernel was changed in this audit.
Production remains frozen and unchanged.

**Recommendation: work on reference-exact multirow Q4_K/Q5_K expert kernels
first, exact batched dense Q8 second, and measured graph/worker scheduling third.**
Expert work is the largest MTP compute group and grows per output token despite
the overall benefit of speculation. It also dominates the remaining prefill math.

## Measured result

Each arm prefills the same 2,029-token input and then generates 512 tokens from
the reused prompt. Both the prefill output and all 512 decode tokens match exactly.
The cached decode refreshes four prompt tokens; retained timing records quantify
that small prefill component. Model loading is outside capture windows.

| Self-cycle group | Plain | MTP | Sampled cycles/output, plain | MTP | Change/output |
|---|---:|---:|---:|---:|---:|
| Q4_K/Q5_K/Q6_K expert math | 22.46% | 31.53% | 6.131 billion | 7.059 billion | +15.14% |
| Native dense Q8 dot | 38.62% | 25.71% | 10.543 billion | 5.756 billion | -45.40% |
| OpenMP runtime | 25.76% | 23.37% | 7.032 billion | 5.232 billion | -25.59% |

Total sampled cycles/output fall 17.98%, although instructions/output rise 40.81%.
Profiled decode is 7.3249 plain versus 8.8855 MTP output tokens/s. These are
**CANDIDATE observations**, one capture per arm, not a replacement for the prior
five-repeat benchmark or a promotion attestation. Self-cycle shares across 48
workers are not wall-time fractions or promised speedups.

The independent 26-token-prompt pair corroborates the ranking: MTP expert work
is 36.78% of self cycles and grows 20.31% per output, while Q8 falls 43.19% per
output. This context dependence is why the long-input matched pair is primary.

## Ranked implementation experiments

1. **Reference-exact multirow expert computation — first priority for decode.**
   Start with Q4_K, then Q5_K. Together they account for 30.51% of long-context MTP
   self cycles. Under row exactness,
   [MulMat::mul_mat_NxM](/mnt/raid0/llm/llama.cpp-experimental-glm53-20260908/ggml/src/ggml-cpu/iqk/iqk_mul_mat.cpp:82)
   calls the single-row function repeatedly for local expert buckets containing
   multiple verification rows. Reuse weight unpacking and scales across those
   rows while preserving each row's current accumulator order, Q8_2_X4 packing,
   row mapping and final reduction. The first experiment should compare every
   output bit with independent Ny=1 calls on the actual expert shapes, then test
   MTP tokens and rejection/replay. Medium/high effort; expert overlap determines
   how much reusable work exists. This is not a claim of reduced DRAM traffic.

2. **Reference-exact two-to-four-vector Q8 verification.**
   [The native Q8 dot](/mnt/raid0/llm/llama.cpp-experimental-glm53-20260908/ggml/src/ggml-cpu/arch/x86/quants.c:1417)
   processes one vector pair. A matrix helper can share weight loads/unpacking
   across independent output rows while retaining a separate original eight-lane
   accumulator, block/FMA order and horizontal sum for each row. This targets
   another 25.71% of MTP self cycles. Medium effort. Widening or reassociating each
   row's reduction would recreate the earlier exactness problem; simply enabling
   IQK for single-token Q8 decode is not the proposed change.

3. **Locate critical-path graph waits, then adapt worker granularity.**
   OpenMP accounts for 23.37% of MTP self cycles; the dominant sampled offset is
   a verified PAUSE/poll loop. Most sampled callchains converge on the graph
   worker loop, so those cycles do not identify one removable barrier. A bounded
   source gap is [mm_batch1](/mnt/raid0/llm/llama.cpp-experimental-glm53-20260908/ggml/src/ggml-cpu/ggml-cpu.c:1444):
   it requires total rows `ne11*ne12*ne13 == 1`, excluding GLM MLA's 64-head
   single-token matrices. Measure those nodes' packing and wait time before
   trying head-parallel packing or worker-private conversion. This local path's
   share of graph-wide waits is unknown; do not credit it with the whole 23.37%.
   Avoid another broad thread sweep or global tiny-op predicate change.

For **prefill**, the remaining identified costs are expert kernels/conversion
32.7%, OpenMP 26.7%, accelerated dense Q8 kernels 10.8%, recurrent/mHC 6.7%, and
attention/indexer 4.4%. Prioritize expert tiling/unpack and conversion reuse for
larger row batches, followed by measured scheduling improvements. The small-row
exact MTP helper and large-prefill tiling are separate paths and need separate
validation. Neither callgraph symbol names nor cache misses prove bandwidth
saturation.

## Correctness findings and rejected shortcut

The initial 2,029-token MTP prefill aborted at `width == mtp_dsa_sel_width`:
selection width grows with the pool across microbatches, but the host export
assumed one fixed rectangle. Prompt catch-up never consumes that export. The
five-line repair suppresses the unused multi-microbatch export and documents
that the getter returns null there; a subsequent single-microbatch drafting
call exports fresh selections normally. Graph/cache arithmetic is unchanged.

The preserved old binary reproduces the assertion with a 257-token/ubatch128
fixture. Both GLM architecture aliases pass the repaired control, including a
fresh 515-wide selection equal to the full-ubatch control. Prefill and next-logit
maximum differences are 2.98e-8 and 4.47e-8, below the declared 1e-5 tolerance;
these are tolerance results, not exact-logit claims. The full-model long
prefill and exact 512-token MTP/plain comparison then pass. The original
experimental tree and its build are updated; the old binary was preserved.

One request-local depth2 control was tested using the actual flat JSON key
`"speculative.n_max": 2`. It was honored, but diverged at generated index 58
(plain/depth3 token 5889, depth2 token 14189) and observed 8.6150 versus 8.8855
output tokens/s. It is rejected, not an adoptable tuning shortcut. An earlier
nested-object attempt was ignored by the server and is retained only as an
instrument diagnostic. The supported evidence here remains the tested depth3
recipe; this audit does not establish exactness for arbitrary draft depths.

The depth3 measured task contains 182 verification events, 329/545 accepted/drafted
tokens, and 110 events with actual rejection. The built-in draft-generation
wrapper accounts for 4.560 seconds, 7.91% of decode time; it excludes catch-up
and other speculative processing. Snapshot/replay work is therefore a secondary
hypothesis requiring separate wall-time attribution, not a measured negligible
cost or the first optimization target.

## Evidence and limits

Primary evidence directories under `/mnt/raid0/llm/tmp/glm53-validation-20260908/`:

- `artifact/run/evidence-profile-fixed2029-plain-t48-20260909T070131Z`
- `artifact/run/evidence-profile-fixed2029-mtp-t48-20260909T065605Z`
- `artifact/run/evidence-profile-fixed2029-mtp-depth2-t48-20260909T070604Z`
- `longprefill-controls-20260909T065500Z` and `longprefill-canonical-controls-20260909T065900Z`

[Independent audit](/mnt/raid0/llm/tmp/glm53-validation-20260908/runtime/profile-analysis-final-t48-20260909/audit.json),
SHA-256 `41628e353a153fd33fd34a9fd95d9ba9b5d41e91064a9350d30dc829e6a62fff`.
[Full source analysis](/mnt/raid0/llm/tmp/glm53-validation-20260908/glm53-next-levers-audit-20260909.draft.md)
uses the earlier 26-token profile numbers; the table above supersedes those
numbers with the repaired long-input pair.

Server SHA-256 `9bc6356b7d9365a58a43e509d39731bddfb3593ce2bd18c0712a1ef2629bdca9`;
libllama `a33c78532eb559a86ce3913e3b006c669555e4edeba3236a89532dc4125a800b`;
libggml-cpu remains `8c5a352b3b899aed15b2dcb827d9a55bbac53f5baece2ec904c9c9043a3024bf`.
Both valid long decode captures have zero lost samples, 321,721/265,593 samples,
100% counter enabled/running ratios, and 48 compute threads carrying over 99.9999%
of sampled periods. All captured servers exited and were confirmed absent;
CPU locks were released. The failed prefill profile is excluded from ranking.

Callchain unwinding is incomplete; self samples cannot fully separate target,
draft and catch-up work or exclude serialized main-thread costs while workers
spin. No UMC/DF bandwidth PMU was exposed. The host remains unrebooted and these
are profiling observations. Fixed-length tests use ignore_eos; broader quality,
natural-EOS, arbitrary-context and GPU/HIP validation are not established here.
