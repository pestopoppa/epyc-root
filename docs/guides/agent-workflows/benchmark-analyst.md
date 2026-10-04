# Benchmark Analyst Workflow

## Baseline Procedure

1. Define controls (model, prompt set, threads, NUMA mode).
2. Run benchmark with explicit configuration capture.
3. Repeat runs to reduce noise.
4. Compare against baseline and prior best.
5. Publish decision-grade summary with caveats.

## Required Metrics

- Decode throughput (`TG t/s`)
- Prefill throughput (`PP t/s`)
- Acceptance rate (when speculative decode is enabled)
- Variance across repeated runs

## Reporting Standard

- Separate observations from inferences.
- Flag suspicious anomalies before making recommendations.
- Include exact commands and source result paths.

## Scarce windows (a peer's CPU window, or a peer-paused GPU slot)

- **Stop on anything but `open`.** When a run borrows an AutoKernel CPU window
  (`/mnt/raid0/llm/autokernel/cpu-window.json`), stop at once on any `state` other than `open`, or when
  `loop_holds_claim=true`. `closing` means stop, not finish up.
- **A side server lives as long as its bench run.** Start it just before the run, and stop it on every exit
  path. (origin: INC-20260929-peer-window-closing-overrun)
- **Test every check against real artifacts before spending the window.** A dry-run does not exercise
  live-only checks, such as startup-log regexes, thread placement, directories that must exist, and `set -e`
  interactions. Run each check read-only against real logs or the live production process first, and have
  it print what it saw. (origin: INC-20260929-dry-run-missed-live-checks)
- **No GPU work inside another session's GPU measurement window — subagents included.** A small footprint is
  not "no interference": any kernel launch shares the GPU's compute and memory bandwidth with the measured
  server. GPU tests, micro-benchmarks and smoke runs go only into a coordinated slot. A main that dispatches a
  subagent able to touch the GPU either hands it that slot or tells it not to use the GPU.
  (origin: INC-20261003-subagent-gpu-tests-in-peer-window)

## Your own load, and what counts as noise

- **Your own subagents are load too, and the easiest to forget.** Before any gate, bench or calibration you
  start or depend on:
  1. Send "pause tests" to every running subagent.
  2. A pause message lands only at the agent's next tool round, so a suite already running keeps going. Find
     pytest/xdist, build and `test-backend-ops` processes whose cwd is one of your worktrees, and wait for
     them to exit.
  3. Confirm the host is quiet with a live `top -bn2 -d 3`. `ps %CPU` is a lifetime average and does not
     show current load.
  4. Measure, then tell the subagents to resume.

  (origin: 2026-09-26, UFH-12 Phase 0 pre-gates started 4 minutes into a fix agent's `pytest -n 8`)
- **An AutoKernel loop's own floor calibration and A/B phases are measurement windows.** While
  `loop-status.json` shows `serving_floor_provenance: absent`, or anchor llama-servers run back to back, the
  loop is calibrating: run no tests, dry-runs or `find /`, pinned or not. On 2026-09-30 pytest runs (some
  pinned to SMT siblings 184-191 of DS41's cores 0-95) during a 48-launch DS41 serving-floor calibration
  inflated the verified floor to **4.533% instead of about 1.9%**. The operator kept that floor, so candidates
  must beat 4.5% until the next promotion. One unpaused afternoon of tests cost a whole promotion cycle's
  sensitivity.
- **Loop test fixtures take the real GPU device lock.** The loop's full-CPU pytest fixtures acquire
  `/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock` (`claim.DEVICE_LOCK`). Run them through a private-lock runner
  (for example `/mnt/raid0/llm/tmp/c78-dry/runtests.py`, which redirects `DEVICE_LOCK` to a private file).
  Otherwise they hang behind the live loop and can block it.
- **Light background load is metadata, not poisoning** (operator, 2026-10-04: "Cloud hosted agent traffic
  can't possibly be considered poisoning… Let's be a bit more pragmatic"). A measurement preflight refuses
  only on genuinely heavy local CPU work: builds, benchmarks, other local inference, `test-backend-ops`,
  pytest suites. It records the rest (agent harness processes at 100-200% CPU, idle servers, a paused loop)
  as metadata on the run and proceeds. ABA ordering plus repetition already absorbs light noise. Refusing on
  it cost whole measurement windows. The hazard that sinks windows is local compute, usually our own
  subagents' (above, and the GPU rule under *Scarce windows*).
