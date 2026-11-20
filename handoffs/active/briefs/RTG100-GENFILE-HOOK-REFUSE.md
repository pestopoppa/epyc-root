---
schema: epyc.brief.v1
id: RTG100-GENFILE-HOOK-REFUSE
box_text_sha: 4c8c101070a1d232
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/hooks/check_commit_hygiene.py::GENERATED_COMMIT_MODE_DEFAULT
- epyc-root:scripts/hooks/tests/test_commit_hygiene_generated.py
approach: 'Time-gated: one week after the hook went live (2026-11-20) and with zero non-hub commits touching generated files
  in that window (warn JSONL plus git log --since=7.days on .index-state.json), flip GENERATED_COMMIT_MODE_DEFAULT from warn
  to refuse and update the test that pins the default. Before the date, only the check can be run.

  '
acceptance: grep -q 'GENERATED_COMMIT_MODE_DEFAULT = "refuse"' scripts/hooks/check_commit_hygiene.py && python3 -m pytest
  -q scripts/hooks/tests/test_commit_hygiene_generated.py
non_goals:
- do not exempt the hub writer (EPYC_INDEX_WRITER=hub stays the only exemption)
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/hooks/check_commit_hygiene.py: d4f3612ea4ea36775eeae3d35d4f4e72d6da2756
    epyc-root:scripts/hooks/tests/test_commit_hygiene_generated.py: 958ecb4e1379e2e28473e55fad9d062c0ba5f435
---
