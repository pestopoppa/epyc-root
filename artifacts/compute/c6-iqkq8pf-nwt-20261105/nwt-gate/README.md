# c6-iqkq8pf-nwt-gate-20261105: no-worse-than-C6 perplexity gate for the C6 iqk Q8_0 prefill fold (AK-CPU-INT8-PREFILL)

## Decision basis (operator, 2026-11-05, relayed by the coordinator)

**The quality gate for numerics-changing Q8_0 routes is no-worse-than-C6 by perplexity on the production weights, over long
prompts. There is no higher-precision reference model.** The same text is written into `RESULT.json` `decision_basis`.

For this route, it replaces the quality parts of `c6-iqkq8pf-fold-gate-20261105` (`4b_q38fn_screen`, `4b_q8_screen`: top-20
KLD(C||F) < 1e-3 at 8 single positions). Those failed. Analysis showed the route is as accurate as C6 per op: NMSE vs exact
1-3% above C's. C and F round activations to int8 in different places, so a C-vs-F KLD bound on hybrid recurrent models cannot be
met by any reroute. The fold gate's 4a, 4b-id and 4d results stand.

## Arms, tool, models

- **C** = `/mnt/raid0/llm/kernels/builds/cpu-20261105-21232569a-llg`, the CPU image of C6 head 9e9d7f291. libggml-cpu sha256 `79e0c13e...`.
- **F** = `/mnt/raid0/llm/kernels/builds/cpu-20261105-f3a6a4ba-c6fold` (f3a6a4baa). libggml-cpu sha256 `129daf99...`.
- **Tool.** The stores ship no `llama-perplexity`, so `tool/llama-perplexity` and `tool/libllama-perplexity-impl.so` were built
  out of tree (`tools-build/`) from the clean fold worktree at f3a6a4baa, with `CMAKE_SKIP_RPATH=ON`.
  - Every libggml*, libllama and libllama-common is loaded from the arm's store (`LD_LIBRARY_PATH=tool:<store>/bin`).
  - Each unit proves this with the store lib sha256 + marker, the running pid's `/proc` maps (store libs and the impl lib only), and
    the `[iqk] ACTIVE: Q8_0 prefill route` line, which must be present in F and absent in C.
  - The tool was built with `LLAMA_LLGUIDANCE=OFF`. No llguidance symbol appears in the common/include headers, so its ABI matches the
    llg stores. The smoke runs on both stores ran clean.
- **Env.** `GGML_IQK=1`, every other `GGML_IQK_*` removed.
- **Placement.** Both arms use the same argv except for the library path: `taskset` + `numactl --membind` on one whole q0/q1
  quarter, `-t/-tb/--load-threads 24 --no-mmap`.
- **Models (production quants), A3B first:**
  - `a3b`: `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf`.
  - `q38`: Qwen3.8-Flash-Next UD-IQ4_XS, which carries 502 Q8_0 tensors. It runs with the frozen r3 q38fn CPU env and `-ctk f16 -ctv f16`.

## Method

- **Corpus.** `corpus.txt` = wikitext-2 test raw: held-out natural text, sha256 in `IDENTITY.json`.
- **Context and chunks.** `-c 4096 --chunks 16 -b 4096 -ub 512 -fa on`. 4096 is the largest round context that keeps each arm
  within minutes on a quarter: the A3B smoke ran at about 200 tok/s on 8 cores.
- **Scoring.** llama-perplexity scores the second half of each chunk (`first = n_ctx/2` is hard-coded in the tool). That gives
  16 x 2047 = 32,752 scored tokens per model, each with at least 2048 tokens of context. The full 4096-token chunk is prefilled at
  512 rows per ubatch, so the iqk route engages on every forward pass.
- **Per model.** First unit `<m>-C-base` (C, `--kl-divergence-base out/logits/<m>-C.bin`), then unit `<m>-F-kld` (F,
  `--kl-divergence`). The F run reports:
  - PPL_F ± SE and PPL_C ± SE;
  - the paired per-token Mean ln(PPL_F/PPL_C) ± SE;
  - KLD(C||F) statistics;
  - the cumulative per-chunk table. From it, the per-chunk paired ln-ratio is derived as `d_i = i*r_i - (i-1)*r_{i-1}`, with
    rounding of about 1e-4. The job records the distribution, its mean and SE, and how many chunks are positive.
- **Model PASS** iff Mean ln(PPL_F/PPL_C) <= its SE (no worse than 1 SE above 0) **and** PPL_F <= PPL_C + SE(PPL_C).
- **Verdict.** `NWT_PASS` iff both models pass; otherwise `NWT_FAIL` with `failed_models`.
- **Stop-on-answer.** If A3B fails, Q38FN is not run.
- **No floor run.** C is deterministic: the C-vs-C floor was exactly 0 in the fold gate.
- **Unit validity.** A unit is valid iff rc is 0, every proof is ok and the metrics parse. An invalid unit exits rc 4, and a rerun
  resumes (`out/results.jsonl`).
- **Exit codes.** rc 8 = not a whole q0/q1 quarter; rc 75 = stop or deadline.
- **Smoke** (`FILLER_SMOKE=1`). One real C base run on A3B at `-c 1024 --chunks 1`.
  - Validated on cores 0-7 on 2026-11-05: valid, PPL 3.9932 ± 0.416.
  - A manual F kld smoke parsed every field: ln-ratio 0.0026 ± 0.0026, KLD 1.3e-3, same top 98.6%.
  - These are smoke-only rows (`mode: smoke`); the gate ignores them.

## Q38FN coverage note

No higher-precision Q38FN GGUF exists, and none is needed under the operator's method: the comparison is C6 vs F on the served
weights.

## Reclaim

`out/logits/*.bin` holds the C logits for the paired run, about 10-25 GB per model. It is not in `keep`. Reclaim it at filing with
`scripts/safety/guarded_rm.sh`; the job never deletes it. `tools-build/` is build scratch and can be reclaimed the same way. `tool/`
is kept.
