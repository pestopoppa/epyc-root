---
schema: epyc.brief.v1
id: PIPE-EVE-RAM-MARGIN
box_text_sha: 021468a39ea23653
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/ram_admit.sh
- epyc-root:scripts/coordination/job_templates/job_fence.py::RAM_MARGIN_GIB
- epyc-root:scripts/coordination/tests/test_rowflow_ram_margin.py
approach: 'Partly done: rowflow RAM_MARGIN_GIB and job_fence already 100 with ram_gib injection (test_rowflow_ram_margin.py
  passes). The remaining 64 is ram_admit.sh MARGIN_GIB (and its header comment); the file is a copy of the compute-flags one
  (its header says edit there first, then re-copy), so change both. Acceptance is the closest deterministic check (box has
  no done-when).

  '
acceptance: grep -q '^MARGIN_GIB=100' scripts/coordination/ram_admit.sh && python3 -m pytest -q scripts/coordination/tests/test_rowflow_ram_margin.py
non_goals:
- do not touch earlyoom thresholds
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/ram_admit.sh: 0ee5947f9f6b0f10bbcefcedfed158c2c09b31bd
    epyc-root:scripts/coordination/job_templates/job_fence.py: c2dc3041ff403963d3359429cd819e36b268944c
    epyc-root:scripts/coordination/tests/test_rowflow_ram_margin.py: b1c8af4a48e3fd8a1238255494407e8b16fedd65
---
