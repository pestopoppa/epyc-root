---
schema: epyc.brief.v1
id: SPEC-GRAM-JSON-1
box_text_sha: t:6506abbec5be4a1c
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:common/sampling.cpp
- epyc-llama:tools/server/server-context.cpp
approach: 'Pull retained json_schema request/response pairs from the orchestrator logs per class, compile each schema with
  llguidance 1.0.1, walk the tokenized output calling llg_matcher_compute_ff_tokens at each step, and count forced tokens,
  run lengths and steps where the mask admits exactly one token. Weight by per-class token volume from the serving logs. Write
  a CSV plus a summary table; no server or model is started.

  '
acceptance: 'per-class table (forced share, run-length histogram, single-allowed subset, serving-token share) filed under
  this box with the input digest and the verdict: decline (every class under 10%) or open the chain-path design (any class
  >= 10% with material token volume)'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:common/sampling.cpp: 21642fb71cebfa0057cd19ae7fa5c50877f04a92
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
