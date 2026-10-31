# DS41-W5d predeclared rule: (a) clean 1017-only llama-bench baseline, (b) MUL_MAT_ID pp512 premise microbench

Written 2026-10-23 by a 3c4ca599 subagent BEFORE any run. Nothing here has been run. Operator decision 2026-10-23: "1017-only + microbench"
(the old W5 "1017 vs Sept" delta, tg128 -5.1% / pp512 -29.9%, is closed INVALID and unrecoverable: the Sept Q4 GGUF was deleted 2026-10-21
(DS41-W7) and will NOT be re-downloaded; the number is not a prior, a threshold or a target for anything below). Operator exception to the
DS41 hold: this task is the operator-chosen replacement for DS41-W5c (3c4ca599 / workspace-58 grant path); every other DS41 test stays held.

## What the premise is (grepped from `handoffs/active/deepseek-v41-flash-evaluation.md`)
DS41-W8a: give the DS41-1017 AK target a prefill surface because seed **S5 `akm-ds41-1017-mxfp4-mmid-gemm-tiles`** is "the likely cause of the -29.9%
pp512 vs Sept Q4_K" (research `da71fa603`): **the repacked MXFP4 MUL_MAT_ID prefill GEMM (`mxfp4_8x8_q8_0`, CPU_REPACK) is slower than the iqk Q4_K
MUL_MAT_ID path at prefill shapes.** The -29.9% was a cross-protocol artefact (V11-103), so the premise has no valid evidence either way. (b) tests it
directly on the 1017's own expert shapes; (a) supplies the absolute pp512 the microbench result is scaled against.

## Instrument (both parts)
Image `/mnt/raid0/llm/kernels/builds/cpu-20261023-141e4bcf5-lbh` (champion 49550eda5 + CH-28 `cmd_params params{}`; version 10412 (141e4bcf5)).
Precondition `/mnt/raid0/llm/tmp/ch28-fold-20261023/DONE`. Caveat, stated not hidden: this is the CHAMPION kernel lineage (MXFP4 is NOT in
`iqk_typeA_supported`, so the 1017 experts load into CPU_REPACK exactly as in the DS41 port; Q4_K MMID goes through iqk), not the ds41-ak 3376147f8 tree.
The result is about the champion kernel's MXFP4-repack-vs-Q4_K-iqk behaviour; it does not reproduce W5's kernel.
Recipe (codified, as the W5 prep and the DS41 `launch.json`): `taskset -c 0-95 numactl --interleave=all`, 48 threads, `OMP_PROC_BIND=spread OMP_PLACES=cores
OMP_WAIT_POLICY=active OMP_DYNAMIC=false GGML_IQK=1`, `LD_LIBRARY_PATH` = the image bin dir only (linkage proven by `verify_ggml_linkage.sh` for BOTH
`llama-bench` and the harness). Whole host (grant regions 0-95), GPU idle and gpu-quiet exclusive, host busy <= 3.0% and GPU use <= 5% before every process.
`ram_admit.sh 739 ds41` before every model load (a); `ram_admit.sh 40 ds41` before every harness process (b). ONE DS41-class process at a time; (a) completes
before (b) starts; (b) loads no model but is timing work and runs in the same quiet window. No process is shared between parts.
Pins: analyze.py sha256 bbb1736a16a499fbf18d804633abfa26f492625bbf31f83f56e796851c6b7eb3 (analyze.py = the mechanical form of this file; job.sh refuses to start if it differs, and runs its self-test).
bin/mb_mmid.cpp sha256 65b7570751085702a13fc51d5e94006318aacf1e172e651d0a3fdee0708f07a8 (verbatim copy of `tmp/cpu-backlog-20261004/c2/bin/mb_mmid.cpp`, the
harness behind the c2 MUL_MAT_ID microbench; NO new kernel or harness code is written here). Vendored ggml headers `bin/ggml-include` = `git archive 141e4bcf5 ggml/include`.

## 1017 expert shapes (read from the shard headers, `ds41-1017-expert-shapes.json`, re-read and re-checked by job.sh)
40 layers, each: `ffn_gate_exps` (5120, 2304, 384) MXFP4, `ffn_up_exps` (5120, 2304, 384) MXFP4, `ffn_down_exps` (2304, 5120, 384) MXFP4; 384 routed
experts, 6 used per token. (Shared experts are Q8_0 dense MUL_MAT, not MMID, not in scope.) There is NO Q4_K tensor in the 1017: Q4_K is the *reference* arm
(the Sept model's type and the iqk MMID production path the premise compares against), at the SAME shapes.

## (a) 1017-only absolute baseline  -- no comparison arm, so NO verdict on any delta
- Model: `DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf` (9 shards, model_size 501596704208).
- Shapes: pp512 (`-p 512`) and tg128 (`-n 128`), depth 0 (no `-d`), both in the same process.
- Argv: `taskset -c 0-95 numactl --interleave=all llama-bench -m M -t 48 -fa 1 -mmp 0 -p 512 -n 128 -r 3 -o json`. Reps: `-r 3` inside a process; **6 processes**
  (one model load each), strictly sequential. The unit of replication is the PROCESS; value = that process's `avg_ts`.
- Unhardened-on-every-row check: the requested protocol is UNHARDENED (no `--autokernel-harden`). EVERY llama-bench row of every process must have
  `autokernel_hardened` == `false` (bool), exactly 2 rows (pp512, tg128), `samples_ts` length 3, build_commit starting `141e4bcf5`, model_size equal to the
  1017's, n_threads 48, flash_attn 1, use_mmap false, n_batch 2048, n_ubatch 512, type_k/v f16, n_depth 0, backends CPU. Any single mismatch => VOID and the job
  aborts at once (a VOID run is never repaired in place; argv containing `--autokernel-harden` voids too).
- Output: per metric mean, sd, CV, median, min/max and the **95% CI of the mean (Student t, df=5, t=2.5706)** over the 6 process values, plus the CI half-width in %.
- Per-run CV validity rule (all required for `BASELINE_VALID`; otherwise `INVALID_NOISY`, and the numbers are descriptive only):
  1. all 6 processes completed with protocol-correct rows (fewer => `INCOMPLETE`);
  2. per metric, CV (sample sd / mean) of the 6 process values <= 4.0%;
  3. per metric, at most 1 of the 6 runs has a within-process CV (of its 3 `samples_ts`) above 4.0%; such runs are listed, never dropped.
  FLAG: 4.0% is a conservative rule, not a calibrated llama-bench floor. No process-level llama-bench floor exists for DS41; the nearest is the 2.862%
  DS41-1017 serving floor (unit = process, n = 24 A/A pairs, build dd3d9721c, `/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/aa/floor-store/serving-floor.ds41-1017-mxfp4-cpu-t48-targetonly.requests-e50732d9ce365259d5bb95fe31e36995f98bcd0986dc0e48d489f99390e42f58.matched_process_v2.pairs-5.json`), so 4.0% is ~1.4x it.
- No delta, no tolerance, no pass/fail against any other build or model: the baseline is a reference for later work, nothing more.

## (b) MUL_MAT_ID microbench at the DS41 pp512 shapes (no model load)
- Harness `bin/mb_mmid` (built in-window from the pinned source against the image's `libggml*`, niced on 160-183, never during a timed process). Synthetic weights
  (random rows quantised once and tiled: valid blocks, speed only), DRAM-streaming, `--n-alloc 384` (= the real expert count, so rows-per-expert match the model),
  `--copies 4` (footprint 9.6-10.2 GB >> 384 MB L3; each rep draws fresh distinct-per-token expert ids), `--n-used 6`, `--threads 48`, `--reps 15`, `--min-mb 8192`.
  Every N also runs the harness's correctness spot check (y vs a dequantised reference dot, rel < 2e-2); a FAIL aborts the run.
- Operating point: pp512 = ONE 512-token ubatch (`-p 512`, n_ubatch 512) => **N = 512 tokens per MUL_MAT_ID node = 512 x 6 / 384 = 8 rows per expert on average**
  (uniform random routing). Secondary N = 1024 and 4096 (16 and 64 rows per expert; arms A and B only) are reported as shape sensitivity and DO NOT enter the verdict.
- Arms: **A** = Q4_K, plain buffer (iqk MMID; proven by the `[iqk] ACTIVE: MoE mul_mat_id` stderr line); **B** = MXFP4, CPU_REPACK buffer (the served 1017 path,
  `mxfp4_8x8_q8_0`; proven by the `mxfp4_8x8` repack lines); **C** = MXFP4, plain buffer (native fallback; N = 512 only; diagnostic, not in the verdict).
  Modes per arm: `gateup` (k 5120, m 2304) and `down` (k 2304, m 5120). A missing path-proof line, or iqk activity in B/C, voids the process.
  If B reports `repack_na` in ALL its processes (build keeps MXFP4 out of CPU_REPACK) the served arm becomes C and the result is flagged `repack_na`; mixed => VOID.
- Design: **6 rounds** x 3 arms x 2 modes = **36 processes**, strictly sequential. Arm order per round (each arm sees each of the three positions exactly twice): ABC, BCA, CAB, CBA, ACB, BAC;
  gateup then down within an arm. The unit of replication is the ROUND; per round the per-layer expert time is **T(arm, N) = 2 x us_med(gateup) + 1 x us_med(down)**
  (us_med = the process's median over 15 timed reps, in us per MUL_MAT_ID node, averaged over the 4 copies) -- the DS41 layer's gate, up and down nodes.
- Statistic: per round ratio R_r = T(B, 512) / T(A, 512); report the geometric mean and the 95% CI of ln R (Student t, df=5) over the 6 rounds.
- **Floor / tolerance, with its unit:** TOL = **3.0% of the per-round T ratio** (unit = ratio of per-layer expert times, one value per round of 6 interleaved harness processes),
  = the 2.862% DS41-1017 process-level serving floor rounded up. FLAG: that floor comes from the serving harness (unit = launched process, n=24 A/A pairs, build dd3d9721c);
  **no MUL_MAT_ID-microbench floor exists at N = 512**, so TOL is UNCALIBRATED. The microbench's own noise is read back from the data: CV of T(A,512) and T(B,512)
  across the 6 rounds must be <= 4.0% (else `INVALID_NOISY`, verdict descriptive only).
- **Decision rule (premise = "the served MXFP4 repack MMID prefill is slower than Q4_K iqk at pp512 shapes"):**
  - `PREMISE_STANDS`  iff CI95 lower bound of R > 1.03 AND R_r > 1 in all 6 rounds;
  - `PREMISE_REFUTED` iff CI95 upper bound of R < 1.03 (parity within tolerance, or faster -- a `direction_note` is added if the upper bound < 0.97);
  - otherwise `INCONCLUSIVE`.
  The premise question "does MXFP4 repack sit far below the reference at pp512" is answered by R itself: the reference is the Q4_K iqk path on the same shapes, same
  window, same harness; no roofline number is used as a threshold (a peak-throughput figure for this host is not a measured quantity here).
- **Scaling to the end-to-end pp512 (uses part (a); informational, never a verdict input):** per 512-token ubatch the MMID time is 40 layers x T. The ceiling for S5 is
  `ceiling% = 100 x 40 x max(T(B,512) - T(A,512), 0) / (512 / pp512_mean_ts)` = the share of the 1017's pp512 wall time recoverable if the repack path matched Q4_K iqk;
  `mmid_share% = 100 x 40 x T(B,512) / wall` must be <= 100 or the verdict becomes `INCONCLUSIVE` (microbench not representative). A premise that STANDS but has a ceiling
  below 3.0% of the pp512 wall is reported as "stands, ceiling below tolerance". Limitation, stated: synthetic uniform routing (real routing is skewed -> more rows on hot
  experts, fewer on cold) and synthetic weights; the microbench bounds the MMID kernel, not attention, norms, the shared expert or the scheduler.
- The old -29.9% pp512 is NOT a threshold: no decision here compares against it.

## Out of scope / not decided here
No claim about served decode, ppl or quality, and none about the Sept Q4 model. Results are OBSERVATIONS until a belief-substrate write-side is attached
(Belief Kernel wiring: add a source row for `out/rows.jsonl` in scripts/vidya/adapters/README.md and a task in vidya-belief-substrate-program.md when it runs).
