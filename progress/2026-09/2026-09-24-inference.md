# 2026-09-24 — Qwen-Image-2.1 acquisition wrap-up

- Confirmed the requested public Qwen-Image-2.1 Diffusers bundle is present at
  `/mnt/raid0/llm/models/diffusion/qwen-image-2.1/` (33,115,613,408 bytes, all encoder and transformer
  shards plus VAE); this acquisition was previously recorded on 2026-09-23 and is not duplicated here.
- Updated the ERNIE evaluation checklist to distinguish completed weight acquisition from the still-unrun,
  matched-prompt Qwen-Image-2.1 vs ERNIE generation comparison. No comparative result is claimed.
- Refreshed the pipeline handoff index and generated state; `index_state.py --check` passed. README freshness
  emitted no warnings. The wiki already contained the Qwen/ERNIE acquisition facts, so this pass avoided a
  duplicate article. The operator-only sweep compiled concurrent DS41 actor/planner findings into
  `wiki/autonomous-research.md` and the TD-21 consumer census into `wiki/agent-architecture.md`, filing
  prospective write-side tasks VB-AK-DS41-OPS and VB-TD-21-CENSUS. Retrospective operational and audit results
  remain unbackfilled. Also corrected a dangling EVL-08 progress link in `wiki/benchmark-methodology.md` to
  its surviving canonical handoff and retired the untraceable n=50/host-throughput rationale.
- Knowledge-base lint exposed 22 pre-existing stale-handoff errors plus two pre-existing missing wiki anchors;
  the broken progress target found during this review was corrected. Read-only audits covered all 22 stale
  handoffs; the concrete next-action rot in RTG-03, RTG-07, and EVL-31 was corrected in their owner indexes.
  The remaining stale entries are live, gated, or preserved reopen pointers; no status was cosmetically
  refreshed. No unrelated handoffs were touched.
- Reviewed generated prune candidates: none were returned; no handoff pruning or compaction was warranted.
