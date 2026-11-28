---
schema: epyc.brief.v1
id: MMID-HELPER-N10-GATE
box_text_sha: t:87c5a3161804f4af
author: planning
written: '2026-11-28'
accepted: auto
where:
- epyc-root:artifacts/analysis/mmid-helper-n10-c22-prep/c22-n10.patch
- epyc-root:artifacts/analysis/mmid-helper-n10-c22-prep/README.md
approach: 'Use the prepared N10-only patch and its operator tests on ratified C22 b1e1864cb. Bind both libraries to source
  and manifest, verify HIP residency and the executed top-10 helper. Predeclare the authorized GPU numerical rule before scoring.
  Interleave independent C22 controls with N10 on identical Q38FN and A3B tokens; retain KLD and same-top, and the original
  absolute-limit verdict. On numerical clearance, compare Q38FN hybrid pp2048 using profiled helper us/call and unprofiled
  paired tok/s, with A3B as regression control. Report effect against repeat variation and the historical contract. See the
  v11 performance closeout plan for fold selection.

  '
acceptance: verdict KEEP, DROP or FAIL_CORRECTNESS filed under MMID-HELPER-N10 with per-arm helper us/call, pp2048 tok/s and
  paired CIs
non_goals:
- readlane, production builds and promotion
tier: local
grounded:
  at: '2026-11-28'
  blobs:
    epyc-root:artifacts/analysis/mmid-helper-n10-c22-prep/c22-n10.patch: 10f92bd7c03b4baacdeb24ff63991819d4b7ffde
    epyc-root:artifacts/analysis/mmid-helper-n10-c22-prep/README.md: 8700f5980f25bf2f18f9ff27b9d4fa1e141fdc76
---
