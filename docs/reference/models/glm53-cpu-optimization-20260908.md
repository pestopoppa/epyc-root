# GLM-5.3 Flash CPU optimization — experimental implementation report

**Status:** implemented and tested on the private experimental candidate at canonical 48 threads, September 8–9, 2026. Production remains unchanged. Performance figures are observations, not promotion attestations.

**September9 follow-up:** [Reprofiling and next levers](glm53-cpu-next-levers-20260909.md)
exposed and fixed a multi-chunk long-prefill MTP assertion. Current experimental
source is `c463f601b`; the historical benchmark identities below remain intact.
Depth3 passes the new long-input comparison; a depth2 diagnostic fails parity.

## Candidate and scope

The implementation is commit `04ffb8ad0` (`cpu: gate Q8 prefill and scope row-exact MTP verification`) on `experimental/glm53-text-mtp-20260908`, based on champion `ef81196d5bdd4190b46dff4ae7eecc333a46c8ce`. It retains the text-only GLM5Next and native embedded-MTP port adapted from pinned upstream heads `8134115f88ed8018474e7db69afcfe97fb097fc4` and `5b8593b5451ec45fd4a81fb844efb6be9b45fd36`. GLM vision code is excluded.

The change implements three high-value outcomes:

1. **Q8 prefill dispatch.** `GGML_IQK_Q8_0_MIN_ROWS` gates IQK Q8_0 by the logical token-row dimension. The final threshold is 32, so long prefills reach the faster IQK route while one-token decode and three/four-row target verification keep their existing kernels. MMID uses `ids->ne[1]`, excluding top-k expansion; dense MLA uses `src1->ne[1]`, excluding its 64-head broadcast dimension.
2. **Logical row-exactness.** Dense IQK decides row-exact eligibility from full `Ny` before internal tiling, and MMID decides it from the global logical batch before per-expert bucketing. A 40-row prefill tail or small expert bucket inside a 26-token prompt can no longer activate a decode-only threshold by accident.
3. **Exact parallel target verification.** `LLAMA_SPEC_EXACT=row` enables row-exact CPU kernels only for target batches whose rows are explicitly tracked speculative-verification rows. Prompt processing, ordinary decode, and the draft context remain disabled. The policy is carried per computation through the CPU backend, `ggml_cplan`, and compute parameters; cached plans refresh it at execution time, and an RAII guard restores the target context on all exits.

The third item is the demonstrated decode lever. It preserves parallel verification so accepted draft tokens amortize weight streaming and graph synchronization. This work did not add or claim a faster single-token Q8 dot kernel: the profile showed the generic Q8 dot path as a major sampled-cycle consumer, but the existing IQK Q8 route improved the isolated 2K-token prefill profile and did not demonstrate a material decode gain.

## Qwen optimization reachability

The champion Qwen kernel audit found that GLM already reaches the reusable high-value paths:

- IQK MoE and the default MMID expert-row slab are active for GLM's top-8-of-288 Q4_K/Q5_K/Q6_K experts.
- row/column splitting, empty-work skipping, and eligible one-row solo scheduling are architecture-neutral and compiled in.
- IQK QSPLIT is reachable for qualifying multi-row dense Q8 prefills after the new gate.
- fused gated-delta-net, lightning-indexer, DSV4 mHC, and flash-attention operations are constructed by the GLM graph and observed at load/runtime.

No missing GLM architecture whitelist was found for a proven Qwen decode kernel. `GGML_VEC_Q8K` serves IQ2/IQ3/IQ4_XS weight families rather than GLM's dominant dense Q8_0 and K-quant expert weights. The whole Qwen4Exp fused decoder remains architecture-specific and the canonical recipe keeps `GGML_FUSED_DECODE_OFF=1`. Prior global tiny-solo widening, AVX-512 loop experiments, and broad Qwen fusion transplants were measured neutral or negative and were not revived.

Detailed reachability evidence and source gates are in [the candidate audit](/mnt/raid0/llm/llama.cpp-experimental-glm53-20260908/tests/glm53/GLM_QWEN_OPT_REACHABILITY.md). The original sampled-cycle evidence is in [the profiling report](glm53-cpu-profile-20260908.md).

## Short correctness gates

- The real-model phase test passed six of six exact comparisons with maximum absolute logit difference zero: split-22+4 prompt preservation, off/on/off reused-context restoration, two verification batches, and rollback continuation. Evidence: `runtime/rowexact-phase-gate-20260908T233319Z`; result SHA-256 `f293f7840f25f57f29eb99501876a91313de60112af8d04083adcf4d80eec462`.
- A fresh 64-token plain run and a fresh 64-token native-MTP run both matched the preserved original token stream exactly, including generated token 6 = 1246. The MTP run exercised both accepted and rejected draft groups, accepted 43 of 59 drafts, and observed 11.8393 tokens/s; this is a bounded correctness run, not the final throughput estimate.
- GLM rollback passed all 12 acceptance cases for both `glm5next` and `glm5-next`; used-MTP restore matched logits and selection; pool/chunk checks passed six of six. The champion Qwen recurrent rollback fixture also passed. Evidence bundle: `runtime/final-tiny-regressions-20260908T234004Z`, digest prefix `ebb77d64`.
- Q8 boundary dispatch was inactive at logical rows 1, 4, and 31 and active at 32, 33, 40, and 48. Dense Ny 40/48 and MMID global-26 Q8/Q4 controls were byte-identical between N=0 and N=16; four-row MMID batches matched four single-token calls.
- A cached CPU-plan F32 test produced an actual row-exact arithmetic difference witness and restored byte-identically after off→on→off. Synthetic IQK dense-Q8 and MMID-Q4 fixtures also restored byte-identically, but their selected inputs happened to be identical with row exactness enabled and disabled, so they are policy-restoration checks rather than difference witnesses.

## Final CPU recipe and identities

The committed build identifies source `04ffb8ad0` and uses:

- `llama-server`: `8ce86a370cad067bcc1e9b2bacc7ca74364ab6a94df1d2f3546284c95de3c9fe`
- `libggml-cpu.so`: `8c5a352b3b899aed15b2dcb827d9a55bbac53f5baece2ec904c9c9043a3024bf`
- `libllama.so`: `f81b1fc28c677ff93fd117ab94413d3ce7962714a399fad448d4411485c4e07f`
- `libllama-server-impl.so`: `a3ad4f4554942cad305d7fc32d50f6cf95557d298e2339e7e89f09db186a8c60`

The canonical CPU launch uses cores 0–95 with 48 compute threads and interleaved NUMA placement:

```text
env -i \
  GGML_FA_SPLIT_KV=0 GGML_FUSED_DECODE_OFF=1 GGML_IQK=1 \
  GGML_IQK_Q8_0=1 GGML_IQK_Q8_0_MIN_ROWS=32 GGML_ROWEXACT_N=16 \
  GGML_NOHUGEPAGE_PROCESS=1 LLAMA_SPEC_EXACT=row LLAMA_TRACE=1 \
  OMP_DYNAMIC=false OMP_PLACES=cores OMP_PROC_BIND=spread OMP_WAIT_POLICY=active \
  LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-experimental-glm53-20260908/build-glm53-cpu/bin \
  PATH=/usr/bin:/bin \
  taskset -c 0-95 numactl --interleave=all \
  .../llama-server --no-webui -np 1 -c 8192 -t 48 --no-mmap -lv 4 \
  --device none -ngl 0 -fa on -ctk f16 -ctv f16 \
  -m .../GLM-5.3-Flash-UD-Q4_K_XL-00001-of-00006.gguf --reasoning off
```

The native-MTP arm adds `--spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-p-min 0`; it does not use a separate `-md` model. `LLAMA_SPEC_EXACT=row` currently requires `-np 1` and a positive `GGML_ROWEXACT_N`; invalid or mixed prompt/verification batches are refused rather than silently changing arithmetic.

## Final composite results

All rates below are **CANDIDATE observations**, with the preserved pre-feature
reference shown as a diagnostic **BASELINE**. The model artifact is identical in
all arms: the six-shard UD-Q4_K_XL distribution. Runs span September 8–9, 2026.
They use the source-pinned canonical 48-thread recipe but have no promotion
attestation on this unrebooted host.

| Measurement | Original plain reference | Final plain | Final native MTP |
|---|---:|---:|---:|
| 24-prompt workload, token-weighted output tokens/s | 7.82075 | 7.67426 | 10.82479 |
| Five 512-token continuations, median output tokens/s | 6.36609 | 7.69689 | 9.60451 |
| Five 2,029-token prefills, median prompt tokens/s | 117.5111 | 144.0811 | Not repeated |

The 24-prompt final pair generates exactly the same 4,800 tokens. MTP is about
41.1% faster on that workload. This is one pass through 24 distinct prompts,
not five independent workload repetitions. The five long repetitions provide a
separate sustained measurement; do not pool the two instruments. Ordinary
decode does not show a consistent cross-workload improvement against the old
binary, so no independent single-token Q8-kernel speedup is claimed.

Q8 prefill is 22.6% faster by the five-run median. Final prefill rates are
145.5795, 144.3317, 144.0811, 143.4930, and 143.6223 prompt tokens/s; all
process 2,029 prompt tokens with cache_n=0. The 26-token repeated decode prompt
stays below the Q8 cutoff: all five final plain continuations match the
preserved original 512-token streams exactly. Final plain decode median absolute
deviation is 0.000618 tokens/s.

All five final MTP continuations match both final plain and the original
reference exactly: 2,560 tokens per arm. MTP median is 9.60451 output tokens/s,
MAD 0.002844, or **24.8% faster than matched final plain**. Two distinct
512-token prompts also match exactly; their MTP/plain rates are 13.2083/7.6407
and 9.5851/7.6682 output tokens/s. The 24-prompt workload has a different
acceptance mix, so its 41.1% gain is not substituted for the sustained-repeat
result.

Independent [final audit](/mnt/raid0/llm/tmp/glm53-validation-20260908/runtime/final-committed-audit-20260909T002613Z/audit.json)
passes (SHA-256 `7bce7808c1042a49ce012d4593ef5bc3ff0b573d4c1d34027a34c7656bbb3626`).
Across the seven measured fixed-512 request windows, 1,262 completed verification
events accept 2,314 of 3,777 drafts; 1,039 events accept at least one draft and
743 witness an actual rejection. These are request-scoped raw-log events,
not a subtraction of aggregate counters. Plain has zero draft events. All
36 paired responses pass exact token comparison; requests and rendered prompts
are retained. Per-batch DEBUG phase messages were filtered at runtime; source,
binary and INFO mode identity establish configuration, while the separate
real-model phase test establishes phase behavior. Both servers exited with rc0 and were
confirmed absent; their physical q0–q3 CPU locks were released. Explicit
candidate library paths and loaded-library identities were retained for both
runs. The benchmark source remains `04ffb8ad0`; subsequent report/helper commits
do not change the measured kernel. Portable workload clients and pinned inputs
are preserved by helper-only commit `49612aae5`; see
[reproduction instructions](/mnt/raid0/llm/llama.cpp-experimental-glm53-20260908/tests/glm53/run/README.md).
Helper validation passes 10 wrapper/client, six serve-plan and four artifact
tests (one additional artifact check is opt-in and skipped), plus Python
compilation checks. The candidate working tree is clean.

Evidence lives under `/mnt/raid0/llm/tmp/glm53-validation-20260908/`:

- `artifact/run/evidence-final-committed-plain-20260908T234438Z`
- `artifact/run/evidence-final-committed-mtp-20260909T001000Z`
- `artifact/run/evidence-baseline2346-canonical-t48-20260908T222048Z`
- `artifact/run/evidence-baseline2346-prefill2029-20260908T232556Z`
- `artifact/run/evidence-full-plain-20260908T210348Z`

## Quality and claim limits

The five-question quality screen is a bounded regression check with reasoning disabled. It can detect obvious truncation, malformed output, or gross answer drift; five prompts cannot establish general reasoning quality, factual reliability, or application-level equivalence. The final plain screen scores 3/5 versus the original 2/5: the previously truncated GSM8K response reaches the correct answer; the SimpleQA and HellaSwag items still fail. MTP also scores 3/5, and all five complete token arrays match final plain exactly. Long-prefill arithmetic changes output trajectories: only 2/24 canonical responses match the old kernel exactly. Thus Q8 acceleration is not lossless, even when MTP exactly preserves its selected plain reference.

All current measurements are experimental observations from an older-running shared host. They support candidate comparison under the recorded recipe and do not support production certification or promotion. GPU/HIP regression, long-context behavior beyond the tested cases, multi-slot serving, and `-np > 1` row-exact verification are outside this result. The fixed-512 checks use `ignore_eos` and do not establish natural-EOS parity. Exact generated token arrays do not imply exact logits; logit equality is established only for the separately described phase/rollback test cases.
