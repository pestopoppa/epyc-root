# 2026-10-21: GPU → CPU timing contamination experiment, designed, built and queued (subagent for workspace-58)

The operator asked for a "noise contribution" measurement that decides whether work needs a quiet host. The task is
U4-NOISE-1 in `handoffs/active/autokernel-unified-surface-program.md` §3.4 (OP-41 evidence). Nothing was run:
dry-run and stub only.

## Design (pre-registered)
- Doc: `docs/design/gpu-cpu-noise-contribution-prereg-20261021.md`. A copy with its sha256 recorded per session is at
  `/mnt/raid0/llm/tmp/gpu-cpu-noise-20261021/PREREG.md`.
- **CPU workload W1** is canonical `bench_canonical.sh` llama-bench on Qwen3.6-35B-A3B-MTP-Q8_0, pp512 + tg128 `-r 3`,
  0-95 `-t 96`.
  - Each rep takes its own 0-95 claim.
  - pp vs tg is the bandwidth-channel test.
  - W2, the DS41 served point, is optional and not in this session.
- **GPU** is the champion `gpu-20261020-dd3d9721c`, Qwen3.8-27B-Q8_0 + DFlash2 at the receipt argv, about 54.5 GB VRAM.
  The MI210 is on NUMA node 1.
- **Conditions:**

  | cond | GPU state | host threads |
  |---|---|---|
  | G0 | idle, no KFD | — |
  | G1 | resident, idle | 184-191 |
  | G2 | decode loop | 184-191 |
  | G3 | prefill-heavy loop, ~16k prompts | 184-191 |
  | G4 | decode loop, as G2 | 136-143 (node 1, local) |
  | S8 | idle, plus 8 ALU spinners | 184-191 |

- **Correction to the brief.** With `-t 96` on all physical cores, every logical CPU is a sibling of a bench core, so
  G4 cannot remove SMT contention. G4 measures placement and locality; the S8 control measures SMT alone.
- **Protocol:**
  - 10 seeded blocks, each a shuffle of [G0, G0, G1, G2, G3, G4] (+S8 on odd blocks);
  - each entry is a run of 5 back-to-back reps;
  - two G0 runs per block give the in-session A/A;
  - warm-up is discarded;
  - B is adapted once, from timing alone, after block 0 (floor 7).
- **Power** (scipy): VR=2 at 0.81 (process unit, df 40/80), arm unit ≈ 0.99, a 1% bias at ≥ 0.99 for sd ≤ 1%.
  - 325 reps, about 3.2 h, cap 3.5 h.
  - Runs of 5 beat pairs: 0.8 df per rep versus 0.5.
- **Decision table** per condition, for each class:
  - DG (champion baselines): bias CI inside ±0.5%, process VR U95 < 2, arm VR U95 < 1.5;
  - AK (keep gates): bias inside ±1%, σ_add U95 ≤ 1.28%, i.e. ≤ 10% widening of the 2.793% serving floor;
  - IND: always, labelled;
  - tg AND pp must both pass;
  - gates: V1 A/A, V2 positive controls, V3 B_min.

## Code (epyc-inference-research `ae93024d2` + `b65284539`, `scripts/benchmark/gpu_cpu_noise/`)
- **`gpu_cpu_noise_driver.py`**:
  - 1 Hz sysfs sampler (GPU busy, the rocm-smi "GPU use" source; VRAM; KFD; host-thread CPU busy), with rocm-smi
    called only between reps;
  - foreign-CPU accounting from /proc deltas;
  - per-rep positive controls in both directions;
  - self-hashed rows `epyc.gpu_cpu_noise.rep.v1`;
  - kills only registered own PIDs (pid plus start time), TERM → KILL → verify;
  - STOP file honoured between runs; END.json on every path.
- **`analyze_gpu_cpu_noise.py`**:
  - median-ratio bias with the union of the block-bootstrap and t CIs;
  - pooled-variance VR and σ_add at the process and arm units (F ∪ bootstrap);
  - A/A gate, INF-70 pair p95, the mechanism contrasts, and the reverse-direction GPU throughput;
  - the decision table.
- **`run_gpu_cpu_noise.sh`**:
  - grant-driven poller under the FILLERS protocol, detached with `arm`;
  - session under `region-lock run --gpu-quiet exclusive` plus the `mi210_0` flock;
  - hard end TERM → KILL → verify, then a registry sweep;
  - `$RUN/END` always; `.ended` and `.complete`.
- **`test_gpu_cpu_noise.py`**: 8/8 pass, file-scoped. They cover null, bias and noise recovery on synthetic data,
  real llama-bench JSON parsing, and the V2 gate.
- **Checks:**
  - **Dry-run clean.** No preflight problems; GPU linkage PASS; the bench_canonical dry-run command carries
    `-t 96 … -o jsonl`.
  - **Stub-test PASS** (poll, start, end, cleanup, END, .ended, .complete, no leaked PIDs). The hard-end path was
    tested too: END rc=124 with every child verified dead.
  - **Live read-only probes** against the production :18970 server (own-port proof, task affinities) and the
    MI210 sysfs.
  - **Fix found by the live probe:** OpenMP-bound threads report single-CPU affinities, so the residency check
    now tests for a subset.

## Queue
- A `gpu-cpu-noise` row is in `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md`: class `block-timing-quiet`, ~3.2 h, min
  window = full (3.5 h), DS41-class n, ready y, REGISTERED and not armed.
- It runs only on a workspace-58 grant `regions=q0,q1,q2,q3,mi210_0`. Launch:
  `/mnt/raid0/llm/worktrees/gpu-cpu-noise-run-20261021/scripts/benchmark/gpu_cpu_noise/run_gpu_cpu_noise.sh arm`
  (pinned detached tree at `b65284539`).
- Belief kernel: source row in `scripts/vidya/adapters/README.md`, task VB-GPU-CPU-NOISE-WIRE.

## Hooks hit (reported, not bypassed)
- The filesystem-containment hook refused a variable-expanded write target, so I re-issued it with literal paths
  (the brief's own rule).
- commit_hygiene refused a stale fetch, so I fetched as instructed.
- commit_hygiene refused `git stash`, so I committed first and rebased afterwards.
