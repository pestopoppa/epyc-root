# Skill card: row-owner-loop

Layout follows the AMD skill-card plus `evals/evals.json` convention adopted from intake-2745#record (amd/skills).

| Field | Value |
|---|---|
| Name | `row-owner-loop` |
| Entry point | [`SKILL.md`](SKILL.md) |
| Owner | pipeline-mgmt |
| Scope | Row OWNER side of rowflow: scaffold, lint, publish, prove queued, watch, triage, file, tick |
| Evals | [`evals/evals.json`](evals/evals.json) |
| Tests | [`tests/test_row_owner_loop.py`](tests/test_row_owner_loop.py) |

## What it does
Drives one `epyc.row.v3` measurement row from preparation to a filed verdict and a ticked box with a
belief tag, and briefs/verifies subagents that build kernels or rows.

## When to use
- Publishing a row, waiting on a smoke or `grants/<id>.ended`, filing a `verdict.json`, ticking a result box.
- Dispatching a subagent to build a kernel or row, or verifying its hand-back claims.

## When not to use
- Bin packing, keeper or grant-writer internals: `inference-backlog-scheduling`.
- Job-side launcher rules: `docs/guides/agent-workflows/compute-fillers.md`.
- Production kernel promotion: `kernel-promotion`.

## Inputs and outputs
- Inputs: a handoff box, a row spec, grant/run-end files.
- Outputs: a published row, one armed zero-token watcher, `verdict.json`, a filed result, a ticked box with `[belief: …]`.

## Bundled resources
`scripts/` (`row_scaffold.py` — retired shim over `scripts/coordination/rowflow/mk_ak_row.py`, the one row generator; `brief.py`, `runend.py`, `watch_rows.sh`), `references/` (hard rules, hand-back checklist, program plan, ratify prep, stop-doing).

## Safety and limits
- Never kills processes by name pattern; only PIDs it captured.
- Does not book compute itself; the calendar owner grants windows.
- A queued claim needs proof (the row visible in the queue), not the publish command's exit code.
