---
schema: epyc.brief.v1
id: SPEC-STOP-EQ7-1
box_text_sha: t:f6a7b79cb7ffc9e4
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:common/speculative.cpp
approach: 'Load the CAFE-1-SERVED-T capture JSONL (per-position draft probabilities, accepted lengths). Fit C(K) = a + b*K
  + c*E_union(K) by least squares on Q38P/CAFE verify timings, with E_union from the routing traces. Implement the Eq 7 argmin
  in a short numpy script, replay it on a 50% held-out split of the captures, and bootstrap the tokens/s ratio against each
  fixed p_min.

  '
acceptance: step-1 fit (R^2 and coefficients) and step-2 modelled gain with CI per temperature filed under this box, with
  verdict KEEP candidate (gain >= 3% with CI lower > 1.0 at both temperatures), CLOSE (gain < 1% with CI upper < 1.02) or
  INCONCLUSIVE
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:common/speculative.cpp: 2b365cf37a40c789c52fc38a2ec2420ce5b4a858
---
