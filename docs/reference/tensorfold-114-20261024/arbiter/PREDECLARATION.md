# AKX-ALL-30a arbiter rocprof probe: predeclaration (2026-10-25)

Written before any run. `job.sh` refuses to start if this file's sha256 differs from `PREDECLARATION.sha256`, and
`VERDICT.json` records the hash it was judged under. Thresholds are also constants in `arbiter_analyze.py`; both files
are pinned in `SOURCES.sha256`.

## What it is

- **Item.** AKX-ALL-30a in `handoffs/active/autokernel-all-devices-all-dimensions.md` (TensorFold 1.1.4 Stage-3 plan,
  packet P1, operator-approved 2026-10-24; `/mnt/raid0/llm/tmp/tensorfold-114-review-20261024/STAGE3-PLAN.md`).
- **Kind.** A profiling probe. No build. It is **not** an AutoKernel launch, and the 2026-10-24 "DO NOT LAUNCH
  AUTOKERNEL" hold stays in force.
- **Decides.** The order in which the GPU FA seeds G2, G3 and G1 are authored (`AK-SEEDS-PROPOSED.md`;
  `inbox-drafts/ak-27b-gpu-verify-20261004/60-…`). It decides nothing about keeps, promotions or throughput.

## Subject (fixed)

- **Kernel.** The CHAMPION GPU store image. `ak/champion` resolves to `refs/heads/ak/champion/llama-cpp-ffc1bac82eec`
  = `dcc853b5559bef4e50acf251f4910f7f4e0ba538` (C3), which is
  `/mnt/raid0/llm/kernels/builds/gpu-20261023-dcc853b55-c3` (PROVENANCE "status: CHAMPION", version
  `10413 (dcc853b55)`, `GGML_HIP_ROCWMMA_FATTN=ON`). If the ref has moved when the run starts (for example a C4 CAS),
  the job refuses with rc 6. It is then re-prepared with the new image and a new predeclaration, and never judged
  under this one.
- **Model.** `Qwen3.8-27B-Q8_0.gguf` with the drafter `Qwen3.8-27B-DFlash2-Q8_0.gguf` ("27B ALWAYS DFlash2").
  - Shape from the GGUF: 16 full-attention layers, `head_count_kv` 4, `key_length` = `value_length` = 256, GQA 6.
- **Argv.** The production :8083 argv from `epyc-orchestrator/logs/server_launches/8083.json` (`argv_sha256 4ea2aa0d…`):
  `-np 4 -c 393216 --kv-unified -ctk q8_0 -ctv q8_0 --flash-attn on --no-mmap -ngl all --spec-type draft-dflash
  --spec-draft-n-max 7`, transformed by the precedent's own `make_argv`.
  - Binary → the champion.
  - Scratch `--port 18430` and its own `--slot-save-path`.
  - `-b/-ub 2048`, as rocprof B. Production is 512. This changes only prefill chunking; one 8-token verify step is
    below either ubatch.
  - `-lv 4`.
- **Launch prefix.** `numactl --membind=3 -- taskset -c 184-191`, plus `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` in the env.
- **Shape.** 1 × 80k context. One request on slot 0: an 80,000-token prompt built with the precedent's corpus, tag and
  tail, so it is the same text as rocprof B's req0. It decodes alone. **N=8 verify** = `--spec-draft-n-max 7` drafts
  + 1 = an 8-token target verify batch per round, as in rocprof B.
- **Profiler.** rocprofv3 from the side-loaded rocprofiler-sdk 0.4.0 (ROCm 6.2.0-66):
  `/mnt/raid0/llm/tools/rocprofiler-sdk-6.2.0-66/opt/rocm-6.2.0/bin/rocprofv3`, sha256 `c753449e…` = AutoKernel's
  pinned copy. `which rocprof rocprofv2 rocprofv3` finds nothing on PATH, and `/opt/rocm/bin` has no profiler. The v1/v2
  tools are under `/mnt/raid0/llm/tools/rocm-profilers-6.2/opt/rocm-6.2.0/bin`; they are not used here.

## Passes and samples

Each pass is one server load. Both passes are needed.

| pass | profiler flags | HIP graphs | yields |
|---|---|---|---|
| `trace` | `--kernel-trace --memory-copy-trace --stats` (exactly rocprof B) | **ON** (production default; no `GGML_CUDA_DISABLE_GRAPHS` in `/proc/<pid>/environ`) | per-step kernel durations: kv_convert (target), FA (target), step wall |
| `counters` | `-i pmc.txt --kernel-trace`, `pmc: FETCH_SIZE TCC_HIT_sum TCC_MISS_sum` | **OFF** (`GGML_CUDA_DISABLE_GRAPHS=1`) | per-dispatch HBM bytes fetched and L2 hits/misses for FA and convert |

- **Why graphs OFF for the counters pass.** It is the condition under which counter collection on this host is proven
  (`lb1-profile-20261003`: rocprofv2 FETCH_SIZE pass on the 27B). Graph launch does not change what a kernel reads.
  Durations from the counters pass are never used, because counter collection serialises dispatches. The live FA
  kernel symbol must be identical in both passes (validity rule 8).
- **Fallback.** The 4-counter TCC set might exceed the gfx90a TCC counter block. If the counters pass dies before the
  server is healthy, the job retries **once** with `pmc_fetch_only.txt` (`FETCH_SIZE`). The FA rule needs only
  `FETCH_SIZE`; the L2 hit rate is then reported as "not collected", and that is not a validity failure.
- **Two samples per cell** (two-sample persistence, minimum-rigor control 3).
  - Each pass records two decode windows, **B1** and **B2**, of 30 s each.
  - B1 starts 4 s after the first token; B2 starts 6 s after B1 ends.
  - Each window is one sample, and the verdict for a branch needs both samples in the same branch.
- **Observation window** (control 4). Every number comes from dispatches whose start lies inside B1 or B2. That means
  during FA dispatches at 1×80k, never after.
  - Trace timestamps are aligned to the window marks by the precedent's clock method (CLOCK_BOOTTIME, validated by the
    6 s idle fiducial before the prompt).
  - Counter rows are joined to kernel-trace timestamps by `Correlation_Id` (fallback: ordinal, with ≥99% kernel-name
    agreement).
  - If the counters pass yields no usable kernel-trace timestamps, the two samples are instead the first and second
    halves of the decode-grid target FA dispatches after the 80k prefill. Those are all at 1×80k and during decode.
    The join method is recorded.

## Quantities

- **f16 K+V view** (per FA call = per layer):
  - `n_kv × 4 KV heads × 256 × 2 B × 2 (K and V)`.
  - `n_kv` is the occupied cells of the decoding slot, as the mean of the window-edge `/slots` reads, rounded up to 256
    (llama.cpp's FA KV padding).
  - At 80k: ≈ 335 MB per call, 5.37 GB per step, matching the seed draft's arithmetic.
- **FA fetched bytes.** The median over the window's target FA dispatches (FA main kernel, head dim 256) of
  `FETCH_SIZE × 1024`. FETCH_SIZE is in KILOBYTES in rocprofiler-sdk 0.4.0, from gfx90a `derived_counters.xml`:
  `(TCC_EA_RDREQ_32B_sum×32 + (TCC_EA_RDREQ_sum−TCC_EA_RDREQ_32B_sum)×64)/1024`.
- **Ratio R** = FA fetched bytes / f16 K+V view.
- **Convert cost C** = `flash_attn_convert_live_q8_0_f16` target ms per step from the trace pass. That is the
  precedent's `K/V q8_0->f16 conversion` target row: the window sum of convert durations / target forwards, where
  target forwards = gated_delta_net dispatches / 48.
- **Reported, not ruled on.**
  - FA ms/step.
  - Step wall.
  - FA L2 hit rate `TCC_HIT/(TCC_HIT+TCC_MISS)`.
  - Convert-derived f16 view: the K+V convert pair's `FETCH_SIZE × 2/1.0625`.
  - R against that view.
  - The structural cross-check (FA fetch of all decode-grid FA dispatches after the prefill).

## Decision rule (predeclared)

Verbatim from the Stage-3 plan, "Minimum-rigor controls, P1 arbiter" control 2:

> FA `FETCH_SIZE` ≥ 3× the f16 K+V view means G2 first; ≈ 1× means re-rank. Convert ≥ 4 ms means G3 stands.

Verbatim from AKX-ALL-30a (plan handoff edits):

> FA fetch ≥ 3× the f16 K+V view means G2 first, then G1; ≈ 1× means re-rank G1 and G2 before authoring; convert ≥ 4 ms
> means G3 stands.

Verbatim from the G3 seed falsifier (`AK-SEEDS-PROPOSED.md`, rank 2):

> kv_convert time on the champion at 80k < 2 ms → dead.

As applied here (the bands the verbatim text leaves open are fixed now, before the data):

**FA branch** (from R, per sample):

| R | branch |
|---|---|
| R ≥ 3.0 | `GQA_REREAD_REAL` |
| R ≤ 1.5 (this band is what "≈ 1×" means here) | `REREAD_ABSORBED` |
| 1.5 < R < 3.0 | `PARTIAL_REREAD` |
| R < 0.8 | `INVALID_RATIO`: impossible for a 335 MB view against 8 MB of L2, so it means a unit or denominator defect |

**G3 branch** (from C, per sample):

| C | branch |
|---|---|
| C ≥ 4.0 ms/step | `G3_STANDS` |
| C < 2.0 ms/step | `G3_DEAD` |
| 2.0 ≤ C < 4.0 | `G3_MARGINAL` |

**Persistence.** A branch is decided only if B1 and B2 land in the same branch. Otherwise it is `UNDETERMINED`.

## What each outcome decides

| FA branch | G3 branch | seed order (AKX-ALL-30 authoring) |
|---|---|---|
| GQA_REREAD_REAL | G3_STANDS | **G2, G3, G1** (G2 first. G1 reuses G3's loader, so G3 precedes G1: plan "G1 follows G2 and G3") |
| GQA_REREAD_REAL | G3_DEAD | **G2, G1**. G3 is dropped, and G1 then needs its own q8 staging loader |
| GQA_REREAD_REAL | G3_MARGINAL | G2, G1. G3 is neither stands nor dead by rule; the owner re-ranks G3 with C recorded |
| REREAD_ABSORBED | any | **re-rank G1 and G2 before authoring**: G2 is dead (the re-read is absorbed by L2), and G1 is only a tile-fill or compute change. G3 follows its own branch |
| PARTIAL_REREAD | any | re-rank G1 and G2 with R recorded. G2 is not first by rule |

`VERDICT.json` `verdict`:

- `COMPLETE`: valid, and both branches decided. Writes `PASSED`. Note that G3_MARGINAL is a decided band: the rule
  then explicitly hands G3's rank to the owner.
- `UNDETERMINED`: valid, but a branch flipped between samples.
- `INVALID`: any validity rule below failed.

Not COMPLETE: both passes are archived (`*.attemptN`) and re-run on the next grant. After 2 full attempts without
COMPLETE the job writes `GAVE_UP` with both attempts' numbers, and the owner re-plans.

## Validity rules (any failure = INVALID, no verdict)

1. **Baseline** (control 1):
   - the champion ref equals `dcc853b55`;
   - the store image matches its `SHA256SUMS` (llama-server and the 7 served libs);
   - `VERSION.txt` = `10413 (dcc853b55)`;
   - the binary and lib mtimes are later than the commit time;
   - `libggml-hip.so` carries `flash_attn_ext_f16`, `flash_attn_convert_live_q8_0_f16` and `GGML_CUDA_DISABLE_GRAPHS`,
     and `libggml-base.so` carries `dcc853b55`;
   - `verify_ggml_linkage.sh` PASSES with the profiler LD path;
   - the live server maps `libggml-hip` from the champion bin dir (HIP dlopen proof), and `/props` `build_info` is the
     same in both passes.
2. **Profiler attached.** `librocprofiler-sdk-tool` is in the server's maps.
3. **Residency** (control 5). In every window there is at least one non-zero own-pid KFD VRAM sample, and exactly one
   KFD process holds VRAM (ours).
4. **Graphs state**, read from `/proc/<server pid>/environ`: trace ON, counters OFF. `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0`
   is present in both passes.
5. **Shape.**
   - Occupied cells at both edges of every window are in [78,000, 82,500], and exactly one request is decoding.
   - The trace pass has ≥ 5 target forwards per window.
   - The counters pass has ≥ 48 target FA dispatches with `FETCH_SIZE` per window.
6. **Denominator cross-check.** The convert-derived f16 view is within [0.75, 1.25] × the analytic view in each counters
   window. This also checks the FETCH_SIZE unit.
7. **Clean pass.**
   - The coherence spot-check returned text.
   - Teardown was graceful (SIGTERM, profile flushed), and the server was verified dead with `ps -p`.
   - The trace pass's kernel trace exists, and the counters pass's counter CSV exists.
   - No VRAM guard trip (60 GiB own pid) and no graphs-state trip.
8. **Provenance** (control 6). These must be recorded in `RUN_RECORD.json`/`run.json`, and the FA symbol must be
   identical between passes:
   - argv;
   - KV type (q8_0/q8_0);
   - n-max (7, N=8);
   - the rocWMMA build flag (ON);
   - the live FA kernel symbol (target FA-256).

## Claim class

- **Counter bytes** are MEASURED. **Kernel durations** are INDICATIVE: device timestamps under the profiler, with ≥ 2×
  margins to the thresholds against the prior's 7.92 ms.
- Neither is a throughput, keep or promotion claim. The convert threshold is the only timing-valued input, so the row
  is booked `block-timing-pairable`: the GPU is exclusive, and host co-tenants are allowed.

## Prior

rocprof B, `/mnt/raid0/llm/tmp/rocprof-longctx-20261004/results/20261004T081019Z/report.md`, 2026-10-04:

- build: KVU-19 fold candidate `gpu-20261004-1bceceb05`;
- B: 1×~80k (79,945 cells), N=8 verify;
- FA 29.38 ms/step (target 29.08), kv_convert 7.92 ms/step, step 120.53 ms;
- FA kernel `flash_attn_ext_f16<256, 16, 4, 64, float, false>`.

That run had no counters. This probe re-measures on the champion and adds the bytes.
