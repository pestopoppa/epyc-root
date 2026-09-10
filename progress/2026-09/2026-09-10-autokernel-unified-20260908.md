# Unified AutoKernel implementation — 2026-09-10

## First actual CPU iteration completed as a measured null

- Checkpoint source: research `2059e30e`, ROOT `be070987`. The running experimental
  GLM CPU trial uses the existing loop, PID1380863 (owning worker handle21102), and
  its dedicated trial store; canonical champion/history remain separate.
- Candidate `akm-q4k-avx512-paired-y` completed source authoring → build → existing
  MUL_MAT correctness gate → five serving A/B pairs → durable `measured_null`.
  Effect fraction `0.009501638190257289` (+0.95016%) is below the 7.801% calibrated
  floor. This is an actual measured null, not a failed build/gate or an accepted gain.
- The original loop advanced automatically into iteration 2. At this boundary:
  one completed iteration, one measurement, no keep. The five-iteration test remains
  incomplete; no canonical champion promotion or qualified performance claim is made.
- Durable evidence: trial-store `experiments.db` attempt `05843e3b…` retains five
  samples per arm, with comparison and floor request digest
  `b8475457d62a637a58cbe90e9b66864804122ed713ac14562a5f6c400c5154d0`.
  The candidate patch is retained at `patches/akm-q4k-avx512-paired-y.lane0.patch`;
  the worker source returned clean to `c463f601`. The five-launch calibration file
  was reused unchanged, not rerun. Runtime residency records explicitly report
  `cpu_placement=unproven`; requested CPU0–95 is not runtime placement proof.
  This and the existing host-uptime qualification limit prohibit treating this
  workflow trial as a qualified performance/admission result.
- This checkpoint records one completed execution subtask only. It does not close
  the broader CPU/GPU autonomy program or start another run. Documentation preparation
  made no runtime changes, index edits, commits or wiki sweep. README freshness check
  exited0 with no warnings.
