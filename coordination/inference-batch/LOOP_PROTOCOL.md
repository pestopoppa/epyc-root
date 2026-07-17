# Inference-Batch Loop Protocol

**For**: the operator's long-horizon `/loop` session that executes `manifest.yaml` methodically.
**Created**: 2026-07-17 (backlog-churn campaign Wave 3).
**Governing constraint**: this loop must NEVER compete with the parallel inference-research session's compute. It runs only in detected quiet windows (except `serial_noninference` entries). NO nightshift.

## The single-writer rule

The loop session is the SOLE writer of `ledger.jsonl`, `op-bundle.md`, and the checkbox flips for batch-owned tasks. `bulk-inference-campaign.md` and the reviewer-plane handoffs point here as the execution source-of-truth while the batch is active. Do not run a manifest entry from any other session.

## Session-init (every loop iteration start)

1. **Reconcile state**: `compile_inference_batch.py` is already compiled → read `manifest.yaml`; fold `ledger.jsonl` (latest-row-per-task_id wins) → live task states via `batch_ledger.reconcile(manifest)`.
2. **Host-health snapshot**: `scripts/autopilot/host_health.py` + `scripts/session/health_check.sh`; record the tier. If throttled → `host_health.py --remediate` (drop_caches + throttle-check) then re-baseline; if uptime ≥ the entry's `max_uptime_days` → quarantine subsequent `throughput_sensitive` results + queue an op-bundle reboot request (host reboots are operator-only).
3. **Quiet-window gate**: `scripts/coordination/inference_load_check.py` → `classify_load()`. Outside a quiet window, only `serial_noninference` entries are eligible this iteration. **This is the hard rider — never start a throughput_sensitive/eval_fanout entry while the parallel session is active** (no llama-server decode / no llama-bench|cli|eval procs / no heavy downloads / MI210 unoccupied / autopilot stopped).
4. **Topology + flag attestation** (only when a reload happened): `scripts/server/preflight_gate.py` → writes `attestations/<ts>.json` (topology hash matching clean_window_manifest, affinity, contention freshness, health). For flag-gated entries, verify the flag is live on ALL uvicorn workers (the 1-of-6 propagation hazard) before trusting any coverage/emission number.
   - KNOWN ISSUE: `health_check.sh` currently exits 1 in-tree (pre-existing security-audit step under `set -e`) → B4 attestations conservatively FAIL. Fix that script or adjust the check profile before attestations can PASS.

## Pick-next-entry

Eligible = `READY` ∧ preconditions satisfiable ∧ `depends_on` all in {DONE_PASS, DONE_MARGINAL_OBS} ∧ operator_gates all granted (see `op-bundle.md` grants) ∧ quiet-window-appropriate for its `contention_class`. Among eligible: prefer entries whose `stack_lineup` matches the currently-resident stack (avoid a reload); else pick the phase with the most unblocked work and pay one reload. Never start a `throughput_sensitive` entry whose `est_wall_clock_h` exceeds the declared remaining window budget. `COORDINATION`-status entries are never picked (they exist only for precondition cross-refs to the parallel session's work).

## Per-entry cycle

1. **Dry-run preflight (MANDATORY for any inference command)**: `run_batch_entry.py` (or the entry's `dry_run` command) validates canonical env/topology/binary linkage with NO inference. Failure → ledger `INFRA_BLOCKED`, do not execute.
2. Ledger `RUNNING` row.
3. **Execute** under the entry's timeout + concurrency_mode; eval fan-out rides `placement_queue` (never `/chat`).
4. **Validate** artifacts exist / parse.
5. **Evaluate `gate_table`** → apply the matching fork via `entry_verdict.decide(...)`:
   - `pass` → flip the entry's checkbox(es) (+ `also_flips`) via `flip_checkbox.py`; ledger `DONE_PASS`; advance to `next`.
   - `marginal` → record as observation (progress log with metric/protocol/n/date), ledger `DONE_MARGINAL_OBS`, no checkbox flip; continue.
   - `fail`/regression → execute the entry's revert recipe **within the locked autonomy policy** (runtime-flag reset and reference-lineup relaunch auto-revert; ANY file/config edit → HELD_OP_GATE + op-bundle, never auto-reverted); flag a finding; ledger `FAILED_REVERTED`.
   - `infra` → classify per the failure-reason taxonomy; one retry if `retry_policy` budgets it, else ledger `INFRA_BLOCKED` + op-bundle row.
   - `ambiguous` → ledger `HELD_AMBIGUOUS` + append a pre-formed op-bundle decision block (Gate / Evidence observed / Options A-B-C); **continue with other eligible entries — never stall the loop.**
6. Ledger terminal row (gate_results, findings, artifacts, `era_stamp`, wall_clock). Package artifacts to `package_to`.

## Autonomy policy (locked with the operator, 2026-07-17)

- **Auto-revert without asking**: runtime flags; relaunch-to-reference-lineup. **Never auto-reverted**: file/config edits, stack config, registry (→ op-bundle).
- **Loop commits directly**: `ledger.jsonl` rows + packaged artifacts. **Checkbox flips**: direct, but list every flip in each wrap-up for audit.
- Every `HELD_AMBIGUOUS` / `HELD_OP_GATE` appends a pre-formed decision block to `op-bundle.md`; the operator processes the bundle asynchronously and records grants there; grants are picked up at the next session-init. The loop NEVER blocks on the bundle.

## Wrap-up cadence

After each phase or ~4 entries: regenerate `batch_status_report.py` output, update the `bulk-inference-campaign.md` status line, commit ledger + packaged artifacts (single-writer). Full wrap-up routine at phase boundaries.

## Instrument discipline

All pre-P-REV-1 reviewer-plane numbers are OBSERVATIONS (journal_quarantine_rule on each entry). Nothing gates a keep/revert/deploy/promote decision until its protocol is cited (P-REV-1 for reviewer calibration; canonical recipes for benchmarks). Era-stamp every result; supersede historical numbers by appending an era, never by editing the record.

## Phase map (see manifest.yaml for the authoritative entry list)

`P0` RCP prologue (OP-6-gated) → `P1` reference-lineup riders → `P2` eval-tower standalone → `P3` bulk-campaign cells → `P4` kernel/OP-2 window → `P5` GLM window (parallel-session handshake) → `P6` decision-grade confirmations (OP-5a/5b-gated). `COORDINATION` rows (phase 90) are non-executable cross-references to parallel-session-owned work.
