---
schema: epyc.brief.v1
id: LOOP-81
box_text_sha: c8ec314f4a25200d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-orchestrator:Makefile
- epyc-orchestrator:Justfile
approach: 'O8: orchestrator CI runs ONLY on pull_request and workflow_dispatch (operator decision 2026-10-24), after the reviewed
  hermetic harness and test-hazards runtime-store isolation merge (LOOP-63, LOOP-66). Use ubuntu-latest CI workers and a reviewed
  host-only exclusion list with one reason per entry, derived from a fresh baseline pinned to the integration commit; make
  Makefile/Justfile/CONTRIBUTING run commands agree (A6-04). Findings A6-04, B1-M3, B5-10, B5-17, A6-13. First step: the baseline
  run and exclusion list file.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && grep -q 'pull_request' .github/workflows/*.yml
non_goals:
- no push-triggered workflows
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-orchestrator:Makefile: 0a40620eafd76ab7b523cc669d091663b26c92fd
    epyc-orchestrator:Justfile: c09ad6d9e8bdc3fc55e0754123440d48cdf5ce51
---
