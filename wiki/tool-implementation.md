# Tool Implementation

**Category**: `tool_implementation`
**Confidence**: verified
**Last compiled**: 2026-04-17
**Sources**: 13 documents (3 deep-dives, 6 intake entries, 4 handoffs)

## Summary

Tool implementation in the EPYC orchestrator spans two dimensions: the REPL tools that coding agents use during task execution (file operations, grep, tests, shell commands), and meta-tooling that provides codebase intelligence to improve those agents' effectiveness. The most significant finding from the research is that **precomputed dependency graph intelligence can replace 5-8 exploratory REPL turns with a single context injection**, reducing both token cost and wall-clock time per coding task. This is not a theoretical claim -- GitNexus is installed, all 4 EPYC repos are indexed (epyc-orchestrator: 12,187 symbols, 33,049 edges, 686 clusters, 300 execution flows), and the integration path is specified down to line numbers in the orchestrator source.

GitNexus implements an 8-phase indexing pipeline: file/folder tree extraction, tree-sitter AST parsing across 13 languages, cross-file import resolution with path normalization, function call tracking with confidence scores (0.3-0.9), inheritance/interface mapping, Leiden community detection for functional clustering, entry point detection with execution flow tracing, and hybrid search indexing (BM25 + snowflake-arctic-embed-xs semantic embeddings + HNSW). The resulting KuzuDB property graph stores symbols, files, folders, clusters, and processes connected by typed edges (CONTAINS, IMPORTS, CALLS, EXTENDS, IMPLEMENTS, DEFINES, MEMBER_OF, STEP_IN). Seven MCP tools expose this graph: `query` (process-grouped hybrid search), `context` (360-degree symbol view), `impact` (blast radius analysis at 3 depth tiers), `detect_changes` (pre-commit impact mapping), `rename` (coordinated multi-file refactoring with dual-confidence), `cypher` (raw graph queries), and `list_repos`.

The key architectural insight from the integration assessment is that **context injection beats tool calling**. The model currently discovers dependencies through trial-and-error grep cycles, each costing a full REPL turn (~5-10s + tokens). A single GitNexus context query returns the same information in <100ms and zero tokens. For a function like `_execute_turn` (7 callers, 30+ callees, 3 process flows), this replaces 5-8 grep turns with one injected context block. The recommended integration path (Option 3) auto-injects codebase intelligence into the prompt at `helpers.py:1276-1327`, after `_auto_gather_context()` but before prompt build, behind a `gitnexus_context_injection` feature flag.

The broader tool ecosystem includes the LLM-Wiki pattern (intake-269, intake-277) for maintaining compiled knowledge bases accessible to coding agents -- now integrated as the project's own wiki system. AST-based code review (intake-330) achieves 8.2x token reduction over full-file review by analyzing semantic diffs rather than raw text. Production agent skill engineering patterns (intake-337) document workflows for building and testing agent skills in production environments.

A 2026-04-17 deep dive (intake-398) investigated Magika, Google's AI-powered content-type detector (ICSE 2025, Apache 2.0, PyPI magika 1.0.2). The model is a 1 MB shallow byte-embedding MLP — not a CNN as commonly described — using three 512-byte windows (beginning, middle, end), 128-dim byte embeddings, two dense GELU layers, and global max-pooling over 200+ content types. Per-class confidence thresholds are calibrated to fix precision at 99% and maximize recall; below-threshold predictions fall back to `txt` or `unknown`, which explains the 99% F1 headline while synthetic OOD classes score 84–94%. Live measurements on the EPYC host showed 225 ms cold-start (onnxruntime init) and 2.8 ms/file amortized, with a confirmed JSON→JSONL misclassification. The deep dive concluded Magika is **not_applicable** to EPYC: the document-ingestion pipeline operates on a five-format, already-labeled corpus (arXiv PDF, GitHub MD, HTML, HuggingFace MD, user-uploaded PDF) where format is declared by URL pattern, HTTP Content-Type, or extension. No existing pipeline stage requires generic filetype detection, and adding ~80 MB of onnxruntime dependencies for zero measurable accuracy gain is pure negative value. Magika is worth reconsidering only if the pipeline begins ingesting truly arbitrary binary corpora.

## Key Findings

- **GitNexus provides single-query answers to dependency questions that currently cost 5-8 REPL turns.** When the coder modifies `_execute_turn()` in helpers.py, it has no awareness that 7 node classes call it, that it depends on 15+ helper functions, or that changing its return signature would break the entire graph. The `impact` tool answers this in one call with confidence-scored edges. Import-resolved calls score 0.90, same-file calls 0.85, fuzzy single-match 0.50, fuzzy multi-match 0.30. Tools default to `minConfidence=0.7` to exclude guesses, letting the agent distinguish "definitely calls X" from "might call X." [gitnexus-codebase-intelligence.md](../research/deep-dives/gitnexus-codebase-intelligence.md)

- **Context injection is strictly superior to tool calling for dependency awareness.** Five integration options were assessed, ranked by ROI: (1) MCP tool server -- zero Python code, 20 lines of config; (2) REPL tool wrappers -- 120 lines, follows existing registry pattern; (3) auto-inject context into prompts -- 150 lines, highest impact on code quality, feature-flagged; (4) pre-commit validation -- 50 lines, safety net for blast radius; (5) KuzuDB direct Python queries -- 200 lines, sub-millisecond queries, no Node.js runtime dependency. The recommended order is 2, then 3, then 4, then 5. Option 3 (auto-injection) represents the highest value because the model gets dependency context before it writes code, matching the "front-load intelligence" pattern analogous to prefix caching. [gitnexus-orchestrator-integration.md](../research/deep-dives/gitnexus-orchestrator-integration.md)

- **Confidence-scored edges enable graduated trust in refactoring.** The `rename` tool distinguishes graph-resolved edits (high confidence, apply automatically) from AST-search edits (lower confidence, flag for review). This graduated trust model maps directly to the orchestrator's cascading tool policy, where different trust levels govern different tool categories. [gitnexus-codebase-intelligence.md](../research/deep-dives/gitnexus-codebase-intelligence.md)

- **Leiden clustering on the call graph produces functional areas that can auto-generate skill files.** Each cluster gets cohesion and separability scores plus member symbols ranked by call density. The `--skills` flag generates SKILL.md files per cluster -- targeted context per functional area. This could replace manual agent role descriptions with data-driven ones that update automatically as code evolves. [gitnexus-codebase-intelligence.md](../research/deep-dives/gitnexus-codebase-intelligence.md)

- **Hybrid search (BM25 + semantic + RRF) with process grouping organizes results by execution flow.** The agent sees "MainREPLLoop: route -> validate -> fetchUser -> createSession" instead of 4 disconnected functions. Reciprocal Rank Fusion (k=60) merges BM25 keyword and semantic embedding results, then 1-hop graph expansion adds CALLS/IMPORTS neighbors. This pattern is directly applicable to the episodic memory retrieval, which currently uses FAISS alone -- adding BM25 lexical matching would improve retrieval for exact function/class name queries. [gitnexus-codebase-intelligence.md](../research/deep-dives/gitnexus-codebase-intelligence.md)

- **AST-based code review achieves 8.2x token reduction** over full-file review (intake-330). By analyzing AST diffs rather than raw text diffs, only semantically meaningful changes are reviewed. This is applicable to the autopilot's code mutation validation, where PromptForge proposes changes that need efficient review.

- **The LLM-Wiki pattern is now integrated.** The Karpathy-inspired pattern of structured knowledge compilation (intake-269, intake-277) has been adopted as the project's own wiki system, demonstrating the loop from research intake to implementation. [intake-269, intake-277, intake-321]

- **Tool output compression provides 60-90% token reduction per tool invocation.** Seven command handlers (pytest, cargo test, git status, git diff, git log, ls, build compilers) compress outputs before they enter the context window, layering before the existing `_spill_if_truncated()` mechanism. Feature-flagged as `tool_output_compression`. [tool-output-compression.md handoff]

- **Production agent skills require structured engineering workflows.** Intake-337 documents patterns for building agent skills in production: hypothesis-driven development, incremental deployment, structured testing, and version-controlled skill definitions. This aligns with the project's existing `.claude/skills/` and `agents/` architecture.

- **Integration test infrastructure for graph execution uses "real REPL, mock LLM" pattern.** 61 integration tests (2026-04-13) cover graph execution loop, node-level paths, observability, and API endpoints using a `GraphRunContext` factory fixture that assembles real `REPLEnvironment` (executing actual Python) with `MockLLMPrimitives` returning canned responses. `StubFailureGraph` and `StubHypothesisGraph` are real in-memory implementations (not `MagicMock`) to exercise the full protocol surface. Key design lesson: mock LLM responses must be wrapped in markdown code blocks to prevent `auto_wrap_final` or prose rescue from converting them to FINAL answers. This pattern enables testing the full orchestration loop independently of inference servers. [integration-test-coverage.md]

- **Risk-weighted coverage classification drives test prioritization.** The 100%-feasibility audit (2026-04-14) classified uncovered branches as must-test (recovery paths, parsing fallbacks, context-size selection) vs acceptable-gap (import fallbacks, portability branches). Staged floor raises follow test tranches rather than forcing blanket 100%. This methodology achieved 100% on all 10 seeding benchmark modules and all 7 enforced orchestrator slice files through 12 targeted tranches (A-L) with zero runtime behavior modifications. [integration-test-coverage.md, progress/2026-04-14]

- **Crawl4AI provides self-hosted deep page scraping for LLM consumption.** Async Playwright-based crawler (51K+ stars, Apache-2.0) with BM25 content filtering, local LLM extraction via Ollama, browser pool management, and Docker deployment. Selected over Firecrawl (108K+ stars) due to open-source-only infrastructure policy -- Firecrawl's cloud-first SaaS model and credit-based pricing conflict with self-hosted philosophy. Complements SearXNG (search aggregation) by handling JS-heavy pages and complex PDFs that WebFetch cannot process. Evaluation gated on post-AR-3 WebFetch failure rate data. [searxng-search-backend.md]

- **Magika (intake-398, ICSE 2025, Apache 2.0) is a 1 MB byte-embedding MLP that outperforms libmagic on text-format discrimination, but is not_applicable to EPYC's pipeline.** Contrary to reviews describing it as a CNN, the model is a shallow MLP: three fixed 512-byte windows (beginning, middle, end) are embedded at the byte level into 128-dim vectors, reshaped, passed through two 256-d Dense+GELU layers, global max-pooled for size invariance, and classified over 200+ content types with per-class thresholds calibrated for 99% precision. Training set grew from 24 M to ~100 M samples (GitHub + VirusTotal). The threshold mechanism causes abstention (falls back to `txt`/`unknown`) when confidence is below per-class calibration point — this is how the paper reports 99% F1 without claiming that accuracy on all inputs. Cold-start on the EPYC host measured 225 ms (onnxruntime init dominates); amortized per-file latency is 2.8 ms (better than the paper's 5.77 ms, consistent with the hardware). libmagic is 5-8x faster per file and has <1 ms cold-start, but struggles with text-format discrimination (Python vs Ruby vs JS). **Not applicable to EPYC**: the orchestrator's document-ingestion corpus is a five-format, already-labeled set (arXiv PDF, GitHub MD, HTML, HuggingFace MD, user-uploaded PDF) where format is declared by URL pattern, HTTP Content-Type header, or file extension. No pipeline stage (`pdf_router.py`, `document_preprocessor.py`, `fetch.py`, `research.py`) requires generic filetype detection. A trivial extension-plus-4-byte-magic check has essentially zero false-positive rate on this corpus. Live measurement confirmed the JSON/JSONL confusion documented in external reviews: Magika classified a `.json` file as `jsonl` (JSONL is line-delimited JSON, a distinct format). Integration cost would be ~80 MB of transitive dependencies (onnxruntime) and 225 ms cold-start with no accuracy gain. Reconsider only if the pipeline begins ingesting truly arbitrary binary corpora (malware, forensic dumps, archives with unknown extensions). [confidence: verified — magika-filetype-detection.md deep dive, 2026-04-17]

## Actionable for EPYC

### High Priority (immediate value)
1. **REPL tool wrappers for GitNexus** (Option 2) -- add 3 tools (`codebase_impact`, `codebase_context`, `codebase_changes`) to `orchestration/tool_registry.yaml` that shell out to `gitnexus` CLI. ~120 lines, integrates with existing registry pattern. Saves 3-5 REPL turns per coding task by front-loading dependency context.
2. **Auto-inject codebase context into prompts** (Option 3) -- when `_execute_turn()` builds the coder prompt, query GitNexus for target symbol context and inject alongside `gathered_context`. ~150 lines, feature-flagged behind `gitnexus_context_injection`. Highest single impact on coding agent quality.

### Medium Priority
3. **Pre-commit validation** -- wire `detect_changes` into the generation monitor. After the coder produces code, check blast radius against the graph before accepting. ~50 lines. Catches unintended side effects.
4. **BM25 + semantic hybrid search for episodic memory** -- the RRF fusion pattern from GitNexus is applicable to the FAISS-only episodic retrieval. Adding BM25 lexical matching via `rank_bm25` would improve retrieval for exact function/class name queries.
5. **Skill generation from clusters** -- run `gitnexus analyze --skills` on the orchestrator to generate data-driven skill files per functional cluster. Evaluate whether these can replace or supplement manual agent role descriptions.
6. **AST-based code review** (intake-330) -- integrate AST diff analysis into autopilot code mutation validation for more efficient review of PromptForge proposals.

### Lower Priority
7. **KuzuDB direct Python queries** (Option 5) -- eliminate Node.js subprocess overhead with native Python bindings to the GitNexus-built graph. ~200 lines, sub-millisecond queries. Pursue if subprocess latency (~50-500ms) becomes a bottleneck.
8. **Cross-repo graph** -- index all 4 EPYC repos into one graph to capture cross-repo dependencies (orchestrator -> llama.cpp binary paths, research -> orchestrator registry references).
9. **Re-indexing automation** -- add GitNexus re-indexing to `session_init.sh` with a HEAD sha staleness check. Current indexes go stale as code changes. Incremental re-indexing takes 2-5s.
10. **Crawl4AI deployment (post-AR-3, gated on WebFetch failure data)** -- if web_research sentinel data shows significant JS-heavy page fetch failures, deploy Crawl4AI Docker container alongside SearXNG. Apache-2.0, no API keys, local LLM extraction via Ollama. Evaluate as fetch backend for ColBERT reranker S5 pipeline.

### Known Issues
- `gitnexus impact` has a known segfault (exit 139) on some queries due to a KuzuDB native binding issue. `gitnexus context` is reliable. All calls must be wrapped in try/except with timeout.
- GitNexus license is PolyForm Noncommercial 1.0.0 -- fine for personal/research use, not for commercial distribution. If licensing becomes a constraint, the core patterns (tree-sitter + leidenalg + kuzu, all with Python bindings) can be reimplemented in ~500-800 lines.
- Disk usage: ~50MB per indexed repo (KuzuDB + HNSW index). All 4 repos total ~200MB.

## Crawl4AI — Self-Hosted Web Crawler for LLMs

Crawl4AI (intake-372, 51K+ GitHub stars, Apache-2.0) is a self-hosted async web crawler designed for LLM consumption. It fills the deep page scraping role that WebFetch cannot handle for JS-heavy pages and complex PDFs, complementing SearXNG which handles search aggregation.

Key capabilities: async Playwright-based crawling with browser pool management, BM25 content filtering for relevance, LLM extraction with local models (Llama 3, Mistral via Ollama integration), HTML-to-markdown conversion for LLM-ready output, and Docker deployment with no API keys required.

**Integration path**: Deploy as a Docker container alongside SearXNG. In the web_research pipeline, SearXNG finds URLs via search aggregation, Crawl4AI extracts page content for JS-heavy or dynamic pages where the current `WebFetch` tool fails. Also a candidate for the ColBERT reranker fetch step (colbert-reranker-web-research.md S5) where fetched pages need reliable content extraction.

**MCP integration**: Crawl4AI can be exposed as an MCP tool for Claude Code sessions, following the same pattern as the mcp-searxng bridge (intake-361). This provides an alternative to direct Python integration for agent workflows that need deep page scraping.

**Policy context**: Selected over Firecrawl (intake-364/365, 108K+ stars) due to the open-source-only infrastructure preference. Firecrawl's cloud-first SaaS model, credit-based pricing, and reduced self-hosted feature parity conflict with the project's self-hosted philosophy. Crawl4AI evaluation is gated on post-AR-3 web_research sentinel data: if WebFetch succeeds on >90% of pages, neither tool is needed short-term.

> Source: [SearXNG Search Backend](/workspace/handoffs/active/searxng-search-backend.md) -- intake-364/365/372, Crawl4AI Docker deployment, MCP integration, open-source-only policy

## Open Questions

- Is the Node.js runtime dependency acceptable long-term, or should core patterns be reimplemented in Python? tree-sitter, leidenalg, and kuzu all have Python bindings. Estimated effort: ~500-800 lines.
- What is the right re-indexing cadence? Options: manual after major changes, session_init.sh at session start (recommended), post-commit hook (2-5s incremental).
- How should GitNexus context interact with the existing `gathered_context` in `_execute_turn()`? Additive injection (simplest) vs competitive replacement of grep-based gathering (more efficient but riskier).
- Can the Leiden cluster skill files replace manual agent role descriptions, or are they too granular for routing decisions?
- How does tool output compression interact with the Omega problem? If compressed tool outputs are more information-dense, they may improve REPL-mode accuracy on suites where tools currently hurt.
- What is the JS-heavy page failure rate with WebFetch in production web_research sessions? This determines whether Crawl4AI deployment priority should be elevated.

## Related Categories

- [Agent Architecture](agent-architecture.md) -- tool implementation is a subsystem of the orchestrator's coding agents
- [Routing Intelligence](routing-intelligence.md) -- tool availability (e.g., web_search) can attenuate factual-risk scores in routing decisions
- [Memory Augmented](memory-augmented.md) -- hybrid search pattern (BM25 + semantic + RRF) applicable to episodic memory retrieval
- [Context Management](context-management.md) -- tool output compression is an upstream compression layer complementary to session-level context folding
- [Search & Retrieval](search-retrieval.md) -- Crawl4AI complements SearXNG search aggregation with deep page content extraction

## Source References

- [GitNexus codebase intelligence](../research/deep-dives/gitnexus-codebase-intelligence.md) -- 8-phase indexing pipeline, 7 MCP tools, hybrid search (BM25+semantic+RRF), Leiden clustering, confidence-scored edges, process-grouped results
- [GitNexus orchestrator integration](../research/deep-dives/gitnexus-orchestrator-integration.md) -- 5 integration options ranked by ROI, context injection > tool calling insight, re-indexing strategy, KuzuDB direct query path
- [tool-output-compression.md](../handoffs/active/tool-output-compression.md) -- 7-handler output compression (60-90% savings), feature-flagged, layered before spill mechanism
- [repl-turn-efficiency.md](../handoffs/active/repl-turn-efficiency.md) -- frecency file discovery, combined operations, contextual suggestions for REPL efficiency
- [intake-269](https://github.com/nvk/llm-wiki) nvk/llm-wiki -- Claude Code plugin for LLM-compiled knowledge bases (adopt_patterns, high relevance)
- [intake-277](https://github.com/NousResearch/hermes-agent/pull/5100) Hermes Agent PR#5100 LLM Wiki Skill -- Karpathy pattern for structured knowledge compilation (already_integrated)
- [intake-321](https://github.com/forrestchang/andrej-karpathy-skills) Karpathy-Inspired Claude Code Guidelines -- CLAUDE.md plugin pattern (already_integrated)
- [intake-330](https://github.com/tirth8205/code-review-graph) code-review-graph -- AST-based code review with 8.2x token reduction over full-file review (worth_investigating)
- [intake-337](https://github.com/addyosmani/agent-skills) Agent Skills -- production engineering workflows for AI coding agents (worth_investigating)
- [intake-340](https://github.com/Kohei-Wada/taskdog) Taskdog -- task management with schedule optimization (not_applicable)
- [Integration Test Coverage](/workspace/handoffs/active/integration-test-coverage.md) -- 61 integration tests with real REPL + mock LLM pattern, GraphRunContext factory, risk-weighted coverage classification
- [Progress 2026-04-14](/workspace/progress/2026-04/2026-04-14.md) -- Coverage tranches A-L (sessions 2-20), 100%-feasibility audit methodology, seeding control-plane characterization
- [SearXNG Search Backend](/workspace/handoffs/active/searxng-search-backend.md) -- intake-372 Crawl4AI (self-hosted web crawler, Apache-2.0, Docker deployment, MCP integration path), intake-364/365 Firecrawl (deferred: cloud-first SaaS)
- [Magika deep dive](/workspace/research/deep-dives/magika-filetype-detection.md) -- intake-398; Google AI content-type detector (ICSE 2025, Apache 2.0); byte-embedding MLP architecture; 225 ms cold-start, 2.8 ms/file on EPYC; not_applicable — no pipeline stage requires generic filetype detection on EPYC's five-format corpus
