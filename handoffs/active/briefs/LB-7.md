---
schema: epyc.brief.v1
id: LB-7
box_text_sha: t:772bdecdb37ceee0
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/autopilot/screening_tier_runner.py
- epyc-inference-research:scripts/benchmark/reviewer_a0_objective_floor.py
approach: 'M3 baseline floor: full review plane (shadow->enforce candidate config) vs single-augmented-LLM baseline (A0/A1
  arms) on the same tasks; the go/no-go the series answers to. A0/A1 floors exist on the C-CRAB P-REV-1 48-row slice (A0 FA
  0, FR 0). Prep: the full-plane arm config; run paired, report FA/FR/CR and throughput. Stop on e-process decision or futility.

  '
acceptance: grep -q 'LB-7 verdict' handoffs/active/reviewer-control-plane.md
non_goals:
- no enforce flip
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/autopilot/screening_tier_runner.py: b0110ac99b04c08454b4d604e739f1d63f5cd43b
    epyc-inference-research:scripts/benchmark/reviewer_a0_objective_floor.py: c756cd1cd6eb4f5f2f67e49500a5cf79c2a87f31
---
