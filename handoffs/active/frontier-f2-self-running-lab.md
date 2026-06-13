# Frontier F2 — The Self-Running Lab: Local Agents Take Over Lab Maintenance

**Status**: W1 branch-ready; W2 runner branch-ready; W3 promotion-gate scaffold branch-ready; W2 nightly shadow scheduling/scoring + W3 evidence collection + W4 still open (created from the Fable 5 strategic-frontiers review)
**Created**: 2026-06-12
**Priority**: HIGH but GATED on N1–N4 instrument repair + F5 injection policy
**Spec**: [fable5-findings-07-strategic-frontiers.md](fable5-findings-07-strategic-frontiers.md) §F2 — read it before claiming any waypoint
**Related**: [fable5-findings-04-impl-plan.md](fable5-findings-04-impl-plan.md) (capability registry); frontier-f5 (injection policy, spec §F5 — handoff not yet opened); [internal-kb-rag.md](internal-kb-rag.md) (kb-search context assembly); [delegation-context-preassembly.md](delegation-context-preassembly.md) (DCP bundles)

## Why

The project's true output is research-decisions-per-week; its binding costs are
operator attention and cloud-agent sessions. What exists is a self-*optimizing
serving layer*, not a self-*running lab*. The maintenance workload — intake
triage, hygiene lints, monitoring, digest drafting — is mechanical enough for
local models IF given output contracts, a review queue, and a reliability
ladder. The prerequisites (evidence plane, attestation, MEASUREMENT.md, index
rewrite) now exist or are queued; this is the 10× on the lab itself.

## Waypoints

- [x] **W1 — job inventory** (1 day): `orchestration/lab_jobs.yaml`, one row per recurring job (`{job_id, input_spec, output_contract, risk, model_role, schedule, reference_skill}`); seed set per spec §F2-W1 ordered by mechanical-ness (hygiene lint → attestation watch → digest draft → intake triage → claims-grammar check → deep-dive drafting) — acceptance: every seed job has a JSON-schema output contract and a risk class. **Branch-ready 2026-06-12**: `epyc-orchestrator` worktree `/mnt/raid0/llm/tmp/lab-jobs-inventory-worktree`, branch `feat/lab-jobs-inventory`, commit `8b4b24b` (`Seed self-running lab job inventory`). Six shadow-stage jobs validate against required fields/risk classes and each embedded JSON Schema compiles under Draft 7.
- [ ] **W2 — the runner** (3–5 days): `scripts/lab/run_job.py` — load job spec → assemble context (kb-search + DCP bundles, both BUILT) → local role via `/chat` `force_role` + structured output → validate against contract → write to `orchestration/lab_review_queue/` (NEVER directly to handoffs/indices) → log a `task_record` (feeds F1+F3); schedule via `scripts/nightshift/` — acceptance: 2 jobs running nightly in shadow (output produced, scored, discarded). **Runner branch-ready 2026-06-13**: `feat/lab-runner` commit `450a366` adds the review-queue runner, contract validation, bounded source-context assembly, explicit `--execute-chat` gating, fixture/dry-run validation modes, immutable review artifacts, and `lab_task_record.v1` JSONL logging. Remaining W2 acceptance: wire richer kb-search/DCP context, add nightly shadow scheduling/scoring, then produce scored/discarded shadow outputs.
- [ ] **W3 — reliability ladder** (ongoing): `scripts/lab/promote_job.py` enforcing shadow → reviewed → autonomous from logged stats (shadow ≥10 runs scored vs a cloud-reference run; autonomous only for read_only report-class jobs at ≥90% accept-rate over 20 reviewed runs) — acceptance: promotion only via the script; every (input, local output, cloud reference, verdict) tuple saved as F3 gold data. **Gate scaffold branch-ready 2026-06-13**: `feat/lab-reliability-ladder` commit `775d230` adds promotion evaluation/reporting over `lab_task_record.v1` + `lab_review_verdict.v1`, requires cloud-reference verdicts and gold tuple paths for reviewed-stage promotion, restricts autonomous promotion to `read_only` jobs with ≥90% accept-rate over ≥20 reviewed gold tuples, and requires `--apply --confirm-job-id` for jobs-file mutation. Remaining W3 acceptance: collect real shadow/reviewed verdicts and use the script as the only promotion path.
- [ ] **W4 — expand** (weeks): intake triage joins after F5 lands; deep-dive drafting after triage proves; research-intake skill stays the orchestrator, local models take per-source extraction steps — acceptance: each expansion enters at shadow and climbs the ladder.

## Gates & pitfalls

- HARD GATES: N1–N4 instrument repair done; F5 injection policy landed before any intake-touching job runs.
- Review queue is mandatory — CLAUDE.md forbids sub-agent index modifications without approval; the queue IS the compliance mechanism. No job writes directly to handoffs/indices.
- No job may self-modify `lab_jobs.yaml` or any trust-boundary file (add to safety-reviewer guardrails).
- Context assembly is the cost center — budget it (DCP bundles, per-job token caps); lab jobs share the stack with the autopilot — run in the contention gate's background class, off-peak.
- A job's accept-rate is a MEASUREMENT.md-grade number — same claims discipline as any benchmark.

## Progress

- 2026-06-12: W1 branch-ready at `feat/lab-jobs-inventory` commit `8b4b24b`. Validation: YAML parse + required job-field/risk/`job_id` const checks passed for 6 jobs; `uv run --with pyyaml --with jsonschema` Draft 7 schema compilation passed for all 6 embedded `output_contract.json_schema` blocks; `git diff --cached --check` passed. The inventory is shadow/disabled only and does not create the runner or queue.
- 2026-06-13: W2 runner branch-ready at `feat/lab-runner` commit `450a366`. Validation: `python3 -m py_compile scripts/lab/run_job.py tests/unit/test_lab_run_job.py` passed; `uv run --with pytest --with pyyaml --with jsonschema pytest -q tests/unit/test_lab_run_job.py` -> 4 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/lab/run_job.py tests/unit/test_lab_run_job.py` passed; `git diff --cached --check` passed; two no-inference smoke runs (`handoff_freshness_lint`, `claims_grammar_check`) wrote contract-valid review artifacts and task records under `/mnt/raid0/llm/tmp/lab-runner-smoke-20260612`.
- 2026-06-13: W3 promotion-gate scaffold branch-ready at `feat/lab-reliability-ladder` commit `775d230`. Validation: `python3 -m py_compile scripts/lab/promote_job.py tests/unit/test_lab_promote_job.py` passed; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_lab_promote_job.py tests/unit/test_lab_run_job.py` -> 9 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/lab/promote_job.py tests/unit/test_lab_promote_job.py` passed; `git diff --cached --check` passed; CLI smoke over the dry-run review queue wrote an ineligible promotion report and made no repo changes.

## Reporting

On completion of each waypoint: tick here, one-line progress entry, update master index row. W3/W4 are ongoing — report ladder promotions per job in progress logs.
