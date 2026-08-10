# Knowledge Management

**Category**: `knowledge_management`
**Confidence**: inferred
**Last compiled**: 2026-08-09
**Sources**: 30 documents

## Summary

Knowledge management in EPYC encompasses two complementary architectures: **internal KB-RAG** (ColBERT-based retrieval over the project's markdown knowledge bases) and **structured-DB alternatives** (SQL-based extraction-and-reasoning for long-document aggregation, tracked separately under `rag-alternatives.md`). Both replace keyword-only retrieval with semantic understanding, but via orthogonal mechanisms — retrieval-then-rerank vs persistent-schema SQL. This page documents the KB-RAG architecture, the Flywheel-derived evaluation methodology adopted for K7, and the wiki/governance pipeline that compiles handoffs and research notes into curated wiki articles.

The core insight from the 2026-04-28 intake update is that *the right architecture depends on corpus scale*. At our scale (24 wiki articles + ~70 active handoffs + ~30 research/deep-dive notes + daily progress logs ≈ 4–5K markdown chunks after heading-aware split), ColBERT-based retrieval over a per-document `.npz` + SQLite catalog is the appropriate primary path. The structured-DB SLIDERS architecture is gated behind a Phase 0 falsification experiment (`sliders-local-validation.md`) and is positioned as an alternative architecture for orders-of-magnitude-larger corpora, NOT an upgrade lane on the ColBERT path.

A third architectural pattern — **persistent compiled wikis** — is itself a knowledge-management approach. This very wiki is an instance: knowledge is pre-compiled by the `project-wiki` skill from handoffs/research/progress logs into curated topic articles, trading per-query synthesis latency for curation burden and staleness risk. EPYC uses a hybrid: `project-wiki` for stable / cross-cutting topics, KB-RAG for dense ad-hoc cross-referencing during Explore-agent runs.

The 2026-05-27 handoff-index audit sharpened the governance side of that architecture: indices are executable coordination surfaces, not passive navigation pages. A coverage check now treats every non-index active handoff as requiring an owning index or top-level tracking entry, and the blocked index is kept as a live unblock queue rather than a historical graveyard. The latest audit closed the active coverage invariant at 84/84 active non-index handoffs linked, 0 missing index links, and 0 broken relative links across active/blocked/README surfaces.

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

1. **Source manifest scanner** (`compile_sources.py`) walks active handoffs, completed handoffs, research deep-dives, and progress logs since `.last_compile`. The scanner now has an explicit `project-wiki-source-manifest` v1 contract: `--full --write-manifest` persists `wiki/source_manifest.json`, `--check-manifest` reports added/changed/removed source drift against current content hashes, and `--changed-since-manifest` emits the added/changed subset that a future KB-RAG `update_files(...)` adapter can consume.
2. **Cluster by taxonomy** category from `wiki/SCHEMA.md`. Categories with 3+ substantive sources get a full compiled article; fewer get stub entries.
3. **Synthesize** (this page is one such synthesis).
4. **Touch** `.last_compile` with `compile_sources.py --touch`.

Lint (`Operation 1`): orphan handoffs, stale entries (>30d ERROR, >14d WARNING), contradictory status, un-actioned intake (verdict `worth_investigating`/`new_opportunity` with no `handoffs_created` and `ingested_date` >7d old), broken cross-references. Run `python3 .claude/skills/project-wiki/scripts/lint_wiki.py` before nightshift runs and after handoff sweeps.

The `research-intake` skill is the upstream complement — it ingests new papers/repos/blogs into `research/intake_index.yaml` with cross-referencing into existing handoffs and chapter docs. Wiki compile pulls *from* intake; intake does NOT write to the wiki. This separation avoids duplicate cross-referencing logic and keeps the wiki a derived artefact.

## Key Findings

### Dashboard brief hygiene (2026-07-08)

- **Optimization-brief churn now distinguishes three classes instead of collapsing them into one noisy “ruled out” bucket.** The dashboard brief keeps live critic fences in the main ruled-out list, but it now separates journal-derived malformed-proposal churn from exogenous `bug_corrupted_by` trial rows and surfaces stale critic fences in a dedicated bucket when the rejected signature later appears on a corrupted trial. That preserves the active rejection ledger while preventing crash/reload noise from masquerading as planner health. Sources: [`scripts/autopilot/optimization_brief.py`](../epyc-orchestrator/scripts/autopilot/optimization_brief.py), [`src/api/routes/dashboard.html`](../epyc-orchestrator/src/api/routes/dashboard.html), [`loops-and-dashboards-audit-2026-07-05.md`](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md), [`progress 2026-07-08`](../progress/2026-07/2026-07-08.md).

### Append-Only Evidence Freshness (2026-07-08)

The current wrap-up cycle tightened a pattern the wiki already depends on: durable records should be **append-only plus supersession-aware**, while the dashboard should only treat a panel as current when the process behind it is still the same process that wrote the tap data. AutoPilot's contaminated seed-batch trials were quarantined in-place with append-only supersession rather than deleted, preserving provenance for later audit while keeping the bad rows out of planner evidence. The dashboard side now carries freshness metadata (`planner_tap_mtime_s`, `planner_tap_precedes_autopilot_start`) so a stale tap file can be labeled historical instead of being mistaken for live planner output. Sources: [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md), [loops-and-dashboards-audit-2026-07-05.md](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md), [frontier-f2-self-running-lab.md](../handoffs/active/frontier-f2-self-running-lab.md), [master-handoff-index.md](../handoffs/active/master-handoff-index.md), [progress 2026-07-08](../progress/2026-07/2026-07-08.md).

This is the same producer/consumer discipline the wiki already uses: operational logs and handoffs stay primary, compiled pages remain derived, and stale-but-useful history is kept readable without letting it re-enter the active decision path.

## OKF Conformance Adoption (2026-06-20, intake-710/711)

The Open Knowledge Format (OKF v0.1, Google Cloud) is a vendor-neutral spec that formalizes the "LLM-wiki" pattern — a knowledge bundle is a directory of markdown files with YAML frontmatter, one concept per file, file path as concept identity, concepts cross-linked via plain markdown links to form a graph. Its mandatory schema is deliberately minimal (exactly one required frontmatter field, `type`), with conventional `index.md` (progressive disclosure) and `log.md` (newest-first change history) reserved filenames, conventional `# Schema` / `# Examples` / `# Citations` headings, and a producer/consumer separation where producers MAY add arbitrary keys and consumers MUST preserve unknown fields. OKF is a FORMAT, not a platform — producible without SDKs and consumable without integrations. Confidence: external (vendor blog + v0.1 spec, no empirical claims, credibility null); verdict `adopt_patterns` not `adopt_component`, because Google's reference enrichment agent and Knowledge Catalog ingest are BigQuery/cloud-coupled and have no self-hosted EPYC analog.

The load-bearing intake finding is **convergence, not novelty**: 5 of OKF's 6 conventions were already satisfied by existing EPYC infrastructure. The deep-dive (intake-710/711) verified this rather than asserting it, and only two genuinely-new conventions were adopted — both now codified in [`wiki/SCHEMA.md` ## Conformance](SCHEMA.md):

1. **Schema-version stamp** — the wiki taxonomy now declares `schema_version: "1.0"` (OKF's `okf_version` analog), so parallel agents and cross-repo consumers can detect backward-incompatible drift in the category set, alias map, or conformance contract.
2. **Codified permissive-consumption contract** — consumers of intake entries MUST preserve unknown/extra keys and MUST NOT reject an entry for carrying fields beyond the required set. This was already the de-facto behavior of `validate_intake.py` (it flags only MISSING required fields and invalid enums); the Conformance section makes it an *intentional* contract, so any future validator change that rejects entries on extra/unknown fields is a conformance break that must be rejected in review. This adoption is **verified** (the behavior exists; the section pins it).

The four conventions deliberately **rejected as already-covered** (confidence: verified): reserved `index.md` (we have `wiki/INDEX.md` as a progressive-disclosure index); per-bundle `log.md` change history (we use per-file dated "Research Intake Update" sections, finer per-file granularity); the `# Schema` / `# Examples` / `# Citations` heading renames (our Summary / Key-Findings / Source-References headings are equivalent in role); and a bespoke HTML force-directed graph visualizer (GitNexus `wiki` / `cypher` already cover symbol-and-relationship graph visualization). This is a conventions adoption, not a tooling import; OKF's enrichment agent is out of scope.

## Governance skill backlog (2026-06-05)

Three active stubs extend the knowledge-management surface beyond retrieval: AutoWiki-style incremental KB generation, repo-readiness scoring, and security-review skill design. The shared pattern is that these are governance tools first: they should emit reviewable artifacts and explicit contracts before they become autonomous writers over handoffs, wiki pages, or code. For wiki/RAG work specifically, this preserves the current source-of-truth layering: intake and handoffs remain primary records, wiki pages are compiled derivatives, and readiness/security outputs are evidence attached to the relevant handoff rather than hidden state.

Sources: [autowiki-incremental-kb-generator.md](../handoffs/completed/autowiki-incremental-kb-generator.md), [repo-readiness-scorer.md](../handoffs/active/repo-readiness-scorer.md), [security-review-skill.md](../handoffs/active/security-review-skill.md).

## Active-handoff hygiene rule (2026-05-27)

The 2026-05-27 backlog hygiene pass formalized a governance rule that matters for KB integrity: **active indices are for outstanding work only**. Completed work should be archived to `handoffs/completed/` at wrap-up cadence, and index cells should be trimmed to live TODOs rather than accumulating chronology. That keeps `handoffs/active/` queryable as an action surface instead of a mixed historical dump, and it reduces drift between active indices, wrap-up reports, and compiled wiki pages.

The execution pass archived nine clearly closed aging handoffs and rewired active references to the completed copies. The important policy detail is procedural, not just structural: pruning happens **during operator-invoked wrap-up**, not ad hoc mid-session, so removals from the active tree remain reviewable in one place.

## Handoff index coverage invariant (2026-05-27 late)

The follow-on audit after the AR-3 tracking gap turned the hygiene rule into a measurable invariant: every active non-index handoff must be linked by `handoffs/README.md`, `master-handoff-index.md`, a domain index, or the blocked index. The audit found and fixed missing/stale tracking for AR-3 restart work, blocked routing-model retraining after episodic-memory reset, Engram conditional memory, ERNIE local image generation, and several completed-reference links.

Six completed handoffs were moved from `active/` to `completed/` during the same pass: MoE dynamic expert selection, CPU22 hybrid spillover design, wdata-aware MUL_MAT coalescing design, CPU4 deferred avenues, Qwen3.6 benchmark fixes, and the SearXNG bash web-search bridge. The active tree now has 84 non-index active handoffs and 7 active coordination indices; validation reported 84/84 linked, 0 unlinked, 0 missing index links, 0 broken active/blocked/README relative links, and 0 stale handoffs over the 30-day freshness threshold.

## Active/completed twin compaction (2026-05-28)

The next governance refinement is for partially complete handoffs whose live task is buried under validated history. The wrap-up routine now uses active/completed twins instead of all-or-nothing archival: the active handoff keeps current status, next actions, blockers, gates, key files, and reporting instructions, while completed or superseded detail moves to a sibling under `handoffs/completed/` or `handoffs/archived/`. Master and domain indices continue to point at the active handoff only.

The first compaction pass created or refreshed 11 completed ledgers: Lightning Attention, integration-test coverage, REPL turn efficiency, TriAttention/KV selection, context folding, intra-process tensor parallel decode, meta-harness optimization, BEP/DCP harness, dynamic stack concurrency, large-MoE expert parallelism, and routing intelligence. Each active twin now contains a `Completed Scope` table and each historical sibling points back to `../active/<handoff>.md`. Validation after the pass reported 0 stale/aging handoffs, 0 missing active-index references, and 0 missing reciprocal ledger links.

The load-bearing rule is qualitative: line count is only a prompt to inspect. Compact only when the first screen of the active handoff no longer answers "what do I do next?" Large active handoffs whose open work is itself large should stay whole. For partial compaction, create or extend the sibling and edit the active file in place; reserve `git mv` for fully complete handoffs. Source: [`handoff-backlog-hygiene-audit.md`](../handoffs/completed/handoff-backlog-hygiene-audit.md), [`progress/2026-05/2026-05-28.md`](../progress/2026-05/2026-05-28.md), [`wrap-up.md`](../.claude/commands/wrap-up.md).

The 2026-06-15 wrap-up hygiene pass confirmed that a no-op compaction is an acceptable outcome when completed-history passages are still intertwined with live next actions, blockers, or reporting instructions. A later N11/N11a correction on the same day clarified the boundary: when commit-by-commit chronology starts burying the pickup contract, preserve that history in completed/archived siblings and compact the active handoff and master-index row back to current state plus next actions. Source: [`progress/2026-06/2026-06-15.md`](../progress/2026-06/2026-06-15.md).

The 2026-06-19 manual wrap-up rerun confirmed the same evidence-based pruning rule: a full audit can legitimately archive or compact nothing when active indices already expose the pickup state. A later same-day wrap-up applied that rule to the routing domain index after completed sidecar notes and old checked-off task narration had again buried the dispatch surface. `routing-and-optimization-index.md` is now a live queue plus dependency graph; the pruning disposition is preserved in [`routing-and-optimization-index-history-through-2026-06-19.md`](../handoffs/archived/routing-and-optimization-index-history-through-2026-06-19.md), with exact pre-prune recovery available from root commit `d3484cf`. The handoff freshness check is a hard stale gate, not a reason to reset mtimes. Operational detail: `scripts/validate/check_handoff_freshness.sh` accepts positional numeric thresholds (`WARN_DAYS`, `STALE_DAYS`) despite usage text mentioning long options; the default run reported `0 stale (>30d)` and `23 aging (>14d)`. Source: [`progress/2026-06/2026-06-19.md`](../progress/2026-06/2026-06-19.md).

The final same-day wrap-up applied the same rule to the acceleration dispatch surfaces. `cpu-inference-optimization-index.md` and `inference-acceleration-index.md` now stay live-work-only, while the pre-compaction benchmark narratives live in dated archive siblings. The important governance distinction is that high-fanout indices can be aggressively shortened only when archive recovery is explicit and the active replacement keeps queues, gates, dependency order, and reporting instructions intact. Source: [`progress/2026-06/2026-06-19.md`](../progress/2026-06/2026-06-19.md).

A subsequent same-day wrap-up applied the rule to the two remaining large domain indices. `user-facing-harness-index.md` and `research-evaluation-index.md` now function as 63-line dispatch surfaces rather than chronological ledgers. Their pre-compaction bodies are preserved in [`user-facing-harness-index-history-through-2026-06-19.md`](../handoffs/archived/user-facing-harness-index-history-through-2026-06-19.md) and [`research-evaluation-index-history-through-2026-06-19.md`](../handoffs/archived/research-evaluation-index-history-through-2026-06-19.md). This reinforces the active-index invariant: current queue, gates, dependencies, key files, and reporting rules stay active; completed checklist detail and research-intake narration move to dated history ledgers. Source: [`progress/2026-06/2026-06-19.md`](../progress/2026-06/2026-06-19.md).

The final pass compacted `pipeline-integration-index.md` under the same rule. The active file now routes vision, image generation, PDF extraction, Lean proving, TTS, doc-to-LoRA, and KB-RAG work by current gate, while historical checklist detail lives in [`pipeline-integration-index-history-through-2026-06-19.md`](../handoffs/archived/pipeline-integration-index-history-through-2026-06-19.md). Source: [`progress/2026-06/2026-06-19.md`](../progress/2026-06/2026-06-19.md).

## K-RAG Validation Update (2026-06-19)

K1-K6 are no longer just architecture notes: the internal KB-RAG indexer/query path has shipped, and K7 now has both a seed harness and a certification pool. The fresh K7 build indexed 577 files into 18,010 chunks with about 1.2 GiB of embeddings. On the 20-case seed suite, the best recall@10 config was `recency_w0.1_s90` at 0.6417 overall, with no missed-all-evidence cases. Rerank settings improved recall@3 and first-evidence rank but lost recall@10 and introduced missed-all-evidence failures.

The seed result is calibration only. The decision pool is now a 70-case evidence-grounded suite: 50 HotpotQA-style and 20 LoCoMo-style cases, with JSON/count/evidence validation passed. The certification sweep is complete: 420 rows passed artifact checks, `recency_w0.3_s90` was the zero-miss candidate with recall@10 `0.6167`, and `recency_w0.1_s90_rerank_w0.3` had the best aggregate recall@10 `0.6298` while missing three all-evidence cases. Use the zero-miss candidate for safety-sensitive retrieval defaults unless a later certification explicitly trades that property away.

Source: [internal-kb-rag.md](../handoffs/active/internal-kb-rag.md).

## Certified KB-RAG Consumer and Parked Two-Pass Retrieval (2026-06-13 / 2026-06-20)

KB-RAG is no longer pre-deployment: K1–K7 are **CERTIFIED 2026-06-13** and shipped under `epyc-orchestrator/src/retrieval/` (additive `colbert_encoder.py`, `markdown_chunker.py`, `kb_rag.py`), plus a query CLI, the `post_commit_kb_rag_update.sh` hook, the `kb-search` Skill (the production Explore-subagent integration path — the MCP-tool variant was never needed), and unit tests. Beyond the certified single-pass MaxSim retrieval (with K9 cross-encoder rerank and K10 Gaussian recency as measured-but-conditional blends, and K11 FTS5 lexical landed default-off, measure-first), there is one **parked retrieval-policy idea** worth tracking so it is not re-discovered: a **self-correcting two-pass retrieval** pattern (from agent-oss, intake-610) — when a downstream consumer signals "evidence incomplete," emit gap-queries and re-retrieve at a lower MaxSim threshold before answering. It stays deferred behind a prerequisite that does not exist yet: a consumer (Explore subagent / orchestrator) that actually emits the incompleteness signal.

A 2026-06-20 research intake added a **second independent instance** of that same family: **MRAgent** ([intake-698], "Memory is Reconstructed, Not Retrieved," arXiv:2606.06036) uses a Cue-Tag-Content associative graph with active reconstruction — LLM reasoning interleaved with retrieval, iteratively exploring the graph and *pruning* retrieval paths on intermediate evidence rather than fetching a flat top-k. It approaches the same evidence-conditioned problem from the pruning side, where agent-oss approaches it from the re-retrieval side. It is logged as a **comparative datapoint against the parked note, not a new workstream** — same deferral, no new K-track, no plan delta. Its numbers are observations, not decision-gating: token cost ~118k vs 245k–3.3M for baselines (the genuinely transferable idea, given our token-budget constraints, is the *token-cost discipline* of evidence-pruned traversal), but it is cloud-LLM-bound (Gemini-2.5-Flash / Claude-Sonnet-4.5) with no CPU/local results and it **loses to Mem0 on LoCoMo multi-hop F1 (43.69 vs 45.17)** — so the accuracy headline does not carry. Explicitly NOT routed to `delta-mem-reproduction` (whose open gates are GPU-bound accuracy reproduction, not retrieval token-cost).

Source: [internal-kb-rag.md](../handoffs/active/internal-kb-rag.md).

## Governance Tooling Update (2026-06-13)

The repo-readiness scorer makes knowledge-management maturity measurable. Its v1 deterministic criteria put the portfolio at Documented (L2), with root at Optimized (L4) and each child repo at Documented (L2). The useful output is the failing-criteria queue: standardized security automation, dev environment enforcement, generated docs, health automation, prioritized task discovery, and autonomous security review. Treat this as a governance backlog generator, not a subjective quality grade.

Source: [repo-readiness-scorer.md](../handoffs/active/repo-readiness-scorer.md).

## 2026-06-19 Update — K7 Certified, Wiki Compile Refreshed

- **K7 is certified for a zero-miss retrieval candidate.** The full 70-case pool produced 420 valid rows; the aggregate winner has slightly higher recall@10, but the zero-miss candidate is the safer default for evidence-seeking workflows because it avoided all-evidence misses. Source: [internal-kb-rag.md](../handoffs/active/internal-kb-rag.md).
- **Wiki compilation remains a derived artifact pipeline with wrap-up discipline.** Active handoffs and indices should stay live-only while completed detail moves to completed/archived twins; the wiki is updated from those sources, not edited as the primary record. Source: [handoff-backlog-hygiene-audit.md](../handoffs/completed/handoff-backlog-hygiene-audit.md).
- **Repo-readiness scoring is a backlog generator, not a quality certificate.** The deterministic scorer is useful because it turns governance gaps into concrete remediation work, but it does not certify the artifact quality behind those gaps. Source: [repo-readiness-scorer.md](../handoffs/active/repo-readiness-scorer.md).

## 2026-06-20 Update — OKF Conventions Adopted, KB-RAG Consumer Certified

- **OKF validates our hand-built KB shape as convergent, not idiosyncratic.** An external vendor-neutral spec (OKF v0.1) independently arrives at markdown+frontmatter knowledge atoms, file-path-as-identity, a markdown-link graph, a progressive-disclosure index, and change history — 5 of its 6 conventions were already present in our KB. The finding is design-risk reduction, not a migration mandate. Source: [intake-710], [intake-711].
- **Only two OKF conventions were genuinely new and both were adopted** (verified): a `schema_version` stamp and a codified permissive-consumption contract, now in `wiki/SCHEMA.md` ## Conformance. The other four were rejected because existing infrastructure (INDEX.md, per-file dated histories, equivalent headings, GitNexus graph viz) already provides the capability — adopting them would be redundant. Source: [`wiki/SCHEMA.md`](SCHEMA.md), [intake-710].
- **Permissive consumption is now a contract, not an accident.** `validate_intake.py` already ignored extra keys; pinning that as an intentional conformance contract means a future validator change that rejects entries on unknown fields is a reviewable regression, which protects forward-compatible schema evolution across parallel agents. Source: [`wiki/SCHEMA.md`](SCHEMA.md).
- **The certified KB-RAG is single-pass; smarter retrieval policy is deliberately parked, not abandoned.** Self-correcting two-pass retrieval (agent-oss / intake-610) and evidence-pruned graph traversal (MRAgent / intake-698) are the same deferred pattern from two angles, both blocked on the absence of a consumer that emits an incompleteness signal. The transferable lever is token-cost discipline, not the cloud-LLM accuracy headlines. Source: [internal-kb-rag.md].
- **Self-hosted constraint governs OKF adoption.** OKF's reference enrichment agent and Knowledge Catalog ingest are BigQuery/cloud-coupled, so the verdict is `adopt_patterns` (conventions) not `adopt_component` (tooling) — the schema is portable, the implementation is not. Source: [intake-710], [intake-711].

## 2026-06-22 Update — Continuity Backup, Single-Source Stack Governance, Repo-Readiness Scorecard

- **F4 continuity-backup exposed an unresolved existential single-point-of-failure: the entire working set is on one RAID0 device with no off-array copy yet.** Inventory + tiered policy (T0/T1/T2 `MANIFEST.yaml`) and a git-state alerting hook landed; `backup_critical.sh` refuses same-device and overlayfs targets; restore tooling (`verify_restore.sh`, `check_latest_backup.sh`) landed 2026-06-21. But both `/workspace` and `/mnt/raid0/llm` sit on `/dev/md127` (RAID0 striping, no redundancy), and no real off-host/off-array backup has been created and no snapshot restore has been validated. The existential risk stands until an off-array target is approved. Source: [frontier-f4-continuity-backup.md](../handoffs/active/frontier-f4-continuity-backup.md).
- **Live model/role/serving facts now flow from a single generated source, enforced by stack-change guards across 13 consumer surfaces (27 rules).** Generated model descriptors, stack priors, and operator summaries are authoritative; runtime attestation, q_scorer priors, production launch, AutoPilot preflight, and direct benchmark runtime all gate on them. High-risk consumer migrations completed (admission slot limits, benchmark seeding topology, `/v1/models` ordering, vision-serving role set, WorkerPool primary-port binding, chat-routing fallback candidates, escalation-prewarm endpoint resolution, `launch_maps` auxiliary-role tail). The standardized pipeline is finalized: `stack_change_pipeline.py check --run-promotion-gate` is the canonical command (174 tests pass), guard baseline clean, all surfaces ownership-labeled, no active waivers, W4 swap-CI covers frontdoor/worker/vision/long-context-ingest swaps. Both pipelines are inference-free governance and require no live model runs. Sources: [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md), [standardized-stack-update-pipeline-finalization.md](../handoffs/active/standardized-stack-update-pipeline-finalization.md).
- **A deterministic repo-readiness maturity scorecard (5 levels, 9 pillars, 45 criteria; adapted from Factory.ai) is deployed advisory-only; the portfolio sits at Level 2 (Documented).** epyc-root is Level 4 (Optimized, 77.8% toward L5); epyc-orchestrator/inference-research/llama are Level 2 (next gate L3, 33-56% coverage). Lowest portfolio criteria: L3 security-automation and standard-dev-env (25% coverage), L4 generated-docs/health-automation, L5 auto-eval-gates/self-optimizing-loop. The 49-item remediation queue (13 P0 blockers) is advisory — items require normal handoff ownership and GitNexus impact gates. A passive AutoPilot pickup JSON (2026-06-21, `mode=advisory_only`, `authority_gate=false`) feeds planning context only; the scorer stays deterministic with no LLM judgment per `feedback_observe_before_diagnosing`. Sources: [repo-readiness-scorer.md](../handoffs/active/repo-readiness-scorer.md), [progress repo-readiness-2026-06-21](../progress/2026-06/repo-readiness-2026-06-21.md), [progress repo-readiness-remediation-2026-06-21](../progress/2026-06/repo-readiness-remediation-2026-06-21.md).

## 2026-07-02 Update — Two-Batch Research Intake, Clean-Window Compile Rule, Dedup Discipline

Two operator-directed `/research-intake` batches ran on 2026-07-02 and grew `research/intake_index.yaml` past **772 entries** (intake-732…772). Both closed clean under `validate_intake.py` (exit 0). The sessions are knowledge-management-relevant less for their model content than for the intake→distill→compile governance discipline they exercised, which is the upstream feeder of this wiki.

- **Clean-window wiki-compile rule (new governance constraint).** A full wiki compile was deliberately **deferred** at the end of the distillation session even though `compile_sources.py` reported new sources (13 handoff-active + 4 progress): a parallel session was actively writing that day's progress and handoffs, so compiling then would have ingested in-flight, uncommitted work. The rule generalizes the existing "wiki is a derived artifact" separation — compile only against a settled corpus, not while a concurrent writer is mid-edit. This is consistent with the parallel-agent staged-files hazard already recorded in operator memory. Source: [distillation progress log](../progress/2026-07/2026-07-02-research-intake-distillation.md).
- **Intake dedup is a first-class integrity step, not a formality.** The larger batch deduped against a 728-entry index and caught 4 already-indexed sources (MRAgent `2606.06036`→intake-698, Autodata→intake-731, liteparse→intake-647, Fugu→intake-728) reported-but-not-re-added, plus **3 arXiv-ID mismatches** (`2606.23595` labeled a local-inference guide actually resolves to SPIRAL; `2606.21228` is Fugu). Trusting the operator's label over the resolved arXiv target would have created cross-referenced entries pointing at the wrong paper. Source: [distillation progress log](../progress/2026-07/2026-07-02-research-intake-distillation.md).
- **Primary-key collisions are handled explicitly at ingest.** Within-batch dedup merged a paper+blog pair describing the same work into one entry (intake-754), but kept a paper+its-weights pair as two entries (intake-751 paper, intake-752 model) with `arxiv_id: null` on the model row to avoid an `arxiv_id` primary-key collision. This is the permissive-consumption / schema-hygiene contract in practice: the schema tolerates the extra weights entry without forcing a synthetic key. Source: [intake progress log](../progress/2026-07/2026-07-02-research-intake.md).
- **Never-dismiss produces URL-less index rows, not silent drops.** An orphaned survey whose operator-supplied arXiv ID was a mismatch was still indexed URL-less as intake-750, flagged for a corrected URL, per the CLAUDE.md "never dismiss a source" rule — the intake index records the gap rather than discarding the source. Source: [intake progress log](../progress/2026-07/2026-07-02-research-intake.md).
- **Distillation writes to handoffs, provenance flows back to intake — the wiki is never the intake write target.** The distillation phase mapped each new insight to its owning handoff with exact line anchors (14 edits across 9 handoffs), all operator-approved, and populated the `handoffs_updated` provenance field for 17 entries. This reaffirms the producer/consumer layering: intake and handoffs are primary records, the wiki compiles *from* them. The fan-out itself used many parallel per-URL sub-agents while the main agent performed all index/handoff writes, keeping mutation authority centralized. Sources: [distillation progress log](../progress/2026-07/2026-07-02-research-intake-distillation.md), [intake progress log](../progress/2026-07/2026-07-02-research-intake.md).
- **A canonical autopilot self-improvement reference entered the corpus.** The Darwin Gödel Machine ([intake-772], `2505.22954`, credibility 6, `adopt_patterns`) — a self-referential agent that rewrites its own codebase and keeps an open-ended archive of all variants as stepping stones — is logged as the canonical reference for the project's own autopilot loop, echoing the "keep-all-stepping-stones vs greedy Pareto pruning" tension already surfaced in the autopilot journal/archive governance sections below. Source: [intake-772](https://arxiv.org/abs/2505.22954).

## Open Questions

- Should the clean-window compile rule become a machine check (e.g., `compile_sources.py` refusing to compile when uncommitted changes touch any corpus root, or when a concurrent-writer lock is held), or remain an operator-judgment step as it is today?
- Should the schema-version stamp eventually be machine-enforced by `validate_intake.py` (reject artifacts whose declared `schema_version` is incompatible), or remain an advisory drift signal as it is today?
- If a consumer that emits an "evidence-incomplete" signal ever ships (Explore subagent / orchestrator), should the parked two-pass retrieval be implemented from the re-retrieval side (agent-oss style) or the evidence-pruning side (MRAgent style) — or measured both ways on our corpus before choosing?
- Does OKF's `okf_version` / cross-org interoperability framing justify ever emitting an OKF-conformant export of the wiki for external sharing, or is that purely hypothetical given the single-user self-hosted scope?
- Should the K7 zero-miss candidate become the default for Explore-agent KB retrieval, or should the higher-recall aggregate winner stay available only as an explicit exploratory mode?
- Does SLIDERS' reconciliation pattern (provenance + rationale + metadata columns) yield governance insights useful for our wiki even if SQL-as-primary-path is not adopted? Worth investigating after KB-RAG K7 ships.
- Can Flywheel's wikilink learning-loop scorer (accept/reject feedback updates link weights) be adapted for `wiki/INDEX.md` cross-reference quality? Deferred as K8.
- What corpus scale threshold makes structured-DB alternatives (SLIDERS) viable vs ColBERT? Current rough estimate: >1M tokens; SLIDERS' headline gains are at 36M-token corpora, far above our scale.
- Should the wiki compiler eventually auto-detect handoff moves and refresh stale source paths in compiled chapters, or is manual wrap-up-time repair sufficient? Current policy is manual review during wrap-up.
- Should the active-handoff coverage audit become a first-class validator alongside `check_handoff_freshness.sh`, or remain a wrap-up-time scriptlet?

## Related Categories

- [Search & Retrieval](search-retrieval.md) — ColBERT encoder, model selection, decontamination protocol, S3/S4 ONNX pipeline shared with KB-RAG K1
- [RAG Alternatives](rag-alternatives.md) — SLIDERS structured-DB+SQL architecture, GPT-4.1 hard-wiring blocker, Phase 0 falsification gate
- [Memory-Augmented Systems](memory-augmented.md) — strategy store + episodic store retrieval patterns; Flywheel's `memory(action=brief)` read-side assembler design pattern
- [Routing Intelligence](routing-intelligence.md) — KB-RAG integration into Explore-agent routing (K6 work item)

## Source References

- [`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) — ColBERT-based RAG architecture, K1–K8 work items, K7 Flywheel-template eval methodology, K8 deferred wikilink learning-loop scorer
- [`sliders-local-validation.md`](../handoffs/active/sliders-local-validation.md) — Phase 0 falsification gate for SLIDERS local-LLM viability (does NOT block KB-RAG)
- [`colbert-reranker-web-research.md`](../handoffs/active/colbert-reranker-web-research.md) — shared ONNX encoder (K1 coordinate), S5 LateOn drop-in candidate, S7 surprisal chunking proposal
- [`handoff-backlog-hygiene-audit.md`](../handoffs/completed/handoff-backlog-hygiene-audit.md) — wrap-up-only active-tree pruning rule; outstanding-only index discipline and archive/dereference procedure
- [`progress/2026-05/2026-05-28.md`](../progress/2026-05/2026-05-28.md) — active/completed twin compaction pilot, validator cleanup, and wrap-up compaction rule tightening
- [`progress/2026-06/2026-06-15.md`](../progress/2026-06/2026-06-15.md) — wrap-up hygiene no-op decision plus later N11/N11a active/archive compaction after completed chronology started burying next actions
- [`routing-and-optimization-index-history-through-2026-06-19.md`](../handoffs/archived/routing-and-optimization-index-history-through-2026-06-19.md) — routing-domain index pruning disposition and live-queue replacement policy
- [`cpu-inference-optimization-index-history-through-2026-06-19.md`](../handoffs/archived/cpu-inference-optimization-index-history-through-2026-06-19.md), [`inference-acceleration-index-history-through-2026-06-19.md`](../handoffs/archived/inference-acceleration-index-history-through-2026-06-19.md) — acceleration-domain index compaction ledgers preserving historical benchmark narrative outside active dispatch files
- [`user-facing-harness-index-history-through-2026-06-19.md`](../handoffs/archived/user-facing-harness-index-history-through-2026-06-19.md), [`research-evaluation-index-history-through-2026-06-19.md`](../handoffs/archived/research-evaluation-index-history-through-2026-06-19.md) — domain-index compaction ledgers preserving Hermes and research/eval completed checklist and research-intake chronology outside active dispatch files
- [`handoffs/README.md`](../handoffs/README.md), [`master-handoff-index.md`](../handoffs/active/master-handoff-index.md), [`BLOCKED.md`](../handoffs/blocked/BLOCKED.md) — current entry points, coverage ownership, and live blocked-work queue after the 2026-05-27 audit
- [`progress/2026-05-27.md`](../progress/2026-05/2026-05-27.md) — handoff-index audit verification metrics, six handoffs archived, and link/freshness validation results
- [intake-453](https://huggingface.co/DataScience-UIBK/Reason-mxbai-colbert-v0-32m) Reason-mxbai-colbert-v0-32m — 32M edge-scale ColBERT, BRIGHT 19.00 (natural-language splits 20–44), Apache-2.0/CC-BY-NC-4.0 README license conflict, ONNX INT8 unvalidated, CPU-latency fallback candidate for KB-RAG K1
- [intake-492](https://github.com/velvetmonkey/flywheel-memory) Flywheel — local-first MCP memory layer (Apache-2.0); HotpotQA 90.0% doc recall on 4,960-doc sui-generis pool; LoCoMo 81.9% evidence recall on 695q; ~1 pp LLM-non-determinism variance band; credibility 3 (1,092 commits + 3,292 tests + 385 releases + dual-OS CI; capped by no peer review / no independent replication / contributor-graph unconfirmed)
- [intake-494](https://arxiv.org/abs/2604.22294) SLIDERS (Joshi/Shethia/Dao/Lam, Stanford OVAL/Genie) — code released at `github.com/stanford-oval/sliders` (MIT, also on PyPI as `sliders-genie`); credibility 4; +6.6 pp avg over GPT-4.1 on FinanceBench / Loong / Oolong existing benchmarks; +~19 pp WikiCeleb100 (3.9M tokens); +~32 pp (abstract) / +~50 pp (repo README) FinQ100 (36M tokens, SEC 10-Q derived) — unresolved discrepancy
- [intake-710](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing) OKF announcement (Google Cloud blog) — formalizes the LLM-wiki pattern into a vendor-neutral v0.1 spec; verdict `adopt_patterns`, credibility null (no empirical claims); 5/6 conventions already present in our KB; enrichment agent + Knowledge Catalog are BigQuery/cloud-coupled (no EPYC analog)
- [intake-711](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) OKF reference repo (GoogleCloudPlatform/knowledge-catalog) — markdown+YAML-frontmatter knowledge atoms, one required field (`type`), permissive consumption (preserve unknown keys), reserved `index.md`/`log.md`, graph via untyped markdown links, `okf_version` forward-compat; verdict `adopt_patterns`
- [intake-698](https://arxiv.org/abs/2606.06036) MRAgent ("Memory is Reconstructed, Not Retrieved") — Cue-Tag-Content associative graph with evidence-conditioned path-pruning; comparative datapoint for the parked self-correcting two-pass retrieval note, NOT a new workstream; cloud-LLM-bound (no CPU/local), loses to Mem0 on LoCoMo multi-hop F1 (43.69 vs 45.17); transferable idea = token-cost discipline (~118k vs 245k–3.3M)
- [`wiki/SCHEMA.md`](SCHEMA.md) ## Conformance (added 2026-06-20) — `schema_version: "1.0"` stamp + codified permissive-consumption contract; the two genuinely-new OKF conventions adopted, with the four already-covered ones recorded as deliberate rejections
- [`progress/2026-07/2026-07-02-research-intake-distillation.md`](../progress/2026-07/2026-07-02-research-intake-distillation.md) — 13-source intake batch (intake-732…750) + deep-dive distillation into 9 handoffs with exact line anchors; the clean-window wiki-compile deferral rule, dedup-caught arXiv-ID mismatches, and `handoffs_updated` provenance population
- [`progress/2026-07/2026-07-02-research-intake.md`](../progress/2026-07/2026-07-02-research-intake.md) — 15-source intake batch (intake-751…772, index to 772 entries); within-batch dedup and the paper+weights `arxiv_id: null` primary-key-collision handling, URL-less orphan indexing (intake-750), and main-agent-writes fan-out governance
- [intake-772](https://arxiv.org/abs/2505.22954) Darwin Gödel Machine — self-referential self-improving coding agent with an open-ended keep-all-stepping-stones archive; credibility 6, verdict `adopt_patterns`; logged as the canonical reference for the project's own autopilot self-improvement loop

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

## Autopilot dashboard data-source rule (2026-05-28)

The `GEPA + Pareto Frontier` dashboard panel should be journal-backed, not state-cache-backed. The append-only `orchestration/autopilot_journal.jsonl` is the durable per-trial source that remains useful when autopilot is stopped; `autopilot_state.json` is operational state and can contain a stale `pareto_archive` cache if a writer path saves an older in-memory state after the archive write. The dashboard now reconstructs the current-session frontier and hypervolume from journal rows at or after `autopilot_fleet_started_at`, filters `bug_corrupted_by` rows, and falls back to `autopilot_state.json` only when journal data is unavailable.

Operationally, apparent Pareto plot staleness should be diagnosed by checking the endpoint source and payload first: `/dashboard/api/pareto` now reports `source=journal_current_session` when it is using the durable journal, plus live totals for frontier size, entry count, and hypervolume points. Source: [`2026-05-28-pareto-dashboard.md`](../progress/2026-05/2026-05-28-pareto-dashboard.md).

2026-07-03 addendum — all-era view: the endpoint gained `scope=all_eras|current` (default `current`, the decision-grade view, unchanged). All-era scope reconstructs across ALL journal shards and instrument-era boundaries, labeling every point from the append-only `orchestration/instrument_eras.yaml` registry (scopes `autopilot_speed`/`autopilot_quality`; synthetic `pre-E2` region) and applying only the codified pre-E2 ×0.5 speed deinflation — later boundaries such as the E5 v6+iqk cutover are labeled, never rescaled (MEASUREMENT.md forbids cross-era rescaling). The UI renders eras as a chronological rainbow ramp (oldest=red → current=cyan) with per-era convex-hull clouds on the scatter and shaded bands on the hypervolume timeline; the payload self-declares `scope` and tags the all-era view non-decision-grade. Source: [`2026-07-03.md`](../progress/2026-07/2026-07-03.md).

## Autopilot journal authority during empty-journal saves (2026-06-19)

The append-only journal remains the archive authority even before an archive-bearing trial exists. Empty-journal lifecycle saves should persist ordinary operational state directly and must not recreate a legacy `pareto_archive` cache through `archive.save(state)`. Compatibility save APIs can remain for explicit state-payload tests/tools, but the live AutoPilot save path should not use them as a fallback when the journal fold is unavailable.

Operationally, if a fresh or reset AutoPilot lifecycle save lacks archive-bearing journal rows, treat the missing fold as a reason to skip archive cache writes, not as permission to rehydrate state-cache authority. Source: [`progress/2026-06/2026-06-19.md`](../progress/2026-06/2026-06-19.md) (`A8 archive-save fallback retirement`) and [`handoffs/active/evidence-plane-event-sourcing-and-narrative.md`](../handoffs/active/evidence-plane-event-sourcing-and-narrative.md).

## Append-only scrub hygiene (2026-06-19)

Evidence-plane correction tools must fail closed if they would rewrite live history or derived memory stores. The retired gate-lock narrative scrubber is the concrete example: an older one-shot script could rewrite `autopilot_journal.jsonl`, generated STM, StrategyStore rows, FTS, and FAISS mirrors in place. It now exits with operator guidance to append supersession events via `scrub_journal.py` and validate with `archive_authority_report.py --strict`.

The durable rule is to keep the journal as the append-only source, express retroactive corrections as policy-versioned events, and regenerate or fold read views instead of editing mirrors directly. That rule also applies to compatibility paths: if a caller supplies a journal or explicit excluded-trial set, StrategyStore promotion helpers must require the journal-aware selector API rather than falling back to raw SQL. Frontier strategy memory follows the same pattern: AutoPilot should append the trial `JournalEntry` first, then project StrategyStore rows from that persisted row with deterministic journal-keyed IDs, so retry/restart projection cannot create duplicates or get ahead of the ledger. The follow-up audit/sync path compares those deterministic rows against the folded journal, inserts only missing safe projections, and fails closed before future writes unless semantic embeddings are available or hash fallback is explicitly allowed. Source: [`progress/2026-06/2026-06-19.md`](../progress/2026-06/2026-06-19.md) (`A8 W2 gate-lock scrubber retirement`, `A8 W6 legacy strategy quarantine fallback hardening`, `A8 W1/W6 journal-keyed frontier strategy projection`, `A8 W1/W6 strategy projection audit and sync`) and [`handoffs/active/evidence-plane-event-sourcing-and-narrative.md`](../handoffs/active/evidence-plane-event-sourcing-and-narrative.md).

## Evidence-plane handoff compaction (2026-06-19)

The active evidence-plane ledger was compacted after W4/W7 implementation history began obscuring the live dispatch gate. Completed W1-W7 chronology now lives in [`handoffs/archived/evidence-plane-ledger-and-sequential-verdicts-history-through-2026-06-19.md`](../handoffs/archived/evidence-plane-ledger-and-sequential-verdicts-history-through-2026-06-19.md), while the active handoff starts with the current readiness blocker: `57/120` trusted vectors and `5/30` seq shadow rows. This is the intended wrap-up pattern for large active handoffs: keep the active file as the next-action surface and move validated chronology to a dated sibling.

## PII / secret hygiene pre-commit hook (2026-05-06)

Regex-only pre-commit hook scanning staged git blobs (NOT working tree, so `git add -p` partial stages are caught) for accidentally-committed secrets and account-number-shaped strings. Installed at `.git/hooks/pre-commit` across the three EPYC repos via exec wrappers pointing to a single canonical `scripts/hooks/pii_precommit.sh` in epyc-root.

15 secret patterns: AWS access keys (AKIA / ASIA), AWS secret keys, GitHub PATs (classic + fine-grained), GitHub server / OAuth / user tokens, Slack `xox[baprs]-`, PEM private-key blocks (RSA/DSA/EC/OPENSSH/PGP/ENCRYPTED), generic `sk-`, Anthropic `sk-ant-api03-`, Google `AIza`, GitLab `glpat-`, JWTs. One account_number pattern: 12-19 digit runs, with disambiguation against (a) phone numbers, (b) Unix-epoch timestamps, (c) bracket-prefixed log timestamps, (d) log-severity lines, (e) decimal floats, (f) YAML config tuning lines.

**Three real bash bugs caught during development**: (1) `${entry%%|*}` truncated regexes containing `|` (PEM alternation) — switched to tab-separated entries via `$'\t'`. (2) `set -e` + sourcing `agent_log.sh` killed the hook silently — removed the optional telemetry source for zero-dependency operation. (3) **Decimal-float false-positive caught mid-integration** when committing `model_registry.yaml` — values like `temperature: 0.0736042256959058` (15 digits after `.`) triggered the account_number rule. Added `is_decimal_float_line()` disambiguator.

Allow-list: `research/fixtures/pii_*`, `.gitignore`, the hook itself. Bypass via `git commit --no-verify` is intentionally available; document the reason if used. Smoke fixture: 40 examples (19 TPs across 7 secret types + 4 account_number types, 21 negatives covering phones / timestamps / log lines / version tags / hex hashes / decimal floats).

Sources: [`handoffs/completed/privacy-hygiene-precommit-hooks.md`](../handoffs/completed/privacy-hygiene-precommit-hooks.md), `scripts/hooks/pii_precommit.sh`, `research/fixtures/pii_hygiene_eval.jsonl`.

### New (2026-07-21, derived-but-unfiled actionables: a named failure mode and its gates)

> **Review flag (project-wiki writer-evidence policy):** model-compiled, not adopted until human or measured review.

- **"Derived-but-unfiled" is a distinct knowledge-loss mode, orthogonal to un-flipped checkboxes.** An operator-prompted audit of one session's deep dives found **seven** high-ROI items — including the session's only time-sensitive one — that were fully derived in analysis prose ("measurable locally today", "cheapest experiment in the program") and then filed nowhere: no task in the owning handoff, no index row. Three recurring shapes: (1) a conclusion stated in prose but never converted to a task; (2) a fix landed while the flag/config that would make it *run* stayed off with no enable task; (3) a live idea silently discarded because a **sibling** idea was falsified. The same audit found the converse defect too: a task filed at line ~1444 of a 1,400-line handoff, in zero indices — *filed is not discoverable*. Sources: [progress 2026-07-21](../progress/2026-07/2026-07-21.md), [routing-and-optimization-index.md](../handoffs/active/routing-and-optimization-index.md), [master-handoff-index.md](../handoffs/active/master-handoff-index.md).
- **The countermeasure is a closure property enforced at four gates, not vigilance.** (1) research-intake Stage 1: every `relevance ≥ medium` entry → a proposal row with verbatim draft task lines, or an explicit decline; **no handoff/index writes in the sweep** — integration is proposed, not performed. (2) Stage 2 (operator-gated): deep dives each end in a derived-actionables ledger; the plan-mode integration proposal must resolve **every Stage-1 proposal row (dived or not) plus every ledger row** — dives correct drafts, they do not scope the plan. (3) Plan approval before any write; mid-execution additions return to the operator. (4) The wrap-up skill's derived-actionables gate backstops whatever leaked into prose anyway, in both harnesses (one real file — `.claude/commands/wrap-up.md` symlinks to `agents/commands/wrap-up.md`). At each gate a silent drop becomes a checkable defect. Sources: `.claude/skills/research-intake/SKILL.md` (2026-07-21 redesign), `agents/commands/wrap-up.md`, [progress 2026-07-21](../progress/2026-07/2026-07-21.md).


## Companion-artifact conflation in research intake (2026-07-25)

A companion **repo / weights collection / project page is a DISTINCT artifact** from the paper it
accompanies. The intake schema's dedup key is an exact `arxiv_id` or `url` match — being
*referenced in another entry's notes* is not a collision.

`intake-335` (github.com/gepa-ai/gepa) was filed 2026-04-12 as "Duplicate — the GEPA paper already
references this GitHub repo in its notes." Nobody read the codebase. Re-reading it surfaced a
shipped engine layer absent from the paper, a six-month-stale local pin, and a **live defect in
EPYC's own autopilot** that the "already integrated" label had hidden for months.

A detector (dismissive verdict + conflation language + **no** exact key collision) found **19**
such entries; 11 were re-read. Highest-cost instance: three DFlash entries filed "supplementary to
the paper" while the blocker they cite (`no llama.cpp support / no GGUF / no CPU path`) had been
**dead for five weeks** — merged upstream, forward-ported to production, artifact on disk.

**Two false alarms worth not re-deriving**: entries with `already_integrated` and no `key_claims`
are overwhelmingly `discovered_via: seed` bootstrap corpus (correct behavior, not dropped value);
and `handoffs_updated` is unreliable as an integration signal — the REAP cluster has an empty field
while `completed/reap-moe-expert-pruning.md` exists and cites it.

## Fabricated citations from summarizer agents (2026-07-25)

Two invented specifics reached the intake index from Stage-1 agent summaries and were caught only
by a later verification dive:

| Fabrication | Reality |
|---|---|
| CORE ablation `0.268/0.234/0.227/0.203` (also cross-pasted into an unrelated entry) | Does not exist in arXiv 2605.28742. Real: `0.907/0.830/0.780/0.617`, one task, one regime, n=3 |
| `/doctor` "dedupes / trims / migrates / reports before changing" | The source contains two generic sentences |

**Rule adopted**: any number, quoted metric, or named mechanism entering a handoff task must be
dive-verified against primary source. **Corollary**: "absent from an index page" is not evidence of
nonexistence — two sources reported unlocatable both return HTTP 200 (one unlinked from its own
blog index; one where the sweep queried the benchmark's site rather than the publisher's).

_Sources: `handoffs/active/intake-derived-work-2026-07-25.md` ID-10/10b/10c;
`research/intake_index.yaml` (dive_corrections fields); `progress/2026-07/2026-07-25.md`._


## Research-intake protocol: four stages, and why (2026-07-25)

The intake pipeline was rewritten from two stages to four after a session in which the two-stage
design failed in three distinct ways at once. The structure is worth recording because each stage
boundary exists to stop a specific observed failure.

| Stage | Mode | May write |
|---|---|---|
| 1 sweep/dedup/expand/recommend | auto | intake index (`stage1-unverified`) + session file |
| 2 deep dives on operator-selected intakes | auto | verification/correction fields on entries |
| 3 audit → action plan | **plan mode** | the plan file only |
| 4 implement | auto | what the approved plan names |

**Comments during stages 1–3 are context, not authorization.** They are appended verbatim to a
steering ledger and folded into the Stage-3 plan — they never license an immediate handoff write,
*even when they appear to grant permission*. Approval of **scope** is not a waiver of the **review
gate**. Stage 3 cannot present a plan until every ledger row is a plan item or an explicit decline.

**Summariser output is provisional until a dive reads primary source.** Entries persist as
`stage1-unverified`; only a Stage-2 dive promotes them. No number, metric or named mechanism from an
unverified entry may be quoted in plan text or a handoff task. This exists because two Stage-1 agents
*invented* specifics that were persisted and read as evidence — a paper ablation whose figures appear
nowhere in the paper (and which was additionally cross-pasted into an unrelated entry), and a
four-step tool behaviour absent from a source containing two generic sentences.

**Three lookup failure modes now guarded explicitly**, each having produced a wrong conclusion:

1. **Truncated dedup** — a `head`-limited grep missed a real URL collision ~10,000 lines further down.
   The sweep must run unbounded.
2. **Companion-artifact conflation** — a repo/weights/dataset page is a *distinct artifact*, not a
   duplicate of its paper. `duplicate` requires an exact `arxiv_id`/`url` collision; "the paper
   mentions this repo" is not one. 19 entries were mis-filed this way.
3. **Stale path lookup** — a category→file map listed 10 handoffs under `active/` after they were
   archived. Treating a failed `active/` lookup as "no prior coverage" is how an intake wrongly
   concludes a technique is novel. Always search `active/` **and** `completed/`.

**Verdict taxonomy**: `not_applicable` asserts *out of scope* and demands the most justification of
any verdict. In-domain, self-hostable, but out-competed is **`superseded`** — and the successor must
be named, because an unexplained `superseded` is unfalsifiable.

_Sources: `.claude/skills/research-intake/SKILL.md`; `references/intake-schema.md` § Verification
lifecycle; `references/session-persistence.md` § Steering ledger; `progress/2026-07/2026-07-25.md`._

## Compiled Update — 2026-07-29: a stale record is an active liability — the correction pass

**Confidence**: verified — each correction below was settled against a primary
artifact (a file at a pinned commit, a repository listing, a weight map, a
paper's own table), not against a secondary summary. **Caveat on independence**:
the corrections and the records they correct were both produced by this project,
and in several cases by the same session; what is independently checkable is the
artifact each correction cites.

### The batch outcome makes the point

Of the 19 intake entries selected for deep dives in this batch, **9 were
overturned** and 10 verified. The dives changed decisions rather than merely
enriching records — a framing was inverted, a vendor uplift claim died, a
drop-in candidate was killed, one entry was found to be substantially fabricated
at Stage 1, another had been read from a stale version, and a ranking this repo
had restated was found to be backwards. **The corrections are the durable
knowledge; the original claims are not.**
[`progress/2026-07/2026-07-29.md`](../progress/2026-07/2026-07-29.md) §"The dives changed decisions, not just records"

### Verify a negative before asserting absence

Two records asserted a capability gap that did not exist, and both were actively
mis-scoping live work:

- A handoff line asserted a retrieval model was framework-only with "no GGUF /
  llama.cpp / Transformers / ONNX". **Three GGUF repositories exist**, one of
  them published **five months before that line was written**, and our frozen
  production tree already supports the path end to end. The stale line was
  pricing a live evaluation as "stand up a new serving stack" when it is a
  one-line server invocation. See [Search & Retrieval](search-retrieval.md).
- An intake entry claimed our pinned image-backend checkout lacks support for a
  model. The pinned commit contains that model's implementation header (646
  lines) and its documentation, and the deployed GPU binary was **built from that
  source**. Struck in both the entry's `recommended_actions` and its
  `verdict_justification`.

The generalized rule — never assert "absent" or "identical" from one encoding,
one key, or one file listing — is the same one that governs architecture
verification: read the artifact that would have to contain the thing.
[`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) §Open Question 1 (corrected);
[`ernie-image-turbo-evaluation.md`](../handoffs/active/ernie-image-turbo-evaluation.md) §2026-07-29 corrections

### Verify architecture from the weight map, not the declaration

A config-level check reports a model's draft head "preserved" while the model
ships **zero** such tensors. Any architecture claim about a fine-tune must be
settled against `model.safetensors.index.json` or GGUF tensor counts. Full rule
and evidence: [Speculative Decoding](speculative-decoding.md).
[`speculative-decoding-mtp-refresh.md`](../handoffs/active/speculative-decoding-mtp-refresh.md) §2026-07-29 Stage-4

### Two intake-pipeline failure modes with named remedies

- **Stage-1 fabrication.** One entry's Stage-1 body contained a product name
  appearing **zero times** in the paper, process metrics that do not exist, and a
  verifier result with its **sign inverted** (+8.40 recorded as −8.4). The body
  was rebuilt from primary source at Stage 2. Follow-on filed: audit the single
  non-dived entry in the batch for the same mode. The structural lesson is that a
  Stage-1 summary is **unverified by construction** and must be labelled as such
  until a dive touches the primary source.
- **Stale-version reads.** Another entry was summarized from a v1 while the live
  v2 had released code under Apache-2.0, added an open-weight arm, and — decisive
  — the authors had **downgraded their own headline 34.2% → 20%**. Both "direct
  tensions" recorded at Stage 1 were wrong. Always resolve to the live version
  before recording tensions against internal work.

[`progress/2026-07/2026-07-29.md`](../progress/2026-07/2026-07-29.md) §dive table

### Cite by identifier, not by title; and check the cross-reference resolves

Two distinct hazards surfaced in one batch. First, a paper from the same week
carries a **near-identical title** to one of the anchors, so anyone re-fetching
by title lands on the wrong document — cite the arXiv ID.
[`context-folding-progressive.md`](../handoffs/active/context-folding-progressive.md) §Dedup hazard.
Second, a handoff *and* its deep dive both cite an intake ID as their subject's
entry, and that ID belongs to an entirely different entry; **no row for the
actual subject exists at all**. A citation that resolves to *something* is not a
citation that resolves to the *right* thing.

**Resolved 2026-07-29** (`intake-937` created; all 6 references repointed). The
failure mode generalises, and it is worth stating in its sharpest form: **a
missing index entry is loud; a wrongly-pointed one is silent.** The subject here
was not obscure — it was the *deployed production model*, with a deep dive, an
active handoff, and a live serving path. What was missing was only the index row,
and because two documents cited a plausible-looking ID, every reader who checked
was *reassured* by an unrelated CPU-matmul blog entry. It survived from
deployment until a dive on a competing model happened to grep the index rather
than trust the handoff — i.e. it was caught by accident, not by any control.

Two durable consequences. (1) **Validators check resolution, not correctness.**
`validate_intake.sh` confirms that referenced handoff files exist; nothing checks
that a cited intake ID is the *right* entry. Cross-reference validity needs a
periodic sweep, and "the link works" must never be read as "the link is right."
(2) **Repointing is not a find-and-replace.** Three of the six references were
verdict-*promotion* instructions ("promote to `new_opportunity` once GPU lands")
that are nonsense against an already-deployed row — both triggers had fired
months earlier. Each repoint carried an inline dated note, so the superseded ID
stays traceable instead of being silently erased.

### Never round-trip a whole document to append to it

Persisting 24 new entries via `yaml.safe_load` → `safe_dump` **destroyed the
index header comments** and reflowed all 18,935 lines, presenting a 24-entry
addition as a whole-file rewrite. Comments are not part of the YAML data model,
so a round-trip discards them without error — the operation *succeeds* while
losing information, which is why nothing caught it. Recovery required verifying
all 912 pre-existing entries field-by-field to prove no semantic change rode
along (none did), and the reformat is not reversible once pushed.

The fix is preventive: **append as text**. Exercised on the very next write, the
same operation produced **101 lines added, 0 removed**, header intact, validator
green. Two orders of magnitude less churn for identical semantics. Worth carrying
beyond YAML — any serialize-parse-reserialize cycle over a human-maintained file
silently drops whatever the parser does not model (comments, key order,
formatting, anchors), and a reviewer facing a whole-file diff cannot see the
actual change.

### Process amendment: the dive-surfaced source gate

The research-intake skill gained a **Stage 2b** gate: dives must emit the list of
new sources they surface, the operator selects from it, and those run as a
combined Stage-1+2 pass **before Stage 3 opens** — plus a fifth Stage-3
completeness gate and a separate entry cap. Motivating failure, from this batch:
four papers were raised only at Stage 3 and had to be bolted on as a
post-approval round, so the rest of the plan was authored without their findings
— and one of them **partly deflated the very entry whose dive had surfaced it**.

### Two record-keeping hazards worth carrying

- **Staged-files ride-along.** Index rows authored by this session were swept
  into a *parallel* session's commit. Content survived intact; only attribution
  moved. On a shared tree, authorship is not established by who wrote the lines.
- **Prose is invisible to the dashboard.** A hardening item recorded only as
  prose inside another checkbox did not count toward progress; it was converted
  to its own `- [ ]` line during this pass. Any edit recording completed work
  must flip a checkbox, not narrate.

[`progress/2026-07/2026-07-29.md`](../progress/2026-07/2026-07-29.md) §Note on attribution;
[`scoring-infra-standardization.md`](../handoffs/active/scoring-infra-standardization.md) §2a-iv

### Source References

- [`progress/2026-07/2026-07-29.md`](../progress/2026-07/2026-07-29.md) — batch outcome (24 entries, 19 dives, 9 overturned), the per-entry overturn table, records corrected, the skill amendment, and the attribution note
- [`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) — the five-month-stale capability assertion and its live mis-scoping effect
- [`ernie-image-turbo-evaluation.md`](../handoffs/active/ernie-image-turbo-evaluation.md) — struck "stale backend" premise; the cross-reference defect and its 2026-07-29 resolution (`intake-937`, 4 of the 6 repoints, 3 needing rewording rather than an ID swap)
- [`research/deep-dives/ernie-image-turbo-dit-text-to-image.md`](../research/deep-dives/ernie-image-turbo-dit-text-to-image.md) — the other 2 repoints; a pre-deployment assessment whose premises production later falsified
- [`speculative-decoding-mtp-refresh.md`](../handoffs/active/speculative-decoding-mtp-refresh.md) — weight-map-over-config verification rule
- [`context-folding-progressive.md`](../handoffs/active/context-folding-progressive.md) — near-identical-title dedup hazard; cite by arXiv ID
- [`scoring-infra-standardization.md`](../handoffs/active/scoring-infra-standardization.md) — prose-to-checkbox conversion during the same pass

## Compiled Update — 2026-08-09: a citation graph nobody had measured was 23.5% broken, and the ranking derived from it was wrong

> **Review flag (project-wiki writer-evidence policy):** model-compiled; the index defect and its repair were measured directly against `research/intake_index.yaml` before and after migration on 2026-08-09.

- **The intake index's citation graph was silently dropping roughly a quarter of its edges.** A census found **458 of 1,952 `cross_references.intake_entries` values (23.5%), across 133 entries, did not resolve** to any existing entry. The dominant class was annotated IDs of the form `intake-261 (Skill0 — RL-based skill internalization)` — a valid ID made unresolvable to tooling by a human-readable suffix. Eight values were worse: an unquoted `:` inside the annotation caused YAML to parse the list item as a **mapping**, so the value stopped being a string at all. Repair normalised every value to a bare resolvable ID and preserved all 458 annotations verbatim in a new `intake_entry_notes` sibling: **0 values lost, 0 unresolvable remaining**, resolvable edges 1,494 → 1,940. Sources: [research/intake_index.yaml](../research/intake_index.yaml), [intake-schema.md](../.claude/skills/research-intake/references/intake-schema.md), [progress 2026-08-09](../progress/2026-08/2026-08-09.md).

- **The generalizable failure is that a broken graph does not announce itself — it produces plausible, wrong rankings.** Repair reordered the most-cited list substantially (one entry moved 12 → 27 inbound and became the index's most-cited; another moved 3 → 17; **239 entries gained edges**). A backfill population that had been *scoped by inbound-citation count* was therefore measuring the wrong set and had to be recomputed against the repaired graph. **Any selection rule computed over a reference graph inherits that graph's defects silently**, which is the same class of error as gating on a metric whose scope does not match the measured subset. Sources: [research/intake_index.yaml](../research/intake_index.yaml), [progress 2026-08-09](../progress/2026-08/2026-08-09.md), [research-evaluation-index.md](../handoffs/active/research-evaluation-index.md).

- **A maintained prior-art register is a cheap, high-leverage artifact, and its design is worth copying wholesale.** An upstream serving project ships one as markdown consulted *before* any profiler finding may be called novel, with a five-column schema — pattern, trace keywords, primary code, existing path, and **a pre-written conclusion**. That last column is the load-bearing one: it moves the verdict out of model judgment at read time and into reviewable data at authoring time, the same move a claim grammar makes for measurement claims. Three further mechanisms transfer directly: partitioning rows **mainline vs in-flight** (a pattern merged upstream but absent from a frozen local build is a *port*, not a research proposal), an **expected-absence register** recording why a path may be legitimately missing so a disabled path does not read as a defect, and a **pinned-head refresh** that records the upstream commit each scan was taken against so staleness is measurable rather than asserted. Sources: [autokernel-research-loop.md](../handoffs/active/autokernel-research-loop.md), [cpu-kernel-env-flags-inventory.md](../handoffs/active/cpu-kernel-env-flags-inventory.md), intake-1029 in [research/intake_index.yaml](../research/intake_index.yaml).

- **External code moves, so an unpinned citation of an external symbol is unfalsifiable later.** Two independent sources — a technical article and a maintained upstream catalog — both named a kernel that no longer exists under that name; neither was wrong when written, both were wrong when read, and neither recorded the head it was true at. This is now a written contract in the intake skill: pin the commit or retrieval date, prefer durable identifiers (the *role* a thing plays) over volatile ones (internal symbol names), record the head for tree-wide claims, and **verify absence across trees rather than one file** — the same dive nearly reported a source as fabricated because a first search covered only a framework's model file while every symbol lived in its kernels tree. Sources: [intake-schema.md](../.claude/skills/research-intake/references/intake-schema.md), [k28-fused-chunked-gdn-kernel-research.md](../handoffs/active/k28-fused-chunked-gdn-kernel-research.md), intake-1030.

## Compiled Update — 2026-08-09 (second batch): auditing a belief-system design, and what the epistemic literature actually licenses

> **Review flag (project-wiki writer-evidence policy):** model-compiled from a single research-intake
> session that ingested and dive-verified 37 sources (`intake-1031`–`intake-1067`); every formal claim
> below was checked against primary text during that session, and each is cited to its intake entry.

- **When a design proposes infrastructure, audit the codebase before auditing the literature.** A
  2,682-line proposal for an "append-only ledger of typed frames plus derived belief state" was
  reviewed against the actual tree first, and the pattern turned out to be **landed in-project three
  times over** — the evidence-plane ledger (13/14 waypoints done, typed sequential e-process
  verdicts, per-candidate views rebuilt by fold), the AutoKernel journal (fsync-per-event, seven
  schema-bound record kinds, pure `rebuild_views()` bound to an events digest, `RETRIEVAL_SUPERSEDED`
  so a record can leave *retrieval* without leaving the *record*), and the experiment journal
  (supersession fold with baseline authority already cut over to `ledger_fold`). The honest scope of
  the proposal shrank from "EPYC lacks a substrate" to three verified gaps: claim-level dependency
  edges (wiki dependency tracking existed nowhere as a design), refusal-semantics freshness gating,
  and provenance-gated actuation. Sources:
  [evidence-plane-ledger-and-sequential-verdicts.md](../handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md),
  [vidya-belief-substrate-audit.md](../research/deep-dives/vidya-belief-substrate-audit.md),
  [vidya-belief-substrate-program.md](../handoffs/active/vidya-belief-substrate-program.md).

- **Vocabulary reuse is a hard governance constraint, not a style preference.** Three independent
  vocabularies already own parts of this space: `MEASUREMENT.md`'s reconciliation verbs
  (`retro-certify` / `demote-to-prior` / `retire-view`), the dashboard's freshness classifier — which
  declares itself "THE ONE CLASSIFIER" over `fresh`/`aging`/`stale`/`missing` plus the independent
  `observed|silent|absent` × `populated|empty|unknown` axes — and the sequential-verdict states
  (`accumulating` / `confirmed_improvement`). Any new taxonomy **maps onto these or extends them
  explicitly; it never forks them**, or the project acquires a second governance system whose
  disagreement with the first is undetectable. Sources: [MEASUREMENT.md](../MEASUREMENT.md) §6,
  `dashboard/freshness.py`, [vidya-belief-substrate-audit.md](../research/deep-dives/vidya-belief-substrate-audit.md) §3.

- **The frame and ledger layers of any claim-tracking system are solved prior art; only the epistemic
  kernel is unserved.** Typed, content-addressed claim units with provenance, actor signature, and
  supersession/retraction are **nanopublications**, running publicly for fifteen years (three named
  graphs; content addressing over a *normalized* graph so identity survives serialization; retraction
  valid only when signed with the original author's key). The field vocabulary is **W3C PROV-O**
  (including `wasInvalidatedBy`/`invalidatedAtTime`). The typed-signed-statement encoding with
  per-step scoped authority is **in-toto/DSSE + SLSA** — which already occupies the exact epistemic
  stance ("verification proves the derivation followed registered rules, not that the artifact is
  good"). The authenticated append-only log without consensus is **RFC 9162 / C2SP tile logs**,
  self-hostable and freshly re-engineered. What remains genuinely unbuilt is the kernel: a
  deterministic fold to *graded* belief state, freshness gates that refuse, and certificates over an
  accumulating supersession-aware state. Sources: intake-1031, 1046, 1047, 1048, 1063, 1064.

- **A semantic trap worth internalizing: record-lifecycle time and world-truth time are different
  clocks.** PROV's `invalidatedAtTime` means *the record became unusable*; a bi-temporal knowledge
  graph's `invalid_at` means *the fact stopped being true in the world*. Aliasing both to one field
  is a category error that silently corrupts every freshness query built on it. The corrected field
  set keeps five distinct times — ledger-side `created_at`/`expired_at`, world-side
  `valid_at`/`invalid_at`, and the source's own `reference_time` (a 2025 paper read in 2026 asserting
  a 2024 fact carries three). Sources: intake-1046, intake-1032.

- **Similarity cannot detect contradiction — so no retraction path may be gated on an embedding
  threshold.** Measured on 98 labelled pairs, cosine similarity separates duplicates from
  contradictions at **AUROC 0.5926**, barely above chance, because a contradiction is often *more*
  embedding-similar to the original than a harmless rephrasing is. This is the empirical basis for
  requiring key-equality-plus-value-inequality (or an explicitly logged adjudicator) rather than a
  similarity score anywhere in an invalidation path. Source: intake-1036.

- **Any LLM judgment that can affect a derived result must be logged as a keyed input, or replay is
  provably inconsistent.** A 2026 result establishes *necessity*: for a boundedly nondeterministic
  judge, a system without a durable keyed log admits an adversarial replay pair that reaches
  different conclusions from identical committed state — and with the log, that anomaly is excluded
  (a tight characterization). Three operational rules follow: key judgment records by the read-set
  plus the full decoder tuple (prompt, seed, model version, temperature, tool-output hash); enforce
  first-committed-vote-wins per key so a re-run judge is short-circuited rather than appended; and
  invoke no model during a fold or replay. The trap: **greedy/temperature-0 decoding does not make a
  judge deterministic** under this model, because the nondeterminism space includes sampling state
  and hardware numerics. Source: intake-1035.

- **Advisory provenance display does not change behaviour; refusal does.** A controlled n=26 study of
  a claim-level provenance interface found it *significantly lowered* participants' trust in
  LLM-generated scholarly edits while **not changing their reliance** on those edits under time
  pressure. Independently, a RAG staleness benchmark found one outdated passage cuts overall scores
  by more than 24% and raises harmful outputs, while retrieval-side mitigation still surfaced stale
  content roughly half the time. Together these are the empirical case for gates that block or
  abstain at serve time over banners that warn — and for a scoring scheme that penalizes confidently
  stale answers (+1 correct / 0 abstain / −1 harmful) rather than rewarding abstention as safety.
  Sources: intake-1060, intake-1054.

- **A published citation can be correct in every particular and still be attributed wrongly.** Five
  formal citations underpinning the design were checked against primary text: four confirmed, one
  partial — the convergence bound the draft attributed to a specific paper is standard Kleene-iteration
  folklore, and the citable theorem is in fact *stronger* than what was claimed. Two further
  corrections came from reading the sources rather than their abstracts: an argumentation paper
  defines **three** proof standards, not the five widely associated with it (the other two arrive in a
  later chapter by the same authors), and a "counterexample" scope caveat turned a headline retraction
  primitive into a positive-fragment-only result. The transferable rule: **verify the attribution, not
  just the existence** — "this paper says X" is a claim about the paper, and it fails independently of
  whether X is true. Sources: intake-1038, 1039, 1040, 1050, 1062, 1066.

### Source References

- [`research/deep-dives/vidya-belief-substrate-audit.md`](../research/deep-dives/vidya-belief-substrate-audit.md) — the consolidated audit: verdict, seven wrinkles, corrections ledger, corrected formal foundations, adoption kit, landscape, machine-wide assessment, and the 37-entry reference table
- [`handoffs/active/vidya-belief-substrate-program.md`](../handoffs/active/vidya-belief-substrate-program.md) — the resulting program: spec-amendment sheet, downscoped gold corpus, shadow pilot, research track, operator decision queue
- [`progress/2026-08/2026-08-09.md`](../progress/2026-08/2026-08-09.md) — session record for the audit batch
- [`research/intake_index.yaml`](../research/intake_index.yaml) — entries `intake-1031`–`intake-1067`, each carrying its verified claims, adoption extract, and dated `dive_corrections`

## Compiled Update — 2026-08-09/10: what building the belief substrate actually taught

> **Review flag (project-wiki writer-evidence policy):** model-compiled from an implementation
> session that landed ~2,600 lines under `scripts/vidya/` with 156 tests passing on two
> architectures. Every measurement below was produced by running the code against the real
> 1,067-entry intake index, not estimated.

- **A correction recorded only in narrative is not a correction — it is worse than none.** A
  fabricated `/doctor` mechanism was reported "struck" on 2026-07-25 by three separate records (a
  progress file, a governance handoff, and a later re-source note) and was **never removed from the
  index**. It served as "CONFIRMED and understated" for fifteen days. The failure is worse than an
  uncorrected entry because a reader who checks the record is told the problem was handled. The
  generalizable rule: **verify a correction in the artifact it claims to change**, not in the prose
  that claims to have changed it. Sources: [research/intake_index.yaml](../research/intake_index.yaml)
  intake-896 `dive_corrections`, [vidya-pilot-corpus.md](../docs/design/vidya-pilot-corpus.md) §4.

- **A validator that checks key presence does not check anything.** Two defects of the same shape
  landed the same day: 538 entries carried duplicate `cross_references.intake_entries` keys (PyYAML
  resolves duplicates last-one-wins, silently), and 9 entries satisfied the *required* `url` field
  with a null. Both had passed every validation run for as long as they existed. The duplicate check
  had to move to **parse time** — after `safe_load` the earlier value is already gone, so it is
  undetectable by inspecting the parsed structure. The empty-field case resolved into a
  **locatability** rule rather than a backfill: an entry needs a url, an arxiv_id, *or* a
  `locator_note` explaining why neither exists, because all 9 were legitimate operator-supplied
  inline material where inventing a URL would be strictly worse than leaving it blank. Sources:
  [validate_intake.py](../.claude/skills/research-intake/scripts/validate_intake.py),
  [intake-schema.md](../.claude/skills/research-intake/references/intake-schema.md).

- **Recording where a claim was read costs seconds at dive time and is often impossible later.** A
  pass over all 1,067 entries found **zero** claims anchored to a span — every entry identified a
  *document*, so no claim could be cited as checkable at a location. That is now measurable as a
  grade: claims without an anchor cap at "located", and a policy requiring an anchored claim was
  satisfied by **0 of 4,191**. Recording the anchor while the source is open is now a Stage-2
  obligation in the intake skill. This is the same failure as the renamed-kernel incident, priced.
  Sources: [SKILL.md](../.claude/skills/research-intake/SKILL.md) Stage 2,
  [vidya-belief-substrate-audit.md](../research/deep-dives/vidya-belief-substrate-audit.md).

- **An evaluation that passes first time has not been tested.** The gold-corpus mutation suite
  ultimately scored 28/28, but scored **20/28 on the first run**, and all four failures were real:
  two engine bugs (retraction operated per-*frame* while evidence lives in per-*token*, so a
  discredited source kept supporting its other claims) and two gold-label errors where the corpus
  encoding was less faithful than reality. Four defects in a system its author had just written and
  believed correct. Corollary observed twice more the same session: a negative control that does not
  verify its own mutation took effect proves nothing, and a test asserting a value the code cannot
  affect (`iterations >= 1` on frames that create no claims) passes against a broken implementation.
  Sources: [vidya-p5c-evaluation-and-decision.md](../research/deep-dives/vidya-p5c-evaluation-and-decision.md).

- **A rising correction rate can mean rising verification, not falling quality.** The monthly series
  shows corrections climbing from 1% (March) to 68% (August), which reads as collapse. It is a
  confound: corrections are recorded by dives, and dive activity went from ~0/month to 123 in August.
  The series measures *when verification happened*. The confound-free figure is the overturn rate
  among dived entries — **27 of 160 = 16.9%**, roughly one dived entry in six with a load-bearing
  claim falsified. Any metric whose denominator is "everything" cannot distinguish an uncorrected
  claim from an unexamined one. Sources:
  [vidya-r4-r5-corroboration-and-decay.md](../research/deep-dives/vidya-r4-r5-corroboration-and-decay.md).

- **Independence is unmeasurable when identity is per-source.** 100% of 4,191 beliefs rest on at most
  one support path — not because the corroboration statistic is wrong, but because claim IDs are
  minted per entry, so two sources can never support the *same* claim. The data model forecloses
  independence before any statistic runs. Cross-entry claim identity is therefore a prerequisite, and
  it is irreducibly human: deciding two differently-worded claims are the same proposition is exactly
  the judgment a deterministic fold must not make.

- **A refusal without a named next action is a shrug, and a one-way flag deadlocks the work it
  protects.** The first live run of the freshness gate blocked 652 claims with no way to clear them,
  because every dived entry carries a correction and the review flag had no counterpart. The fix was
  a `correction_reviewed` frame, so the gate's named next action produces the thing that unblocks it.
  Related: an unprovable absence is refused outright rather than approximated — "no rule can produce
  X" is kept as a function that *raises*, because a plausible implementation would be an unprovable
  absence that looks like a proof. Sources:
  [vidya-pilot-spec.md](../docs/design/vidya-pilot-spec.md) §8, `scripts/vidya/absence.py`.

- **A null result needs demonstrated detection power to mean anything.** An exhaustive search for a
  counterexample to an open conjecture found none across 5,670 instances. On its own that is worth
  little. Two things make it a result: boundary growth was confirmed present in the corpus (so the
  search exercised the case at issue), and a mutation test replaced the implementation with a
  plausible-but-wrong variant, which produced **2,715 counterexamples from the same instances**. The
  comparison can see a wrong answer; it does not see one here. Sources:
  [vidya-r1-r2-stratified-negation.md](../research/deep-dives/vidya-r1-r2-stratified-negation.md) §2.4b.

### Source References

- [`docs/design/vidya-pilot-spec.md`](../docs/design/vidya-pilot-spec.md) — the binding pilot contract, all §19 decisions ratified 2026-08-09
- [`docs/design/vidya-pilot-corpus.md`](../docs/design/vidya-pilot-corpus.md) — 19 gold claims from four documented real corrections
- [`research/deep-dives/vidya-p5c-evaluation-and-decision.md`](../research/deep-dives/vidya-p5c-evaluation-and-decision.md) — 28/28, and the four failures found first; verdict ITERATE
- [`research/deep-dives/vidya-r1-r2-stratified-negation.md`](../research/deep-dives/vidya-r1-r2-stratified-negation.md) · [`vidya-r4-r5-corroboration-and-decay.md`](../research/deep-dives/vidya-r4-r5-corroboration-and-decay.md)
- [`handoffs/active/vidya-belief-substrate-program.md`](../handoffs/active/vidya-belief-substrate-program.md) — 58 done / 4 open

## Compiled Update — 2026-08-10: a citation is not a dependency, and a check can be passed by deleting what it inspects

> Model-compiled from an implementation session (vidya program + a full citation audit of the intake
> index). Every number below is measured against the live index or ledger and is reproducible from
> the cited artifact. **Retracts one claim from the 2026-08-09/10 section — see the first item.**

- **RETRACTION: the "5,670 instances, 0 counterexamples" null recorded above is vacuous.** The two
  routes it compared reduce to the same expression — specializing a base fact to ⊥ and then dropping
  ⊥ entries *is* deleting that fact — so agreement was guaranteed by construction and measured
  nothing. The mutation test was sound but showed only that the harness can detect disagreement; it
  could not show the routes differed, which is how it was read. The lesson generalizes past this
  instance: **a mutation test validates the detector, never the distinctness of the things being
  compared.** Pin the distinctness separately, or a tautology passes as a result. Replaced by a real
  finding — genuinely incremental retraction across a negation boundary is **refuted** (2,241 of
  5,670), dual tokens cut it to 270, and only dual tokens plus intra-stratum dependency closure is
  exact. Source: [vidya-r1-r2-stratified-negation.md](../research/deep-dives/vidya-r1-r2-stratified-negation.md) §2.4c.

- **A citation is not a dependency, and the gap is measurable.** Hand-classifying a 20-edge uniform
  sample of the intake citation graph suggested that citations from *dived* entries were evidential
  at 4/6 precision. A **60-edge sample stratified over the 672 dived-source edges refuted it: 18%
  evidential, 75% topical, 7% companion artifact.** The first figure was a small-sample artifact —
  its edges happened to fall in one intake batch where citations really are foundational. Promoting
  all 672 would have created ~550 false dependencies, and a false dependency is worse than a missing
  one because it propagates invalidation into work that never depended on anything. Two mechanical
  shortcuts were tried on the same sample and both failed (naming the target in the claim text:
  precision 0.50, recall 0.09; verification-language keywords: 0.50/0.27). **Dependency has to be its
  own edge, written when the dependency is real** — hence the `depends_on` field with a required
  `why` and a counterfactual authoring test. Source:
  [vidya-p5c-evaluation-and-decision.md](../research/deep-dives/vidya-p5c-evaluation-and-decision.md) §4d.

- **A validation rule can be passed by omitting the field it inspects.** Duplicate `arxiv_id` was a
  hard error. Exactly **3 entries in 1,067** carried an arXiv *URL* with a null `arxiv_id` — all three
  `novelty: duplicate`, all three from one 2026-07-08 batch, and all three holding an id that already
  existed elsewhere. Each would have failed validation had the field been filled in. Whether that was
  deliberate is unknowable and irrelevant: the check could not see its own blind spot, because absence
  of a field is indistinguishable from a source that genuinely has none. The fix looks at the *other*
  field (the URL) rather than trusting the one being validated.

- **Labelling a duplicate is not the same as refusing to create one.** Dedup was working — it
  correctly marked collisions `novelty: duplicate` — and then persisted them as full entries anyway,
  each with its own `key_claims`. **12 such entries existed and 10 were cited by other entries**, so
  every one read downstream as an independent source. A classifier whose output is a label rather than
  a control-flow branch does not prevent anything.

- **Five sources were cited across the knowledge base and had never been ingested**, each carrying a
  *neighbouring* entry's id — which reads as provenance and is not. All five turned out to be real
  papers (ADAS, Hyperagents, Self-Harness, ACE, RE-Bench). The papers were never the problem: **two
  headline claims resting on them were false.** "LLM-as-judge benchmark design is itself optimizable"
  is supported by none of its three sources — all three optimize harness or context against a *fixed*
  benchmark. "A trajectory toward fully autonomous task generation" is supported by none of the
  ADAS → DGM → Hyperagents lineage; Hyperagents lists *"a fixed task and evaluation distribution"*
  among its own limitations. A downstream scoping document had already taken *"only the
  task-generation half"* of a system with no task-generation half.

- **Verifying one clean fix is what finds the rest.** The audit began with two mis-stamps noticed by
  accident while checking something unrelated. A naive label-vs-title checker over 271 files produced
  **780 hits, almost all noise** (any prose before a parenthetical id). Tightened to name-like labels
  in curated paths, it found 8 real mis-stamps — and separately revealed that **101 entries, the whole
  2026-03 seed batch, had titles that were just their arXiv id**, which is why four *correct*
  citations (YaRN, Sarathi-Serve, Cascade, SkillRL) had looked like mismatches. One batched arXiv
  sweep (25 ids per request, 5 requests) resolved all 101.

- **An identifier stops being cheap to change the moment something immutable references it.** Merging
  four duplicate entries left permanent id gaps. Closing them would have renumbered 728 entries,
  rewritten 5,565 references across 479 files, and changed 731 of the 1,067 intake ids embedded in
  append-only ledger claim identifiers whose hash chain a checkpoint had already signed. The argument
  that decides it holds even without the ledger: **a reused id makes an old reference resolve to the
  wrong thing, silently; a removed id resolves to nothing, visibly.** But that defence is only valid
  if the absence is *recoverable* — 44 references to absorbed ids sat in 20 files with no forward
  pointer until a generated redirect map was published. **A redirect map must be generated from the
  data, never hand-kept**, because one that drifts answers confidently and wrongly.

- **Resolution is a lookup, not a rewrite.** The obvious follow-up — bulk-repoint every reference to a
  merged id — would have corrupted records. Of 57 references, exactly **one** was mechanically safe to
  rewrite; four would have been damaged, three of them because the dead id is named *precisely because
  it was wrong* (a correction record), and one because it is a range endpoint. Historical records
  naming a superseded identifier are correct as written.

### Source References

- [`research/intake_merge_map.md`](../research/intake_merge_map.md) — generated redirect table for merged ids
- [`.claude/skills/research-intake/references/intake-schema.md`](../.claude/skills/research-intake/references/intake-schema.md) — `depends_on`, `merged_ids`, ID-sequencing rationale
- [`research/deep-dives/vidya-p5c-evaluation-and-decision.md`](../research/deep-dives/vidya-p5c-evaluation-and-decision.md) §4b–4d — promotion status, live-ledger evaluation, the citation-edge samples
- [`research/deep-dives/vidya-r1-r2-stratified-negation.md`](../research/deep-dives/vidya-r1-r2-stratified-negation.md) §2.4c — the vacuity retraction and the four retraction routes
- [`research/deep-dives/vidya-r4-r5-corroboration-and-decay.md`](../research/deep-dives/vidya-r4-r5-corroboration-and-decay.md) — alias candidate generation, source-identity defect
- [`research/recommendations.md`](../research/recommendations.md) — rec-001 and rec-002 rewritten after their sources were read

## Belief-kernel ingestion contract — one carrier, one ladder per source class (2026-08-10)

Heterogeneous producers write measurements in different shapes: an autopilot trial row, an
AutoKernel `evaluation_event`, a sealed benchmark manifest, an intake entry. The Vidya spec defined
what the carrier's grade levels *mean* (§4.5) but never how a producer *enters* the carrier, so each
adapter arrived with its own reading of the measurement constitution. Two were then caught
disagreeing on the same input — a record with no protocol and no attestation graded `Judged/T0` by
one and `Judged/Located` by the other. Neither reading is wrong on its face, which is the hazard: a
rule reimplemented per source becomes N dialects of itself, and the drift surfaces later as
unexplainable grade differences between corpora.

**The contract (spec §4.7).** An adapter *projects* its native record into a canonical `ClaimTuple`
and never grades:

```
native record  --project-->  ClaimTuple  --grade()-->  (Q, T, reasons)  --> frames
```

The tuple's vocabulary is AutoKernel's `claim_grammar`, which already enforces `MEASUREMENT.md:13`
as a REQUIRED schema block (category ∈ OPTIMUM/BASELINE/CANDIDATE, `protocol_id`, `metric`,
`metric_direction`, `reps` ≥ 1, `attestation_ref`). The strictest existing producer defines the
shape rather than the newest adapter redefining it.

**Source classes are the generalisation.** The carrier is shared; the grading rule is not.

| class | graded by | ceiling |
|---|---|---|
| `measurement` | the claim rule — protocol / n / date / attestation | `Witnessed` |
| `literature` | verification status — anchored, dive-verified, dive-overturned | `Verified` |

The literature ceiling is structural, not a limitation to lift: an intake entry records what someone
else reported. Each class registers exactly one ladder; `register_ladder()` refuses a second, and a
conformance test fails any adapter that returns a lattice level without declaring itself one.

**The standing practice this exists to support.** A process that produces measurements or verified
findings gets its wiring task filed the moment it is noticed, because the asymmetry is total:
instrumenting the WRITE side is cheap and permanent, while retrofitting the READ side is impossible
— a tuple invented on read claims warrant the original run never captured. Measured proof:
`benchmarks/results` holds 2,605 files and the wider research repo 4,562 measurement-shaped files,
but **0 of 200 sampled carry the constitution's full tuple** (`reps` essentially never recorded,
`sha256` absent from three of four areas). Those numbers can never gate a decision, and no adapter
can repair that. By contrast the 6 sealed manifests, which carry the tuple by construction, reached
`Witnessed/Attested` the first time anything read them.

Two further traps are recorded with the contract: price a bulk adapter before writing it (sample ~50
records, count full tuples), and watch the locator — support is counted by *source locator*, so N
result files measuring one thing read as N independent witnesses, and same-harness runs are not
independent evidence.

### Source References

- [`docs/design/vidya-pilot-spec.md`](../docs/design/vidya-pilot-spec.md) §4.7 — the normative contract
- [`scripts/vidya/adapters/README.md`](../scripts/vidya/adapters/README.md) — implementer's guide and the live source register
- [`research/deep-dives/vidya-r4-r5-corroboration-and-decay.md`](../research/deep-dives/vidya-r4-r5-corroboration-and-decay.md) — the withdrawn 2.2% ceiling and the corrected structured-corpus measurement
- [`handoffs/active/vidya-belief-substrate-program.md`](../handoffs/active/vidya-belief-substrate-program.md) SC1–SC11 — the source-coverage track
