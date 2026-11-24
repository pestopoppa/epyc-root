---
schema: epyc.brief.v1
id: RSL-R2
box_text_sha: t:8bae048956cc53e8
author: planning
written: '2026-11-24'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/census_update.py
- epyc-root:scripts/coordination/akloop/ak_runend.py
approach: 'new pure module census_inbox.py installs/removes BWS-*.md inbox stubs from seedable_surfaces, deduped on target_surface
  vs inbox and candidate spool; ak_runend calls it after census_update (D9 ack needed for ak_runend)

  '
acceptance: nice -n 19 taskset -c 84-87 python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_census_inbox.py
new_tests:
- scripts/kernel_rnd/autokernel/loop/test_census_inbox.py
non_goals:
- no committed seed-file writes at run-end
tier: terra
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/census_update.py: d29f0fab3b76f8ad84e6b4910a343c9014b8036f
    epyc-root:scripts/coordination/akloop/ak_runend.py: 871aa44af8d8cf292687cba0507d7b09653f086f
---
