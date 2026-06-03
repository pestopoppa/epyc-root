# AutoWiki-Style Incremental KB Generator

**Status**: stub
**Created**: 2026-06-03 (via research intake → factory.ai deep-dive)
**Categories**: knowledge_management, rag_alternatives, search_retrieval

## Objective

Add a generator that compiles our repos + handoffs into structured, cross-linked wiki pages and **refreshes them incrementally** (only pages whose source files changed), re-embedding only the changed chunks into the ColBERT index. This extends our existing compiled KB ([`internal-kb-rag.md`](internal-kb-rag.md), project-wiki skill) with change-driven freshness and closes the staleness gap the project-wiki lint currently flags.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-657 | Factory.ai docs (AutoWiki: overview / generate / auto-refresh) | high | adopt_patterns |

Full mining → [`research/factory-ai-harvest-2026-06-03.md`](../../research/factory-ai-harvest-2026-06-03.md) (Part 3E).

## Mechanism to reproduce (from Factory AutoWiki)

- **Structured topic taxonomy**: every generated page is one of {architecture overview, module breakdown, API, conventions, setup}, cross-linked. Standardize our `wiki/` to emit these page types per subsystem.
- **Per-page incremental refresh**: maintain a `page → source-paths` manifest with a **content hash per source-set**; on a push, recompute only pages whose source-set intersects the git diff (first run full, later runs reuse prior work — Factory does this automatically, no flag).
- **Change-driven re-embed**: re-embed only the changed chunks into the ColBERT index ([`colbert-reranker-web-research.md`](colbert-reranker-web-research.md)) rather than rebuilding (current build = 409 files / 13,537 chunks / 17 min).
- **CI auto-refresh**: a push-triggered job (or a nightshift schedule) with a `paths:` filter — the OSS equivalent of Factory's `/install-wiki` GitHub Action.

## Open Questions

- The `page → source-paths` manifest is also the basis for **drift detection** — does it subsume / improve our `scripts/validate/` document-drift validator?
- Generator model: which local model writes the pages, and how do we keep it from hallucinating structure (lint gate on output)?
- Scope: in-repo git-versioned wiki (we already have this — git = versioning) vs any app/UI sync (SaaS-only, skip).
- Trigger cadence: on-push CI vs nightshift batch — and how does it coordinate with the autopilot loop without contending for inference?

## Notes

- The SaaS-only parts (Factory App Cloud Sync, web viewer UI, GitHub-Wiki sync) are excluded; the reproducible core is the topic-taxonomy + page→source manifest + incremental re-embed.
- Cross-refs: `internal-kb-rag.md`, `colbert-reranker-web-research.md`, `knowledge-base-governance-improvements` (in cross-reference map), project-wiki skill, `scripts/nightshift/`.
