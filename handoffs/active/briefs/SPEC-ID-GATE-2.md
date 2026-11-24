---
schema: epyc.brief.v1
id: SPEC-ID-GATE-2
box_text_sha: t:7da0d0f9246cf76d
author: planning
written: '2026-11-24'
accepted: auto
where:
- epyc-root:docs/guides/agent-workflows/spec-identity-gate-protocol.md
approach: 'Edit sections 2, 3, 4 and 6 of the protocol doc: add a replica table (launches, pair list, largest-pair floor),
  a preconditions checklist (cache_prompt, --cache-ram, -ub, -ctk/-ctv, spec width) and a RESULT.json field list (env knobs,
  route histogram, binary sha256, config dump). In the gate reporter, return INCONCLUSIVE when fewer than 3 reference launches
  are supplied, with a pytest case. Append the cache-off label to the SPEC-ID-NOISE-1 result line.

  '
acceptance: protocol sections (a)-(e) committed with the commit SHA recorded under this box, the gate script returns INCONCLUSIVE
  below 3 replicas in a committed unit test, and the SPEC-ID-NOISE-1 result line carries the cache-off label
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:docs/guides/agent-workflows/spec-identity-gate-protocol.md: e93776398676ded76fe1204418822b2b90370037
---
