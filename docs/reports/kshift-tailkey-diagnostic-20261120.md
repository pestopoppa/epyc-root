# K-shift diagnostic: controls complete, qualification remains inconclusive

`kshift-tailkey-diagnostic-20261120` ended rc=0 on 2026-11-20, native verdict `DIAGNOSTIC_COMPLETE`, exactly two units. Filed verdict: **inconclusive for qualification**. The diagnostic question was whether the repaired tail-key-plus-query and dropped-prefix controls expose sensitivity and whether fresh-offset-d controls reproduce translation mismatch positions/margins. Expected effect was unknown; this was one exploratory fixture without statistical significance, repetition calibration or a population claim. Stop-on-answer was the candidate/baseline pair; first input/build/mapping/record/run failure would stop immediately without retry. Both units completed.

The arm used Qwen3-1.7B-Q8_0, native RoPE, f16 K/V, 448 prefix tokens and 64 teacher-forced probe positions, 24 CPU threads on granted CPUs 24–47. Candidate C10 + H2/H3 and baseline C10 retained their original library SHA pins and each reported the expected mapped libllama/libggml-cpu paths. Lower KLD and fewer mismatches mean closer outputs.

| Comparison | Candidate mean KLD | Baseline mean KLD | Candidate top-1 mismatches |
|---|---:|---:|---:|
| repeat offset 0 | 0 | 0 | 0 |
| fresh offset d | 0.001353490 | 0.001353490 | 2 |
| fresh offset 4d (historical noise control) | 0.001426211 | 0.001426211 | 0 |
| translate x1 | 0.002114893 | 0.002114893 | 2 |
| translate x4 | 0.001501084 | 0.001501084 | 0 |
| round trip | 0.001092505 | 0.001092505 | 1 |
| half-prefix shift | 0.003770928 | 0.003770928 | 0 |
| tail-key-plus-query shift 64 | 0.014662190 | 0.014662190 | 1 |
| dropped prefix | 1.356316 | 1.356316 | 21 |
| seq_div | 0 | 3.025076 | 0 (baseline 48) |

The sensitivity requirement remains `max(0.03, 5 * max(0.003, 3 * 0.001426211)) = 0.03`. Only the dropped-prefix control clears it. The repaired tail control moves key 447 to 511, leaving keys 0–446 intact, then probes consecutively at 512; it perturbs keys and queries together. Dropping the entire prefix is a distinct, more drastic perturbation. Neither added control can retroactively replace the historical half-prefix gate. Candidate x1 still exceeds the original mismatch ceiling of one. The original r1 verdict and thresholds remain unchanged.

Fresh offset-d versus zero and translate-x1 versus fresh-offset-d disagree at exactly indices 52 and 54 in both libraries. Token pairs are 1379/733 and 2422/821, reversed between comparison directions. The fresh-offset-d winner margins are 0.027290344 and 0.027032852; shifted winner margins are 0.280246735 and 0.017147064. This is consistent with shared offset-associated top-1 instability, but the changed KLD/margins do not establish that offset numerics alone explain the shifted outputs. Repeat-zero has no difference in this pair. No causal diagnosis or threshold relaxation follows.

Half-shift first8/last8 mean KLD is 0.000476921/0.002318995: the proposed early-to-late attenuation is not observed for the original weak control. Tail-key-plus-query first8/last8 is 0.008541699/0.003076350, and dropped-prefix is 4.262358776/0.070670799. Those decreases describe these controls in this fixture; they do not establish why the half-prefix gate is insensitive. Candidate seq_div KLD 0 versus baseline 3.025076 reproduces bounded H2 discrimination, without validating H1–H3 as a package. No YaRN, quantized-K or second-model arm ran; partial-rotary H3 remains uncovered.

Evidence stays under `/mnt/raid0/llm/tmp/triattention-kv-selection/kshift-tailkey-diagnostic-20261120/` (no copied logs or source trees):

- `out/results.jsonl`: SHA-256 `87b35e431a16de953891061279c7d50b3f583df3e55e7548799a77a23e046a6b`.
- `out/RESULT.json`: SHA-256 `58c2b48a735655a74e50f09a144ed7dfb7add91b1fc0b1921dac191be4dacfb5`.
- `out/cand.stdout`: SHA-256 `171167ba4f5a48d31c7534a11a7d995613aa6f3566dc723a6318a6560834ee73`.
- `out/base.stdout`: SHA-256 `6a6417d57541533b6d115fa23890152bf84c1d9c380a6eb1522be688c5bbed29`.
- `pins.json`: SHA-256 `9b5e5e550e522c32985bdacb21421da0e3f22a9bcda6f3c5745eae2149456a11`.
- `spec.json`: SHA-256 `4ac1ffee62166ce5ece8ba464333882b1ae3311e57ba34b93dcb09a84ba86ac2`.
- Generator `scripts/diagnostics/kshift-model/instrument.py`, git `3b1d8fb9a24a86dfcf4f24b8115c4e94057aa206`, SHA-256 `05e0a366567a87f6d380610b25a1de91e2123e0d4b5878202180723a04e9b5e3`.

Next result-bearing step: implement and test an offset-matched calibration protocol that retains historical metrics separately, then preregister its acceptance/control semantics before publishing any new qualification row. Do not simply relabel this pair or relax r1 thresholds. Parent model acceptance, champion fold and upstream draft remain open. Existing prospective capture task `VB-YARN-E1` owns this source; this committed report is an OBSERVATION only (`[belief: cc]`), without reconstructed measurement warrant.
