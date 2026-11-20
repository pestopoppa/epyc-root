---
schema: epyc.brief.v1
id: TASKFLOW-NEEDS-BRIEF-TAG
box_text_sha: 6c980a7cb314871a
author: wrap-up
written: '2026-11-20'
accepted: auto
where:
- epyc-root:scripts/coordination/taskflow/dispatch.py::phase1_or_skip
- epyc-root:scripts/handoffs/box_index.py::skip_reason
- epyc-root:tests/coordination/test_taskflow_needs_brief_tag.py
approach: 'Dispatch never edits handoffs, so the tag lives in a gitignored sidecar the index reads: on a needs-brief verdict
  append {id, text_sha, missing, at} to handoffs/active/briefs/.needs-brief.jsonl; box_index sets needs_brief when a line
  matches the box''s current text_sha (a box edit clears it by identity).

  '
acceptance: pytest -q tests/coordination/test_taskflow_needs_brief_tag.py
new_tests:
- tests/coordination/test_taskflow_needs_brief_tag.py
non_goals:
- do not write the NEEDS-BRIEF tag into the handoff text from the dispatcher
- do not skip boxes that merely lack a brief
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/taskflow/dispatch.py: 26f594dbb32d82074d6bce24719922b147c20c27
    epyc-root:scripts/handoffs/box_index.py: bc57c9ba837cee1e5cb9671617ef02b241dff29c
    epyc-root:tests/coordination/test_taskflow_needs_brief_tag.py: null
---
