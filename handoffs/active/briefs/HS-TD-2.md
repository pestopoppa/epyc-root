---
schema: epyc.brief.v1
id: HS-TD-2
box_text_sha: a37b97526ad31247
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/harness/hs_td2_selfcheck.py
- epyc-root:scripts/harness/hs_td2_probe.py
- epyc-root:tests/test_hs_td2_probe.py
- epyc-root:docs/reports/hs-td2-worker-selfcheck-20261119.md
approach: 'Offline worker screen is filed (30/32 agreement, mean extra-call 5.19 s). Remaining: run the logging-only self-check
  consumer on a real captured OpenCode session through the HS-TD-4 receipt API and review a sample of disagreements. Question:
  per-turn cost and disagreement quality on live turns. Stop when >=20 live turns are judged and disagreements reviewed; futility
  on two consecutive transport failures. Feeds the decision whether to keep self-check logging on.

  '
acceptance: grep -q 'live-session' docs/reports/hs-td2-worker-selfcheck-20261119.md
non_goals:
- never gate or route on the self-check
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/harness/hs_td2_selfcheck.py: eec62bc6e480cd5610d77f061ca0291d4afe58c7
    epyc-root:scripts/harness/hs_td2_probe.py: 6973f2f80f7e59f1dfbb93acfd8281ee824679e2
    epyc-root:tests/test_hs_td2_probe.py: 81fb97c7f3fee0e50c4f4dae2c4bc2e9792c96b6
    epyc-root:docs/reports/hs-td2-worker-selfcheck-20261119.md: 3af3a9faebf9086a247c25756e6aeaede57c3e9d
---
