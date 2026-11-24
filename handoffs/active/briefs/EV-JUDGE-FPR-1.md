---
schema: epyc.brief.v1
id: EV-JUDGE-FPR-1
box_text_sha: t:f894f2ca8c91d9c1
author: intake
written: '2026-11-24'
accepted: owner
where:
- epyc-orchestrator:src
approach: 'Clone hkust-nlp/RL-Verifier-Robustness to read Table 8''s strings and the Figure 6 prompts. Build a string x problem
  matrix (about 471 DeepScaleR items). Call each judge config through its existing eval_tower adapter with the three prompt
  templates, and compute per-string accept rates with Wilson intervals. The propensity scan greps journal outputs with the
  same detectors.

  '
acceptance: 'per-judge, per-string FPR table and the propensity counts filed under this box with the problem-set digest; verdict
  per judge: no-go for any optimiser use if the FPR of any string is >= 1%, else cleared at that rate'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-orchestrator:src: tree:8fbfbe16e38959d711e1700615b5208b9d9ce0be
---
