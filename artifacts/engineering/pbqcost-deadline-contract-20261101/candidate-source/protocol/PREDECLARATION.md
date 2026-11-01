# PB-QCOST-1 confirm + q axis: PREDECLARATION

Written 2026-10-23 by a workspace-f8 subagent BEFORE any run of this item. Nothing in this file may be edited after the first
launch; the job records its sha256 in RUN_RECORD.json and in VERDICT.json. The verdict is mechanical (`verdict_q.py`); a human
reading of the numbers does not change it.

## 0. What this run is for

Handoff row `pb-qcost-1-confirm` (BACKLOG, `gpu-serving-tie-in-program.md` PB-QCOST-1) and the offline proposal in
`docs/design/pb-qcost-1-results-20261023.md`, "Compute proposals" 1 and 2:

1. **Confirm.** Repeat the 2026-10-21T21:29Z n = 1 / n = 4 re-validation (harness `pb_qcost_1.py`, sha256 in `ORIG_DRIVER.sha256`)
   with the SMT siblings of host threads 184-191 held idle by a region claim. The 21:29Z run is graded INDICATIVE because it ran
   beside the KVU-12 np8 CPU timing.
2. **q axis.** The 21:29Z run swept the cached prefix c at ONE tokens-per-iteration q per n (504 at n = 1, 480 at n = 4), so it
   cannot identify the q coefficient `b` or the q*c coefficient `d`; `b = 0.9865 ms/token` was carried from the 2026-10-20 offline
   fit. This run adds q levels by varying `-ub` (with `-b = -ub`), so `b`, `d` and the intercept `a_n` are identified per n.

Pending-decision independence: nothing here depends on an operator decision. The live A/B (KVU-16g) is a separate item.

## 1. Fixed conditions (identical to the 21:29Z run unless listed under "differences")

- Binary `/mnt/raid0/llm/kernels/builds/gpu-20261020-dd3d9721c/bin/llama-server` (the 21:29Z binary; sha256 recorded by the job).
  Qwen3.8-27B-Q8_0 + DFlash2 draft, `-np 5` (4 feeder slots + prefill slot 0), gate argv
  `/mnt/raid0/llm/tmp/overnight-20261020/argv.8083-gate.txt` with `-np 5`, port 18391, prompt set
  `/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run/prompt_set.jsonl` (trunk group 7, prefill slices of 4k 8k 16k 32k 64k).
- Prefill slot 0 `cache_prompt=false`, slot erased between requests; slots 1..n decode (DFlash2) for the whole block; n in {1, 4};
  blocks interleaved n=1, n=4 per rep; lengths ascending on odd reps, descending on even reps.
- TRAIN lengths {4k, 16k, 64k}, HELD-OUT lengths {8k, 32k}. HELD-OUT intervals and requests are never used to fit.
- Unit of every iteration quantity: **ms per server iteration** (interval between consecutive "prompt processing, n_tokens" log
  lines of slot 0). The 21:29Z refit coefficients A, B are per 512-NORMALISED iteration (`iter_ms = dt*1000*512/dn`); the confirm
  compares them in that same unit. The q-axis fit uses RAW `t_ms = dt*1000` and the actual `dn`.
- Differences from 21:29Z (each recorded, none changes the model under test):
  (a) `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` in the server environment (GPS-PIN-1 knob, via the launch prefix);
  (b) own-pid VRAM guard 60 GiB (GPU-LEAK-1; was 62.5);
  (c) host: GPU flock + gpu-quiet claim on `mi210_0` with `--claim-cpus 184-191` (their SMT siblings 88-95 idle), production :8083 parked;
  (d) one server per `-ub` phase (restart between phases);
  (e) sibling-load sampler (section 2).
- HIP graphs: production condition is graphs ON (GPU-LEAK-1d: the production argv leaks ~1.7 MiB/request with graphs on or off).
  Graphs ON/OFF is recorded per server from `/proc/<pid>/environ` (`GGML_CUDA_DISABLE_GRAPHS` absent = ON). A server with it
  present is aborted and the run is INVALID_PROOF.
- GPU residency is proven by own-pid KFD VRAM (`/sys/class/kfd/kfd/proc/<pid>/vram_*` > 0 at ready, sampled 1 Hz for the whole
  server life, peak recorded), never by startup-log text (this build's log omits device/offload lines). KFD sampler aborts the
  server above 60 GiB own-pid.

## 2. The uncontended confirm (ub 512 phase)

Protocol = the original: `-b 512 -ub 512`, 3 reps x 5 lengths x n in {1, 4}, in the first phase. q = 504 (n=1) and 480 (n=4).

Uncontended grade. During the whole job a sampler reads `/proc/stat` every 5 s for CPUs 88-95 (the SMT siblings of 184-191) and
writes `out/sibling_summary.json`. Over non-overlapping 30 s windows the run is graded **UNCONTENDED** iff the median sibling busy
fraction is <= 5 % AND at most 5 % of windows exceed 25 %, AND every phase's graphs/HSA/VRAM proof is ok. Otherwise the numbers
stand as measured but the grade is INDICATIVE and a re-run is owed (the verdict label says so).

CONFIRM verdict, per n (`verdict_q.py: confirm()`), using the `analyse()` of the original driver on ub-512 rows of completed phases:

- `INCOMPLETE` if any length has < 3 valid reps.
- `mape_ok` = refit request-level held-out MAPE <= **10 %** (the operator-accepted bar, reused unchanged).
- `coef_agree` = |A_new - 766.85 (n=1) / 871.40 (n=4)| <= noise AND |B_new - 0.010794 (n=1) / 0.013798 (n=4)| x 32000 <= noise,
  where **noise = the new run's train rmse of the ub-512 interval refit (ms per iteration)** and 32000 is the reference cached
  length (ms per iteration at c = 32000).
- `CONFIRMED` iff mape_ok and coef_agree; `REFIT_FROM_UNCONTENDED` iff mape_ok but not coef_agree (the handoff says refit from the
  uncontended data: the new ub-512 coefficients become the replacement); `FAIL_MAPE` otherwise.
- Overall confirm: CONFIRMED iff both n are CONFIRMED; INCOMPLETE if any n is; else FAIL_MAPE if any n is, else REFIT_FROM_UNCONTENDED.
- The frozen-model request-level MAPE is REPORTED, not gating (it failed at 12.84 % / 26.32 % on 21:29Z and is not re-adjudicated).
- Per-n refit convention unchanged: coefficients are per n and are never pooled across n.
- The held-out P99 abs residual and the one-sided P99 under-prediction (ms per iteration) are reported beside rmse/MAPE and are not
  thresholded; KVU-16g-2 takes its target-ms margin from the n = 4 under-prediction figure of the CONFIRMED (or replacement) refit.

## 3. The q-axis cells

Phases after the confirm, one server each, `-b = -ub`, same `-np 5`:

| phase | `-b = -ub` | q at n=1 | q at n=4 | reps per length (4k, 8k, 16k, 32k, 64k) |
|---|---|---|---|---|
| 1 (confirm) | 512 | 504 | 480 | 3, 3, 3, 3, 3 |
| 2 | 256 | 248 | 224 | 1, 1, 3, 3, 1 |
| 3 | 1024 | 1016 | 992 | 1, 1, 3, 3, 1 |

Why `-b = -ub`: llama-server clamps ubatch to batch, and with `-b 512 -ub 256` one logged "iteration" would carry two ubatches. The
interval floor on dn is 256 for ub >= 512 (as the original) and 128 for ub 256, so dn = 224 / 248 is kept.
Estimated cost (offline model, `plan_estimate`): ub 512 = 36.5 min, ub 256 = 28.5 min, ub 1024 = 21.4 min, total 86 min. The
proposal's "~20 min" for the q axis was an underestimate: ub 256 is slower per token, and 3 reps at 16k/32k add up to 50 min.
A phase is started only if it fits (x1.1) before the hard stop; an incomplete phase is VOIDED (its rows are ignored) and redone on
re-grant (`--skip-done`).

## 4. The fit that identifies b (ms/token) and the q*c term

Per n (never pooled across n), over ALL completed ub phases, TRAIN-length intervals:

`t_ms = a_n + b * q + d * q * c`     (q = actual tokens in the iteration `dn`, c = cached prefix before it, raw ms per iteration)

OLS (3x3 normal equations on scaled features). Reported with: a_n, **b (ms/token)**, **d (ms per token-times-cached-token)**, the
implied intercept at q = 512, c = 0, the train noise floor (rmse, ms/iter, n intervals), 95 % CIs by cluster bootstrap over
requests (seed 20261023, 2000 draws), held-out interval residual stats (rmse, MAPE, P95/P99/max abs, P99 one-sided under-
prediction) pooled and per ub, and leave-one-ub-out stats (fit on two ub levels, predict the third; reported, not gating).
- b agreement vs the assumed 0.9865 ms/token: `|b - 0.9865| x (q-span between the lowest and highest median dn)` <= noise.
- d agreement vs the 21:29Z-implied raw `d_old = B_old / 512` (2.108e-5 at n=1, 2.695e-5 at n=4): `|d - d_old| x q0 x 32000` <= noise.
- Agreement flags are REPORTED, not gating. If b does not agree, the measured b replaces 0.9865 in the 80k-neighbour replay.

## 5. Pass bar for the q axis (mechanical)

Per n: **identified** iff all three ub levels have data from >= 3 requests at that n and the median dn spread across levels is
>= 500 tokens (n=1: 248 to 1016 = 768; n=4: 224 to 992 = 768). Then:

- `PASS` iff pooled held-out (8k, 32k, all ub) **interval-level MAPE <= 10 %** (same bar).
- `FAIL` if identified and MAPE > 10 %: then the quadratic budget form is not adequate across q; KVU-16g-2 must not enable a
  constant-ms budget off an extrapolated q; the per-ub cells above are the measured table to use.
- `INCOMPLETE` if not identified (a phase missing/voided).
- Overall q axis: PASS iff both n PASS; INCOMPLETE if any n is; else FAIL.

## 6. Mechanical verdict

`python3 -B verdict_q.py --out <job out dir> --write VERDICT.json` (script sha256 recorded by the job; unit tests in
`test_pbq_q.py`, including a synthetic CONFIRMED case, a voided-phase case and a graphs-OFF case). Label =
`PB-QCOST-1 confirm <CONFIRMED|REFIT_FROM_UNCONTENDED|FAIL_MAPE|INCOMPLETE|INVALID_PROOF>; q axis <PASS|FAIL|INCOMPLETE|INVALID_PROOF>`
plus the grade (UNCONTENDED / INDICATIVE) from section 2. `INVALID_PROOF` = any completed phase without graphs ON, own-pid VRAM > 0
and the HSA knob in its server environ.

## 7. What this run does not decide

It does not tick PB-QCOST-1 (the live A/B, "follows KVU-16g's A/B", is separate), does not enable any budget, and makes no speed claim.
The 21:29Z binary is kept even if a newer champion exists, because the confirm compares coefficients with that run.
Host drift (~3 % over hours) is not controlled by ABA here: the ub-512 phase runs first and the q cells follow; the
noise-floor tolerance is the only allowance.
