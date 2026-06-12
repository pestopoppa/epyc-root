# Frontier F2 — The Self-Running Lab: Local Agents Take Over Lab Maintenance

**Status**: SPEC'D, not started (created from the Fable 5 strategic-frontiers review)
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

- [ ] **W1 — job inventory** (1 day): `orchestration/lab_jobs.yaml`, one row per recurring job (`{job_id, input_spec, output_contract, risk, model_role, schedule, reference_skill}`); seed set per spec §F2-W1 ordered by mechanical-ness (hygiene lint → attestation watch → digest draft → intake triage → claims-grammar check → deep-dive drafting) — acceptance: every seed job has a JSON-schema output contract and a risk class.
- [ ] **W2 — the runner** (3–5 days): `scripts/lab/run_job.py` — load job spec → assemble context (kb-search + DCP bundles, both BUILT) → local role via `/chat` `force_role` + structured output → validate against contract → write to `orchestration/lab_review_queue/` (NEVER directly to handoffs/indices) → log a `task_record` (feeds F1+F3); schedule via `scripts/nightshift/` — acceptance: 2 jobs running nightly in shadow (output produced, scored, discarded).
- [ ] **W3 — reliability ladder** (ongoing): `scripts/lab/promote_job.py` enforcing shadow → reviewed → autonomous from logged stats (shadow ≥10 runs scored vs a cloud-reference run; autonomous only for read_only report-class jobs at ≥90% accept-rate over 20 reviewed runs) — acceptance: promotion only via the script; every (input, local output, cloud reference, verdict) tuple saved as F3 gold data.
- [ ] **W4 — expand** (weeks): intake triage joins after F5 lands; deep-dive drafting after triage proves; research-intake skill stays the orchestrator, local models take per-source extraction steps — acceptance: each expansion enters at shadow and climbs the ladder.

## Gates & pitfalls

- HARD GATES: N1–N4 instrument repair done; F5 injection policy landed before any intake-touching job runs.
- Review queue is mandatory — CLAUDE.md forbids sub-agent index modifications without approval; the queue IS the compliance mechanism. No job writes directly to handoffs/indices.
- No job may self-modify `lab_jobs.yaml` or any trust-boundary file (add to safety-reviewer guardrails).
- Context assembly is the cost center — budget it (DCP bundles, per-job token caps); lab jobs share the stack with the autopilot — run in the contention gate's background class, off-peak.
- A job's accept-rate is a MEASUREMENT.md-grade number — same claims discipline as any benchmark.

## Reporting

On completion of each waypoint: tick here, one-line progress entry, update master index row. W3/W4 are ongoing — report ladder promotions per job in progress logs.
