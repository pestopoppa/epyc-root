# 2026-05-26 — Docs/Chapters Audit & Refresh

## Summary

Autonomous swarm pass over `docs/chapters/` in both sibling repos (`epyc-orchestrator`, `epyc-inference-research`). Triggered by planning for a public-site narrative layer — chapters were ~3 months stale, so building narrative on top would inherit pre-Qwen3.6, pre-gemma4, pre-stack-consolidation falsehoods.

Driven from a single session: 6 parallel audit agents → 6 parallel editing agents → 2 parallel validation agents. Zero Phase 4 rework needed.

## Results

23 files modified across both sibling repos (staged uncommitted on `main`):
- **epyc-orchestrator**: 14 chapters
- **epyc-inference-research**: 9 files (7 chapters + 2 guides rewritten)

~145 audit items applied. 3 audit claims caught and rejected by editing agents (verified against actual code/registry). 1 editor/audit disagreement flagged for user review (MODEL_MANIFEST worker row — editor chose current-registry value; validator agrees).

## Notable fixes

- `architect_coding` references purged everywhere as a live role (eliminated 2026-05-06)
- Pre-Qwen3.6 frontdoor → Qwen3.6-35B-A3B Q8 consolidated on port 8070
- Pre-gemma4 worker_general → gemma-4-26B-A4B with MTP, port 8072
- Stack consolidation 2026-05-09 documented (shared GGUF, full vs quarter NUMA mode)
- Learned routing controller (2026-05-21 deployment) wired into Ch07/Ch10 narrative
- `enable_thinking=False` chat-template requirement for Qwen3.x routes documented
- Pre-monorepo-split `/mnt/raid0/llm/claude` paths replaced in 2 research guides
- Research Ch10 internal contradiction resolved (regime-difference framing: GPU HBM vs EPYC DDR5; K saturates at ~16; NUMA 4-way is primary lever, spec-dec is +17–21% incremental)

## Cross-references

- Handoff: `handoffs/active/docs-chapters-audit-refresh.md`
- Per-cluster audit + edit + validation reports: `handoffs/active/docs-chapters-audit/`
- Originating context: README/wiki UX + GH Pages narrative-layer planning (no separate handoff yet)

## Open items

- User commit approval pending (single coordinated commit per repo recommended)
- Worker-row disagreement in `MODEL_MANIFEST.md` for review
- Once chapters are committed: build the public-site narrative layer (~10–20 curated pages weaving chapters + wiki + falsified-hypothesis trail; MkDocs Material on GH Pages)

## Process notes

- 6-parallel agent swarms worked well; total wall time ~25 min across all phases
- Editing agents caught 3 audit errors by cross-checking sources before applying — verification step in the prompt was load-bearing
- One hook gotcha surfaced in Cluster F: `agents_reference_guard.sh` blocks `Write`/`Edit` when stale inline `` `*.md` `` references don't resolve; cluster-F agent worked around with Python in-place edit before Write
