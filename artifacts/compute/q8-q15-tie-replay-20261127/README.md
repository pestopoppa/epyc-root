# Q8/Q15 final-head replay

**NO_KEEP.** Signed Q15 recovered all five engineered near-tie Q8 flips and one natural calibration flip. Both Q8 and Q15 matched the FP32-reference winner on all 48 held-out decisions. The results repeated at 1, 8 and 24 threads. Q15 activation packing took about 72–78 ns per 1,024-element row compared with 126–136 ns for Q8. The full Q15 head trailed the native Q8 head in every single-thread pair, and the 24-thread result fell inside the matched Q8 A/A floor.

## Decisions before sampling

The replay froze Qwen3-0.6B Q8_0 `output.weight` (151,936 × 1,024, 165,306,368 bytes), FP32 pre-head activations, prompt and continuation token prefixes, and full-vocabulary logits. The 88 unique positions comprised 24 calibration, 48 held-out, 12 engineered near-tie and 4 engineered wide-gap decisions. The natural continuations use the same captured native greedy trajectory. The engineered rows shift two real activations along their top-two dequantized weight difference and preserve both intended top tokens and signed target gap. The FP32 reference uses the same dequantized Q8 weights with unquantized activations.

| Fixture split | Positions | Incumbent Q8 flips versus FP32 | Q15 flips versus FP32 |
|---|---:|---:|---:|
| Natural calibration | 24 | 1 | 0 |
| Natural held-out | 48 | 0 | 0 |
| Engineered near ties | 12 | 5 | 0 |
| Engineered wide gaps | 4 | 0 | 0 |

Calibration position `p3-s4` had FP32 token 264 over token 279 by 0.002892 logit units. Q8 selected 279 by 0.018257. Q15 selected 264 by 0.002905. The held-out median logit RMSE fell from 0.026848 (Q8) to 0.0000993 (Q15). At each thread count, the standalone and native Q8 logits were byte-identical on all 88 rows. The native replay also matched all 72 captured natural logit rows byte for byte.

Native greedy selected the first maximum in each replay arm. The independent sampling-boundary fixture held logit bytes fixed and changed post-logit filtering and seeded draws. With the November 26 four-way tie, native top-p 0.5 retained IDs 1 and 3 and drew ID 1 under seed 3, while unfiltered greedy selected ID 0. [Sampling-boundary replay](../../../data/spec-filter-ties-20261127/README.md)

## Throughput on one EPYC 9655 quarter

Each entry summarizes eight paired, interleaved rounds on q0 physical CPUs 0–23. Each head call processes the full vocabulary, including activation packing for the Q8 and Q15 columns. The native comparator uses the original model weight buffer and frozen V10 CPU GGML. The matched standalone arms traverse identical frozen weight bytes with identical OpenMP row partitioning.

| Threads | Native Q8 ms | Matched Q8 ms | Q15 ms | Q15 prepacked ms | Q15 / native throughput | Q15 / matched throughput | Matched Q8 A/A floor |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4.803 | 5.279 | 5.106 | 5.107 | 0.938× | 1.033× | 2.38% |
| 8 | 1.580 | 1.121 | 0.768 | 0.786 | 2.070× | 1.427× | 38.88% |
| 24 | 1.362 | 0.972 | 0.777 | 0.842 | 1.784× | 1.241× | 35.48% |

Throughput ratios are medians of the eight paired ratios. The full-head and prepacked calls have independent timing noise, so their difference does not estimate pack cost. The dedicated repeated packer timings resolve that cost directly. At eight threads, the matched Q8 arm took 1.12–1.20 ms when first or immediately after native Q8 and roughly 0.77–0.82 ms on repeat or after another standalone arm. The repeat arm's 0.794 ms median was close to Q15's 0.768 ms. This run-order sensitivity limits interpretation of the apparent wide-thread gain. Single-thread Q15/native throughput ranged from 0.876× to 0.950× across the eight pairs. The performance conclusion covers this CPU vocabulary-head replay and its tested widths.

## Signed-word arithmetic

The Zen 5 binary uses AVX-512 VNNI `vpdpwssd` to accumulate pairs of sign-extended int8 weights and signed Q15 activations. The signed scalar int64 oracle passed 4,098 mixed and extremal blocks plus 5,696 traced model/token/block records. A Q8 × Q15 block peaks at 134,213,632 in magnitude, within int32. Two unrestricted `-32768 × -32768` terms sum to 2,147,483,648 in int64. The instruction control observed `vpdpwssd` wrapping to −2,147,483,648 and `vpdpwssds` saturating to 2,147,483,647. The candidate rescales each block and accumulates in float.

## Evidence and reproduction

The model, bytes and libraries are pinned by [RESULT.json](RESULT.json), [weights.tsv](weights.tsv), [linkage.txt](linkage.txt), [store-check.txt](store-check.txt) and [SOURCE.sha256](SOURCE.sha256). The native CPU store is bound to source commit `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`. The production CPU library manifest and disassembly supplied content checks. The candidate builds with GCC 15 using the recorded [build.sh](build.sh).

The first smoke exposed an SMT-only allocation and was rerun after the launcher accepted the granted logical CPUs. The first direct slot stopped before model load because inherited affinity exceeded its grant. The replacement explicitly intersected `FILLER_CPUS` with the permitted CPU mask and used only the 24 physical cores. Row `q15-head-replay-cpu-20261127-r2` completed with rc 0. [Smoke PASS](SMOKE-PASS.json) · [Row receipt](row.ended)

The immutable raw evidence is stored on the EPYC host at `/mnt/raid0/llm/archive/compute-evidence/q8-q15-tie-replay-20261127/`. It includes the full matrices, per-block signed accumulators, the sealed binary, and execution receipts. Raw arrays are little-endian float32, ordered by `fixtures.tsv`, then by the FP32, Q8, Q15 and native Q8 arms in each `head-t*.f32` file. Captured logits contain the 72 natural rows. The portable verifier hashes every raw artifact and recomputes the top two IDs and logits for 1,128 records. [Frozen verification result](FROZEN-VERIFICATION.json)

```bash
python3 verify_frozen.py /mnt/raid0/llm/archive/compute-evidence/q8-q15-tie-replay-20261127
```

[Predeclared plan](PLAN.md) · [Per-position decisions](decisions.csv) · [Paired timing samples](timings.csv) · [Signed-pair control](signed-pairs.csv)
