---
schema: epyc.brief.v1
id: HS-TD-1
box_text_sha: 5677e053bea22df8
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/harness/hs_td1_shadow.py
- epyc-root:scripts/harness/hs_td1_probe.py
- epyc-root:tests/harness/test_hs_td1_shadow.py
- epyc-root:scripts/harness/HS-TD1-SHADOW.md
approach: 'Remaining work is the parent acceptance only: capture and replay a real opt-in OpenCode session window through
  hs_td1_shadow.py (capture and join code are done and ticked) and report agreement and confidence against the OBSERVED harness
  permissive/restrictive decision. Question: does the typed risk/intent call agree with real harness decisions? Stop when
  one real-session window with >=30 joined turns is replayed or the capture is unavailable; futility-only interim. Decides
  whether HS-TD-1 stays logging-only.

  '
acceptance: grep -q 'real-session shadow-log.*agreement' docs/reports/hs-td1-risk-intent-real-session.md
non_goals:
- no gating
- do not use authored references as observed decisions
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/harness/hs_td1_shadow.py: 9ef1e1aba75cc18cded56556c225350d7c493ca2
    epyc-root:scripts/harness/hs_td1_probe.py: 762c93b7e14832ad0a453a65ba762b8533f2842b
    epyc-root:tests/harness/test_hs_td1_shadow.py: c6d1e462582a935ae8023f9ca485d8fe6f23dd82
    epyc-root:scripts/harness/HS-TD1-SHADOW.md: ee9debbb681c0b87316af69126fd77aa3c4f6ef2
---
