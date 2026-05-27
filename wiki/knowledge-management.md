# Knowledge Management

**Category**: `knowledge_management`
**Confidence**: framework (methodology + scoping; primary KB-RAG implementation pre-deployment)
**Last compiled**: 2026-05-27
**Sources**: 4 active handoffs (internal-kb-rag, sliders-local-validation, colbert-reranker-web-research, handoff-backlog-hygiene-audit), 3 intake entries (intake-453 Reason-mxbai, intake-492 Flywheel, intake-494 SLIDERS)

## Summary

Knowledge management in EPYC encompasses two complementary architectures: **internal KB-RAG** (ColBERT-based retrieval over the project's markdown knowledge bases) and **structured-DB alternatives** (SQL-based extraction-and-reasoning for long-document aggregation, tracked separately under `rag-alternatives.md`). Both replace keyword-only retrieval with semantic understanding, but via orthogonal mechanisms — retrieval-then-rerank vs persistent-schema SQL. This page documents the KB-RAG architecture, the Flywheel-derived evaluation methodology adopted for K7, and the wiki/governance pipeline that compiles handoffs and research notes into curated wiki articles.

The core insight from the 2026-04-28 intake update is that *the right architecture depends on corpus scale*. At our scale (24 wiki articles + ~70 active handoffs + ~30 research/deep-dive notes + daily progress logs ≈ 4–5K markdown chunks after heading-aware split), ColBERT-based retrieval over a per-document `.npz` + SQLite catalog is the appropriate primary path. The structured-DB SLIDERS architecture is gated behind a Phase 0 falsification experiment (`sliders-local-validation.md`) and is positioned as an alternative architecture for orders-of-magnitude-larger corpora, NOT an upgrade lane on the ColBERT path.

A third architectural pattern — **persistent compiled wikis** — is itself a knowledge-management approach. This very wiki is an instance: knowledge is pre-compiled by the `project-wiki` skill from handoffs/research/progress logs into curated topic articles, trading per-query synthesis latency for curation burden and staleness risk. EPYC uses a hybrid: `project-wiki` for stable / cross-cutting topics, KB-RAG for dense ad-hoc cross-referencing during Explore-agent runs.

## Internal KB-RAG Architecture (K1–K8 work items)

Per [`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md), the planned KB-RAG indexes the wiki + active handoffs + completed handoffs + research/deep-dives + progress logs + (cross-repo) `epyc-inference-research/docs/chapters` with heading-aware chunking. Storage: per-document `.npz` of token embeddings + SQLite catalog mapping `(chunk_id, file_path, line_range, heading_path, mtime, content_hash)`. Per-document files keep incremental rebuild cheap — only re-encode files whose `content_hash` changed since last index. Excluded by design: `handoffs/archived/*.md` (archived state is misleading by design and pollutes retrieval signal).

**Reused plumbing from `colbert-reranker-web-research.md`**: GTE-ModernColBERT-v1 ONNX model (already on disk at `/mnt/raid0/llm/models/gte-moderncolbert-v1-onnx/`), `onnxruntime` in the orchestrator venv, MaxSim + per-token 128-dim embeddings, EPYC latency measured 180 ms / 10-snippet rerank. The K1 task extracts the encode/MaxSim layer into a shared module that both web_research reranking and internal-KB RAG import — only indexer + storage + query-CLI differ. Sibling cross-references coordinate with `colbert-reranker-web-research.md` S5.

**K7 — validation (Flywheel-template eval methodology)**: rewritten 2026-04-28 from "five hand-curated queries" to a Flywheel-derived two-protocol Python re-implementation. (1) HotpotQA-style document-recall probe over a 4,960-doc-pool-equivalent assembled from our corpora, ~50 multi-hop questions whose ground-truth evidence spans 2+ documents, measure document-recall@k for k ∈ {3, 5, 10}, KB-RAG vs grep baseline. (2) LoCoMo-style multi-session probe simulating ~20 multi-session "agent investigations" (e.g., follow the v3 kernel rebase across handoffs over 4 weeks). Variance band: ~1 pp run-to-run from LLM non-determinism is the noise floor — any cross-config delta under ~2 pp is within noise.

**K8 — wikilink learning-loop scorer (deferred)**: Flywheel's auto-wikilink suggestion uses an accept/reject feedback loop that updates a graph-edge scorer over time (alias + co-occurrence + graph + semantic context). Adapt as a wiki-cross-reference quality signal for the existing `wiki/INDEX.md` compilation pipeline. Deferred until K1–K7 ships and a measured wiki-cross-link gap emerges.

## Flywheel as Methodology Source (intake-492, credibility 3)

[Flywheel](https://github.com/velvetmonkey/flywheel-memory) (Apache-2.0) is a local-first MCP memory layer for AI agents over Obsidian/Markdown vaults. Its primary value to EPYC is the **eval methodology**, not the runtime. The runtime is Node/MCP/Obsidian-coupled — `demos/hotpotqa/` and `demos/locomo/` ship as demo directories tightly bound to the harness and require Python re-implementation, not lift-and-shift. The methodology IS portable: corpus-pool sizing (4,960-doc HotpotQA-derived pool), multi-session evidence-recall protocol (LoCoMo 695-question / 272-session split), variance band (~1 pp from LLM non-determinism).

Credibility scored 3 (out of 6) per `feedback_credibility_from_source_not_readme.md` discipline — engineering-rigor signals (1,092 commits, 3,292 tests across 185 files, 385 releases, dual-OS dual-Node CI matrix) justify upgrade above 2; capped at 3 because no peer review, no independent third-party replication, and contributor graph not confirmed (single-author independent project).

Self-reported headline numbers from Flywheel's README (HotpotQA 90.0% doc recall on a 4,960-doc pool, LoCoMo 81.9% evidence recall over 695 questions, LoCoMo unit retrieval 84.8% R@5) carry an explicit "directional, not apples-to-apples" caveat from the project README itself. The 4,960-doc pool is sui generis — neither standard HotpotQA-distractor (10 docs) nor fullwiki — so cross-paper comparison is methodologically not direct. Capture this explicitly when reporting numbers.

**Portable patterns separate from the eval methodology**:
- Hash-before-write + single-step undo log as a portable abstract write contract (Node/Obsidian implementation NOT lift-and-shift; the contract itself is a Python-friendly design pattern). Captured in `meta-harness-optimization.md` as a design note.
- Token-budgeted memory brief assembly with confidence decay — Flywheel's `memory(action=brief)` is correctly framed as a *read-side* token-budgeted assembler over already-persisted vault content, NOT a "promote to persistent memory" action. The persistence happens via separate write tools.
- Wikilink learning-loop scorer (see K8 above).

## Wiki Compilation Governance

This page itself is a product of the `project-wiki` skill compile operation (`/workspace/.claude/skills/project-wiki/SKILL.md` Operation 3). The pipeline:

1. **Source manifest scanner** (`compile_sources.py`) walks active handoffs, completed handoffs, research deep-dives, and progress logs since `.last_compile`.
2. **Cluster by taxonomy** category from `wiki/SCHEMA.md`. Categories with 3+ substantive sources get a full compiled article; fewer get stub entries.
3. **Synthesize** (this page is one such synthesis).
4. **Touch** `.last_compile` with `compile_sources.py --touch`.

Lint (`Operation 1`): orphan handoffs, stale entries (>30d ERROR, >14d WARNING), contradictory status, un-actioned intake (verdict `worth_investigating`/`new_opportunity` with no `handoffs_created` and `ingested_date` >7d old), broken cross-references. Run `python3 .claude/skills/project-wiki/scripts/lint_wiki.py` before nightshift runs and after handoff sweeps.

The `research-intake` skill is the upstream complement — it ingests new papers/repos/blogs into `research/intake_index.yaml` with cross-referencing into existing handoffs and chapter docs. Wiki compile pulls *from* intake; intake does NOT write to the wiki. This separation avoids duplicate cross-referencing logic and keeps the wiki a derived artefact.

## Active-handoff hygiene rule (2026-05-27)

The 2026-05-27 backlog hygiene pass formalized a governance rule that matters for KB integrity: **active indices are for outstanding work only**. Completed work should be archived to `handoffs/completed/` at wrap-up cadence, and index cells should be trimmed to live TODOs rather than accumulating chronology. That keeps `handoffs/active/` queryable as an action surface instead of a mixed historical dump, and it reduces drift between active indices, wrap-up reports, and compiled wiki pages.

The execution pass archived nine clearly closed aging handoffs and rewired active references to the completed copies. The important policy detail is procedural, not just structural: pruning happens **during operator-invoked wrap-up**, not ad hoc mid-session, so removals from the active tree remain reviewable in one place.

## Open Questions

- What is the document-recall baseline via grep on our actual corpus? K7 will measure this against KB-RAG top-3.
- Does SLIDERS' reconciliation pattern (provenance + rationale + metadata columns) yield governance insights useful for our wiki even if SQL-as-primary-path is not adopted? Worth investigating after KB-RAG K7 ships.
- Can Flywheel's wikilink learning-loop scorer (accept/reject feedback updates link weights) be adapted for `wiki/INDEX.md` cross-reference quality? Deferred as K8.
- What corpus scale threshold makes structured-DB alternatives (SLIDERS) viable vs ColBERT? Current rough estimate: >1M tokens; SLIDERS' headline gains are at 36M-token corpora, far above our scale.
- Should the wiki compiler eventually auto-detect handoff moves and refresh stale source paths in compiled chapters, or is manual wrap-up-time repair sufficient? Current policy is manual review during wrap-up.

## Related Categories

- [Search & Retrieval](search-retrieval.md) — ColBERT encoder, model selection, decontamination protocol, S3/S4 ONNX pipeline shared with KB-RAG K1
- [RAG Alternatives](rag-alternatives.md) — SLIDERS structured-DB+SQL architecture, GPT-4.1 hard-wiring blocker, Phase 0 falsification gate
- [Memory-Augmented Systems](memory-augmented.md) — strategy store + episodic store retrieval patterns; Flywheel's `memory(action=brief)` read-side assembler design pattern
- [Routing Intelligence](routing-intelligence.md) — KB-RAG integration into Explore-agent routing (K6 work item)

## Source References

- [`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) — ColBERT-based RAG architecture, K1–K8 work items, K7 Flywheel-template eval methodology, K8 deferred wikilink learning-loop scorer
- [`sliders-local-validation.md`](../handoffs/active/sliders-local-validation.md) — Phase 0 falsification gate for SLIDERS local-LLM viability (does NOT block KB-RAG)
- [`colbert-reranker-web-research.md`](../handoffs/active/colbert-reranker-web-research.md) — shared ONNX encoder (K1 coordinate), S5 LateOn drop-in candidate, S7 surprisal chunking proposal
- [`handoff-backlog-hygiene-audit.md`](../handoffs/active/handoff-backlog-hygiene-audit.md) — wrap-up-only active-tree pruning rule; outstanding-only index discipline and archive/dereference procedure
- [intake-453](https://huggingface.co/DataScience-UIBK/Reason-mxbai-colbert-v0-32m) Reason-mxbai-colbert-v0-32m — 32M edge-scale ColBERT, BRIGHT 19.00 (natural-language splits 20–44), Apache-2.0/CC-BY-NC-4.0 README license conflict, ONNX INT8 unvalidated, CPU-latency fallback candidate for KB-RAG K1
- [intake-492](https://github.com/velvetmonkey/flywheel-memory) Flywheel — local-first MCP memory layer (Apache-2.0); HotpotQA 90.0% doc recall on 4,960-doc sui-generis pool; LoCoMo 81.9% evidence recall on 695q; ~1 pp LLM-non-determinism variance band; credibility 3 (1,092 commits + 3,292 tests + 385 releases + dual-OS CI; capped by no peer review / no independent replication / contributor-graph unconfirmed)
- [intake-494](https://arxiv.org/abs/2604.22294) SLIDERS (Joshi/Shethia/Dao/Lam, Stanford OVAL/Genie) — code released at `github.com/stanford-oval/sliders` (MIT, also on PyPI as `sliders-genie`); credibility 4; +6.6 pp avg over GPT-4.1 on FinanceBench / Loong / Oolong existing benchmarks; +~19 pp WikiCeleb100 (3.9M tokens); +~32 pp (abstract) / +~50 pp (repo README) FinQ100 (36M tokens, SEC 10-Q derived) — unresolved discrepancy

## Unified trace / memory service (2026-05-06)

Read-only SQLite query layer over the three fragmented audit/trace formats already written by existing infra:

- `logs/agent_audit.log` (~2700 lines, dual JSON + legacy text format — JSON for recent sessions, `[ts] CAT: msg | k=v` for older)
- `progress/YYYY-MM/*.md` (manual session summaries; sibling `.jsonl` when present for granular events)
- `epyc-orchestrator/orchestration/autopilot_journal.{tsv,jsonl}` + `autopilot_state.json` (per-trial autopilot detail)

Source files keep their existing writers; the new layer at `epyc-orchestrator/src/trace/` is purely additive. Schema: `event(ts_utc, source, source_path, source_line, session_id, trial_id, role, category, status, summary, detail_json, redacted)` with FTS5 virtual tables on `summary + detail_json`. Dedup key is `(source_path, source_line)` — append-only semantics mirror the source files; idempotent re-ingest is a no-op.

**No-op-when-absent design** (T3): autopilot files don't exist on every host (fresh checkouts, hosts that haven't run autopilot). The parser emits a single `source_unavailable` event per missing file rather than silently skipping. Schema still anticipates the columns so when files appear, ingest works without re-migration.

**PII coverage gap (documented)**: trace ingest reads `agent_audit.log` which may contain shape-realistic credential fragments. The PII pre-commit hook (Wave A) only scans staged git changes. The trace SQLite DB lives in `data/trace/` (gitignored, so not committed) but is outside the hook gate by design. The schema includes a `redacted` column for a future redaction pass.

**Live ingest (2026-05-06)**: 3477 events ingested (2214 agent_audit + 1260 progress + 3 autopilot source_unavailable markers) in <1s; idempotent re-ingest skipped 3477/3477. CLI: `python -m src.trace.cli {ingest,query,stats}` with date-range, session_id, trial_id, role, category, status, source filters + FTS5 text search.

Sources: [`handoffs/active/unified-trace-memory-service.md`](../handoffs/active/unified-trace-memory-service.md), `epyc-orchestrator/src/trace/`.

## PII / secret hygiene pre-commit hook (2026-05-06)

Regex-only pre-commit hook scanning staged git blobs (NOT working tree, so `git add -p` partial stages are caught) for accidentally-committed secrets and account-number-shaped strings. Installed at `.git/hooks/pre-commit` across the three EPYC repos via exec wrappers pointing to a single canonical `scripts/hooks/pii_precommit.sh` in epyc-root.

15 secret patterns: AWS access keys (AKIA / ASIA), AWS secret keys, GitHub PATs (classic + fine-grained), GitHub server / OAuth / user tokens, Slack `xox[baprs]-`, PEM private-key blocks (RSA/DSA/EC/OPENSSH/PGP/ENCRYPTED), generic `sk-`, Anthropic `sk-ant-api03-`, Google `AIza`, GitLab `glpat-`, JWTs. One account_number pattern: 12-19 digit runs, with disambiguation against (a) phone numbers, (b) Unix-epoch timestamps, (c) bracket-prefixed log timestamps, (d) log-severity lines, (e) decimal floats, (f) YAML config tuning lines.

**Three real bash bugs caught during development**: (1) `${entry%%|*}` truncated regexes containing `|` (PEM alternation) — switched to tab-separated entries via `$'\t'`. (2) `set -e` + sourcing `agent_log.sh` killed the hook silently — removed the optional telemetry source for zero-dependency operation. (3) **Decimal-float false-positive caught mid-integration** when committing `model_registry.yaml` — values like `temperature: 0.0736042256959058` (15 digits after `.`) triggered the account_number rule. Added `is_decimal_float_line()` disambiguator.

Allow-list: `research/fixtures/pii_*`, `.gitignore`, the hook itself. Bypass via `git commit --no-verify` is intentionally available; document the reason if used. Smoke fixture: 40 examples (19 TPs across 7 secret types + 4 account_number types, 21 negatives covering phones / timestamps / log lines / version tags / hex hashes / decimal floats).

Sources: [`handoffs/active/privacy-hygiene-precommit-hooks.md`](../handoffs/active/privacy-hygiene-precommit-hooks.md), `scripts/hooks/pii_precommit.sh`, `research/fixtures/pii_hygiene_eval.jsonl`.
