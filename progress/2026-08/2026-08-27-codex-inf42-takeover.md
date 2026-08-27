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
