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
