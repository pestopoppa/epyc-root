# GPU → CPU timing contamination: bias and noise contribution (pre-registration)

**Status:** PRE-REGISTERED 2026-10-21, not yet run. Dry-run and stub lifecycle test pass. It runs only on a grant
from the calendar owner (workspace-58). Queue row `gpu-cpu-noise` in `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md`.
**Owner task:** U4-NOISE-1 in [`handoffs/active/autokernel-unified-surface-program.md`](../../handoffs/active/autokernel-unified-surface-program.md) §3.4 (OP-41 evidence).
**Code:** `epyc-inference-research` `b65284539` `scripts/benchmark/gpu_cpu_noise/` (driver, analysis, launcher, tests). The pinned run tree is `/mnt/raid0/llm/worktrees/gpu-cpu-noise-run-20261021`, detached at `b65284539`.
**Operator, 2026-10-21:** *"ultimately we will use GPU and CPU simultaneously in production. We should get to the
bottom of this and measure a noise contribution of sorts. This way we can assess whether work truly requires a quiet
host or not."*

## 1. Question and estimands

For each GPU condition *k*, measured against GPU-idle G0 in the same session:

- **Bias** `b_k`: the mean shift of CPU timing. Sign convention is t/s, so negative means slower.
- **Noise inflation**: the variance ratio `VR_k = s²_k / s²_G0` and the added noise `σ_add,k = sqrt(max(0, s²_k − s²_G0))`.
  - Both are given in % (log scale) at two units: **process** (one llama-bench launch) and **arm** (between the
    samples inside one launch).
  - `σ_add` is the "noise contribution". It carries over additively to any instrument with floor `σ_c`:
    `σ_total² ≈ σ_c² + σ_add²`.

These feed a decision rule (§7): which timing classes may share the host with which GPU conditions.

## 2. Prior evidence (why this is not settled)

- **2026-09-08** (INF-70 MEAS-6; memory `feedback_pinned_gpu_host_threads_still_degrade_cpu_floor_9x`):
  - A pinned GPU llama-bench chain on 184-191 moved the CPU hot-harness A/A pair p95 from 0.80% (n=7) to 7.22%
    (n=5).
  - Attribution is **not separable** from those two points. The conjunction is what is established.
  - Channel claimed: DRAM bandwidth. Prefill stayed flat while decode fell 7%.
- **2026-10-21** DS41-W5 ABA (research `da71fa603`, `data/ds41-1017-w5-20261021/SUMMARY.md`): inconclusive.
  - Decode drifted +24% over 2 h, and A1 was a cold outlier.
  - GPU-on vs off read +2.2%, inside the drift.
  - Verdict: inconclusive, not "no effect".
- Neither run interleaved the conditions, held an in-session A/A, or had a power calculation. This design has all
  three.

## 3. CPU workloads

| id | workload | unit | role |
|---|---|---|---|
| **W1** (this session) | **codified canonical llama-bench**: `bench_canonical.sh -m Qwen3.6-35B-A3B-MTP-Q8_0.gguf -p 512 -n 128 -r 3 -- -o jsonl`. Production v10 store binary, `taskset 0-95 numactl --interleave=all -t 96 -fa 1 -mmp 0`, GGML_IQK=1, pre-evict 40 GiB/node, placement proof required. | process (rep = one launch, value = mean of 3 samples); arm (the 3 samples) | the CPU timing surface for kernel A/B work; `instrument_class = bench` |
| W1-pp / W1-tg | the same launch gives **pp512** (compute-bound) and **tg128** (DRAM-bandwidth-bound) | as above | the two shapes are the channel test: bandwidth contention should hit tg, not pp |
| W2 (optional, NOT in this session) | one DS41-1017 served indicative point (one persistent server, arm unit, G0/G2 ABBA, at most ONE DS41 server) | arm | serving-class spot check of the transfer (§9). Separate queue item if wanted, DS41-class = y, ~60 min |

**Per-step CPU claim.** Each rep's `bench_canonical.sh` takes its own `region-lock` claim on cpu-list 0-95
(`--role bench-canonical`) for that step. The driver takes no outer CPU claim, because an outer claim on the same
regions deadlocks the recipe ("hold once").

## 4. GPU conditions

All conditions use the champion GPU build `kernels/builds/gpu-20261020-dd3d9721c` (build `b10345-dd3d9721c`) and
Qwen3.8-27B-Q8_0 with the DFlash2 drafter. The argv is the 2026-10-04 receipt / CH-20 item e argv:
`-np 4 -c 393216 --kv-unified -t 8 -ub 2048 -fa on -ctk/-ctv q8_0 --no-mmap -ngl all --cache-ram 65536
--spec-type draft-dflash --spec-draft-n-max 7 --device ROCm0`, about 54.5 GB VRAM.

The MI210 is PCI `43:00.0` on **NUMA node 1**.

| cond | GPU state | host threads | purpose |
|---|---|---|---|
| **G0** | no KFD process | none | reference; two runs per block give the in-session **A/A** |
| **G1** | 27B resident, idle | 184-191 (node 3, siblings of 88-95), `--membind=3` | residency tax alone |
| **G2** | 27B decode loop, one stream (`/completion`, n_predict 512, ignore_eos) | 184-191, membind 3 | sustained decode, today's production shape |
| **G3** | 27B prefill-heavy loop: unique ~16k-token prompts, n_predict 8, one stream | 184-191, membind 3 | prefill bursts (PCIe/DMA, host staging) |
| **G4** | = G2 | **136-143** (node 1 = the GPU's node, siblings of 40-47), `--membind=1` | placement / locality |
| **S8** | GPU idle; 8 pure-ALU spinners on 184-191 | 184-191 | **SMT-only mechanism control** (no memory, PCIe or driver traffic) |

**Why S8 exists (a correction to the brief's G4 rationale).** W1 runs `-t 96` on all 96 physical cores, so every
logical CPU 96-191 is the SMT sibling of a busy bench core. Moving the host threads to another quarter therefore
cannot remove SMT contention.

- G4 − G2 isolates **placement**: node-local vs remote PCIe/Infinity-Fabric path and driver/IRQ locality, with
  SMT exposure held equal (8 siblings either way).
- S8 isolates the **SMT channel** directly, as an upper bound at 100% duty. The GPU server's real host-thread duty is
  recorded per rep (per-CPU busy on 184-191 and 136-143).
- The non-SMT residual is G2 − S8 (with the duty-cycle note).

**Verified per rep (positive controls, both directions; BOUNDED-NULL-1).** These come from a 1 Hz sysfs sampler.
`gpu_busy_percent` is the counter rocm-smi reports as "GPU use". rocm-smi itself runs only between reps, because
it is a Python process that would load the bench cores.

- G0/S8: KFD empty on every sample.
- G1-G4: our server pid is in KFD on every sample, VRAM ≥ 20 GiB, no foreign KFD pid.
- G2/G3/G4: GPU busy > 10% on ≥ 50% of samples.
- G1: median busy ≤ 5%.
- S8: 184-191 at least 90% busy.
- Server: own pid owns the port; the own `libggml-hip.so` is mapped; `/props` build matches; every task's
  `Cpus_allowed_list` equals the placement.

A rep that fails a control stays a row with `valid=false` and the reason. It is never dropped silently.

## 5. Protocol

1. **Warm-up (discarded):**
   - two G0 llama-bench launches (CPU page cache, NUMA placement);
   - GPU server up, decode loop for 20 s;
   - one rep under G2 and one under G3 (both sides warm together).
2. **Blocks.** B = 10 blocks, back to back. Each block is a seeded shuffle of the runs
   `[G0, G0, G1, G2, G3, G4]`, plus S8 in the odd blocks (5 S8 runs).
   - Seed `gpu-cpu-noise-20261021`; blake2b(seed, "order", b).
   - The schedule is written with its sha256 before the first measured rep.
3. **Runs.** Each run is **5 back-to-back reps** of one condition. The GPU state changes only between runs: client
   stop → `/slots` idle; server stop → KFD empty; server restart is about 4 s from page cache.
4. **Per rep** the driver records:
   - start/end, the bench rc, placement-proof rc, and the pp/tg `samples_ts`;
   - a GPU and host-CPU sample summary;
   - foreign CPU, as `/proc` utime+stime deltas of processes outside our own tree, in cores;
   - the server pid and placement, the client mode, and a self-hash (`content_sha256`).
5. **Exclusions** (pre-registered):
   - a rep with bench rc ≠ 0 is retried once in place;
   - reps with failed controls, placement skew or foreign load > 4 cores are excluded from the primary analysis;
   - the `--include-invalid` sensitivity analysis is reported beside the primary.
6. **Stopping rule.** The deadline is min(grant end, start + 3.5 h) − 3 min.
   - After block 0, B is reduced ONCE, from timing alone and before any analysis, to the largest number that fits
     (floor `B_min = 7`).
   - A run that cannot finish before the deadline is not started, and the session ends with a G0-safe teardown.
   - The table produced by `analyze_gpu_cpu_noise.py` on the completed blocks is **FINAL**. No confirmation rerun
     unless the decision table says UNDECIDED for a (class, condition) cell that a pending deployment depends on.

## 6. Power and n (computed, scipy, one-sided α = 0.05 for VR, two-sided for bias)

- **Variance, process unit.** At B = 10 and runs of 5, df_k = 40 and df_G0 = 80 (two G0 runs per block).
  - **Power to detect VR = 2: 0.81**; VR = 3: ~0.97.
  - At B_min = 7 (df 28/56): 0.69 at 2×.
  - Runs of 5 were chosen over pairs: they give 0.8 df per rep where pairs give 0.5, and pairs would need 480 reps.
- **Variance, arm unit.** df_k ≈ 100 and df_G0 ≈ 200 give power ≈ 0.99 at 2×.
- **Bias (paired by block, 10 blocks).** The per-block log-ratio sd is σ·sqrt(1/5 + 1/10).
  - At process sd ≤ 1%, power to detect a **1% shift is ≥ 0.99**.
  - At an inflated sd of 2%: 0.73. At 3%: 0.41, but there the variance verdict is already NOT-SHAREABLE.
  - Prior llama-bench tg128 A/A on this host: pair sd 0.28% (INF-70 hot-harness quiet subset), so σ ≈ 0.2-0.5%.
- **Total:** 65 runs × 5 = 325 measured reps + 4 warm-up reps. At an estimated 30 s/rep plus about 20 s per run
  switch and 10 min of setup, that is **about 3.2 h** (cap 3.5 h).

## 7. Analysis (`analyze_gpu_cpu_noise.py`, numpy; scipy adds the parametric intervals)

- **Rep value** = mean of llama-bench `samples_ts`, on the log scale.
- **Bias.** `b_k = median(k reps)/median(G0 reps) − 1` over the blocks holding both conditions. This is the
  matched_process_v2 estimator shape.
  - 95% CI = the union of the block-bootstrap percentile CI (20,000 resamples of blocks, pairing kept) and the
    t-CI of the per-block log ratios. Decisions use the union.
- **Noise.**
  - Pooled within-run variance per condition at the process unit, and pooled within-launch sample variance at the
    arm unit.
  - VR with F-CI ∪ block-bootstrap CI.
  - `σ_add` with CI.
- **A/A (G0 run 1 vs run 2 of each block)**: same estimator. This is validity gate **V1**.
- **INF-70 continuity**: the "A/A pair p95" per condition, from non-overlapping consecutive rep pairs inside runs,
  unit process. It is quotable only with ≥ 20 pairs.
- **Mechanism**:
  - G4 − G2 (placement);
  - S8 bias (SMT);
  - tg vs pp (the bandwidth channel);
  - the reverse direction: GPU client t/s for requests that overlap a CPU rep vs those between reps.
- **Multiplicity**: the verdicts are per (class, condition) cell on 95% CIs, and no global claim is made.

## 8. Decision rule (pre-registered; constants live in the analysis script)

A cell is **SHAREABLE** only if every criterion holds on BOTH tg and pp; the worse of the two decides.

It is **NOT-SHAREABLE** if a criterion fails at the near end of its CI, and **UNDECIDED** otherwise. UNDECIDED is
power-limited and is treated as not shareable until replicated.

| class | what it is | bias criterion | noise criterion |
|---|---|---|---|
| **DG**, decision-grade baselines | the consolidated champion speed test, anything future work is measured against | 95% CI of `b_k` inside ±0.5% | process VR upper-95 < 2.0 AND arm VR upper-95 < 1.5 |
| **AK**, keep gates | resolve 1-3%; matched_process_v2, process unit | 95% CI inside ±1.0% (the condition may differ between arms) | `σ_add` upper-95 ≤ 0.458 × 2.793% = **1.28%**, i.e. ≤ 10% widening of the AK serving floor (process sd 2.793%, INF-70 RETEST-1, FLOOR-UNIT-1) |
| **IND**, indicative | DS41/Nemotron sanity speeds (operator 2026-10-21) | always admissible with the GPU job labelled; the measured `b_k` is published as the correction note; flagged LARGE if \|b\| > 5% | — |

Gates:

- **V1**: the G0 A/A bias CI contains 0 and \|A/A\| ≤ 0.5%. If it fails, all verdicts are WITHHELD as session drift.
- **V2**: ≥ 80% of a condition's reps (and of G0's) pass their positive controls. Otherwise that condition is
  UNTESTED.
- **V3**: blocks done < B_min means every verdict is labelled reduced-power.

**What each outcome triggers.** A condition that is SHAREABLE for AK lets AK keep gates and the champion's
non-baseline A/Bs run beside that GPU job, labelled, and is proposed to the operator as the OP-41 co-scheduling
input. NOT-SHAREABLE for DG confirms the quiet-host requirement for baselines under that condition.

## 9. Caveats carried with every number

- **Instrument class.** W1 is `bench`. A *contamination* estimate (b, σ_add) is transferred to serving-class AK
  gates as a policy input, never as a speed number. Cross-class speed comparison stays REFUSED (INSTRUMENT-CLASS-1).
  W2 is the serving spot check.
- **Host health.** Uptime is recorded. At ≥ 1 week (8 d 13 h on 2026-10-21) the tier is "STALE": the relative
  estimands are within-session and valid, but the session's G0 floor is not quotable as the host's quiet floor.
  Reboots are the operator's.
- **Placement.** G4 moves the host threads AND the memory node together, so it measures the placement as a whole,
  not a single cause. S8 is a 100%-duty SMT upper bound.
- **No CPU claim for the contaminant.** The GPU server, client and spinners deliberately hold no CPU-region claim
  while the bench holds 0-95, because they are the variable under test. The session holds `gpu-quiet exclusive`
  and the `mi210_0` device flock for its whole length, so no other GPU job can join.
- **Third-party load** is not prevented by the locks ("region-lock serialises those who call it"). It is measured
  per rep and excluded above 4 cores.

## 10. Lifecycle and files

- Launcher `run_gpu_cpu_noise.sh`:
  - `dry-run`, `stub-test` and `status` run in the foreground;
  - `arm` detaches the grant poller with `setsid nohup … </dev/null &` and writes a pidfile;
  - the session runs under `region-lock run --gpu-quiet exclusive --role bench`, and the driver takes the
    `mi210_0` flock;
  - hard end: TERM the captured session group, wait, KILL, verify, then a registry sweep of the driver's own
    children (pid plus start time);
  - `$RUN/END` is written on every exit path, followed by `grants/gpu-cpu-noise.ended` and, on success,
    `.complete`.
- Run dir `/mnt/raid0/llm/tmp/gpu-cpu-noise-20261021/`, with:
  - `PREREG.md` (this file);
  - `runs/<session>/`: `RUN_RECORD.json` (prereg sha256, code HEAD, binaries' sha256, host state), `schedule.json`,
    `timeline.jsonl`, `reps.jsonl` (schema `epyc.gpu_cpu_noise.rep.v1`, self-hashed), `gpu_client.*.jsonl`,
    `ANALYSIS{,-sensitivity}.{json,md}`.
- Belief kernel: the write side is native (self-hashed rep rows). The adapter is task VB-GPU-CPU-NOISE-WIRE in
  `handoffs/active/vidya-belief-substrate-program.md`, with its source row in `scripts/vidya/adapters/README.md`.
