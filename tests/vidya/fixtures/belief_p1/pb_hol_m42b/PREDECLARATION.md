# m4-2b-champion-control (M4.2b): C2 against a same-window champion control — predeclaration (written 2026-10-24, BEFORE any compute)

Item: `handoffs/active/gpu-serving-tie-in-program.md` → M4 → M4.2 → **M4.2b** (task text filed 2026-10-24 by the workspace-f8 sweep;
the text is the identity). Owner: workspace-f8 (launcher prepared by a subagent). Nothing in this directory has run when this
file is written; no M4.2b number exists. Supersedes, for C2 only, the cross-day band of
`../m4-srpf-pbhol-2a/AMENDMENT-M4.2a.md` (sha256 `770309cf3270a2d5be061298df5b0ff0a75fe9cc755e7a17b84e5cd49531d3c9`), as the
task text directs ("Replace the cross-day band with a same-window pair"). C1 and C3 stay as decided in M4.2.

## 1. Diagnosis (new, written): why M4.2a's C2 FAIL is not yet evidence about the candidate

M4.2a (`../m4-srpf-pbhol-2a/VERDICT.json`): C2 = **25.227x** against the band 19.845-24.255 (PB-HOL-1 22.05x ± 10 %), 6/6 reps valid.
Three facts say the miss may be the window, not the code:

1. **No off-path code difference.** Checked again for this file: `git diff 141e4bcf5 c6ca031ac` in
   `/mnt/raid0/llm/worktrees/llama-m4-srpf` touches 7 files; excluding tests (`tests/CMakeLists.txt`,
   `tests/test-server-prefill-order.cpp`) the runtime diff is `common/arg.cpp` (two new options), `common/common.h` (a bool and an
   int32 in `common_params`), `tools/server/CMakeLists.txt` (a header), `tools/server/server-prefill-order.h` (pure functions, only
   called under the flag) and `tools/server/server-context.cpp`: with `--prefill-order` unset the batch-fill lambda is the same
   body, now named `fill_prompt` and passed to the same `iterate(slots, …)`; the only new off-path work is one empty
   `std::vector<server_slot *>` per iteration; `pb_iter.budget` is untouched off the flag.
2. **The window drifted inside the load.** C-solo (the idle-server short) went 282.1 → 885.4 ms from the start to the end of the
   M4.2a load; B reps were 71.7 / 85.5 / 81.8 s and the long's own TTFT 123.4 / 139.2 / 144.2 s, while the same binary on
   2026-10-23 (M4.2 off512) gave B 74.78 / 74.83 / 74.82 s (22.13x) with C-solo 284.3 → 287.2 ms.
3. **The band came from a different build and day** (PB-HOL-1 ran the base image on 2026-10-21). Within-load B noise of the kind
   M4.2a shows (±10 %) is as large as the band itself, so a cross-day band cannot separate "candidate differs" from "window differs".

Hypothesis tested here: **the candidate with no flag (`c6ca031ac`, slot order) reproduces the champion's (`141e4bcf5`) slot-order
head-of-line B/A when both are measured in the same window.** A possible within-window drift mechanism common to both binaries is
the HIP graph-exec leak (GPU-LEAK-1c; fixed only in the later C4 fold `cdb4d8c77`, which neither binary carries); the 60 GiB own-pid
guard covers it and the alternation shares it.

## 2. Design

- **Binaries (kernel STORE only):**
  - champion = `/mnt/raid0/llm/kernels/builds/gpu-20261023-141e4bcf5-lbh/bin/llama-server`, sha256 `f0fe65c83f397dae0f40cb2bbf15223bef9be3df455f338409d5037699093882` (the branch's base);
  - candidate = `/mnt/raid0/llm/kernels/builds/gpu-20261023-c6ca031ac-m4/bin/llama-server`, sha256 `901743a0fc26bc2b4e9cfcabe3c3f8d46c9cbd7d6249e088f41ba2af417e3d90`.
    This store image is a byte-identical copy (staged 2026-10-24 by `stage_store_copy_gpu.sh`, nothing compiled, every file
    `cmp`-identical, RUNPATH `$ORIGIN:/opt/rocm/lib`, linkage PASS) of the M4.1 build that M4.2 and M4.2a ran (BUILD_OK sha
    `901743a0…`). Strings gate on every run: the candidate's libllama-common carries `--prefill-order`,
    `LLAMA_ARG_PREFILL_ORDER`, `--prefill-contend-cap`; the champion's carries none (negative control). The candidate runs with
    **no M4 flag** (default `slot` order) — the off path.
- **Server and protocol, unchanged from M4.2/M4.2a:** Qwen3.8-27B-Q8_0 + DFlash2 on `argv.8083-gate.txt` with `-np 3`, `-b`/`-ub` 512,
  HIP graphs ON (production condition), `env HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0 numactl --membind=3 -- taskset -c 184-191`, port
  18392; 64 000-token long (group 6 trunk), 128-token short (group 3 suffix 0), short sent at long progress ≥ 0.5, `cache_prompt=false`,
  slots erased between runs; prompt set sha256 `dc37cdf1…94de`. Arms: A = short slot 0 / long slot 2; B = short slot 2 / long slot 0.
- **Harness:** `pb_hol_1.py`, a copy of the M4.2a harness (sha256 `8d3b7f23…8923`) with exactly three edits: phase `off512ch` = off512 on
  the champion image; `--c-reps 3` = three solo shorts (C) at the start and at the end of every load (was one); the candidate path
  defaults to the store copy. sha256 of the edited file: `9452fdfd365adff7257e278c30e292bfe606ce41e16a3ed6492de77835da0e26`.
- **Per load (one fresh server):** solo-64K calibration, then C,C,C, A,B,A,B,A,B, C,C,C (3 reps of A and of B).
- **Window:** ONE grant; planned loads, alternating **CH, M4, CH, M4** (ABAB). A load that the §3 rule makes INVALID is followed by
  a **replacement load of the same binary** at the end of the queue, at most **2** replacements, only while the grant holds the
  per-load need. **Atomic:** the job never starts unless the grant holds the whole planned ABAB; loads from different windows are never
  pooled (each window writes `out/w-<window id>/`). Before EVERY load: `ram_admit 48`, a VRAM drain wait (poll 2 s, ≤ 120 s) until
  ≥ 60 GiB free and no foreign KFD pid, else the window is abandoned.
- **Per server proofs:** linkage (own bin dir first in LD_LIBRARY_PATH), our pid owns the port, HIP graphs ON and
  `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` from `/proc/<pid>/environ`, residency = own-pid KFD VRAM ≥ 40 GiB (harness), own-pid VRAM
  ceiling 60 GiB (harness sampler + job watcher; a trip kills OUR pid only and ends the window), and the job watcher's own-pid VRAM
  peak written on every rise to `vram_peak.<pid>.json`.
- **NON-GATING diagnostics:** `diag_sampler.py` every 10 s (sibling cores 88-95 and host threads 184-191 busy %, MI210
  gpu_busy, VRAM used, sclk/mclk, temperatures, power) to attribute any drift. Never part of the verdict.

## 3. Load validity (a load is VALID iff all hold; else INVALID, and it contributes nothing)

1. harness rc 0 and `summary.json` status `complete`; no guard trip;
2. proofs present: one port-ownership row, ok, binary sha256 = the role's store sha above, phase = the role's phase; graphs ON and
   HSA knob `0` in every graphs proof; residency ok (own-pid ≥ 40 GiB);
3. the job watcher's own-pid VRAM peak is **non-null** and ≤ 61 440 MiB (a missing own-pid residency proof never passes);
4. ≥ 2 valid A and ≥ 2 valid B reps under the M4.2a predicate, unchanged (AMENDMENT-M4.2a §2: not skipped, short answered HTTP 200,
   long progress at send ≥ 0.40, long not errored, and the long still in flight when the short was SENT);
5. **C-solo drift (task text):** all 6 solo shorts answered, and median(end 3) − median(start 3) ≤ **2.8 ms** — the C-solo spread of
   PB-HOL-1 (its only two C-solo values, 278.4 and 281.2 ms, `pb-hol-1/runs/20261021T160010Z`). One-sided: a load whose end exceeds
   its start by more than that is host/server drift, as in M4.2a (+603.3 ms).
6. the load's window id is this window's.

**Known risk, recorded before compute:** 2.8 ms is at the level of clean-load jitter. End − start on the six prior loads of this
harness: PB-HOL-1 +2.8, M4.2 srpf512 −0.6, srpf2048 +67.1, off512 +2.9, srpf2048cap0 +1.4, M4.2a off512 +603.3 ms (single shots).
Under this bar 3 of 6 would be INVALID, one of them by 0.1 ms. Taking the median of 3 solo shorts at each end lowers the random part;
the replacement loads absorb some INVALIDs. The bar is the task text's and is not loosened here. Non-gating sensitivity rows (§6)
show what 5 % and 10 % relative bars would have decided.

## 4. C2 rule (mechanical: `verdict.py`, sha256 `05fa4ef9d20f7ca2d92bb7f37d3f65b7e640c0cf7a80389e91ba4456d1fc7b8c`)

Over VALID loads only, with ≥ **2 valid champion loads and ≥ 2 valid candidate loads** (else C2 = NOT_MEASURED):

- per load L: medA_L = median(valid A short TTFT); per-rep ratio r = B_i / medA_L for each valid B rep;
- **champion band** = [min r, max r] over every valid B rep of every valid champion load — the champion's own run-to-run spread in
  this window (≥ 4 ratios, normally 6);
- **candidate statistic** R = median(all valid candidate B) / median(all valid candidate A), pooled over the valid candidate loads,
  rounded to 3 decimals;
- **C2 PASS iff band_lo ≤ R ≤ band_hi.** R < band_lo → FAIL_LOW; R > band_hi → FAIL_HIGH.

Direction: TTFT is lower-is-better; the B/A ratio measures how long a short waits behind the long under slot order. The off path should
reproduce the champion, so the test is two-sided.

## 5. What each outcome decides

| C2 | M4.2 overall (with the decided C1 PASS, C3 PASS from the sha-pinned M4.2 VERDICT.json `4b47d4b7…2078`) | decides |
|---|---|---|
| PASS | **PASS** | Tick **M4.2b**, and tick **M4.2** (its measurement half is discharged: C1 + C3 from M4.2, C2 from this same-window control). The M4.2a FAIL is attributed to the cross-day band / window, recorded, not re-judged. Next: M4's production gate, then the fold through the ledger (re-cut on the current champion first, fresh-tip rule). |
| FAIL_HIGH | **FAIL** | The candidate's off path waits longer than the champion in the same window: a real off-path regression although the source diff is behaviour-equivalent. Tick M4.2b (it decided). File **M4.2c**: localise it as a build-level difference (codegen / struct layout of `common_params`), e.g. a rebuild of `141e4bcf5` with the same recipe as a second champion arm and a disassembly diff of `update_slots`. M4 is not shippable as-is. |
| FAIL_LOW | **FAIL** | The off path changed behaviour (HOL weaker without the flag). Same consequence: tick M4.2b, file M4.2c (as above, plus a check that the default really is `slot`). |
| NOT_MEASURED (< 2 valid loads of either binary: drift, proofs, harness, window cut) | **INCOMPLETE** | No claim. If the window ran its whole plan, it is not repeated automatically; a further window needs a new written diagnosis that uses `diag.jsonl` to say what drifted (and, if the INVALIDs are clean-jitter drift at the 2.8 ms bar, an amendment of the bar with that evidence). If the window was cut before the four planned loads, the next grant runs a fresh window. |

Whatever the outcome, report NON-GATING: the champion's pooled ratio and whether it falls inside the PB-HOL-1 band (was the band itself
window-dependent?), per-load ratios and drifts, and the sensitivity rows.

## 6. NON-GATING (reported, never the verdict)

Per-load ratios, per-load C-solo drift, solo-64K calibration, own-pid VRAM at ready and peak; the champion pooled ratio vs 22.05 ± 10 %;
C2 recomputed with the drift bar replaced by 5 % and by 10 % of the load's start C-solo median; the diagnostics sampler.

## 7. Claim class, placement, window

- Claim class: **INDICATIVE timing** (a TTFT ratio on one host), the same as M4.2/M4.2a. Derived booking class
  **block-timing-pairable**: it is a timing measurement, so not correctness, and it names no floor file, so not quiet. The ratio
  is paired against the same server's own A arm, and the comparison is paired in time by the ABAB alternation. It shares the host
  with labelled work and is never co-resident on the MI210.
- Placement: mi210_0 (engine flock) + host threads 184-191, `filler_run9 --class gpu --claim-cpus 184-191 --no-fold-siblings`
  (gpu-quiet shared, no q3 fold; the M4.2/M4.2a shape), `--sched-port 8083` (production :8083 must be parked).
- Time: measured M4.2a load 733 s (harness start to end). Per load about 880 s with the drain wait. Four planned loads take about
  59 min; with two replacements, about 88 min. The task text's "about 45 min" did not count four fresh loads plus drain waits. The
  per-load start floor is 1340 s to deadline: the harness's own preflight is 1031 s × 1.15 = 1186 s, plus the drain and slack.
  `--min-window` is 4200 s (70 min): the atomic ABAB of 4010 s plus the 90 s deadline margin, rounded up. Grant at least 75 min;
  105 min is recommended so that both replacements fit.
- RAM 48 GiB (27B Q8 + DFlash2 host side, as M4.2a). STOP flag `STOP.f8-m4-2b-champion-control`.

## 8. Files and pins (this directory)

- `PREDECLARATION.md` (this file; sha256 in `PREDECLARATION.sha256`; job.sh refuses on mismatch).
- `pb_hol_1.py` `9452fdfd…0e26`, `verdict.py` `05fa4ef9…7b8c` (selftest: 20 cases, each outcome reachable; job.sh refuses if either differs).
- `diag_sampler.py` `f78cf1ab…0a59` (non-gating), `precond.sh` `ac5d545c…818c`, `stage_store_copy_gpu.sh` `42d41604…a411` (already run:
  `stage.real-20261024.log`).
- No repo code: the candidate branch `experimental/m4-srpf-batch-fill-20261023` @ `c6ca031ac` is unchanged and not rebuilt.
