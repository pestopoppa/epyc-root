# 2026-09-29 — workspace-8d (bundled :8083 window 07:05-07:09Z: B2, ARCHSWAP-3b re-run, RI-23b A/B; GPU A/B hardened)

Per-task wrap-up. Handoff text plus offline script work in `/mnt/raid0/llm/tmp/gpu-champion-ab/`. In this task: no
inference, no server started or stopped, no index row edited. The window itself ran earlier on workspace-76's go,
with DS41 paused.

## What the window did (recorded in the handoffs)

- **ARCHSWAP-4, :8083 half (B2)** (`thesis-experiment-orchestrator-vs-strongest-model.md`).
  - Production :8083 was relaunched through the stack on v10 `ffc1bac82` with the `architect_critic` slot dir.
    The final PID is 3363961, after two A/B retries that each ended in the same B2.
  - The status attestation no longer shows the :8083 drift.
  - The :8074 half is still open: it needs a CPU-window reload, coordinated with workspace-76. Until then both
    servers point at the `architect_critic` slot dir.
- **ARCHSWAP-3b P2/P3 re-run** after the HS-OD-10 fix.
  - All three roles returned the same clean templated answer, with no template echo and no inline `<think>`.
  - `reasoning_content` came back empty.
  - ARCHSWAP-3b stays open only on the A-3 scout-stage sample.
- **RI-23b** (`routing-intelligence.md`) is ticked.
  - With the flag OFF, the review verdict never parses: it hits the 80-token limit inside `<think>`. This is live
    confirmation of RI-22. With the flag ON, both verdicts parse and are correct.
  - Escalation, ingest and the REPL turn were correct in both arms.
  - There was no stop-string-in-thinking hazard.
  - RI-23 (landing plus enable) waits for the operator's landing approval. RI-23a still needs its stack-change
    package.
- **V6R-4d** (`autokernel-champion-aggregate.md`): the GPU A/B was attempted and did not complete, because of the
  over-strict per-arm checks. It is re-planned for the vision window, which tests identity, speed and residency
  only. The SW-9 GPU check needs an MTP model: a :8083 window or the 2nd MI210.

## A/B scripts hardened (offline)

Every per-arm check is now an `ab_probe.py` subcommand that prints what it saw. Each one was tested read-only against
today's arm logs and the live production :8083/:8086 (`selftest/live_checks.sh`: 24 cases, 0 failures).

- **Device.** The check is now the pid's KFD VRAM (at least 1 GB). The startup-log lines are recorded but not
  required, because v10 logs none of them at verbosity 3.
- **Placement.** Threads are classified individually. All threads are named `llama-server`, so a name-only split
  cannot work. ROCr's async-event thread is recognized by its wait channel (`kfd_wait_on_events`). Its affinity
  is reset to 0-191 in all four live GPU processes, so it is reported, not failed.
- **Placement is checked again after the probe.** The OMP compute pool is created at the first compute, which on
  production :8083 was 60 s after start. The post-probe result is gated in the summary.
- **`/props`.** The check covers build_info, model_path and, for the vision kind, `modalities.vision`.
  `speculative.*` in `/props` reads `none` on production :8083 even though it runs draft-mtp, so it is not used as
  a check.
- **Watcher.** A new paused mode serves `--force-window` runs inside a peer-paused loop. The strict watcher would
  have aborted within 5 s, because the window reads closed/exited. Paused mode refuses a loop that is not
  actually stopped.
- **Summary.** A failed probe no longer counts toward the result, which used to make identity vacuously equal.
  `failed_checks` is named, and the vision run says "SW-9 NOT TESTED".
- **Pipes.** The `curl | grep -q` / `ss | grep -q` pipelines under pipefail (a SIGPIPE false negative) are replaced
  by captured output, including B2's `/props` post-proof.
