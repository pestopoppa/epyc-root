---
schema: epyc.brief.v1
id: PFXC-ID-REPLICA-1
box_text_sha: t:f0e1c880e716f8e6
author: planning
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Run llama-server with the served flags and cache_prompt true. Per prompt, send a priming request, then the target
  request (cache hit), restart and send it cold. Repeat over 3 launches. Classify first divergences with the protocol''s margin
  classes and compare against the per-path A/A largest pair. Log cache_n from the response timings.

  '
acceptance: 'per-device divergence counts out of 64 per path with the largest-pair A/A floor filed under this box, and the
  verdict: any cache-path divergence outside the floor marks cached requests outside the exact regime in the protocol'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
