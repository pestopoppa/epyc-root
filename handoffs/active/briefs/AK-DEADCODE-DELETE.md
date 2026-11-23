---
schema: epyc.brief.v1
id: AK-DEADCODE-DELETE
box_text_sha: t:497bd0d4ad2c30f3
author: owner
written: '2026-11-23'
accepted: owner
where:
- handoffs/active/autokernel-loop.md
approach: 'Code lives in epyc-inference-research scripts/kernel_rnd/autokernel/loop (baseline loop_code_budget_baseline.json,
  guard check_regrowth_guards.py). Candidate list: /mnt/raid0/llm/tmp/ak-deadcode-20261123/CANDIDATES.md (+ candidates.json).
  101 modules, 38,818 code lines (C2-01 56 modules 34,320 lines; 45 further DEAD 4,498 lines) and about 75-84 test files.
  Tier A (34 modules, 5,040 lines) has no live importer: delete as soon as AutoKernel confirms. Tier B (67 modules, 33,778
  lines) is still imported by live code (journal.py, serving_preparation, observation_binding, cpu_profile, unified_planner,
  search_window, campaign_service, lane_watchdog, serial_run, producer_pins): re-home those bridges first (refactor-audit
  C2-03 and C2-05, research/refactor-audit-2026-10/findings-autokernel.md C2-01) or the live loop stops importing. Order:
  AutoKernel confirms the list; delete confirmed tier A with its tests, test_scratch.py rows and baseline entries; re-home
  tier B bridges; delete tier B; run python3 -m scripts.kernel_rnd.autokernel.check_regrowth_guards --tighten-total and commit.
  Anything with dynamic or indirect use (host_claim_provider loads worker_lifecycle and standalone_inputs by name) stays.

  '
acceptance: Every AK-confirmed module and its tests are gone; the remaining loop test suites pass unchanged (same pytest result
  minus the deleted files, pinned taskset -c 24-47); check_regrowth_guards exits 0; total_ceiling lowered by --tighten-total
  in an ordinary commit.
non_goals: []
tier: local
grounded:
  at: '2026-11-23'
  blobs:
    epyc-root:handoffs/active/autokernel-loop.md: 9890c8ec2c73e8e0bea4ed796f01ea02955b777c
---
