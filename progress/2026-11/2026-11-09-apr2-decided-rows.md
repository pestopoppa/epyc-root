# 2026-11-09 apr2 decided-rows

Operator decisions 1-4 executed on branch `apr2/decided-rows-20261109`.

- **R18-D re-run (published).** Row `vidya-r18d-aa-wire-20261109-r2`, GPU, rank 35, estimate 14,400 s, RAM 48 GiB,
  disk about 60 MB (r1 wrote 59 MB). r1's 136 invocations all recorded `clock_stable=false` (sclk 800-1700 MHz).
  Clocks are proven by `residency.sclk_mhz()` (hwmon `freq1_input`, achieved clock; `clock_stable` = min equals max);
  they are pinned only by host policy `power_dpm_force_performance_level=high` (root-owned, operator-set, lost on
  reboot), which currently reads `auto`. The stability check is unchanged. The new job refuses to run (`--check`
  precondition, rc=5, and again at measurement start) unless the level is `high`; smoke is exempt. The operator must pin
  before the grant. Inputs are read from the r1 directory, outputs go to the r2 directory. The smoke is queued by the
  keeper (GPU busy); no manual dry run (inference).
- **TOC-CMP-4 (not published).** Option (a) acknowledged. Needs the live frontdoor `:8070` and a runner and frozen point
  list that do not exist; see the box note.
- **ODL-013 r2 evidence (committed).** 22 files, 200 IDs pseudonymized, map outside git, note in the directory. The box
  stays open for the 800+ raw per-document files.
- **M-12 judge.** Qwen3.8-27B judge accepted with same-family caveat; rules recorded on the M-12 box.

## Follow-up (coordinator, same day)

- R18-D r3 `vidya-r18d-aa-wire-20261109-r3` supersedes r2: the job itself sets `high` (one approved sudo tee write, this row only)
  and restores `auto`; gpu-quiet exclusive; smoke probes `sudo -n` only. See the R18-D box for exit codes and the leak check.
  Tested with a fake-sudo harness against a temp file: normal exit, SIGTERM and not-auto refusal all behave; the real
  keeper-env `sudo -n` confirmation is the smoke itself (fails closed rc 5).
- ODL-013 raw outputs archived at `/mnt/raid0/llm/archives/pip04-odl013-r2-20261107/` (read-only); 855/855 digests verified; box ticked.
