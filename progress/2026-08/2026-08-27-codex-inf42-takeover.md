# Progress — 2026-08-27 — codex-inf42-takeover

## INF-42 G1 live-run recovery and full-instance continuation

- Diagnosed OpenCode session `ses_fc6e4b606ffeGMfIEPwL7fxX0D` in tmux `agent:2`: its main turn was
  awaiting four long monitor tool calls while the detached INF-42 campaign continued.
- Verified the original INF-42 server was a malformed serving-half launch: `-t 48` was copied from
  the production half shape, but the process had affinity `0-191`, default first-touch memory
  placement, no canonical OMP environment, and no `GGML_IQK=1`.
- Verified driver resumability and preserved 161/200 q8 trials. All 161 JSONs parse, have non-null
  scores, and are exact-match hits; the driver skips those files on restart.
- Created a durable checkpoint at
  `/mnt/raid0/llm/epyc-inference-research/data/frontdoor-amnesia-g1-checkpoints/20260827T074200Z-pre-corrected-resume/`.
  It contains the 161 trial files, original run/server logs, original scripts, sanitized OpenCode
  export, process manifest, SHA-256 inventory, and an explicit recipe-boundary manifest.
- Found a second defect in the session-local lease: `lease.py acquire` recorded the short-lived
  acquisition subprocess PID, so the claim was reaped while INF-42 still occupied the machine.
  Established a live compatibility lease (`inf42-g1-full-resume`) and the authoritative physical
  `region-lock` over q0–q3 before interrupting anything.
- Sent `SIGINT` to the captured Python driver PID `4010548`; it remained blocked in its HTTP read.
  Escalated that same captured PID to `SIGTERM`. The wrapper performed cleanup; verified old driver
  `4010548`, server `4009924`, and wrapper `3833169` are dead and port 8301 was down.
- Started the corrected continuation at 07:46Z. Server PID `708658` runs `-t 96`, is confined to
  physical CPUs `0-95`, carries the canonical OMP environment plus `GGML_IQK=1`, and is launched
  under `numactl --interleave=all`. The driver resumed through trials 1–161 without recomputation and
  began rerunning the previously unpersisted trial 162.
- Interpretation is explicit: INF-42 measures exact-match recall, so phase-A scores are retained;
  timing fields are not pooled across the 48-thread and 96-thread phases.
- Filed Vidya source SC52 immediately. The current corpus predates its producer hook and remains
  native experiment evidence only; it must never be reconstructed into `ClaimTuple` rows on read.
- Restored steerability to the original OpenCode session without stopping its detached campaigns.
  Four exact captured children of PID `1908397` were confirmed to be monitor/sleep shells and were
  terminated with `SIGTERM`; all eight shell/sleep PIDs were verified dead. The subagents responded
  by issuing shorter waits, so the identity-confirmed `agent:2` pane's displayed two-Escape
  interrupt confirmation was used. The parent turn now shows `interrupted`, has no child processes,
  and presents the queued operator message in an idle composer. No Enter/key submission was sent
  because the composer contains operator-authored input.

## Operator-invoked wrap-up checkpoint — 10:56Z

- The corrected chain remains live and identity-confirmed: region-lock runner PID `701965`,
  compatibility-lease guard PID `701993`, wrapper PID `708656`, production-v9 server PID `708658`,
  and probe driver PID `709327`. The physical `q0`–`q3` locks and advisory
  `inf42-g1-full-resume` lease remain held.
- Q8 persistence advanced to 163/200: 4K 50/50, 32K 50/50, 64K 50/50, and 128K 13/50. All 163
  records parse, carry non-null scores, and are exact-match hits. Trial 164
  (`l131072_d25_s03`) was active; a live-window sample showed 84,122 prompt tokens processed
  (75%) at 33.25 tok/s. The wrapper remains autonomous through the rest of Q8, the required f16
  control, both summaries, verified server cleanup, and lock release.
- The original OpenCode owner is now responsive rather than interrupted. It completed operator
  follow-up turns at 08:21Z and 10:52Z, has zero direct child processes, and is idle at an empty
  composer. No further steering action is required from this takeover session.
- Residual throughput caveat: the live argv and environment declare `-t 96`, CPUs `0-95`,
  `numactl --interleave=all`, canonical OMP placement, and `GGML_IQK=1`, but `numastat` sampled
  32.28 GiB of 41.89 GiB on NUMA node 3 (~77%). The largest 9,006,874-page anonymous mapping is
  likewise concentrated on node 3 despite reporting policy `interleave:0-3`. This does not impair
  the exact-match recall claim, but it keeps all phase-B timing fields non-authoritative. Existing
  INF-43 task T5 / N25 P2-3 owns the missing multi-node locality gate and tolerance decision; no
  duplicate task was filed.
- Filed one non-duplicative post-G1 fence under INF-42: identity-reverify that the two legacy
  session-local lease waiters have expired before treating release as safe, while preserving the
  authoritative region-locked INF-40 waiter. At this checkpoint the legacy INF-40 child PID
  `3847760` and EVL-08 child PID `3999604` remained asleep with deadlines around 15:03Z and 15:57Z;
  the authoritative `inf40-moespec-bsweep` region-lock waiter PID `774647` remained queued.
- Bus drain for `codex-inf42-takeover` failed closed because it is a lane/task identity, not a
  roster id. It advanced no cursor and wrote no acknowledgement. The unrostered audit log has
  successful task-end events for all three takeover tasks and no open task to close.
