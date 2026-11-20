---
schema: epyc.brief.v1
id: VB-CF3C-POLICY-WIRE
box_text_sha: de7c96dfcf40dc3a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:tests/vidya/test_toc_ab_cf3c.py
- epyc-root:tests/vidya/test_toc_ab_cf3c_task.py
- epyc-root:/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-active/native/RESULT.json
- epyc-root:/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-task/native/RESULT.json
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: Extend the existing TOC measurement projection for the prospective deterministic-policy
  pilot. Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py
  + README row) with a synthetic-fixture test and refusal controls. Box has no code-level done-when; acceptance is the closest
  check.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_cf3c_policy_wire_wire.py tests/vidya/test_toc_ab_cf3c.py tests/vidya/test_toc_ab_cf3c_task.py
new_tests:
- tests/vidya/test_vb_cf3c_policy_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:tests/vidya/test_toc_ab_cf3c.py: ff3c818beee33294c7f05026df3c120a2b017949
    epyc-root:tests/vidya/test_toc_ab_cf3c_task.py: 9b670d76f26684df211383255d93fef7f4bc8eb9
    epyc-root:/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-active/native/RESULT.json: b560b1c806a4ca78084189566fbc4f0e3ae7d9e8
    epyc-root:/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-task/native/RESULT.json: 65965eaa60ede77629278a5e856c36daf422f220
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
