---
schema: epyc.brief.v1
id: HITL-R4-FRESH-CEILING
box_text_sha: 97f820d197a0d82e
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/token_guards.py::lease_verdict
- epyc-root:scripts/coordination/tests/test_token_guards.py
approach: 'token_guards.py ~L258 parks on usage.total_tokens > session_token_ceiling (15M) for any thread. Decision: apply
  it only to fresh threads; on a resumed-thread breach rotate to a fresh thread first (the AUTO_UNPARK ''thread token ceiling''
  path ~L385), park only if the fresh one breaches. Pin with a test (HS-FRESHNEXT: covered event resumes only). Needs D9-ack
  before merge. Box has no runnable done-when; acceptance is the closest check.

  '
acceptance: grep -q resumed_thread scripts/coordination/token_guards.py && python3 -m pytest -q scripts/coordination/tests/test_token_guards.py
non_goals:
- do not raise the 15M ceiling
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/token_guards.py: 4f0f67c198f8a49d5902085b5457fd901ecd0706
    epyc-root:scripts/coordination/tests/test_token_guards.py: 148859367354d45990301b32a7b765b5ade3dc04
---
