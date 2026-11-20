---
schema: epyc.brief.v1
id: REPL-EMB-R5
box_text_sha: 552699dc249fa1a1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/embedding_dims.py
- epyc-orchestrator:scripts/benchmark/repl_emb_eval.py
approach: 'First measure EG2@256 cosine percentiles (top-k over ~500 sampled queries, package section 6 G-S), then re-derive
  every BGE-tuned similarity threshold listed in the box (min_similarity 0.3, confidence 0.6, q_scorer 0.85, combined 0.7*Q+0.3*sim,
  classification_retriever, skill_bank, replay, knowledge_distiller, session store, research_context) with a dated sweep each;
  the old BGE value stays recorded. Stop when every threshold has a sweep. CPU embed pass; offline.

  '
acceptance: test -f docs/reports/eg2-256-threshold-recalibration.md
non_goals:
- no live threshold change before MIGRATED
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/embedding_dims.py: f46c27a24ee2b7954b3be576fb78a48e744190c6
    epyc-orchestrator:scripts/benchmark/repl_emb_eval.py: 1668d4b48c04da06ee4229a3bf65ccc925d48256
---
