# c6-iqkq8pf-nwt-null-20261105: empirical-null no-worse-than-C6 gate for the iqk Q8_0 prefill route (AK-CPU-INT8-PREFILL)

## Decision basis

- **Operator, 2026-11-05.** The quality gate for numerics-changing Q8_0 routes is no-worse-than-C6 by perplexity, on the production
  weights, over long prompts.
- **Coordinator, 2026-11-05.** Implement that decision against an empirical null.
- **Why a null is needed.** The paired-SE rule of `c6-iqkq8pf-nwt-gate-20261105` and its r2 rerun was mis-specified for this model.
  Qwen3.6-35B-A3B is a hybrid model (gated DeltaNet plus MoE top-k routing) and it is chaotic:
  - Routing only the 32-row `ssm_alpha` projections through iqk changes the output only in float summation order. That op's output
    equals C6's int8 dot to 1e-15 NMSE.
  - Even so, that single change already gives a mean KLD of 0.0052 vs C6.
  - Its ln-PPL shift is -0.0002 ± 0.0013 over 4 chunks, so its sign is random.
  - Every op class gives KLD ≈ 0.005: experts, shexp, attn/ssm, and the lm_head together with attn_output.
  - The diagnosis is in `/mnt/raid0/llm/tmp/c6-iqkq8pf-fp16s-dev/bisect/`.
- **Consequence.** A trajectory-level shift is not captured by a per-token SE. F is judged against the spread of shifts produced by
  perturbations known to be precision-neutral.

## Arms

Every arm runs `tool/llama-perplexity`, copied unchanged from the NWT gate, with that arm's store as `LD_LIBRARY_PATH` and `GGML_IQK=1`.

| arm | store | env | meaning |
|---|---|---|---|
| base | `cpu-20261105-21232569a-llg` (C6) | none | `--kl-divergence-base`, regenerated once, sha256 recorded |
| F | `cpu-20261105-65da39eb1-c6fold2` | none | candidate with the full Q8_0 prefill route |
| null_ssm_alpha | `cpu-20261105-fff2c6909-nullknob` | `GGML_IQK_Q8_0_ROUTE_ONLY=ssm_alpha` | precision-neutral |
| null_ssm_beta | same | `ssm_beta` | precision-neutral |
| null_blk0_shexp | same | `blk.0.+_shexp` | precision-neutral |
| null_blk20_shexp | same | `blk.20.+_shexp` | precision-neutral |
| null_lm_head | same | `=output.weight` (exact name) | precision-neutral |
| null_attn_k | same | `attn_k.weight` | precision-neutral |

Notes on the arms:

- **Why the null arms are precision-neutral.** The nullknob store is `fff2c6909` on the measurement-only branch
  `experimental/c6-iqkq8pf-nullknob-20261105`, which is `65da39eb1` plus the env knob. With the knob set, the routed ops use Q8_2_X4_H
  activations, whose codes are identical to C6's `quantize_row_q8_0`. Only the float summation order of those ops changes.
- **Build.** The nullknob store is built by `/mnt/raid0/llm/tmp/c6-iqkq8pf-nullknob-build-20261105/`. This packet's precondition
  reads that build's RESULT and refuses with rc 3 until it reports BUILD_OK.
- **Why the base is regenerated.** The r1 and r2 base logits carry no sha256 from the run that created them, so they are not reused.

Each unit proves it ran the right code: the store lib sha256 and its marker, the `/proc` maps of its own pid, and the iqk route line.
The route line must be absent for base and present for F and the null arms. The null arms must also print the knob line.

## Method and verdict

**Corpus and settings** (same as the NWT gate): wikitext-2 test, `-c 4096 --chunks 16 -b 4096 -ub 512 -fa on --no-mmap`, with
`-t/-tb/--load-threads` set to the quarter's 24 cores. The run uses one whole q0 or q1 quarter.

**Verdict.** **NWT_NULL_PASS** iff both conditions hold; otherwise NWT_NULL_FAIL.

- `ln_ratio(F) <= mean(null) + 2*SD(null)`
- `KLD(F) <= mean(KLD null) + 2*SD(KLD null)`. This rule was pre-registered on 2026-11-05, before any run. It replaces the earlier `1.25 * max(KLD null)`, which would have hinged on the single largest null arm.

**Also reported in RESULT:**

- the null's mean, SD and SE;
- F's z-score against the null;
- the per-chunk ln-ratio of F;
- a sign test on the null ln-ratios (two-sided binomial). If all K null arms are positive with p <= 0.05, RESULT says explicitly
  "NULL IS BIASED POSITIVE: any reroute costs quality". That would be a separate finding.

**Stop-on-answer.** A3B runs first: base, F, then the 6 nulls, about 8 × 3-4 min. Q38FN UD-IQ4_XS runs the same arms only if A3B
passes and at least 3 h remain in the window. Q38FN arms whose tensor does not exist never engage the route and are dropped. Q38FN needs
at least 4 nulls, otherwise it is INCONCLUSIVE and the A3B verdict stands.

**Exit codes:** 0 done | 3 precondition | 4 invalid unit (a rerun resumes) | 8 not a whole q0/q1 quarter | 75 stop or deadline.

**Smoke** (`FILLER_SMOKE=1`): runs the A3B base and `null_ssm_alpha` at `-c 1024`, 1 chunk, and writes ONE unit record. The base result is folded into that record as `smoke_base`. **Row id is now `c6-iqkq8pf-nwt-null-r2-20261105`:** the r1 dry run failed because the harness raises the stop file once the first record lands, and that SIGTERMed the null smoke (rc -15).

## Reclaim

`out/logits/*.bin` is about 10-25 GB and is not in `keep`. Reclaim it at filing with `scripts/safety/guarded_rm.sh`.
