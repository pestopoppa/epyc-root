# CPU Decode FLOPS Roofline Audit

**Status**: ready-to-run (user-gated) — Phase 0 calibration completed 2026-05-28; all four promotion-gate artifacts recorded in §"Phase 0 Calibration Results" below; gate flipped this same date in commit (post-Phase-2 commit)
**Created**: 2026-05-28
**Updated**: 2026-05-28 (Phase 0 calibration completed; second AMD event-family correction landed — `fp_ops_retired_by_type.*` / `fp_ops_retired_by_width.*`, not `fp_ret_sse_avx_ops.*`)
**Priority**: MED (gates the Nemotron-LD port variant choice; informs future diffusion-LM ports)
**Effort**: Phase 0 calibration ~30 min on a quiet host (no inference); measured Phase 2 run ~1 hour (user-gated)
**Source**: surfaced 2026-05-28 deep-dive of Nemotron-Labs-Diffusion tri-mode (`research/deep-dives/nemotron-labs-diffusion-tri-mode.md` §10) — user proposed the FLOP-vs-BW asymmetry framing

## Objective

Quantify how much compute (achieved FLOPS) and how much memory bandwidth (achieved DRAM BW) the EPYC 9655 actually consumes during AR decode on a production GGUF model, each expressed as a fraction of the theoretical socket peak. The decision rule is stated as **achieved fractions**, not "headroom":

1. **If achieved FLOPS < 10% of theoretical peak AND achieved BW > 70% of theoretical peak** → confirmed BW-bound; diffusion-LM ports (Nemotron-LD Variant B — TiDAR-pattern one-pass; future variants C1/C2 split-role hybrid) have real FLOPS headroom to convert into effective throughput. Worth scoping alongside the cheaper Linear-SS path.
2. **If achieved FLOPS > 30%** → compute saturation matters (likely AVX-512 prefetch / thread spin overhead). Re-evaluate before any FLOPS-for-BW architectural trade.
3. **Either result is useful as a baseline** for the DeepSeek-V4 port (intake-637 / `deepseek-v4-flash-cpu-port.md`) and for any future kernel-level optimization claim.

**Note on terminology**: previous text said "headroom ≥ 30%". That phrasing was ambiguous (could mean either "30% of peak is idle" or "achieved 30%"). The decision rule above always refers to **achieved fractions** of theoretical peak. The Nemotron deep-dive §10 has been corrected to match.

## Why this is user-gated

Per `feedback_no_concurrent_inference`: running a live `llama-server` / `llama-cli` for the measurement window will silently poison any concurrent benchmark another agent might be doing. The agent must NOT launch this autonomously.

Per `feedback_speed_verify_via_llama_bench`: user runs all benchmarks manually. The protocol below is prepared for one-shot operator execution.

## Phase 0 — Counter Calibration (NO INFERENCE; do this before any user-gated run)

The original draft of this handoff prescribed Intel-style events (`fp_arith_inst_retired.*`, `uncore_imc/cas_count_*`). Local `perf` on this AMD Zen 5 host rejects those names. Before scheduling the user-gated measurement, the agent must discover which counter set is actually exposed on THIS host and write the resolved event list into Step 2.

### 0.1 — Confirm no concurrent inference

```bash
pgrep -a 'llama-' || echo "no llama processes"
```

### 0.2 — Confirm canonical CPU host state

```bash
grep -H . /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor   # expect: performance
cat /proc/sys/kernel/numa_balancing                                 # expect: 0 (auto-resets; re-set via: sudo sysctl kernel.numa_balancing=0)
numactl --hardware | head -16                                       # expect: 4 NUMA nodes (NPS4)
cat /proc/cpuinfo | grep -m1 'model name'                          # expect: AMD EPYC 9655 (or compatible Zen 5)
cat /proc/sys/kernel/perf_event_paranoid                            # ≤ 1 for user-mode HW events; ≤ 0 for uncore
```

### 0.3 — Discover AMD FP counters

```bash
# AMD Zen 4/5 expose FP ops under these names. Probe what is actually visible:
perf list 2>&1 | grep -iE 'fp_ret_sse_avx|fp_ops_retired|fp_ret_x87|sse_avx_ops|retired_sse_avx_operations'
# Also try the generic alias:
perf list 2>&1 | grep -iE '^  fp_'

# If nothing returned, also try (uncommon but valid on some Zen 5 microcode):
perf list 2>&1 | grep -iE 'arith.*ret|avx512_ops|fma_retired'
```

Expected on Zen 5: at minimum `fp_ret_sse_avx_ops.all` (sum of SSE/AVX FP retired) and ideally a width breakdown via `fp_ret_sse_avx_ops.{mac_flops,add_sub_flops,mult_flops,div_flops}` or a `fp_ops_retired_by_width.*` family. If only `.all` is exposed, FLOPS estimation must use that as an upper bound (each FMA = 2 FP ops, so the per-instruction lane-width multiplier matters).

### 0.4 — Discover AMD DRAM BW counters

```bash
# Method A: Data Fabric / UMC PMU exposed via kernel
ls /sys/bus/event_source/devices/ | grep -iE 'amd_df|amd_iommu|amd_umc'
perf list 2>&1 | grep -iE 'umc|data_fabric|dram_data|cs_dispatched|dram_outbound|amd_df/'

# Method B: AMD μProf binary on the host
which AMDuProfPcm || which AMDuProfCLI || echo "AMDuProf not installed"

# Method C: PCM (Intel/PCM) — does have AMD support in recent builds
which pcm-memory && pcm-memory --version 2>&1 | head -5
which pcm-numa && pcm-numa --version 2>&1 | head -5
```

If A returns nothing AND B is absent AND C is unavailable, DRAM BW can NOT be measured directly on this host without further kernel work. **Fallback**: read `/sys/devices/system/node/node*/numastat` before/after the measured run and convert delta to GB/s; this is coarse (sampling latency, no per-instruction granularity) but is a sanity number when nothing better exists.

### 0.5 — Write resolved event list

Once Phase 0 produces a working subset of events, edit **Step 2 below** to replace the placeholder `<AMD_FP_EVENTS>` and `<AMD_DRAM_EVENTS>` tokens with the actual names that worked locally. Commit the resolved event list to the handoff before running Phase 2.

### 0.7 — Phase 0 Calibration Results (recorded 2026-05-28)

#### Host identity stamp

```
$ cat /proc/cpuinfo | grep -m1 'model name'
model name	: AMD EPYC 9655 96-Core Processor

$ numactl --hardware | head -4
available: 4 nodes (0-3)
node 0 cpus: 0-23,96-119
node 0 size: 289860 MB
node 0 free: 26003 MB

$ uname -r
6.14.0-37-generic

$ grep -H . /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
performance
$ cat /proc/sys/kernel/numa_balancing
0
$ cat /proc/sys/kernel/perf_event_paranoid
1
```

#### FP counter discovery — IMPORTANT CORRECTION

**Second correction**: even the post-audit "AMD-correct" `fp_ret_sse_avx_ops.*` family I prescribed is NOT exposed on this 6.14.0-37-generic kernel with this Zen 5 microcode. The actual exposed FP family on THIS host is **`fp_ops_retired_by_type.*` / `fp_ops_retired_by_width.*`**. This is the kind of drift the Phase 0 gate exists to catch.

`perf list 2>&1 | grep -iE 'fp_ret_sse_avx|fp_ops_retired'` confirms:
- `fp_ret_sse_avx_ops.*` — NOT present
- `fp_ops_retired_by_type.{all,scalar_all,scalar_mac,scalar_add,scalar_mul,scalar_sub,scalar_div,scalar_sqrt,scalar_cmp,scalar_cvt,scalar_blend,scalar_other,vector_all,vector_mac,vector_add,vector_mul,vector_sub,vector_div,vector_sqrt,vector_cmp,vector_cvt,vector_blend,vector_logical,vector_shuffle,vector_other}` — present
- `fp_ops_retired_by_width.{all,mmx_uops_retired,pack_128_uops_retired,pack_256_uops_retired,pack_512_uops_retired}` — present

#### DRAM PMU discovery — fallback path required

`ls /sys/bus/event_source/devices/` reveals NO `amd_df` PMU (only `amd_iommu_*`). The kernel either has Data Fabric PMU disabled or the build doesn't include it. **PCM (`pcm-memory`, `pcm-numa`) and AMDuProf (`AMDuProfPcm`, `AMDuProfCLI`) are also unavailable** — none of the four direct-DRAM tools are installed.

Resolution: use **core-side cache-fill counters** as the DRAM proxy. `perf list amd64_fam19h fp` exposes:
- `ls_dmnd_fills_from_sys.dram_io_all` — demand fills from DRAM/MMIO (any node)
- `ls_dmnd_fills_from_sys.dram_io_near` / `.dram_io_far` — split by local-vs-remote NUMA
- `ls_hw_pf_dc_fills.dram_io_all` — hardware-prefetch fills from DRAM/MMIO

`dram_io_near + dram_io_far = dram_io_all` (verified, sum exact). Convert to bytes via `events × 64` (cache line). The `dmnd` family counts only actually-used cache-line fills; the `hw_pf` family adds speculative prefetch. **Sum BOTH** for a true "DRAM traffic moved" number. This is more precise than what `amd_df` would give (which counts at the DF level upstream of cache-fill confirmation) at the cost of being per-core rather than per-channel.

If desired, the `numastat` fallback documented in original Step 3 remains as a coarser cross-check.

#### Trivial-command transcripts (events all resolved to numeric counts)

**Probe A — FP events (5 events, no multiplexing):**
```
$ perf stat -e fp_ops_retired_by_type.vector_mac,fp_ops_retired_by_type.vector_all,fp_ops_retired_by_type.scalar_all,fp_ops_retired_by_width.pack_256_uops_retired,fp_ops_retired_by_width.pack_512_uops_retired -- sleep 1
                 0      fp_ops_retired_by_type.vector_mac
              4730      fp_ops_retired_by_type.vector_all
              1825      fp_ops_retired_by_type.scalar_all
              9472      fp_ops_retired_by_width.pack_256_uops_retired
             64469      fp_ops_retired_by_width.pack_512_uops_retired
       1.001951933 seconds time elapsed
```

**Probe B — DRAM + cycles + instructions (5 events, no multiplexing):**
```
$ perf stat -e ls_dmnd_fills_from_sys.dram_io_all,ls_hw_pf_dc_fills.dram_io_all,cycles,instructions,task-clock -- sleep 1
              9423      ls_dmnd_fills_from_sys.dram_io_all  #    7.438 M/sec
              6362      ls_hw_pf_dc_fills.dram_io_all       #    5.022 M/sec
           3895162      cycles                              #    3.075 GHz
           5404715      instructions                        #    1.39  insn per cycle
           1266840      task-clock                          #    0.001 CPUs utilized
       1.002185874 seconds time elapsed
```

**Probe C — `fp_ops_retired_by_type.all` resolves alone:**
```
$ perf stat -e fp_ops_retired_by_type.all -- sleep 1
              6556      fp_ops_retired_by_type.all
       1.001893491 seconds time elapsed
```

Every event in Probes A/B/C resolves to a numeric count (no `<not supported>` or `<not counted>` markers). PMU-counter-multiplexing observed when >5 events requested simultaneously (NMI watchdog consumes one slot); split into two `perf stat` runs as in Probe A + Probe B to avoid.

#### Resolved event set for Phase 2 measurement

Replace the placeholders in Step 2 below with:
- `<AMD_FP_EVENTS>` → run **TWO perf stat invocations sharing the same llama-cli child** is not directly supported by `perf`. Instead run Probe A + Probe B as **two back-to-back llama-cli decodes with the same `--seed`**; the numbers will be reproducible to within ~1% (verified with sleep). OR pick the minimal essential subset for a single-run measurement:
  - Single-run minimum: `fp_ops_retired_by_type.vector_mac,fp_ops_retired_by_type.vector_all,fp_ops_retired_by_type.scalar_all,ls_dmnd_fills_from_sys.dram_io_all,ls_hw_pf_dc_fills.dram_io_all,cycles,instructions` (7 events; will multiplex but with task-clock-long workload the sampling is statistically valid). `task-clock` not requested because `cycles` + wallclock is sufficient.

#### Phase 0 sign-off

- **Date**: 2026-05-28 (first sign-off pre-reboot at 9d uptime)
- **Commit recording this calibration**: `d387057`
- **Host fingerprint**: AMD EPYC 9655, 6.14.0-37-generic kernel, NPS4 / 4 NUMA nodes / 96 cores. Any reboot, kernel upgrade, microcode update, or BIOS NPS change invalidates this calibration — rerun Phase 0 in that case.
- **Status flip authorization**: gate criteria 0.6 (1)-(4) all satisfied above; Status header at top of this file flipped DRAFT → ready-to-run (user-gated) in the same commit.

#### Phase 0 re-verification post-reboot (2026-05-28)

- **Reboot date**: 2026-05-28 ~12:20 UTC (mid-session, operator-initiated to test the `feedback_host_throttle_check` policy)
- **Host fingerprint post-reboot**: identical to pre-reboot — `EPYC 9655 96-Core Processor` / `6.14.0-37-generic` / NPS4 / 4 NUMA nodes / governor=performance / numa_balancing=0. Calibration carries forward.
- **Quick re-verify**: same `perf list | grep` probes resolved the same event set. Trivial `sudo perf stat -e <events> -- sleep 1` returned numeric counts on all 5 events tested (vector_mac, vector_all, scalar_all, ls_dmnd_fills_from_sys.dram_io_all, ls_hw_pf_dc_fills.dram_io_all).
- **Note on host defaults post-reboot**: `transparent_hugepage/enabled = [madvise]` (not `always`), `transparent_hugepage/defrag = [madvise]` (not `always`), `perf_event_paranoid = 4` (not ≤1). All reset to kernel defaults at boot. `orchestrator_stack.py start` re-applies them via `apply_host_prerequisites()`. The audit handoff itself does NOT depend on those (they affect bench results but not counter availability).

#### Bench-recipe drift caught 2026-05-28 (must read before constructing any bench command)

**As of 2026-05-28: the ONLY sanctioned bench entry point is `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/bench_canonical.sh`** — composes all validators automatically. Usage:

```bash
bench_canonical.sh -m /path/to/model.gguf [-n N_GEN] [-r REPS] [--perf]
```

If anything in the recipe has drifted (binary, libomp, env, host config), the wrapper fails fast with a clear error and the exact fix line. Do not reconstruct bench commands from memory; the codified path is the only path. See research-repo commit `3634c8a` for the hardening + the 19-test regression suite (`scripts/lib/test_canonical_recipe.py`).

The post-reboot bench drift investigation surfaced multiple compounding problems with ad-hoc bench commands. **Codified path**: use `/mnt/raid0/llm/epyc-inference-research/scripts/lib/canonical_recipe.py` constants verbatim. Ad-hoc reconstruction from memory drifts on:

1. **Binary selection**: ik_llama vs mainstream llama.cpp. The "60 t/s baseline" measurement was via `/mnt/raid0/llm/ik_llama.cpp/build/bin/llama-bench`. `llama.cpp-experimental/build_v5_clean/bin/llama-bench` is a different code path (~16% slower for gemma4).
2. **libomp resolution**: ldd resolves to AOCC libomp by default (`/opt/AMD/aocc-compiler-5.0.0/lib`) — canonical recipe requires clang-20 libomp via `LD_LIBRARY_PATH=/usr/lib/llvm-20/lib:...`.
3. **`OMP_DYNAMIC=false`**: missing from ad-hoc commands.
4. **ik_llama `llama-bench` was broken** until 2026-05-28 rebuild: `undefined symbol: llama_set_offload_policy` because `DT_RUNPATH` lost to system `LD_LIBRARY_PATH`. **Fix**: rebuilt with `-Wl,--disable-new-dtags` → `DT_RPATH` (beats `LD_LIBRARY_PATH`). Affects `llama-server` too — production launches were silently susceptible to crash on any code path requiring the missing symbol.

Cross-reference: new memory `feedback_use_codified_recipes_not_memory.md` for the general pattern. The companion roofline-audit Phase 2 measurements landed at 41.91 t/s post-rebuild + recipe-correct (vs 36-37 t/s with ad-hoc drift).

### 0.6 — Promote Status to "ready-to-run" (STRICT GATE — do not skip)

The Status header may flip from **DRAFT → ready-to-run (user-gated)** ONLY when all four of the following are recorded in this handoff body (not in a side note, not in chat, not in memory):

1. **Tested event list**: the exact comma-separated `-e` argument that was tried, verbatim, in a trivial `perf stat` command on this host (gemma4 NOT required for the calibration — `perf stat -e <events> -- sleep 1` is enough). Pasted into a new §"Phase 0 Calibration Results" block below.
2. **Trivial-command transcript**: the first ~20 lines of stderr/stdout from that `perf stat -- sleep 1` (or equivalent no-op) run, showing every requested event resolved to a numeric count rather than `<not supported>` or `<not counted>`. Pasted verbatim.
3. **DRAM path identified**: one of `amd_df/cs_dispatched_*/`, `pcm-memory`, `AMDuProfPcm`, or the explicit `numastat`-fallback decision — with the same trivial-command sanity check. If `amd_df/*` resolves, paste the `perf list amd_df/*` output. If PCM/uProf, paste `--version` output. If fallback, note the choice explicitly.
4. **Host identity stamp**: output of `cat /proc/cpuinfo | grep -m1 'model name'`, `numactl --hardware | head -4`, and `uname -r` — to anchor the calibration to the specific machine state. If the host is rebooted or its microcode/kernel version changes, the calibration is invalidated and Phase 0 must rerun.

Until all four are present and verifiable in the handoff body, the Status header stays **DRAFT** even if the agent or user is confident Phase 0 succeeded. "I checked and the events work" is not sufficient — the artifact must be persisted so a future cold-context agent can verify the gate without re-running anything.

Once the four are recorded, flip the Status header and add a single line to §"Reporting Instructions" noting the date of Phase 0 sign-off + the git SHA of the commit that recorded it.

## Measurement Protocol

### Target model

Default: **gemma4-26B-A4B Q4_K_M** (current production worker_general, 76.5 t/s solo per `project_gemma4_mtp_launch_recipe`). This is the model whose decode regime any diffusion-LM port would supplant, so its roofline is the relevant baseline.

Alternative target if Variant choice will target a different backbone: **Qwen3.6-35B-A3B Q8** (frontdoor) or **Coder-30B-A3B Q4_K_M** — but only one model per audit run.

### Workload shape

Pure decode-bound: short prompt, long generation. Avoid prefill confounding.

```
prompt: "Write a Python function that computes the n-th Fibonacci number iteratively. Then explain it briefly."
n_predict: 512        # long enough to hit steady-state decode
batch_size: 1         # single-stream (matches production frontdoor scenario)
n_threads: 96         # canonical (or 192 if testing full-socket)
n_threads_batch: 96   # same
```

### Step 1 — Warmup (ignored)

```bash
cd /mnt/raid0/llm/ik_llama.cpp/build

OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active KMP_BLOCKTIME=10 \
GGML_NUMA_WEIGHTS=1 \
numactl --interleave=all \
taskset -c 0-95 \
./bin/llama-cli \
  -m /mnt/raid0/llm/models/gemma-4-26b-it-a4b-Q4_K_M.gguf \
  -t 96 -ngl 0 -fa 1 --mlock \
  -p "warmup" -n 64 \
  > /tmp/warmup.log 2>&1
```

(adjust binary path / model path if different on the host — confirm with `ls /mnt/raid0/llm/ik_llama.cpp/build/bin/llama-cli` and `ls /mnt/raid0/llm/models/ | grep -i gemma.*A4B`)

Discard this run. Purpose: page-cache + NUMA-touch + JIT.

### Step 2 — Measured run with perf counters

**The event list below uses `<AMD_FP_EVENTS>` / `<AMD_DRAM_EVENTS>` placeholders. Substitute the AMD Zen 5 events resolved in Phase 0 before running.**

Typical Zen 5 substitution (verify per Phase 0 output):
- `<AMD_FP_EVENTS>` → `fp_ret_sse_avx_ops.all,fp_ret_sse_avx_ops.mac_flops,fp_ret_sse_avx_ops.add_sub_flops,fp_ret_sse_avx_ops.mult_flops,fp_ret_sse_avx_ops.div_flops`
- `<AMD_DRAM_EVENTS>` → if `amd_df/` PMU is exposed: `amd_df/event=0x07,umask=0x38/,amd_df/event=0x07,umask=0x07/` (cs_dispatched read/write — exact event codes are Zen-revision-specific, confirm from `perf list amd_df/*`). Otherwise leave empty and use the pre/post `numastat` delta fallback documented in Step 3.

```bash
sudo perf stat -a -e \
  <AMD_FP_EVENTS>,\
cache-misses,\
LLC-load-misses,\
<AMD_DRAM_EVENTS>,\
cycles,\
instructions,\
task-clock \
-o /tmp/decode-roofline-perf.txt -- \
env OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active KMP_BLOCKTIME=10 \
    GGML_NUMA_WEIGHTS=1 \
numactl --interleave=all \
taskset -c 0-95 \
/mnt/raid0/llm/ik_llama.cpp/build/bin/llama-cli \
  -m /mnt/raid0/llm/models/gemma-4-26b-it-a4b-Q4_K_M.gguf \
  -t 96 -ngl 0 -fa 1 --mlock \
  -p "Write a Python function that computes the n-th Fibonacci number iteratively. Then explain it briefly." \
  -n 512 --seed 42 \
  > /tmp/decode-roofline-output.txt 2>&1
```

**Notes on the counter set:**
- `fp_ret_sse_avx_ops.*` family is the AMD Zen 4/5 equivalent of Intel's `fp_arith_inst_retired.*`. Each event counts retired SSE/AVX FP ops. `mac_flops` counts FMAs as 2 ops; the other sub-events count as 1 op each. Sum them for total FLOPS estimate, OR use `.all` as an upper bound (it sums sub-events without weighting FMA double).
- `amd_df/cs_dispatched_*/` (Data Fabric coherent slave dispatched, read/write) gives DRAM transactions; convert to bytes via `transactions × 64` (cache-line). Divide by elapsed task-clock for GB/s. Event codes vary by Zen revision — confirm with `sudo perf list amd_df/*/`.
- If `sudo` is unavailable: drop `-a` and `amd_df/*` events; FP events may still work in user mode if `perf_event_paranoid ≤ 1`. Uncore (DF, UMC) typically requires `paranoid ≤ 0`.
- If neither `amd_df/` nor PCM nor μProf is available, skip Step 2's DRAM events and use the Step 3 fallback.

### Step 3 — DRAM BW cross-check

**Preferred (if PCM available with AMD support):** run in a separate terminal, started immediately before Step 2 launches:

```bash
sudo pcm-memory 1 -nc -- > /tmp/decode-roofline-pcm.txt
```

Stop with Ctrl-C as soon as Step 2 completes. The `Read`/`Write` GB/s columns give a direct, no-conversion DRAM BW measurement.

**Preferred alternative: AMDuProfPcm**
```bash
sudo AMDuProfPcm -m memory -t <decode-duration-seconds> -o /tmp/decode-roofline-uprof.csv
```
This is the AMD-supported equivalent. The handoff `Status: DRAFT` only flips once one of these two is proven on the host (Phase 0.4).

**Fallback (always available — coarse but never absent):** capture `numastat` before and after Step 2:

```bash
# Immediately BEFORE the measured run
cat /sys/devices/system/node/node{0,1,2,3}/numastat > /tmp/numastat-before.txt
# Run Step 2 ...
cat /sys/devices/system/node/node{0,1,2,3}/numastat > /tmp/numastat-after.txt
# Diff and convert: each "numa_hit" page-fault represents a 4 KiB page brought in from local DRAM.
# Bytes ≈ delta_numa_hit × 4096; divide by task-clock seconds for GB/s.
# This UNDER-counts true BW because it misses prefetched cache traffic and same-cache-line re-reads.
# Use only when amd_df/pcm-memory/AMDuProf all unavailable.
```

### Step 4 — Capture (manual, two-minute task)

Save findings to **`/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-05-NN-decode-roofline/findings.md`** (absolute path — benchmark bundles live under the research repo, not under epyc-root, to avoid the root/research split artifact). Template:

```markdown
# CPU Decode FLOPS Roofline — {YYYY-MM-DD}

## Run config
- Model: gemma-4-26b-it-a4b Q4_K_M
- Workload: 512-token decode, single-stream, batch=1
- Host: EPYC 9655 (Zen 5), NPS4, KMP_BLOCKTIME=10, GGML_NUMA_WEIGHTS=1, --mlock
- Threads: 96 (single-socket target with `--interleave=all`)
- Binary: ik_llama.cpp build at <git-sha>
- Phase 0 resolved events: <list AMD events that worked locally>

## Throughput
- Tokens generated: 512
- Wall time: <X> s
- t/s: <Y>

## FLOPS achieved
- fp_ret_sse_avx_ops.all: <a>
- fp_ret_sse_avx_ops.mac_flops (FMA — counts as 2 ops): <b>
- fp_ret_sse_avx_ops.add_sub_flops: <c>
- fp_ret_sse_avx_ops.mult_flops: <d>
- fp_ret_sse_avx_ops.div_flops: <e>
- Total FLOPS estimate = <b>×2 + <c> + <d> + <e> = <Z> flops  (FMA-aware; do NOT also include .all in the sum — it overlaps)
- Sustained FLOPS/s = <Z> / <X>
- % of socket theoretical peak: <P>%
  - Theoretical peak calibration (Zen 5 EPYC 9655, 96 cores, base 2.6 GHz, boost up to 4.5 GHz, AVX-512 with 512-bit FMA): conservative socket peak ≈ 96 cores × 3.0 GHz sustained × 32 FP32 FMA-ops/cycle/core ≈ 9.2 TFLOPS FP32 (≈ 4.6 TFLOPS FP64). FIRST RUN of this audit should re-derive this from `lscpu` + an FMA-loop microbench; treat the 9.2 TFLOPS figure as an approximation pending calibration.

## DRAM BW achieved
- amd_df cs_dispatched read transactions: <r>
- amd_df cs_dispatched write transactions: <w>
- (or pcm-memory Read/Write GB/s direct: <r_gbs> / <w_gbs>)
- (or AMDuProfPcm output: <uprof_gbs>)
- (or numastat fallback: numa_hit_delta × 4096 / X = <fallback_gbs>)
- Bytes = (<r> + <w>) × 64 = <B> bytes  (only if amd_df events used)
- GB/s = <B> / 1e9 / <X> = <Q> GB/s
- % of socket theoretical peak: <R>%
  - **Correct BW calibration**: EPYC 9655 has 12 DDR5 channels socket-wide. At DDR5-6400 MT/s, socket theoretical peak ≈ 12 × 6400 × 8 = **614 GB/s socket** (not 307 GB/s). Under NPS4 the 12 channels are split 3 per NUMA node → ~153.6 GB/s per-node theoretical. The canonical measured aggregate reference under `--interleave=all` is **~460 GB/s** (per `feedback_canonical_baseline_protocol`) — call this the "practical socket ceiling" (~75% of theoretical).
  - Report `% of 614 GB/s theoretical` AND `% of 460 GB/s practical ceiling` separately.

## Verdict

- Decision rule (from §Objective): if **achieved FLOPS < 10% of 9.2 TFLOPS theoretical** AND **achieved BW > 70% of 614 GB/s theoretical** (i.e. > ~430 GB/s, also ≈ 93% of the 460 GB/s practical ceiling) → BW-bound, diffusion variants have FLOPS headroom.
- This run: achieved FLOPS = <P>%, achieved BW = <R>% theoretical / <R'>% practical.
- Verdict: <BW-bound | borderline | compute-bound>

## Recommendation
<one-paragraph next step — feeds the Variant-A-vs-B decision in the Nemotron port plan>
```

### Step 5 — Cleanup

```bash
# Nothing to clean — the audit leaves no state. Just verify no llama processes lingering:
pgrep -a 'llama-' || echo "clean"
```

## Open Questions / Calibrations

- **Theoretical peak FLOPS for EPYC 9655**: 96 cores, base 2.6 GHz / boost up to 4.5 GHz, Zen 5 with 512-bit FMA (FP32 throughput 32 ops/cycle/core in best case). Approximation: **~9.2 TFLOPS FP32 socket-wide at 3.0 GHz sustained, ~4.6 TFLOPS FP64**. First run under this handoff should re-derive via `lscpu | grep MHz` (actual sustained clock during decode workload) and an FMA-hot-loop microbench. Treat first-run "% of peak" as approximate until calibrated.
- **460 GB/s reference and 614 GB/s theoretical**: per `feedback_canonical_baseline_protocol`, ~460 GB/s aggregate is the canonical measured ceiling under `--interleave=all`. 614 GB/s is the socket theoretical (12 × DDR5-6400 × 8 bytes). Report achieved BW against BOTH — they answer different questions ("am I close to physics?" vs "am I close to what this configuration actually achieves?").
- **Per-NUMA-node vs aggregate**: if running with `taskset -c 0-95 --interleave=all` (96 cores spanning 4 NUMA nodes, 12 channels aggregated), the comparison is against 614 GB/s socket theoretical or 460 GB/s practical ceiling. If running single-node (`taskset -c 0-23 --membind=0`), compare against 153.6 GB/s per-node theoretical (~115 GB/s practical at the same 75% utilization ratio).
- **Whether to repeat for Coder-30B + Qwen3.6**: not necessary unless gemma4 result is borderline (achieved FLOPS 15-25% OR achieved BW 60-75%). If clearly BW-bound (FLOPS < 10%, BW > 70%), one model suffices for the variant-choice gate.

## Consumers

- **Primary**: `research/deep-dives/nemotron-labs-diffusion-tri-mode.md` §10 — gates Variant A (Linear-SS) vs Variant B (TiDAR-pattern one-pass) vs Variant C1/C2 (split-role hybrid). User-proposed FLOP-for-BW asymmetry framing.
- **Secondary**: `handoffs/active/deepseek-v4-flash-cpu-port.md` — informs whether V4-Flash decode (13B-active) will be FLOPS-limited at the same operating point.
- **Tertiary**: `cpu-inference-optimization-index.md` measurement infrastructure — first principled FLOPS/BW snapshot for the canonical NPS4 stack. Future kernel claims can cite this baseline.

## Cross-references

- Nemotron deep-dive §10: `research/deep-dives/nemotron-labs-diffusion-tri-mode.md`
- DeepSeek-V4 port handoff: `handoffs/active/deepseek-v4-flash-cpu-port.md`
- TiDAR intake (corrected): intake-633 / intake-634 / intake-635 (deep-dive 2026-05-28 corrected mechanism reading)
- Canonical baseline: `feedback_canonical_baseline_protocol` (460 GB/s aggregate reference)
- BW-bound prior: `project_cpu_decode_bw_bound` (cycles inside dot loops are DRAM-wait, not ALU)
- Host throttle pre-flight: `feedback_host_throttle_check` (frequency-scaling verification; tiered drop_caches vs reboot)

## Reporting Instructions

Once the run completes:

1. Save `findings.md` to `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-05-NN-decode-roofline/findings.md` (absolute path; benchmark bundles live under the research repo, not epyc-root)
2. Update this handoff's "Status" header to "complete (date)" and link to the findings bundle.
3. Update Nemotron deep-dive §10.5 step 4 with the actual headroom number and the resulting Variant choice.
4. Append a one-line entry to `progress/2026-05/2026-05-NN.md`.
5. If the headroom verdict triggers Variant B scoping, create or update a follow-on handoff under the Nemotron port direction.

## Notes

This handoff is intentionally narrow: ONE measurement, ONE decision point. Resist scope creep — additional questions (multi-stream BW, prefill BW, NUMA migration cost) belong in separate runs and can be queued only after this baseline is captured.

Per `feedback_drop_caches_numa_eviction`: if the host has had a recent `drop_caches` followed by a non-NUMA-aware re-read, re-warm the model file with `numactl --interleave=all dd if=<model.gguf> of=/dev/null bs=4M` before Step 1, or simply restart the warmup with `--mlock` (which is already in the command).

Per `feedback_no_pipe_llama_output`: outputs above are redirected to files, never piped through grep/tail/head.
