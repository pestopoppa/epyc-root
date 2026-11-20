---
schema: epyc.brief.v1
id: QSTATUS-GPU-QUIET-LABEL
box_text_sha: 59d14f516c281e11
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:.claude/skills/inference-backlog-scheduling/scripts/queue_status.py
- epyc-root:scripts/coordination/tests/test_queue_status_rowflow.py
approach: 'In main() RUNNING rows get x[''util''] from hu.regions_pct over toks incl ''gpu-quiet'' (a token sample) and x[''idle_held'']
  from hu.idle_regions; the L309 print labels it ''measured gpu-quiet=N%''. Decision: rename the label to ''token-sample'',
  additionally print GPU util/VRAM from rocm-smi, and never derive IDLE-HELD for gpu-quiet from the token sample alone. Add
  a test in test_queue_status_rowflow.py. Box has no done-when; acceptance is the closest check.

  '
acceptance: grep -q 'token-sample' .claude/skills/inference-backlog-scheduling/scripts/queue_status.py && python3 -m pytest
  -q scripts/coordination/tests/test_queue_status_rowflow.py
non_goals:
- do not change the other regions' util measure
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:.claude/skills/inference-backlog-scheduling/scripts/queue_status.py: a53b581b6ea822907905ad9bc5c2262159169870
    epyc-root:scripts/coordination/tests/test_queue_status_rowflow.py: 879cf13cd2554dcb8a309293e5db47d4422d2c08
---
