---
schema: epyc.brief.v1
id: VB-CAFE3-ROUND-WIRE
box_text_sha: 20d11835bebe666f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/diagnostics/cafe3-adaptive/native_sink.h
- epyc-root:scripts/diagnostics/cafe3-adaptive/protocol_requests.py
- epyc-root:scripts/diagnostics/cafe3-adaptive/native_runner.py
- epyc-root:scripts/diagnostics/cafe3-adaptive/multi_arm.py
- epyc-root:scripts/diagnostics/cafe3-adaptive/p9_grade.py
- epyc-root:scripts/diagnostics/cafe3-adaptive/launch_context.py
approach: 'Producers and model-free tests already exist (59 tests collect). Add the missing journal emission per p1-p4: each
  of the five epyc.cafe3 schema IDs written by its producer file, per-request residency fields, sealed LLAMA_CAFE3_CONTEXT_SHA256
  manifest with refuse-on-mismatch. Project via existing carrier and ClaimTuple.grade(); no new ladder. Native canary is separate
  (operational); acceptance is the model-free tests.

  '
acceptance: python3 -m pytest -q scripts/diagnostics/cafe3-adaptive/test_native_sink.py scripts/diagnostics/cafe3-adaptive/test_protocol_requests.py
  scripts/diagnostics/cafe3-adaptive/test_native_runner.py scripts/diagnostics/cafe3-adaptive/test_multi_arm.py scripts/diagnostics/cafe3-adaptive/test_p9_grade.py
  scripts/diagnostics/cafe3-adaptive/test_launch_context.py
non_goals:
- no new claim-grade ladder
- no native GPU run in this box; the native canary stays operational
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/diagnostics/cafe3-adaptive/native_sink.h: 0a94f633d7b9f149fe453d3b40df2e931bb5078d
    epyc-root:scripts/diagnostics/cafe3-adaptive/protocol_requests.py: ddca643ed6b9f08dc56bcc35761e55be1df65f0c
    epyc-root:scripts/diagnostics/cafe3-adaptive/native_runner.py: 9290ce917eb30bff2c9fd8e5b094cb3d6de64849
    epyc-root:scripts/diagnostics/cafe3-adaptive/multi_arm.py: c027a6765fef6ce71625c26a6b76591aa13adc5f
    epyc-root:scripts/diagnostics/cafe3-adaptive/p9_grade.py: 2260f07d14d2c04fea6b8f701c729e8b7463d769
    epyc-root:scripts/diagnostics/cafe3-adaptive/launch_context.py: 38108c3148aa7449b3681efff7604562e679f28b
---
