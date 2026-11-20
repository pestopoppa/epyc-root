---
schema: epyc.brief.v1
id: RM-2
box_text_sha: t:73b8d30e69f6be77
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:data/reviewer_model_ablations
- epyc-inference-research:docs/data/reviewer_model_ablations_rm2_next_ccrab_p_rev1_20260719.md
approach: 'Anchor arms: A0 floor and A3 (Qwen3.5-122B IQ2 on GPU) done; A4 failed under the current policy; A4g obsolete (GLM-5.2
  retired). Re-scoped 2026-11-03: A3 -> Qwen3.8-27B resident on GPU (grammar mandatory) and A4 -> DS41-1017 or Flash-Next
  CPU, plus Ref external judge-of-judge (~100 sampled decisions, pinned model id+date, budget-capped). Prep: row specs for
  A3-27B on the matched C-CRAB 48-row slice. Stop on each arm''s FA/FR/AUC/ECE filed.

  '
acceptance: grep -q 'RM-2.*A3 Qwen3.8-27B' handoffs/active/reviewer-control-plane.md
non_goals:
- no GLM-5.2 rerun
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:data/reviewer_model_ablations: tree:0cbbd95e7556d2c52a0eb65abd11925a3107e49a
    epyc-inference-research:docs/data/reviewer_model_ablations_rm2_next_ccrab_p_rev1_20260719.md: 992c79c0538d6d11e2ea5e5affebc193e9a590db
---
