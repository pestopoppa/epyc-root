# Internal Knowledge-Base RAG

> **Fold destination** (BRF-T1-F8, BRF-T1-1, route 1a, 2026-11-02): renamed from `internal-kb-rag.md`; absorbs 5 handoff(s) as `## Track:` sections at the end of this file (`colbert-reranker-web-research.md`, `document-parser-table-bench.md`, `opendataloader-pipeline-integration.md`, `searxng-search-backend.md`, `sliders-local-validation.md`). The body above the first track is the former `internal-kb-rag.md`.

**Scratch**: `/mnt/raid0/llm/tmp/codex-ni06-kb-20261006/`; owned APP worktrees `/mnt/raid0/llm/worktrees/codex-ni07-k2-20261006/`, `/mnt/raid0/llm/worktrees/codex-ni07-s9-20261006/`.

Retired ROOT publication custody: `/mnt/raid0/llm/tmp/codex-ni-root-legacy-retirement-20261030`; original heads, patches and exact dirty bytes remain preserved there.

**Status**: K1-K7 CERTIFIED 2026-06-13 — `epyc-orchestrator/src/retrieval/` (additive shared `colbert_encoder.py`, `markdown_chunker.py`, `kb_rag.py` build/update/query) + CLI + `.claude/hooks/post_commit_kb_rag_update.sh` + `.claude/skills/kb-search/SKILL.md` + unit tests. **Fresh K7 build**: 577 files / 18,010 chunks / 1,227.6 MiB embeddings, max corpus mtime `2026-06-13T00:26:51Z`. **K7 certification sweep complete** over the final 70-case pool (50 HotpotQA-template + 20 LoCoMo-template): best aggregate recall@10 is `recency_w0.1_s90_rerank_w0.3` at 0.6298, but `recency_w0.3_s90` is within the 2pp noise band at 0.6167 and is the only config with 0 missed-all-evidence cases. Decision: validate the temporal recency signal; do not promote cross-encoder rerank as a default without a consumer that explicitly prefers first-rank/recall@3 over miss-risk. K8 wikilink scorer remains deferred; the next concrete no-inference slice is doc maintenance only, not a retrieval-code change. K11 FTS5 lexical signal is implemented default-off in `epyc-orchestrator` `74120be`; the 2026-07-21 batch sweep found no recall uplift from lexical weights 0.1-0.3, so ColBERT-only `lexical_weight=0` remains the default.
**Created**: 2026-04-25 (from local-RAG architecture review of friend's stack)
**Categories**: search_retrieval, knowledge_management, document_processing
**Priority**: MEDIUM
**Effort**: ~1–2 inference-free days end-to-end (minimal version)
**Depends on**: shared encoder layer extracted from `colbert-reranker-web-research.md` (S3/S4 ONNX runtime + GTE-ModernColBERT-v1 plumbing already in place)
**Sibling consumer**: [`colbert-reranker-web-research.md`](knowledge-pipelines.md#track-colbert-reranker-web-research) — reuses the same ONNX/MaxSim encoder, but for *external* search snippets gated on AR-3 data. This handoff is for *internal* knowledge and is **not** AR-3-gated.

## 2026-11-09 audit refresh

*Premise reset.* The orchestration stack has been off for a long time and no traffic is flowing; Autopilot is on operator HOLD. Goal: stack running by end of November 2026, in a brand-new era. Nothing in this handoff truly waits on the Autopilot HOLD; compute rows go through normal keeper grants.

- **Index row `Next action` was entirely done and is stale.** Fence fix `8b3706f3b` (2026-11-07, ancestor of origin/main); R36 republished and finished (final record 2026-11-08T16:51:02Z, 65/65 paired pages, ODL table TEDS 0.265 vs PaddleOCR-VL 0.910 over 52 GT tables; **observation only, not a Phase D gate verdict**); the ODL-013 r2, G14 r2 and Unlimited-OCR r2 rows were filed 2026-11-08 10:37Z; **P-DOCPARSE-1 ratified** (`artifacts/operator/ratify_p_docparse_1_20261108.json`, commit `4c6565a27`, ancestor of origin/main); **ODL-013 r2 is a formal NO DECISION** (LiteParse minus ODL +0.0385, CI [0.0176, 0.0614] > 0, but LiteParse median latency 676.9 ms vs ODL 237.2 ms fails the adopt latency clause; routing default unchanged).
- **Current next actions, in order:** (1) the KB index is broken (box below; rebuild dispatched separately, not here); (2) Phase C is rescoped to the 65 eligible pages with keeper custody, and the table-path decision needs an operator rule for a 65-page result (Decision needed under Phase D); (3) install the G14 candidate; (4) copy ODL-013 r2 evidence into the repo.
- **Doable now (no compute):** G14 install and parity check, ODL-013 durable evidence copy, Unlimited-OCR receipt adjudication, SX-6 driver script, SLIDERS 0.1-0.3 prep, KB-GS-1 question set.
- **Needs compute (normal grants):** SLIDERS final filler row, remaining parser arms, SX-6 sentinel (needs the stack to bring SearXNG up), KB-GS-1 arms.
- Anchor note: the filed OCR verdict cites `knowledge-pipelines.md:2540`; the box is the one by text ("Run the canonical Unlimited-OCR profile as a fresh matched A/B"). `BACKLOG-handoff-sliders-local-validation.md` still cites `sliders-local-validation L702`, which is the KB-GS-1 box in this file: re-resolve by text.

- [x] **PIP04-KB-INDEX-BREAK — the KB RAG index is stale and `kb_rag` query and update are failing (found 2026-11-09).** Orchestrator commit `7d92b1a8` (2026-10-31) bumped `colbert_encoder.PREFIX_CONVENTION` from `qd-v1` to `qd-v2` ("qd-v1 stores must be rebuilt in a fresh path"). The live store `data/kb_rag/index-qd-v1/` is still stamped `prefix_convention=qd-v1` (stamped_at 2026-08-12T21:32:15Z, verified read-only), and `kb_rag._roles_for_convention` raises `ValueError` for it (`src/retrieval/kb_rag.py:~327-337`, called from build, update_files and query), so `kb_rag.query` and every post-commit update fail; the update hook swallows the error as non-fatal (`logs/kb_rag_update.log` shows ~2,156 such errors). The newest chunk is 2026-10-31T08:30Z. Coverage did not survive the 11-02/03 fold either: 26 of 38 active handoffs are unindexed (including this file), 7 indexed paths no longer exist. **The qd-v2 rebuild is being dispatched separately: do NOT rebuild from this handoff.** Done when a fresh `index-qd-v2` path is built, `DEFAULT_INDEX_DIR` points at it, `kb_rag.query` answers, the update hook stops erroring, and the index covers all current `handoffs/active/*.md`; also make the update hook fail loudly (or write a freshness marker) instead of swallowing a convention mismatch, and update the kb-search skill text ("~53 active handoffs / 24 wiki articles"). Related: `scripts/lab/run_job.py` kb_rag context (`orchestration/lab_jobs.yaml:46,133`) degrades silently on this error. (added 2026-11-09; owner of the rebuild: separate dispatch) ✅ 2026-11-10 pipeline-mgmt: met. The qd-v2 store was built 2026-11-09 by the separate dispatch (`data/kb_rag/index-qd-v2`, stamped qd-v2 13:34Z, last write 20:33Z); `DEFAULT_INDEX_DIR` and the hook default point at it (orchestrator `897e30ad`); `cli.py query` answers from the shared clone (top hit `handoffs/active/churn-pipeline.md`); read-only coverage check: 2392 indexed files, 0 of the current `handoffs/active/*.md` missing, 1 dead path (`handoffs/completed/churn-pipeline.md`, cleared by the next hook delta); the last `unknown prefix convention` ValueError in `logs/kb_rag_update.log` precedes the build and the next update returned `ok` under qd-v2 (the two `database is locked` failures overlapped the build). The hook already prints a loud CONVENTION MISMATCH line. Silent lab degradation fixed in orchestrator `5a4fb7cb`: `kb_rag.check_index_convention()` + `IndexConventionError`, and `scripts/lab/run_job.py` raises `LabRunnerError` instead of recording a refused store as `kb_rag_no_results` (tests: 131 passed over the kb_rag/lab/federation suites). kb-search skill convention paragraph updated (qd-v1 is refused, not a rollback). [no-belief: code fix and read-only verification, no measurement]
  - 2026-11-09 wrap-up check (box stays OPEN; the clone check failed): `/workspace` (root) was fast-forwarded to `3ac7ba9cd`, but it holds no `src/retrieval/kb_rag.py`; the code and its hooks live in the shared orchestrator clone. There `origin/main` already points `DEFAULT_INDEX_DIR` at `index-qd-v2` (merge `b4e25aa1`, rebuild row PASS, `data/kb_rag/index-qd-v2/` exists), but the clone's local `main` (`98221350`) is 62 commits behind and still reads `index-qd-v1`. REMAINING STEPS: (1) fast-forward the shared orchestrator clone to origin/main (needs the operator or its owning session; the clone has local edits to `orchestration/model_registry.yaml`), then confirm `grep -n DEFAULT_INDEX_DIR src/retrieval/kb_rag.py` shows `index-qd-v2` and `kb_rag.query` answers; (2) coverage of all current `handoffs/active/*.md` and the loud-failure/freshness-marker change to the update hook are not shown by `b4e25aa1` (it touched config, `parallel_reembed.py`, `kb_rag.py`, two tests) and remain unverified; (3) the kb-search skill text. [no-belief: not-a-result]
  - **2026-11-09 rebuild FILED (row `kb-rag-qd-v2-rebuild-20261109`, rc 0, verdict PASS; the first attempt's encode unit was terminated rc -15, the resume finished in 104 s; result `/mnt/raid0/llm/tmp/kb-rag-qd-v2-rebuild-20261109/out/RESULT.json`):** fresh `data/kb_rag/index-qd-v2`, 52,436 chunks = manifest chunks, `prefix_convention` qd-v2, probe query 'DeepSeek V4.1 Flash evaluation' returns `handoffs/active/deepseek-v41-flash-evaluation.md` at rank 2 of the top results (rank 1 is a completed-through sibling). Orchestrator main `b4e25aa1` merges the cutover (`DEFAULT_INDEX_DIR` = `index-qd-v2`, `PREFIX_CONVENTION` qd-v2); the root hook `.claude/hooks/post_commit_kb_rag_update.sh` now surfaces a convention mismatch (root `50f9bb342`). The kb-search skill's stale counts were refreshed by this wrap-up. Coverage by content: the qd-v2 catalog has 38 of the 39 current `handoffs/active/*.md` (missing `churn-pipeline.md`, newer than the build) and no indexed path that no longer exists.
  - **NOT ticked, one step outstanding:** the shared orchestrator clone `/workspace/repos/epyc-orchestrator` is still at `98221350` with `DEFAULT_INDEX_DIR` = `index-qd-v1` (`src/retrieval/kb_rag.py:66`) and one dirty file, so live consumers there (the post-commit update hook, `kb_rag.query`, `scripts/lab/run_job.py`) still hit the `ValueError`. It needs a sync to origin/main `b4e25aa1`; the first post-sync update also adds `churn-pipeline.md`. A wrap-up does not modify a shared clone without the owner's go-ahead, so this is filed as the box below. [no-belief: status, native result filed by the row]
  - [ ] **PIP04-KB-INDEX-LIVE-SYNC — sync the shared orchestrator clone to origin/main so the live consumers read `index-qd-v2`, then confirm the update hook stops erroring.** Done when `kb_rag.query` from `/workspace/repos/epyc-orchestrator` answers, `logs/kb_rag_update.log` shows no new `ValueError` after one commit, and `churn-pipeline.md` is indexed. [no-belief: sync task]
- [x] **PIP04-KB-SEED-UNBOUND — `operator_seed_strategies.yaml` names a knob no code defines (found 2026-11-09).** `scripts/autopilot/operator_seed_strategies.yaml` in the orchestrator repo (line 72) seeds a "retrieval-weight sweep for NumericSwarm" with `bind_identifiers: kb_rag_retrieval` (status future, `source_handoff` the renamed `internal-kb-rag`); grep over `src/`, `orchestration/` and `scripts/` finds no definition of `kb_rag_retrieval` anywhere else. No Autopilot path measures KB retrieval quality (the K7 70-case pool lives in `data/kb_rag/eval`). Done when either a real `kb_rag_retrieval` knob exists in the orchestrator and the seed binds to it, or the seed is repointed to `knowledge-pipelines.md` and marked unbound. Autopilot stays on HOLD; this edits a seed file only. (added 2026-11-09) ✅ 2026-11-10 pipeline-mgmt: never built (the identifier appears only in the seed file, since `412392c3`; no `numeric_swarm.SURFACES` entry). Seed repointed to `source_handoff: knowledge-pipelines`, kept `bind_status: future` (the validator's documented-unbuilt state; there is no `unbound` value), `seeded_reason` states UNBOUND; test `test_kb_rag_retrieval_seed_is_documented_unbound_not_live` fails once a real surface exists so the seed gets flipped to live. Orchestrator `5a4fb7cb`; `--dry-run --audit-identifiers` ok over 48 rows. [no-belief: seed-file edit, no measurement]

## Objective

Stand up a ColBERT-based RAG over our own markdown knowledge base so every Explore-agent invocation can retrieve relevant prior context instead of grep/find blind across 53+ active handoffs and 24 wiki articles. Same plumbing as the web_research reranker (ONNX Runtime + MaxSim + small embedder), pointed at our own corpus and refreshed on commit via the existing PostToolUse hook pattern that already keeps GitNexus current.

## Why This Matters

| Problem today | Cost |
|---|---|
| Explore subagent grep/finds across `handoffs/active/`, `research/`, `wiki/`, `progress/` blind | Multiple turns per investigation; misses cross-cutting context |
| 53 active handoffs + 24 compiled wiki articles + 246 source documents are all keyword-indexed only | Topical/semantic queries miss documents that don't share keywords |
| GitNexus indexes **code only** — markdown is invisible to the code-intelligence pipeline | Knowledge ↔ code crossover queries (e.g., "where did we discuss this benchmark in handoffs?") have no path |
| `wiki/` (24 compiled articles synthesizing 246 sources) is the highest-density knowledge surface and currently has **no retrieval layer at all** | Highest-leverage corpus is hardest to query |

## Corpora to Index

| Source | Files | Why include |
|---|---|---|
| `wiki/*.md` | 24 articles + INDEX + SCHEMA | Highest-density compiled knowledge — primary corpus |
| `handoffs/active/*.md` | ~53 | In-progress work; the most-queried surface during Explore-agent runs |
| `handoffs/completed/*.md` | many | Historical decisions still load-bearing for active work |
| `research/*.md` (incl. `deep-dives/`) | ~30+ | Intake notes, deep dives, reference material |
| `progress/YYYY-MM/*.md` | many | Daily session summaries — best source for "when did we last touch X?" |
| `docs/chapters/*.md` (in `epyc-inference-research`) | many | Compiled chapter knowledge from research repo |

**Excluded**: `handoffs/archived/*.md` (intentionally — archived state is misleading by design; including it pollutes retrieval signal). `CHANGELOG.md` is a candidate for inclusion if Explore-agent traces benefit, but defer to a later iteration.

## Reusable Plumbing (from colbert-reranker-web-research.md)

| Component | Status | Location |
|---|---|---|
| GTE-ModernColBERT-v1 ONNX model | ✅ on disk | `/mnt/raid0/llm/models/gte-moderncolbert-v1-onnx/` |
| `onnxruntime` in orchestrator venv | ⚠️ drifted missing 2026-06-12; `/mnt/raid0/llm/pace-env` works | restore orchestrator venv or explicitly bless `pace-env` before K7 |
| MaxSim + per-token 128-dim embeddings | ✅ designed | colbert-reranker-web-research.md S3 |
| EPYC latency probe | ✅ measured | 180 ms / 10-snippet rerank call (S4) |
| `LATEON_MODEL_PATH` env override pattern | ✅ landed | NIB2-47 (extends to alternate ColBERT models) |

**Goal**: extract the encode/MaxSim layer into a shared module that both web_research reranking and internal-KB RAG import. The ONNX session, tokenizer, and MaxSim implementation are corpus-agnostic; only the indexer + storage + query-CLI differ.

## Architecture (proposed)

```
                                                   ┌─ web_research (existing, S5 gated on AR-3)
ColBERT encoder (shared)                           │
  + MaxSim                ──┬──> reranker call ────┘
  + ONNX runtime           │
                            └──> KB indexer ───┬──> per-doc token embeddings (npz/parquet)
                                               ├──> heading/paragraph chunk index (sqlite)
                                               └──> query CLI / Python API ──> Explore subagent
                                                          ▲
                              PostToolUse-on-commit ──────┘  (incremental rebuild for changed files)
```

**Storage**: per-document `.npz` of token embeddings + a SQLite catalog mapping (chunk_id, file_path, line_range, heading_path, mtime, content_hash). Per-document files keep incremental rebuild cheap — only re-encode files whose `content_hash` changed since last index.

**Chunking**: heading-aware (split at `^#{1,3}` boundaries with a max-chars cap). Heading hierarchy carried into the chunk metadata so retrieval results can show breadcrumbs (`handoffs/active/foo.md > ## Phase 2 > ### Subsection`).

**Query**: top-K snippet retrieval with MaxSim against the encoded query, returns `(file_path, heading_path, line_range, snippet, score)` tuples. Default K = 8, callable returns top-3 after rerank.

## Work Items

- [x] **K1: Extract shared encoder module** — Pull the ONNX session + tokenizer + MaxSim implementation out of the web_research path into `epyc-orchestrator/src/retrieval/colbert_encoder.py` (or similar). Single class instance, lazy-loaded, used by both consumers. ~1 h. Cross-coordinates with `colbert-reranker-web-research.md` S5 — both should import the same module.
- [x] **K2: Corpus configuration + chunker** — Define `kb_rag_config.yaml` listing corpus roots + glob patterns + exclusions (archived/). Implement heading-aware chunker (`src/retrieval/markdown_chunker.py`). Unit tests on a fixture set. ~2 h.
- [x] **K3: Initial index build** — Walk corpus, encode every chunk, write per-doc `.npz` + SQLite catalog at `data/kb_rag/index/`. CLI: `python -m epyc.kb_rag build`. Measure end-to-end time on full corpus (expect: ≤5 min for ~150 markdown files at 180 ms/encode). ~3 h.
- [x] **K4: Query CLI + Python API** — `python -m epyc.kb_rag query "<question>" [--top-k 8]` returns ranked chunks with breadcrumbs. Python API for orchestrator/Explore-agent integration. Result schema: `[{file, heading_path, line_range, snippet, score}, ...]`. ~2 h.
- [x] **K5: Index-on-commit hook** — Extend the existing PostToolUse-on-commit hook (currently runs `npx gitnexus analyze` for code) to also run `python -m epyc.kb_rag update --since-commit HEAD~1` for markdown changes. Detect changed files via `git diff --name-only` filtered by corpus globs; re-encode only those. ~1 h.
- [x] **K6: Explore-subagent integration** — Add a thin tool wrapper (e.g., `kb_search` MCP tool or in-orchestrator helper) so Explore subagents call the KB-RAG instead of grep-first for semantic queries. Document the pattern in `.claude/skills/...` or agent file overlays. ~2 h.
- [x] **K7: Validation pass — Flywheel-template eval** (rewritten 2026-04-28, from intake-492). Adopt Flywheel's HotpotQA + LoCoMo eval **methodology** (NOT its harness code — Flywheel ships as Node/MCP/Obsidian-coupled `demos/hotpotqa/` + `demos/locomo/`; we re-implement in Python against our own corpus). Two protocols:
  - **HotpotQA-style retrieval probe**: assemble a 4,960-doc-pool-equivalent over our wiki + active handoffs + research + completed-handoffs (target: 4,000–5,000 markdown chunks after K2 chunking; pool size dictated by corpus size, not arbitrary number). Curate ~50 multi-hop questions whose ground-truth evidence spans 2+ documents. Measure document-recall@k for k ∈ {3, 5, 10}, and KB-RAG top-3 vs grep on the same questions. **Note**: 4,960-doc pool is sui generis (Flywheel's choice — neither HotpotQA-distractor 10-doc nor fullwiki); record this methodology choice explicitly so future cross-paper comparison is honest.
  - **LoCoMo-style multi-session probe**: simulate ~20 multi-session "agent investigations" (e.g., "follow the v3 kernel rebase across handoffs and progress logs over 4 weeks"). Measure evidence-recall (did KB-RAG return the chunks containing the load-bearing facts?) and answer accuracy with a small judge LLM in noisy-grading mode. Match Flywheel's reported single-hop / multi-hop split if the question pool supports it.
  - **Variance band**: per Flywheel README, ~1 pp run-to-run variance from LLM non-determinism is the noise floor. Any cross-paper or cross-config delta under ~2 pp is within noise — record this explicitly so KB-RAG decisions never chase noise.
  - Effort revised: ~2 sessions (vs original 1 h estimate). Output: `data/kb_rag/eval/hotpotqa_template_results.json` + `loco_template_results.json` + a one-page summary in `data/kb_rag/eval/SUMMARY.md`.
  - Cross-link: intake-492 (Flywheel) and `research/intake_index.yaml` entry. Harness code is NOT being lifted — only methodology.
  - **2026-06-12 diagnostic note**: a small hand-curated 8-case sweep ran against the stale May-30 index with `/mnt/raid0/llm/pace-env`. It is not a K7 substitute. Before a decision-grade sweep: restore/bless runtime, refresh the index, create the K7 query/evidence set, then rerun configs.
  - **2026-06-13 seed eval note**: fresh build + 20-case seed sweep completed at `/mnt/raid0/llm/tmp/kbrag_k7_eval_20260612/summary.json`. Index: 577 files / 18,010 chunks / 1.2 GiB embeddings, max corpus mtime `2026-06-13T00:26:51Z`. Best recall@10 config: `recency_w0.1_s90` at 0.6417 overall (HotpotQA-template 0.6944, LoCoMo-template 0.5625), 0 missed-all-evidence cases. `rerank_w0.3`/`rerank_w0.6` improve recall@3 to 0.4417 and first-evidence rank to ~2.1 but lose recall@10 and miss 3 all-evidence cases. Treat as calibration evidence, not certification: the harness metadata explicitly says this is a seed suite, not the final 50+20 pool.
  - **2026-06-13 certification-pool note**: `feat/kbrag-k7-eval` commit `edba4d9` adds `scripts/kb_rag/k7_cert_cases.json` with the final 70-case decision pool (50 HotpotQA-template + 20 LoCoMo-template). Validation command checked JSON parse, protocol counts, duplicate IDs, and existence of every evidence file; `tests/unit/test_kb_rag_eval.py` still passes. Run with `--cases scripts/kb_rag/k7_cert_cases.json` against the fresh K7 index.
  - **2026-06-13 certification result**: clean-window parallel sweep completed against `/mnt/raid0/llm/tmp/kbrag_index_k7_20260612`; combined artifacts at `/mnt/raid0/llm/tmp/kbrag_k7_cert_parallel_20260613_075405/combined/{summary.json,rows.jsonl,cases.json}` (`420` rows, `ok=true`, no missing evidence files). Overall recall@10 ranking: `recency_w0.1_s90_rerank_w0.3` 0.6298 / missed-all-evidence 3; `recency_w0.3_s90` 0.6167 / missed 0; `recency_w0.1_s90` 0.6131 / missed 1; `rerank_w0.6` 0.5905 / missed 5; `rerank_w0.3` 0.5810 / missed 4; `maxsim` 0.5690 / missed 5. Protocol split for the zero-miss candidate: HotpotQA-template recall@10 0.6567, LoCoMo-template recall@10 0.5167. Because the top two configs differ by only 1.31pp (< the declared 2pp noise floor), prefer `recency_w0.3_s90` for safety/default-candidate decisions and reserve `recency_w0.1_s90_rerank_w0.3` for workloads optimizing first-evidence rank/recall@3.
- **[declined: ws58 2026-11-03 content-review: LOW/defer by its own text; no consumer]** **K8 (LOW priority, defer): wikilink learning-loop scorer** (NEW 2026-04-28, from intake-492). Flywheel's auto-wikilink suggestion uses an accept/reject feedback loop that updates a graph-edge scorer over time (alias + co-occurrence + graph + semantic context). Adapt as a wiki-cross-reference quality signal for the existing wiki/INDEX.md compilation pipeline. Defer until KB-RAG K1–K7 ships and we have a measured wiki-cross-link gap to address. NOT blocking K1–K7.

## Open Questions

1. **Embedder choice**: reuse the existing GTE-ModernColBERT-v1 (150M, BEIR 54.67) for both encode-query and encode-doc, or pair a smaller embedder for indexing (e.g., mxbai-edge-colbert-32m) with GTE for rerank? Indexing latency is dominated by doc count × tokens-per-doc; for ~150 files this matters less than for a 100K-doc corpus. **Recommendation**: start with GTE for both; revisit only if index-build time exceeds 10 min.
   - **Candidate to track (2026-05-29, via research intake intake-652; CORRECTED 2026-07-29 via intake-920 Stage-2 dive)**: **LFM2 / LFM2.5-ColBERT-350M** (Liquid AI) — a late-interaction retrieval/reranker embedder in the LFM2 "Nanos" line, open-weights (LFM Open License v1.0: Commercial Use is conditioned on a $10M annual-revenue Threshold — non-binding at our scale, but it is NOT "no restrictions" as the vendor blog claims). Direct architectural analogue to GTE-ModernColBERT for this corpus.
     - ~~**Deployment caveat (verified against Liquid docs 2026-05-29)**: requires PyLate + a PLAID index; no GGUF / llama.cpp / Transformers / ONNX / MLX — a PyLate/HF-only eval candidate, not a drop-in.~~ **STRUCK 2026-07-29 — FALSE for the 2.5 generation, and already false for the 1.x generation when it was written.** **THREE GGUF repos exist**: `LFM2.5-ColBERT-350M-GGUF` and `LFM2.5-Embedding-350M-GGUF` (both **2026-06-16**) **and `LFM2-ColBERT-350M-GGUF` (2026-01-05 — ~5 months BEFORE this line was written)**. Each ships **7 quants** (BF16/F16/Q4_0/Q4_K_M/Q5_K_M/Q6_K/Q8_0) plus reference `colbert-rerank.py` / `dense-retrieve.py` driving `llama-server /embedding` with client-side MaxSim. The ColBERT backbone is **BIDIRECTIONAL** (`architectures: Lfm2BidirectionalModel`, 17 layers = 10 conv + 6 attn + 1 dense), not causal as previously assumed.
     - **Our frozen v8 tree already supports it end-to-end, no kernel work**: `conversion/lfm2.py:67` `@ModelBase.register("Lfm2Model","Lfm2BidirectionalModel")` → `LFM2ColBertModel` with `add_causal_attention(False)` + `dense_2` projection; `src/models/lfm2.cpp:194-195` non-causal symmetric-padded conv path; `src/llama-graph.cpp:3283` `build_dense_out()`. The run path is the vendor's one-liner: `llama-server -hf LiquidAI/LFM2.5-ColBERT-350M-GGUF --embeddings`. (Gap, and deliberately NOT closed: `Lfm2BidirectionalForMaskedLM` — the *encoder* arch, intake-920 — is unregistered; that buys nothing until an encoder workload exists.)
     - **Counterweight the swap case never had**: on the vendor's own numbers the **ENGLISH** advantage over our certified GTE-ModernColBERT-v1 is **+0.7pp NDCG@10 (0.687 vs 0.680 — inside our declared 2pp noise floor)** and **−0.6pp MKQA-11 Recall@20 (0.748 vs 0.754, i.e. the INCUMBENT is ahead)**. The large gaps are entirely **multilingual** (AVG 0.605 vs 0.489; ar 0.551 vs 0.309; ko 0.590 vs 0.368). Our KB corpus is English markdown, so expected gain is ~zero unless we index non-English sources. This converts the pending K-eval from a **cost** question into a **scope** question — see the 2026-07-29 section below. Deep dive: `research/deep-dives/lfm2-lfm25-family-deep-dive.md`.
2. **Chunking unit**: pure heading-bounded vs sliding-window (e.g., 512-token windows with 64-token stride)? Heading-bounded gives semantic cohesion but variable size; sliding-window gives uniform size but breaks headings. **Recommendation**: heading-bounded with max-chars cap (split a too-long section at the next `^- ` or paragraph boundary).
3. **Staleness vs immediacy**: index-on-commit means a session that just edited a handoff would query a stale index until commit. Acceptable? **Tentative answer**: yes for the first iteration; add optional `--since-uncommitted` flag later if the staleness window proves painful.
4. **Cross-repo corpora**: include `epyc-inference-research/docs/chapters/*.md` and `epyc-orchestrator/AGENTS.md`-style files? They're outside `epyc-root` but topically essential. **Tentative answer**: yes, behind explicit roots in the config; the indexer doesn't care about repo boundaries.
5. **Wiki re-compile coupling**: `wiki/INDEX.md` notes a "Last compiled" date; wiki articles synthesize source documents. If a wiki article is regenerated, the index naturally re-encodes it. No special handling needed.

## Non-Goals (explicit)

- **No web UI** — CLI + Python API only. Aligned with the "skip Web RAG UI" decision from the architecture review.
- **No auth / scopes / token boundary** — single-user, no external exposure.
- **No replacement for GitNexus** — code stays in GitNexus, markdown goes here. Two indices, no overlap.
- **No vector DB service** — flat per-doc `.npz` + SQLite catalog. We can adopt a vector DB (LEANN, FAISS, qdrant) later if scale demands it; the LEANN evaluation in `handoffs/archived/leann_vector_db.md` was gated on MemRL size and is unrelated to this corpus.

## Cross-References

- **Sibling consumer**: [`colbert-reranker-web-research.md`](knowledge-pipelines.md#track-colbert-reranker-web-research) — extract shared encoder module (K1) coordinates with S5.
- **Indexing pattern**: existing GitNexus PostToolUse hook documented in `/workspace/CLAUDE.md` § "Keeping the Index Fresh" — K5 generalizes this to markdown.
- **Excluded by design**: `handoffs/archived/leann_vector_db.md` (different problem: episodic memory scaling, not document retrieval).
- **Pipeline integration index**: see `pipeline-integration-index.md` for cross-cutting concerns (RAM budget, disk allocation under `data/`).

## Key Files (proposed)

| Path | Purpose |
|---|---|
| `epyc-orchestrator/src/retrieval/colbert_encoder.py` | Shared encoder (K1) |
| `epyc-orchestrator/src/retrieval/markdown_chunker.py` | Heading-aware chunker (K2) |
| `epyc-orchestrator/src/retrieval/kb_rag.py` | Index build + query (K3, K4) |
| `epyc-orchestrator/scripts/kb_rag/build_index.py` | CLI entry point (K3) |
| `epyc-orchestrator/scripts/kb_rag/query.py` | Query CLI (K4) |
| `epyc-orchestrator/data/kb_rag/index/` | Per-doc `.npz` + `catalog.sqlite` (K3 output) |
| `epyc-orchestrator/config/kb_rag_config.yaml` | Corpus roots + globs + exclusions (K2) |
| `.claude/hooks/post_commit_kb_rag_update.sh` | Index-on-commit hook (K5) |

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-494] "Contexts are Never Long Enough: Structured Reasoning for Scalable Question Answering over Long Document Sets"** (arxiv:2604.22294, Stanford OVAL/Genie group, Joshi/Shethia/Dao/Lam)
  - **Framing**: ALTERNATIVE architecture to ColBERT-based RAG (NOT an upgrade lane on the same path). SLIDERS replaces retrieval with persistent SQL state — they share a problem statement but not a code path.
  - Relevance: directly addresses the same problem this handoff scopes — multi-document QA over a long corpus — but via per-question schema induction + LLM extraction into a relational database + SQL reasoning + provenance-aware reconciliation. Code released at `github.com/stanford-oval/sliders` (MIT) and on PyPI as `sliders-genie`.
  - Reported results (concrete): +6.6 pp avg vs union of baselines (RAG / base GPT-4.1 / DocETL / Chain-of-Agents / RLM) across FinanceBench / Loong / Oolong; **WikiCeleb100** (3.9M tokens, new) +~19 pp over next-best; **FinQ100** (36M tokens, SEC 10-Q derived, new) abstract reports ~32 pp / repo README reports ~50 pp — unresolved discrepancy.
  - Critical adoption blocker (Tier 2b): code paths hard-wired to **GPT-4.1 / GPT-4.1-mini** via Azure OpenAI / OpenAI public API at every stage (schema induction, relevance gating, extraction, primary-key selection, reconciliation controller+executor, SQL generation, answer synthesis, citation generation). **NO local-model code path** in the released repo. Earlier intake claim that SLIDERS "runs locally on any capable LLM" was unsupported. Adoption requires both endpoint substitution AND SQL-agent-loop revalidation on a Coder-30B/35B-class local model.
  - Other Tier 2b: schema hallucination is #1 LLM-to-SQL production failure; long-context relational reasoning underpredicts (arxiv:2510.03611); single-source (one Stanford group); per-query reconciliation cost is heavy (5 controller iter × 5 SQL × 3 retries × 20 inspections × LLM calls per stage); per-question schema induction uses a fixed taxonomy library (`sliders_taxonomy.json`) keyed by query-type × document-type, partly mitigating schema-design overhead.
  - Action: SLIDERS is an alternative architecture for K3/K4, NOT an upgrade lane. Do not block ColBERT plan on it. **Sequential evolution as a separate validation experiment** AFTER base ColBERT ships AND a focused experiment confirms a Coder-30B-class local model can drive the controller/executor loop. The reconciliation-pattern (provenance + rationale + metadata) is independently valuable for knowledge-base governance even at small scale and can be lifted without the full architecture.

- **[intake-492] "Flywheel — local-first MCP memory layer for AI agents over Obsidian/Markdown vaults"** (`github.com/velvetmonkey/flywheel-memory`)
  - Relevance: Flywheel is the closest *running implementation* of the architecture this handoff scopes — hybrid BM25 + optional local semantic search over a markdown vault, with section-aware snippets, frontmatter, and linked-context expansion in a single MCP call. Apache-2.0, Node/MCP, fully self-hostable.
  - Eval methodology (NOT code) is the portable win: HotpotQA 90.0% doc recall on a **sui generis 4,960-doc pool** (neither standard 10-doc distractor nor fullwiki — flag for cross-paper comparison), LoCoMo 81.9% evidence recall over 695 questions / 272 sessions, **~1pp run-to-run variance from LLM non-determinism**. Harness code itself ships as `demos/hotpotqa/` and `demos/locomo/` directories — demo-coupled to the Node/MCP/Obsidian runtime — so borrowing the harness means re-implementing the methodology in Python, not lifting code.
  - Key patterns: (a) wikilink learning-loop scorer (accept/reject feedback updates link weights) for our wiki cross-references; (b) hash-before-write + single-step undo log as a **portable abstract contract** for agent mutations (Node/Obsidian implementation is NOT lift-and-shift); (c) HotpotQA / LoCoMo eval methodology as a reusable template for K4 retrieval-quality measurement.
  - Caveat (Tier 2b): credibility 3 (1,092 commits + 3,292 tests + 385 releases + dual-OS dual-Node CI as engineering-rigor signals; capped at 3 by no peer review, no independent replication, contributor-graph confirmation not obtained). Self-reported benchmarks with ~1pp variance band — any cross-paper delta under ~2pp is within noise.
  - Action: borrow Flywheel's HotpotQA/LoCoMo eval **methodology** (4,960-doc pool, 695q LoCoMo split, ~1pp variance band) as a Python template for K4 retrieval-quality eval — harness code is Node/MCP/Obsidian-coupled and must be re-implemented. Evaluate the learning-loop wikilink scorer separately as an enhancement to the wiki-governance work.

## Research Intake Update — 2026-04-30

### New Related Research

- **[intake-519] "Granite-Embedding-97M-Multilingual-R2"** (HF `ibm-granite/granite-embedding-97m-multilingual-r2`, Apache 2.0, IBM, released 2026-04-29)
  - Relevance to KB RAG: **MEDIUM**. Candidate dense embedder for K-track retrieval. 97M params, ModernBERT backbone, 32K context, 384-dim embeddings, 200+ languages with 8 programming languages (code retrieval @ 60.5). MTEB Multilingual Retrieval 59.6 — claimed best open <100M-class multilingual score. Apache 2.0; ONNX, OpenVINO (incl. INT8), Sentence Transformers, vLLM-embedding endpoint; GGUF convertible (no native release).
  - Why it matters here: KB content is heavy on code + English + occasional multilingual; the 32K context is unusual at this scale and would let a single embedding cover entire CLAUDE.md / handoff files without chunking — directly relevant to K2/K3 indexing decisions. Throughput claim ~3× gte-multilingual-base 305M on reference HW makes ingestion-side cost low.
  - Tier 2b: BGE-M3 (~305M, ~63.0 MTEB) wins on raw quality but is 3× larger; retrieval-quality gap likely narrows on EPYC's English-heavy KB workload. The 59.6 / +8.7-vs-e5-small claim is self-reported on the model card; corroboration limited to the HF leaderboard and the Granite-R2 paper (arxiv:2508.21085, "Granite Embedding R2 Models"). No native GGUF — for CPU-quantized deployment plan to use OpenVINO INT8 path or our own ONNX→GGUF pipeline.
  - Action: when the K-track moves from stub to design phase, A/B Granite-97M-r2 vs (a) BGE-M3 (quality ceiling), (b) multilingual-e5-base (size-matched competitor), on a curated slice of CLAUDE.md + handoff content. Measure NDCG@10 + per-doc encode latency on EPYC.
  - Verdict: `worth_investigating`. Cross-ref `colbert-reranker-web-research.md` 2026-04-30 update — same model, evaluated for the web-research side of the dense-then-rerank stack.

#### Deep-dive refinement (2026-04-30; corrected 2026-07-29) — bench plan persisted

Deep-dive at [`/workspace/research/deep-dives/granite-embedding-97m-r2-evaluation.md`](../../research/deep-dives/granite-embedding-97m-r2-evaluation.md). Bench handoff at [`granite-97m-r2-bench-plan.md`](../completed/granite-97m-r2-bench-plan-completed-through-2026-08-23.md).

**Critical infra finding**: there is **no production multilingual retrieval today** — only English-only BGE-large-en-v1.5 routing pool on `:8090–:8095` (`/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/parallel_embedder.py`). Granite-97m-r2 (or any multilingual embedder) would be **net-new infrastructure**, not a swap-in.

**Phase-C correction (2026-07-29):** K1–K7 are certified, so the old “K2 is
the gate” wording is stale. `BULK-K-EMB-1` gives Granite 0.9222 NDCG@10 versus
BGE-M3 0.9150 at 4.36× lower wall-clock (1.614s versus 7.037s). Adopt Granite
as the default **if** this KB track activates a multilingual dense first stage;
do not replace the certified English ColBERT/BGE path or claim 32K performance
from this fallback-corpus result.

**The bench cannot run with "K-track activation" as the gate** — it needs the **K2 chunker output** specifically, since the eval corpus depends on having chunked KB content. The bench handoff includes a fallback eval-corpus path (100 code snippets from `epyc-orchestrator/src/` + 30 NL queries with manual labels, ~half day) that does NOT require K2, so the bench can run earlier if a K2-blocked K-track scope is undesirable. Decide which path to take when this handoff exits stub status.

**Other corrections**: ModernBERT IS supported in llama.cpp; the "Ollama unsupported" note refers only to Ollama's wrapper. 2,894 docs/s is GPU not CPU — calibrate expectations before benching. BGE-M3 ~63.0 figure is from MMTEB 131-task aggregation, NOT apples-to-apples with IBM's 18-task 59.6 — the bench needs to produce same-corpus same-metric numbers to settle the comparison.

### Architectural corroboration from intake-520 (2026-04-30)

- **[intake-520] "markdownfs (mdfs)"** (https://github.com/subramanya1997/markdownfs, MIT) — deep dive at [`/workspace/research/deep-dives/markdownfs-rust-mcp-vfs.md`](../../research/deep-dives/markdownfs-rust-mcp-vfs.md).
  - Relevance to this handoff: **architectural validation only — no code dependency, no plan change**.
  - The mdfs project ships a forward-looking design doc, `docs/semantic-index.md`, that independently arrives at the same architecture as K1–K7 here:

    | mdfs `semantic-index.md` | This handoff (K1–K7) |
    |---|---|
    | FS canonical, vector DB derived | git + filesystem canonical, FAISS/.npz derived |
    | Heading-aware chunking (title / heading / subsection) | Heading-aware split at `^#{1,3}` with max-chars cap (K2) |
    | Metadata: file_path, heading_path, commit_hash, author, perms | Metadata: file_path, heading_path, line_range, mtime, content_hash (K3) |
    | Index update: on write / on commit / on revert | PostToolUse-on-commit hook + content_hash diff (K5) |
    | Result shape: `{path, heading, score, excerpt}` | `{file, heading_path, line_range, snippet, score}` (K4) |
    | Principle: vector layer accelerates retrieval, FS remains truth | Same — FS is canonical, retrieval is derived |

  - Reading: this is independent corroboration that "FS-truth + derived vector index + heading-aware chunking + on-commit reindex" is the convergent architectural shape for markdown-agent-workspace retrieval, not a private design choice. Useful as design-risk reduction for K1–K7.
  - Caveats from the deep dive that do NOT change our plan: mdfs itself is 17-day-old / single-author / just-pivoted / MCP-runs-as-root / single-writer-per-state.bin and is **not adopt-as-substrate** material. The architectural pattern is portable; mdfs's own implementation is not.
  - No work-item delta. Pattern B is a confirmation, not a new K-task.

## Research Intake Update — 2026-05-20

### New Related Research

- **[intake-572] "Mirage: A Unified Virtual Filesystem For AI Agents"** (Strukto AI; github.com/strukto-ai/mirage, Apache-2.0)
  - **Relevance**: Mirage's two-layer cache architecture (index cache for metadata/listings + file cache for object bytes, RAM-default with optional shared Redis backend) is a third independent data point alongside markdownfs (intake-520) and this handoff's K1–K7 design. The cache-layer separation specifically maps to our K3 (content_hash for diff-detection) + K5 (PostToolUse-on-commit reindex) boundary.
  - **Delta from current plan**: Mirage uses a FUSE mount as its primary access path and chooses Unix command semantics over JSON-RPC; we chose ColBERT + heading-aware chunking with a `kb-search` Skill surface. The architectures are not interchangeable, but Mirage's RAM-default + Redis-shared cache shape is a useful reference for any future multi-process retrieval scenario (e.g., autopilot parallel-species workers sharing a hot KB cache). No work-item delta — file as a third-party design corroboration for the "shared cache layer over a derived index" pattern.

### Mirage Pattern Adoption — 2026-05-20 (design references, no runtime dep)

Three patterns lifted from `strukto-ai/mirage` source audit. Apply at design time for the K1–K7 work; do NOT take a dependency on Mirage itself (single-author, v0.0.2a0, viral hype-cycle stars, native-compile deps including mfusepy + tree-sitter-bash + jq + numpy>=2.4.3; revisit at v0.1.0 + sustained 2nd committer + first published benchmark, earliest 2026-08).

- **K-Pattern-A — Per-source `SUPPORTS_SNAPSHOT` flag + content-fingerprint contract** (Mirage `python/mirage/resource/base.py:46`). Each chunk source (markdown file, code symbol, transcript, eventual ingestable PDF) declares a class-level boolean: does its `chunk_fingerprint` (mtime+sha256 of source range) remain stable when content is unchanged? Sources that answer yes participate in the on-commit reindex diff (K5) and the drift-detection contract (K-Pattern-B); sources that answer no (e.g., a live-pulled web doc, a Skill that runs against current `git log`) bypass diffing and are always re-fetched. Cleaner than implicit special-casing every source type, and shifts the "is this stable enough to cache" decision to the source author rather than the indexer. Apply as part of K1 (source-type taxonomy) and K3 (content-hash for diff-detection) — add a `supports_snapshot: bool` field to each chunk source's metadata.

- **K-Pattern-F — `live_only_prefixes` companion declaration for non-replayable sources** (Mirage `workspace/snapshot/state.py:74`). Some sources (a `git log`-backed wiki page, a live `gh api`-driven status snippet, a Skill result that depends on the current process's mtime) can be indexed for retrieval but cannot be replayed deterministically from a snapshot. Mirage surfaces this honestly via a `LIVE_ONLY_MOUNTS` list in the snapshot state dict rather than pretending all backends are content-addressable. Apply at K2 (chunk-source registry): a chunk-source declared `live_only=True` produces retrievable text but is never written into the persistent vector index — only into the hot RAM cache for the session that issued the query. Avoids the failure mode where a six-month-old vector index returns embeddings of long-vanished `git status` snippets.

- **K-Pattern-V — `FORMAT_VERSION`-gated compiled-artifact state dict** (Mirage `workspace/snapshot/state.py:106-110`). The compiled KB index file (chunks.json or the ColBERT shard tarball) carries a `FORMAT_VERSION = "k7-v1"` constant; load-time mismatch surfaces an explicit "regenerate via `npx kb-compile`" error rather than silently mis-deserializing and producing garbage retrieval. Cleaner than ad-hoc try/except migrations — and crucial when we change the chunk schema (e.g., switching from heading-path tuples to hierarchical breadcrumb strings) since we'll inevitably do that as the corpus grows. Apply as the very first line of the eventual compiled-artifact format: `{"format_version": "k7-v1", "compiled_at": "...", "source_repo_head": "...", "chunks": [...]}`. Make `format_version` a required field at the schema level so the validator rejects untagged artifacts.

## Research Intake Update — 2026-05-20 (chunking-quality evaluation)

### New Related Research

- **[intake-579] "Adaptive Chunking: Optimizing Chunking-Method Selection for RAG"** (arxiv:2603.25333, Ekimetrics, LREC 2026)
  - **Relevance to K2**: Proposes 5 intrinsic, document-only metrics (RC, ICC, DCC, BI, SC) that can score K2 `markdown_chunker.py` output on fixture corpora **without downstream RAG ground truth** — a candidate unit-test quality signal for the heading-aware markdown chunker. Reported +30% questions resolved and +8-10 pp answer correctness via per-document method selection on a 33-doc / 3-domain / ~1.18M-token corpus.
  - **Caveat**: 33-doc corpus is a small empirical base; two metrics (ICC, BI) rest on the cohesion-within-chunk premise that intake-581 (HOPE) empirically falsifies.

- **[intake-580] "ekimetrics/adaptive-chunking"** — MIT-licensed Python implementation (`github.com/ekimetrics/adaptive-chunking`)
  - **Lift potential for K7 eval**: ~~Modular chunker ABC means K2's `markdown_chunker.py` can be slotted in as an additional candidate.~~ **CORRECTED 2026-07-25 (intake Stage-2a dive): there is NO chunker ABC.** The only `ABC` in `ekimetrics/adaptive-chunking` is `BaseParser` (PDF/Excel parsers); the five chunkers share no base class, no interface and no registry. Slotting ours in means writing our own harness, at which point the repo buys nothing — re-cost accordingly. The 5 metric implementations are the most lift-able piece (core MIT; only FMRE pulls `maverick-coref` CC BY-NC-SA 4.0). Useful for K7 if we want intrinsic chunk-quality scores alongside the HotpotQA/LoCoMo retrieval probes — those are corpus-extrinsic; the Ekimetrics suite is chunk-intrinsic and would catch chunker regressions that don't yet show up in retrieval-recall.

- **[intake-581] "A New HOPE: Domain-agnostic Automatic Evaluation of Text Chunking"** (arxiv:2505.02171, Brådland et al., SIGIR 2025) — **corroborates K2 design choice**
  - **Relevance to K2**: K2 chose heading-aware splitting at `^#{1,3}` boundaries with a max-chars cap (handoff Open-Question #2). That choice produces more-independent chunks at structural boundaries — and HOPE empirically finds semantic INDEPENDENCE between passages is the load-bearing retrieval-quality signal (+56.2% factual correctness with independence enforcement; intrachunk concept unity has **minimal impact**). The architectural choice was previously un-defended in the handoff; HOPE provides empirical support.
  - **Action for K7**: when the eval runs, capture HOPE three-level scoring on K2 chunker output as a secondary quality signal alongside the HotpotQA/LoCoMo retrieval-recall numbers. Will also serve as the side-by-side reference against the Ekimetrics metric suite (cross-link `opendataloader-pipeline-integration.md` 2026-05-20 update — same evaluation question over there).

### Next Actions

- [x] Bookmark the Ekimetrics MIT 5-metric implementation as candidate eval scaffolding for K7 ✅ 2026-07-29 — already indexed as [`intake-580`](../../research/intake_index.yaml) and documented above with its MIT core, the FMRE non-commercial dependency caveat, and the lack of a reusable chunker interface. Adoption remains gated on the HOPE-vs-Ekimetrics side-by-side from opendataloader Phase 2; this records the source only and adopts no metric or harness.
- **[declined: ws58 2026-11-03 content-review: a note for future reviews, not a task]** When defending K2's heading-aware chunking choice in any future review, cite HOPE's independence finding as empirical support rather than relying on the "natural for markdown" argument alone.

## Research Intake Update — 2026-05-21

### Hy-MT2-1.8B-1.25bit as optional multilingual pre-processor (narrow scope)

- **[intake-586] Hy-MT2 (Tencent Hunyuan, 2026-05-21 release)** — 33-language translation model family. The 1.8B-1.25bit variant is 440 MB on-disk (claimed 1.5x decode speedup) — small enough to live as a research-intake-pipeline tool rather than a server role.
- **Why this lands on the KB-RAG handoff**: CLAUDE.md routing guidance explicitly calls out Chinese-lab papers / EU/JP sources as a "prefer-SearXNG" case. Today, ingest of foreign-language abstracts relies on frontdoor (Qwen3.6) or ingest_long_context (Qwen3-Next-80B thinking ON) translating inline. Per user framing 2026-05-21, those models "already handle translation somewhat" — so a dedicated MT specialist is **overkill at 7B/30B scale** and only marginally useful at 1.8B-1.25bit scale.
- **Concrete adoption scope (narrow)**: optional tool, not a stack role. If/when the ColBERT ingest pipeline encounters foreign-language snippets that the existing model handles poorly (measure first), the 1.8B-1.25bit variant is a low-cost candidate to slot in as a pre-encode translation step. No standing role allocation. No autopilot routing.
- **Higher-leverage artefact (correctly scoped — see correction 2026-05-21)**: The **STQ1_0 llama.cpp kernel** (PR #22836) is generic at inference — it can decode any Sherry-QAT'd 1.25-bit weights. The **Sherry algorithm itself is QAT (training-time)**, not PTQ — applying it to an arbitrary worker would require ~10B tokens of QAT training that we have no infrastructure for. Today the only public Sherry-QAT'd weights are Tencent's Hy-MT1.5-1.8B and HY-1.8B-2bit; no Qwen3.6 / gemma4-26B-A4B / Qwen3.5-122B / Qwen3-Next-80B Sherry releases exist. So the kernel is "a decoder for weights only Tencent currently produces, and only at 1.8B class." Tracked on [[angelslim-techniques-evaluation]]; the PR #22836 watch is consolidated on `tq3-quantization-evaluation.md` (2026-06-12; formerly `llama-cpp-kernel-push-rebase`, archived to `../completed/`).

### What NOT to do

- Do NOT add Hy-MT2-30B-A3B or 7B as a stack role — existing multilingual coverage suffices for the workflows we run today.
- Do NOT commit to autopilot routing for a translation specialist before measuring whether the existing models actually have a quality gap on the foreign-language snippets the KB-RAG ingest actually receives.

Cross-references: [[searxng-bash-websearch-bridge]] (multilingual web-search ingest), [[colbert-reranker-web-research]] (external snippet pipeline), [[angelslim-techniques-evaluation]] (umbrella for the quant/early-exit techniques).

## Test Scope — Multilingual Ingest Quality-Gap Measurement (added 2026-05-21)

The 2026-05-21 Hy-MT2 intake left an open empirical question: do existing stack models (Qwen3.6 frontdoor, Qwen3-Next-80B ingest_long_context, gemma4-26B-A4B worker_general) have a measurable quality gap on foreign-language ingest content that a dedicated MT specialist (Hy-MT2-1.8B-1.25bit, 440 MB) would close? The answer is **contingent on what languages we actually see**, so the only way to resolve it is direct measurement. This subsection scopes that test.

### Hypothesis

- **H0 (overkill)**: For the foreign-language content the research-intake / KB-RAG pipeline actually encounters, inline translation via Qwen3-Next-80B (thinking ON) yields downstream summaries of equal quality to a pipeline that pre-translates with Hy-MT2-1.8B-1.25bit. The specialist provides no measurable lift.
- **H1 (niche found)**: For ≥1 language stratum the existing inline-translation pipeline measurably underperforms a pre-translate-then-summarize pipeline using Hy-MT2-1.8B-1.25bit. The gap is large enough to justify slotting the 440 MB specialist as an optional pre-encode step.

Decision threshold (set in advance to avoid post-hoc rationalization): **H1 holds if the pre-translation pipeline wins ≥60% pairwise on at least one non-Chinese-English stratum AND the win rate on Chinese/English is not significantly worse than baseline (i.e., no regression on the strong-coverage languages).**

### Language Stratification (refined 2026-05-21)

This is the load-bearing design choice. A test that pulls only Chinese-English samples will under-report H1 because all three stack models already cover that pair well. Required strata (≥10 samples each, target 40 total):

| Stratum | Sample target | Why | Hy-MT2 emphasis |
|---------|---------------|-----|-----------------|
| **Chinese (Simplified) → English** | 10 | Strong-coverage control; H1 must NOT win here or scoring is biased | Yes (general pair) |
| **European mainstream → English** (Italian, French, German, Russian) | 10 | **Primary user interest** — high-resource EU where existing stack models *should* be strong; a Hy-MT2 win here is the meaningful niche finding, since these are the languages the user's actual research-intake pipeline encounters | Yes (33-language scope) |
| **Japanese / Korean technical → English** | 10 | Medium-coverage; CJK shared script complications | Yes |
| **Mixed-script / structured content** (Chinese paper with English equations/code, JSON-embedded MT) | 10 | Tests structural fidelity; tokenizer-fertility edge case | IFMTBench-style |

Total: 40 snippets, ~200-500 tokens each (paper abstract scale, matches our actual research-intake unit of work).

**Dropped stratum (2026-05-21)**: Mandarin-minority/dialect (Tibetan/Mongolian/Uyghur/Cantonese). Per user direction — not represented in actual research-intake content. Hy-MT2's marketed strength on this stratum is therefore irrelevant to the user's workflow; testing it would inflate the H1 conclusion in a way that doesn't generalize to actual use.

**Re-scoring implication**: dropping the Hy-MT2-favorable stratum makes the test more honest, not less. If Hy-MT2 still wins on European-mainstream — where existing models *should* already be strong — the niche is real. If it doesn't, H0 holds for the user's actual content mix.

### Sample Provenance

SearxNG returns snippets (~150-300 chars) per result, not full documents. For 40 full-snippet samples in the 200-500 token range, sources to draw from:

1. **Recent research-intake foreign-language sources** — papers from Chinese labs (Tencent Hunyuan, DeepSeek, Kimi, Qwen, Kuaishou, Baichuan, MiniMax, AntGroup) plus any European-language technical content the user encounters. Pull abstracts directly. Already-indexed examples in `intake_index.yaml`: intake-543 (SkillSynth), intake-546 (Training-Free GRPO), intake-590-596 (Hunyuan MT family).
2. **WMT competition test sets** — Flores-200 is the canonical multilingual corpus. Free, standardized, covers all four required strata (zh, en, it, fr, de, ru, ja, ko all natively supported).
3. **Manual curation** — for the mixed-script-structured stratum, Flores-200 doesn't cover composite documents; hand-curate from intake-indexed papers that mix Chinese prose + English equations / code blocks.

Provenance log: record each sample's source URL, language, character/token count, and content type (paper abstract, blog post, structured doc) so the test is reproducible.

### Pipelines

**Pipeline A — Baseline (current production)**:
```
foreign-language snippet
  → Qwen3-Next-80B (ingest_long_context, thinking=ON, --enable-thinking=true)
  → English summary (target ~100-150 tokens)
```

**Pipeline B — Specialist pre-translation**:
```
foreign-language snippet
  → Hy-MT2-1.8B-1.25bit GGUF (one-shot translation prompt, --enable-thinking=false)
  → English translation (raw)
  → Qwen3-Next-80B (ingest_long_context, thinking=ON, same prompt as A)
  → English summary (target ~100-150 tokens)
```

**Pipeline C — Control (chain-of-thought confound check)**:
```
foreign-language snippet
  → Qwen3-Next-80B step 1: "Translate to English" (thinking=OFF)
  → English translation (raw)
  → Qwen3-Next-80B step 2: same summarization prompt as A and B (thinking=ON)
  → English summary
```

Pipeline C is mandatory: if B beats A, we must verify whether the gain is from Hy-MT2 specifically or from the two-step (translate → summarize) decomposition itself. C controls for that. If B ≈ C and both beat A, the lift is structural (decomposition) not specialist-specific, and Hy-MT2 is still overkill.

### Prerequisites

- **[declined: ws58 2026-11-03 content-review: the Hy-MT2 weights were declined by the 2026-11-03 model audit and the STQ1_0 upstream watch is retired]** **STQ1_0 llama.cpp PR #22836 either landed OR confirmed to load via existing GGUF support**. If the 1.25-bit GGUF cannot load without the new kernel, fall back to the BF16 safetensors variant via a temporary HF transformers loader OR use the 2-bit GGUF (also released, no special kernel needed). Document which variant was used — speedup numbers do not transfer across variants. (re-scoped 2026-11-03 from Hy-MT2-1.8B 1.25-bit/STQ1_0: frozen v10 lacks tensor types 40/42 and never loaded it; now the Q4_K_M/2-bit variants on v10)
- **[declined: operator 2026-11-03 model-audit: satisfied: Hy-MT2-1.8B 1.25bit, 2bit and Q4_K_M are on disk under models/hy-mt2-1.8b]** **Hy-MT2-1.8B weights downloaded** to `/mnt/raid0/llm/models/` (pick variant per above)
- **[declined: ws58 2026-11-03 content-review: weights declined by the 2026-11-03 model audit]** **Test launch recipe verified** — Hy-MT2-1.8B likely needs `--enable-thinking=false` (fast-thinking model per release notes), verify chat template + sampling params before bulk run
  - **2026-10-30 Q4_K_M alternative preparation checkpoint:** `codex-ni-hymt-q4-recipe-r1-20261030` is keeper-accepted READY-WAIT (19:08:37Z, rank 67). Native exact template match and sampling-card parameters are verified for this alternative only; frozen-v10 does not support the original low-bit tensor types 40/42, which were never loaded. Original STQ compatibility and full ABC/RAG quality remain unresolved, so this prerequisite stays open. See [recipe checkpoint](../../progress/2026-10/2026-10-30-codex-ni-hymt-q4-r1.md) and private packet `/mnt/raid0/llm/tmp/codex-ni-hymt-q4-recipe-r1-20261030`. [no-belief: alternative recipe preparation; original prerequisite incomplete] (re-scoped 2026-11-03 from Qwen3-Next-80B summarizer in Pipelines A/B/C: deleted/retired; now Qwen3.8-27B-Q8_0 (GPU))
- **[declined: ws58 2026-11-03 content-review: a standing rule (operator runs benchmarks), not a task]** **Approval to run** — per `feedback_speed_verify_via_llama_bench`, NEVER launch `run_benchmark.py` autonomously; user runs ALL benchmarks manually. Same constraint applies here: prepare commands, do not execute. Per `feedback_no_concurrent_inference`, get explicit per-run approval to avoid contaminating concurrent agent work.
- **[declined: ws58 2026-11-03 content-review: a standing rule, not a task]** **Sample set frozen** before any pipeline runs — no swapping samples post-hoc

### Metrics

Three layers, listed in order of decision weight:

1. **Downstream KB-RAG retrieval quality** (primary, load-bearing). For each summary produced by A/B/C, index it into the ColBERT KB-RAG (`epyc-orchestrator/src/retrieval/kb_rag.py`) and measure NDCG@5 / MRR on a held-out query set drawn from the source documents' topics. If a pipeline produces summaries that retrieve worse, the pipeline is worse — this is the only metric that directly maps to the KB-RAG use case. Threshold: ≥0.05 lift in NDCG@5 to count as a win.
2. **Pairwise LLM-as-judge** (secondary). Use a sibling model (gemma4-26B-A4B worker_general, NOT Qwen3-Next-80B which is in-the-loop on A) as the judge. Present A vs B vs C summaries blind, ask for preference + reasoning. Bias caveat: LLM judges have known position bias — randomize order; verbosity bias — normalize length. Threshold: ≥60% A-vs-B win for H1 on the relevant stratum.
3. **Structural / terminology fidelity** (tertiary, manual spot-check). On ~5 mixed-script / structured samples, manually verify whether: (a) JSON delimiters are preserved, (b) named entities (people, places, model names, paper titles) are translated correctly, (c) equations / code blocks pass through unmodified. Hy-MT2 is explicitly trained for structural preservation (IFMTBench) — if it loses on this metric, the specialist-framing is wrong.

### Confounders to control

- **Length normalization**: longer translations may retrieve better simply by having more keywords. Cap summary lengths consistently across pipelines.
- **Sampling stochasticity**: run each pipeline 3× per sample with temperature > 0, report median. OR run at temperature=0 if reproducibility is more important than diversity.
- **Order effects in pairwise judging**: randomize A/B/C presentation order per sample.
- **Tokenizer fertility skew**: Hy-MT2-1.8B may tokenize the source language differently from Qwen3-Next-80B. Record tokens-in for each pipeline; if costs are wildly different, factor that into the decision (a 10% quality lift that costs 5× the tokens is not a win for an optional tool).
- **Hy-MT2 prompt sensitivity**: Hy-MT2 is fast-thinking + translation-SFT — generic chat prompts will degrade it. Use the prompt format documented in the model card / HY_MT2_0_Report.pdf, not a generic "translate the following" prompt.

### Acceptance Criteria

| Outcome | Decision |
|---------|----------|
| H0 confirmed on all strata | Mark `intake-586` as `not_applicable` (downgrade from `worth_investigating`). Remove Hy-MT2 from candidate-tools list. Close [[angelslim-techniques-evaluation]] sub-track for translation models specifically (Sherry/STQ1_0 quant track continues independently). |
| H1 confirmed on 1+ stratum, B ≫ C (specialist-specific lift) | Add Hy-MT2-1.8B-1.25bit (or whichever variant won) as optional pre-encode step in the KB-RAG ingest pipeline, gated by language detection. Specify which stratum triggers the tool route. Update `intake-586` verdict to `adopt_component`. |
| H1 confirmed but B ≈ C (structural-decomposition lift) | Pipeline change without Hy-MT2: switch ingest_long_context summarization to a 2-step (translate then summarize) prompt for the affected strata. Hy-MT2 specialist is NOT adopted — the win was decomposition, not the specialist. Mark `intake-586` as `not_applicable` (specifically); update relevant prompts in `epyc-orchestrator`. |
| Mixed results, ambiguous threshold | Escalate to user for stratum-by-stratum decision. Do NOT auto-adopt. |
| Test infeasible (samples unavailable, STQ1_0 not loadable + 2-bit GGUF crashes, etc.) | Document the blocker. Defer test until the prerequisite resolves; do NOT proceed with adoption decision based on partial evidence. |

### Cost Estimate

- Sample curation: ~1-1.5 hours manual (most time on the mixed-script-structured stratum since Flores-200 covers all single-language strata natively after the 2026-05-21 refocus)
- Pipeline A baseline run (50 × 3 reps): ~30 min on ingest_long_context :8083
- Pipeline B run (50 × 3 reps): ~20 min Hy-MT2 + ~30 min Qwen3-Next-80B = ~50 min total
- Pipeline C run (50 × 3 reps): ~60 min on ingest_long_context (2 calls per sample)
- KB-RAG retrieval eval: ~10 min (precomputed query set)
- LLM-as-judge pairwise on gemma4-26B-A4B: ~20 min (150 judgments × 3 pipelines)
- Total: ~3-4 hours user-attended runtime + 2-3 hours sample curation

### What this test does NOT decide

- Whether to deploy a translation route as a first-class stack role (still NO regardless of outcome — even H1 maps to "optional pre-encode tool", not a server role).
- Whether the AngelSlim 1.25-bit quantization recipe scales beyond 1.8B (separate question, gated on Tencent releases per the AngelSlim stub correction).
- Anything about other AngelSlim techniques (Sherry, SpecExit, Tequila, DAQ) — those are tracked on [[angelslim-techniques-evaluation]] and are independent of this test.

### Reporting

When the test runs, record results in `progress/2026-MM/YYYY-MM-DD.md` with: sample set + provenance, per-stratum NDCG@5 / win-rate / structural-fidelity numbers, decision under the acceptance criteria above, and update both this handoff and `intake-586` verdict accordingly. Per `feedback_handoff_driven_tracking`, no test runs without a handoff update afterward.

Cross-references: [[angelslim-techniques-evaluation]] (umbrella for Sherry/SpecExit/Tequila/DAQ — independent of this MT test), [[searxng-bash-websearch-bridge]] (multilingual ingest origin), [[colbert-reranker-web-research]] (external snippet pipeline).

## Research Intake Update — 2026-05-26

### New Related Research
- **[intake-609] "FastMCP — Pythonic framework for building MCP servers and clients"** (`github.com/prefecthq/fastmcp`, Apache-2.0, v3.3.1)
  - Relevance: K6's original phrasing offered "`kb_search` MCP tool OR in-orchestrator helper" — the **skill route** (`.claude/skills/kb-search/SKILL.md`) shipped 2026-05-06 and satisfies the Explore-subagent integration goal. The MCP-tool variant was not built and is not currently needed.
  - 2026-05-26 update: standalone `fastmcp>=3` is now pinned in `epyc-orchestrator/pyproject.toml` and `src/mcp_server.py` runs on it (migration verified, 40 MCP tests pass). If a future workflow needs an MCP-tool variant of `kb_search` (e.g., a different agent runtime that does not consume Claude Code skills, or a multi-MCP-client scenario), the framework choice is settled and the scaffold pattern in `src/mcp_server.py` is the reference. **No outstanding K6 work is unblocked** — the skill route is the production path.
  - Cross-ref: the FastMCP v3 middleware pattern being built out in [`tool-output-compression.md`](context-and-token-economy.md#track-tool-output-compression) Phase 4 (P4b) is the precedent if a `kb_search` MCP variant is ever added.

## Research Intake Update — 2026-05-27

### New Related Research
- **[intake-611] "agentmemory V4 — LongMemEval real-retrieval #1 (96.2%)"** (`github.com/JordanMcCann/agentmemory`, MIT)
  - Relevance: its retrieval engine is **local and self-hostable** (all-mpnet-base-v2 embedder + ms-marco-MiniLM cross-encoder reranker) — directly compatible with our ONNX/MaxSim stack, unlike OpenAI-bound peers.
  - Key technique: **six-signal hybrid retrieval** — semantic + BM25 lexical + graph activation + importance + confidence + temporal proximity, fused per query; deterministic HNSW (SHA-256 content-based level assignment).
  - Reported results: 96.20% LongMemEval_S real-retrieval (481/500), beats PwC Chronos 95.6%; per-category single-session 100% / knowledge-update 97.4% / temporal 96.2% / multi-session 93.2%.
  - Delta from current approach: our K1–K6 layer is single-signal ColBERT MaxSim over markdown. agentmemory adds BM25 + graph-activation + temporal-proximity signals plus a cross-encoder rerank stage — additive on top of the existing encoder, and corroborates the `colbert-reranker-web-research.md` rerank direction.
- **[intake-610] "Quarq Agent (agent-oss)"** (`github.com/quarqlabs/agent-oss`, Apache-2.0)
  - Relevance: hybrid vector+keyword retrieval with a **self-correcting fallback pass** when initial evidence is incomplete — a retrieval-policy pattern for kb_rag query-time.
  - Key technique: self-correcting fallback retrieval + HyDE query optimization.
  - Reported results: 99.59% on a 241-q LongMemEval-S *partial checkpoint* (unverified — see intake-610 contradicting_evidence; verified field full-run SOTA is ~96.2%).
  - Delta from current approach: adds a fallback retry loop on low-evidence queries; we currently do single-pass MaxSim retrieval.

## Research Intake Deep-Dive — 2026-05-27 (six-signal retrieval → scoped K9/K10)

Source-level deep dive of intake-611 (agentmemory V4) + intake-610 (agent-oss) at `research/deep-dives/2026-05-27-agent-memory-cluster.md` (both repos cloned + read at file:line). The Phase-4a note above flagged "six-signal hybrid retrieval" as a candidate; the deep dive **scopes it down** — most of agentmemory's six signals are tuned to conversational agent-memory and do not transfer to a structured-markdown corpus. Concrete, gated additions to the **already-landed K1–K6 ColBERT layer**:

- [x] **K9 — Cross-encoder rerank stage.** ✅ CODE LANDED 2026-05-27; K7 measured 2026-06-13. New `src/retrieval/cross_encoder.py` (ONNX, mirrors `colbert_encoder.py`; graceful no-op when model absent) + `cross_encoder.rerank()` blend `(1−w)·maxsim + w·sigmoid(CE_logit)` (agentmemory `reranking.py:62`). Wired into `kb_rag.query(rerank=…, rerank_weight=…)` over the top-`4×K` pool (`KB_RAG_RERANK` / `_WEIGHT` / `_POOL_MULT` env overrides). Model downloaded: `cross-encoder/ms-marco-MiniLM-L-6-v2` ONNX int8 at `/mnt/raid0/llm/models/ms-marco-minilm-l6-v2-onnx`. Live smoke: relevant logit +8.0 vs irrelevant −11.3; rerank flips a lower-base relevant doc to top. 4 unit tests (mocked + real-model skipif). **K7 verdict**: useful for first-rank/recall@3, not default-safe; rerank configs missed 3-5 all-evidence cases on the certification pool.
- [x] **K10 — Temporal Gaussian recency signal.** ✅ CODE LANDED 2026-05-27; K7 measured 2026-06-13. `_recency_score(mtime, now, σ_days)` Gaussian + blend in `kb_rag.query(recency_weight=…, recency_sigma_days=…)`; `mtime` now SELECTed from the K3 catalog. Default `recency_weight=0.0` → identical to MaxSim-only (back-compat); env overrides `KB_RAG_RECENCY_WEIGHT` / `KB_RAG_RECENCY_SIGMA_DAYS` for sweeps. 2 unit tests (monotonicity + tie-break reorder). **K7 verdict**: validated; `recency_w0.3_s90` is the safest default candidate (0 missed-all-evidence, recall@10 within noise of the aggregate winner).
- [x] **K11 (optional, measure-first) — FTS5 lexical signal.** SQLite FTS5 porter-stemmed lexical matching landed default-off in `epyc-orchestrator` `74120be`: `kb_rag.py` now maintains an optional `chunk_fts` table during full builds and targeted updates, backfills it for unchanged chunks, and blends a reciprocal-rank lexical score only when `lexical_weight` or `KB_RAG_LEXICAL_WEIGHT` is explicitly set. ColBERT MaxSim remains the default because lexical weight defaults to zero. Validation: `tests/unit/test_retrieval.py` and `tests/unit/test_kb_rag_eval.py`.
- [x] **K11 batch lexical sweep.** ✅ 2026-07-21 Run `BULK-kbrag-autowiki-k11` against the remapped K7 certification pool and fresh FTS5 catalog; close only the batch measurement decision, not model-backed AutoWiki drafting. Result: `DONE_MARGINAL_OBS`, protocol `internal-kb-rag.k11-lexical-sweep.v1`, `n=70`, all weights 0.0/0.1/0.2/0.3 had `mean_recall@10=0.5048` and `missed_all_evidence_count=14`; AutoWiki deterministic writer dry-run passed under `evidence_policy=verified`; no default lexical-weight promotion.

### Diagnostic Update — 2026-06-12

Tiny, non-certifying K-RAG diagnostic artifacts live at `/mnt/raid0/llm/tmp/k_rag_diag_20260612/` (`summary.json`, `rows.jsonl`, `cases.json`). Corpus state during the run: 137 files / 4,634 chunks, catalog max mtime `2026-05-30T11:22:46Z`, while current Fable/J9/J13/J7 docs are from 2026-06-12. Runtime state: orchestrator `.venv` failed to import `onnxruntime`; `/mnt/raid0/llm/pace-env` loaded both ColBERT and cross-encoder.

Results over 8 hand-curated file-recall cases:
- MaxSim baseline: mean recall@3 `0.5208`, @5 `0.5833`, @10 `0.7083`, perfect@10 `5/8`.
- Recency-only sweeps (`weight=0.1/0.3`, `sigma=90`) were neutral on this stale set.
- Cross-encoder rerank (`weight=0.3/0.6`) improved recall@10 to `0.75` and perfect@10 to `6/8`, with no @3 gain.

Decision: keep K9 worth-testing in the formal K7 sweep, keep K10 neutral/default-off, and do not promote any KB-RAG default weights from this diagnostic.

### K7 Harness Update — 2026-06-12

Branch `feat/kbrag-k7-eval` in `/mnt/raid0/llm/tmp/kbrag-k7-worktree` is committed at `280c092` (`Add KB-RAG K7 eval harness`). It adds:
- `scripts/kb_rag/eval_k7.py` plus `kb_rag eval` CLI subcommand.
- `scripts/kb_rag/k7_seed_cases.json`: 20 curated multi-hop evidence-file recall cases (12 HotpotQA-template, 8 LoCoMo-template), validated against disk with zero missing evidence files.
- Metrics: recall@3/5/10, perfect@k, first/all evidence ranks, protocol splits, config comparison across MaxSim, recency, rerank, and hybrid configs.
- Validation: `ruff check`, `ruff format --check`, `tests/unit/test_kb_rag_eval.py` pass; existing retrieval suite passes with the known exception that orchestrator `.venv` lacks `onnxruntime` for the real cross-encoder test. `/mnt/raid0/llm/pace-env` loads ONNX Runtime and discriminates the real cross-encoder smoke (`4.79` relevant vs `-11.29` irrelevant logit).

Operational note: the fresh index build is CPU-heavy under ONNX Runtime, not CPU-light. The first unconstrained attempt was stopped to avoid contaminating live AutoPilot timing; the current build writes to `/mnt/raid0/llm/tmp/kbrag_index_k7_20260612` under `nice=15`, `taskset`-constrained to CPUs `168-175`, with thread env caps. Full K7 sweep should run against that tmp index when complete, then document the result before any default-weight promotion.

**Explicitly NOT adopting** (deep-dive rationale): spreading-activation graph signal (agentmemory's entity extraction is regex-based and brittle on structured markdown — would need spaCy/LLM NER at high cost for low gain), importance×confidence (all KB chunks ≈ equal importance by design), node-activation LRU recency (a static-doc corpus has no meaningful access-frequency signal). agentmemory's six-signal weights are hand-tuned to **conversational** QA over 46 iterations — any blend we adopt must be re-tuned on our query distribution via K7, not copied.

**Self-correcting two-pass retrieval (from agent-oss, intake-610).** Backend-agnostic pattern worth a K-track later: if a downstream consumer (Explore subagent / orchestrator) signals "evidence incomplete", emit gap-queries and re-retrieve at a lower MaxSim threshold before answering (agent-oss `agent.py:1488-1566`). Defer behind K9/K10 — it needs a consumer that emits the incompleteness signal; note it here so it isn't re-discovered.

Cross-refs: [[colbert-reranker-web-research]] (shared encoder + rerank), `research/deep-dives/2026-05-27-agent-memory-cluster.md`, intake-610/611.

## Research Intake Deep-Dive — 2026-05-27 (Understand-Anything: lift-not-fork shopping list — GATED, do not action yet)

Deep-dive of [intake-625](../../research/intake_index.yaml) at `research/deep-dives/2026-05-27-understand-anything-vs-gitnexus.md` (Lum1104/Understand-Anything cloned at commit `26edf61` — full 547-commit history + all 9 agent files + 7-phase `SKILL.md` read). Two of UA's three design-reference patterns have a natural home **here**, but the revisit-trigger has four gates and none are currently met — record now so the patterns aren't re-discovered later.

**Pattern A — LLM-annotation layered on Tree-sitter structural truth (KB chunking skeleton).** UA's `file-analyzer.md:15` enforces a two-phase split: a deterministic `extract-structure.mjs` (334 LOC, 10 first-class Tree-sitter langs) produces a *structural skeleton* (functions, classes, imports, exports, size, complexity); the LLM then annotates the **skeleton + source** with summary, tags, complexity-grade, and semantic edges. A separate `merge-batch-graphs.py` canonicalizes IDs and drops orphans deterministically after the LLM. **Application here:** for code-doc chunks, feed skeleton-only to the annotator instead of raw source (cheaper, less drift); make the K3 catalog hold the skeleton; add a canonicalization pass before the K5 index write. Concrete artifact to port: `understand-anything-plugin/skills/understand/extract-structure.mjs` (or build the equivalent on our existing parsers).

**Pattern B — Dependency-ordered guided context expansion (BFS from entry-point).** UA's `tour-builder.md` Phase 1 is a **deterministic** topology script: fan-in / fan-out rankings, an explicit entry-point scoring rubric (`README.md` at root = +5, `main.{ts,py,go,rs,...}` = +3, root/one-deep = +1, high-fan-out top-10% = +1, low-fan-in bottom-25% = +1), BFS-with-depth-bands from the top entry point, bidirectional-cluster detection. The LLM only writes narrative around this; ordering is computed. **Application here:** for a KB query hit, expand context by BFS over `[[wiki-link]]` cross-references (depth ≤ 2), not by flat top-k. Bands the LLM sees the same way UA bands tour steps. Also applies to handoff-index reading order (entry = `master-handoff-index.md`, edges = `[[…]]` graph), but that's a separate skill — not a kb_rag task.

**Pattern C — Code → business-domain mapping schema.** UA's `domain-analyzer.md` ships a 3-level `domain → flow → step` hierarchy with `flow_step.weight` as monotonic ordering in [0,1] and `step.filePath + lineRange` as the round-trip anchor back to source. Schema is well-specified; caveat is that UA leaves the filePath/lineRange anchor as a *soft prompt rule*, not an enforced post-write check. **Application here:** orthogonal to kb_rag's current scope — only relevant if a future handoff explicitly asks for a code-to-domain view; if lifted, enforce the anchor at write time.

**Gating — DO NOT LIFT YET.** All four gates must hold before any of the above is actioned (intake-625 verdict_justification, deep-dive §6):
1. **Internal pull** — kb_rag declares an explicit chunk-skeleton or guided-expansion requirement that current K1–K10 + measure-first K11 does *not* cover. The current K9/K10 work (cross-encoder + Gaussian recency) and any K7 outcomes must be **measured** before adding a structural-skeleton chunker — additional retrieval features only after K-RAG-1 lands.
2. **Sustainability** — UA shows a sustained second-committer ≥30 commits / ≥60 days. Today: Lum1104 = 83% of 547 commits; second-largest contributor = 9 commits (1.6%).
3. **Stability** — UA ships a `CHANGELOG.md` and a written schema-stability commitment for `knowledge-graph.json`. Today: no CHANGELOG.
4. **Empirical** — third-party-published full-rebuild + incremental benchmark on a >1 k-file repo. Today: only GitHub social signals (39 127 ★ / 3 116 forks, 10 weeks old) — explicitly *not* a substitute per [[feedback_credibility_from_source_not_readme]].

**Earliest realistic revisit:** 2026-08. **Do NOT** install the `understand-anything` plugin on epyc-root, **do NOT** swap GitNexus, **do NOT** lift UA's 9-agent decomposition (no ablation justifies it). If gate 1 fires before 2026-08, the lift-not-fork shopping list above is the action plan — port the deterministic phase scripts, not the prompts.

Cross-refs: [[meta-harness-optimization]] (parallel "do-not-lift the 9-agent decomposition" note), `research/deep-dives/2026-05-27-understand-anything-vs-gitnexus.md`, intake-625, [[project_gitnexus_cli_only_setup]] (GitNexus is the production code-intelligence layer; UA does not displace it).

## Research Intake Update — 2026-06-10

### New Related Research
- **[intake-686] "turbovec — Google TurboQuant vector index (Rust + Python, SIMD-accelerated quantized vector search)"** (github.com/RyanCodrai/turbovec)
  - Relevance: a low-RAM local vector index applying Google TurboQuant (arxiv:2504.19874, ICLR 2026) to standalone retrieval — ~8x RAM cut (31 GB → 4 GB for 10M docs) with FAISS-parity/better search. Candidate low-RAM index for the KB-RAG corpus and the orchestrator's FAISS repl_memory/strategy_store path.
  - Key technique: data-oblivious quantization (no training), random rotation + per-coordinate Lloyd-Max (TQ+), 2/4-bit packing, hand-written AVX-512BW/NEON nibble-LUT distance kernels with runtime ISA detection.
  - Reported results: 16x raw compression at 2-bit; +0.3–3.4 R@1 vs FAISS PQ; x86 search +1–6% (4-bit), ARM +12–20%.
  - Delta from current approach: NextPLAID (intake-355) is the existing Rust-local-PQ comparable; turbovec is not yet integrated. **The 12–20% headline is ARM/NEON-specific — on EPYC's AVX-512 x86 the gain is only 1–6%, so the value is compression/RAM, not QPS.** Needs a recall+RAM+QPS bench at AVX-512 before any swap; separately mine its AVX-512BW kernels against our Q8_0 GEMV kernels. credibility 3 (TurboQuant has independent third-party ports).

### Deep-Dive Refinement (2026-06-12) — refined to NO-GO / parked
The intake premise doesn't hold against our **actual** baseline: repl_memory/strategy_store run `faiss.IndexFlatIP` (EXACT, dim=1024 BGE-large, `faiss_store.py:103`), **not** a PQ index — so turbovec's 8x-RAM/PQ-parity story has nothing to beat. Live footprint is ~304 MB (episodic ~72.8K vecs + strategy ~1.3K) of 1.1 TB → the ~266 MB saving is 0.024% of RAM; the 31 GB→4 GB headline is a 10M-doc corpus we don't have. The +12–20% QPS is ARM/NEON-only; on EPYC AVX-512 it's PQ-parity-to-negative. **Kernel-mining REJECTED** — turbovec's AVX-512BW kernel is a FastScan nibble-LUT *distance scanner* (LUT-throughput-bound); our Q8_0 kernel is a BW-bound 8x8 integer GEMV — different op/layout/bottleneck, nothing ports. KB-RAG is multi-vector MaxSim, which turbovec's single-vector MIPS API doesn't model. **WATCH-gate:** revisit only if a single-vector corpus exceeds ~1M vectors under real RAM pressure. Full: `research/deep-dives/2026-06-12-turbovec-vector-index.md`.

### Incremental wiki/KB refresh (merged from autowiki stub, 2026-06-12)

Scope inherited from `autowiki-incremental-kb-generator.md` (now in [`../completed/autowiki-incremental-kb-generator.md`](../completed/autowiki-incremental-kb-generator.md)) per the 2026-06-12 Fable 5 portfolio pass — it was an extension of this handoff's compiled-KB work (intake-657, Factory.ai AutoWiki patterns; full mining in `research/factory-ai-harvest-2026-06-03.md` Part 3E). Goal: refresh generated wiki/KB pages **incrementally** (only pages whose sources changed), closing the staleness gap the project-wiki lint flags. The reproducible core (SaaS parts — App Cloud Sync, web viewer, GitHub-Wiki sync — excluded):

- **Page → source-paths manifest**: every generated page declares its source file set with a content hash per source-set; on a push, recompute only pages whose source-set intersects the git diff (first run full, later runs reuse prior work). Pages follow a structured topic taxonomy ({architecture overview, module breakdown, API, conventions, setup}, cross-linked).
- **Change-driven ColBERT re-embed**: re-embed only the changed chunks into the existing ColBERT index (current build = 409 files / 13,537 chunks / 17 min full rebuild) rather than rebuilding — extends the K3 content-hash + K5 on-commit machinery already landed; cross-ref [`colbert-reranker-web-research.md`](knowledge-pipelines.md#track-colbert-reranker-web-research) for the shared encoder.
- **CI/nightshift trigger**: a push-triggered job with a `paths:` filter, or a `scripts/nightshift/` schedule — the OSS equivalent of Factory's `/install-wiki` GitHub Action.

**2026-06-19 first implementation slice:** `project-wiki`'s `compile_sources.py` now formalizes the source manifest as `project-wiki-source-manifest` schema v1. It can persist a full baseline with `--full --write-manifest`, drift-check added/changed/removed sources with `--check-manifest`, and emit the added/changed subset with `--changed-since-manifest`. Follow-up orchestrator commits `0af0415` and `3418188` wire the KB-RAG update CLI to this contract: `scripts/kb_rag/cli.py update --manifest <manifest.json> --manifest-root /workspace` resolves manifest rows to paths, forwards current `sources[].path` rows into `kb_rag.update_files(paths, ...)`, and prunes `removed_sources[].path` rows through `kb_rag.remove_files(...)` so catalog rows, FTS rows, and stale embedding files are removed without a full rebuild.

**2026-06-21 hook integration slice:** `.claude/hooks/post_commit_kb_rag_update.sh` now uses the manifest contract instead of raw `git diff` markdown filtering. On first run it emits a full project-wiki source manifest, updates KB-RAG through `kb_rag update --manifest ... --manifest-root <repo>`, then persists the baseline at `wiki/source_manifest.json`; later runs emit `--changed-since-manifest` deltas and skip KB-RAG entirely when there are no added/changed/removed sources. This closes the deterministic source-manifest-to-ColBERT refresh loop; the AutoWiki page generator/writer and output lint gate remain open design work below.

**2026-06-21 output lint gate slice:** the project-wiki lint command now includes `wiki_article_structure`, enabled in `wiki.yaml`. It scans generated `wiki/*.md` article pages, excludes `INDEX.md`/`SCHEMA.md`, errors on structural corruption (missing H1, `## Summary`, or source-reference section), and warns on legacy/reference pages without category metadata or missing recommended article sections. Focused tests landed in `tests/skills/test_project_wiki_lint.py`. Live smoke passed with zero errors; current warnings are the expected legacy/reference debt (`chat-templates.md` uncategorized, and three pages missing recommended section headings). This closes the deterministic output lint gate for generated wiki updates; the model-backed AutoWiki page writer remains open.

**2026-06-21 manifest-backed doc-drift slice:** `scripts/validate/validate_doc_drift.py` now reuses the project-wiki compiler's `build_manifest_drift_report()` instead of maintaining a second source scan. The validator keeps the existing CLAUDE.md port/path/make checks, and adds a `source-manifest-drift` leg that fails when `wiki/source_manifest.json` is stale against the current source inventory. This makes the source manifest the authoritative wiki freshness gate without pretending it is a universal file/link manifest. Focused unit coverage landed in `tests/validate/test_validate_doc_drift.py`; the live validator now reports added/changed/removed source examples when the manifest needs refresh.

**2026-06-21 trigger-cadence/observability slice:** the incremental refresh cadence is now explicitly the existing Claude PostToolUse hook on HEAD-moving git commands (`commit`, `merge`, `pull`, `rebase`, `cherry-pick`), not cron/nightshift and not `/wrap-up`. `scripts/hooks/posttool_kb_rag_update.sh` still dispatches `.claude/hooks/post_commit_kb_rag_update.sh` in the background so it does not block tool use or contend with AutoPilot, but it now appends dispatch and updater output to `logs/kb_rag_update.log` (or `KB_RAG_HOOK_LOG`) instead of dropping it on the floor. Focused coverage landed in `tests/hooks/test_posttool_kb_rag_update.py`.

**2026-06-27 writer evidence-policy slice:** the source-manifest contract now carries a `writer_evidence_policy` block for model-written wiki article adoption. New manifests require `minimum_confidence: verified`, at least 3 source references, a source-reference section, structural wiki lint, and human or measured review evidence. `build_manifest_drift_report()` now fails closed when a saved manifest omits or weakens that policy, and `scripts/validate/validate_doc_drift.py` reports those policy failures alongside source drift. This closes the content-quality policy half of the AutoWiki writer gap; the writer/model choice remains open.

**2026-06-28 writer review/control-plane slice:** `.claude/skills/project-wiki/scripts/wiki_writer_review.py` now provides the missing inference-free writer seam without authoring or adopting pages. `wiki.yaml` declares `wiki_writer.role: worker_general` as a stack-role alias, so the concrete model id is resolved from current stack truth at execution time instead of duplicated in wiki config. The script can build a review packet from a source manifest (`plan`) and validate a draft plus sidecar evidence (`validate`) against the existing writer evidence policy. It refuses weak manifests, unreviewed drafts, too few source references, wrong writer roles, or non-verified confidence. This closes the model-choice/control-plane portion; actual draft generation, human/measured review, and adoption remain gated by the validation report and structural wiki lint.

Open design questions (carried from the stub, unresolved):

1. The page→source-paths manifest now improves `scripts/validate/` document-drift validation as the **wiki source freshness** gate. It does not subsume the existing port, Makefile, or generic CLAUDE.md relative-link checks because those are not project-wiki source inventory concerns.
2. Generator model: role-level choice is `worker_general` in `wiki.yaml`; exact model identity is intentionally stack-derived. Remaining implementation is the measured/human review execution path that produces accepted writer evidence for a concrete draft.
3. Scope: in-repo git-versioned wiki only (we already have this — git = versioning); any app/UI sync is SaaS-only, skip.
4. Trigger cadence is settled for the local workflow: Claude PostToolUse after HEAD-moving git commands, background/nonblocking, no cron/nightshift, with durable logs for audit. Any future CI/on-push workflow should be a separate productionization decision.

## Research Intake Update — 2026-06-20

### MRAgent — evidence-pruned retrieval (intake-698, comparative datapoint)

- **[intake-698] "MRAgent — Memory is Reconstructed, Not Retrieved"** (arXiv:2606.06036) — **comparative datapoint against the parked self-correcting two-pass retrieval note (above, line ~414, under "Research Intake Deep-Dive — 2026-05-27 (six-signal retrieval → scoped K9/K10)", sourced from agent-oss / intake-610), NOT a new workstream.**
  - **Mechanism**: a Cue-Tag-Content associative graph with ACTIVE RECONSTRUCTION — LLM reasoning is interleaved with retrieval, iteratively exploring the graph and PRUNING retrieval paths on intermediate evidence rather than fetching a flat top-k. This is evidence-conditioned path-pruning: the same family as the already-parked "evidence incomplete → gap-query → re-retrieve at a lower threshold" pattern, approached from the pruning side rather than the re-retrieval side.
  - **Why logged here**: this is a SECOND independent instance of the parked self-correcting two-pass retrieval pattern (the first being agent-oss / intake-610). Record it as a comparative datapoint against that parked note. It stays **deferred-pending-a-consumer-that-emits-an-incompleteness-signal**, exactly like the existing note — no new K-track, no plan delta.
  - **Observations (NOT decision-gating)**: token cost ~118k vs 245k–3.3M for baselines; reports LoCoMo / LongMemEval gains. BUT it is cloud-LLM-bound (Gemini-2.5-Flash / Claude-Sonnet-4.5), with NO CPU/local results, and it **LOSES to Mem0 on LoCoMo multi-hop F1 (43.69 vs 45.17)**. The transferable idea, given our token-budget constraints, is the **token-cost discipline** of evidence-pruned traversal — not the accuracy headline.
  - **Routing**: do NOT route this to `delta-mem-reproduction` — that handoff's open gates are GPU-bound accuracy reproduction, not retrieval token-cost. Keep this parked alongside the agent-oss two-pass note here on the KB-RAG handoff.

## Research Intake Update — 2026-07-16

### LEANN — storage-efficient vector index (intake-831, sibling of turbovec intake-686)

- **[intake-831] "LEANN: A Low-Storage Vector Index"** (arXiv:2506.08276; repo `github.com/StarTrail-org/LEANN`; MLSys 2026 Oral / NeurIPS 2025; Berkeley Sky Computing Lab — Wang, Li, …, Stoica, Min, Zaharia, Gonzalez) — **logged as a comparative datapoint against the storage-efficient-index space already scoped by turbovec (intake-686), NOT a new K-track.**
  - **Key technique**: graph-based *selective recomputation* — store a high-degree-preserving pruned proximity graph and RECOMPUTE embeddings on the fly at query time instead of persisting them. A two-level search uses approximate distances to prune which nodes need exact recomputation; dynamic batching amortizes recomputes across hops (GPU-oriented). Backends: HNSW (default), DiskANN.
  - **Reported results**: index <5% of raw data / up to 50x smaller than conventional indices; ~90% top-3 recall in <2 s on QA benchmarks; README storage table 91–97% savings (e.g. Wiki 60M 201 GB → 6 GB).
  - **Delta from current approach**: KB-RAG (K1–K7 certified) is **multi-vector late-interaction ColBERT MaxSim**; LEANN models **single-vector ANN**, which does not express MaxSim — the same modeling gap that parked turbovec. More fundamentally, LEANN trades **storage** (abundant on this host: 3.7 TB raid0, 1.1 TB RAM) for **query-time embedding compute** (the scarce resource on a CPU-inference host) — the trade runs backwards for us. Its 50x/97% story needs a >1M-vector, storage-constrained corpus; KB-RAG is ~18K chunks / ~1.2 GiB (no storage/RAM pressure).
  - **Status**: `worth_investigating`, **parked behind the same three scale gates as turbovec** (see `research/deep-dives/2026-06-12-turbovec-vector-index.md`): (1) single-vector corpus >~1M vectors, (2) single-vector inner-product index, (3) genuine RAM/storage pressure. None hold today. No plan delta, no new K-track.
  - **Creative angle flagged (operator-review candidate, NOT a workstream)**: LEANN ships native Claude Code MCP + personal-data connectors (files, email, browser, chat, codebase). Per CLAUDE.md ("consider creative uses before not_applicable"), the *connector tooling* — distinct from the index — is the only part with a plausible near-term hook here; surfaced for operator judgement, not adopted.
  - **Deep-dive (2026-07-16)**: full analysis persisted at [`research/deep-dives/2026-07-16-leann-vector-index.md`](../../research/deep-dives/2026-07-16-leann-vector-index.md). Refinements vs the note above: (a) **venue corrected** — MLSys 2026 Oral + ICML 2025 Workshop on Vector Databases (poster), **not** NeurIPS 2025; (b) the NO-GO reason is **"storage saving is unneeded"** (all vector indexes total ~3.3 GB ≈ 0.3% of 1.1 TiB RAM), **not** a storage-for-compute inversion — the live **MI210** (gfx90a, ROCm-torch=CUDA) would absorb LEANN's recompute on GPU HBM with zero CPU-token-gen contention; (c) LEANN can only model the single-vector **episodic/strategy FAISS `IndexFlatIP`** stores, never KB-RAG's multi-vector MaxSim; (d) the **episodic store grew ~8.9x → ~646K vecs / 2.65 GB** (single instrumented WATCH: `ntotal>1M` AND real RAM pressure; if it fires, first remedy is stock FAISS HNSW/IVF, not LEANN); (e) technique/kernel-mining: **nothing transferable**. Recompute-not-store is **not novel vs EdgeRAG** (arXiv:2412.21023). Supersedes the naive ">50K entries → consider LEANN" trigger in `handoffs/archived/leann_vector_db.md` (2026-01-26).


## Research-intake integration — 2026-07-22 (graph-wiring: code<->docs crossover)
_Via /research-intake Stage-2 (intake-881 graph-engineering wiring assessment)._
- [x] Build a code<->docs crossover query: federate the GitNexus symbol/flow graph with the ColBERT KB index (symbol/file -> related handoff/wiki chunks; doc-mention -> code symbols). This handoff already names the gap at :21; federation is additive, not the "replace GitNexus" non-goal (:102) ✅ 2026-07-22

### Follow-ups discovered during federation implementation — 2026-07-22
- [x] Re-run `scripts/gitnexus-analyze.sh` for **epyc-orchestrator** — its GitNexus index is corrupt (LadybugDB `lbug.wal` without `lbug.shadow` → CLI segfaults, signal 11, on every read). The `federation.py` tool degrades gracefully (skips that repo) but the orchestrator code-graph side is unavailable until re-indexed. ✅ 2026-07-22 (re-indexed 32.9s, 52,993 nodes; index reads clean, no more signal-11)
- [x] Tidy `federation.py`'s hardcoded `onnxruntime` site-packages fallback path (env-overridable via `FEDERATION_ORT_SITE_PACKAGES`) — discover the encoder deps without the hardcoded `/mnt/raid0/llm/venv/...` path. ✅ 2026-07-22

- **[declined: ws58 2026-11-03 content-review: tooling bookkeeping; gitnexus-analyze.sh runs whenever status reports stale]** Re-index **epyc-orchestrator** with `scripts/gitnexus-analyze.sh` (never bare `gitnexus analyze`) at a quiet CPU [too-big: quiet-window reindex and legacy index disposition require owner]
  window. `gitnexus status` there reads STALE (2026-09-26): the `main` branch index
  (`.gitnexus/branches/main-0d6e4079`, 2026-09-25, `b9e004e3`) is 24 commits behind `30626243`. A separate legacy
  top-level `.gitnexus/meta.json` (2026-07-22, branch `spec-dec-mtp-refresh-2026-06-22`) is 783 commits behind.
  `status` no longer reads it; confirm whether the wrapper can retire it without touching `lbug`. The re-index takes
  CPU, so it is not run inside a wrap-up. Filed 2026-09-26 (workspace-8d wrap-up).


## 2026-07-25 — intake Stage-2a dive corrections (intake-580, intake-890)

_Via `/research-intake` Stage-2; coordination point [`intake-derived-work-2026-07-25.md`](../completed/frontier-lab-automation.md) ID-18/ID-35._

- [x] **Adaptive-chunking lift re-costed ✅ 2026-07-29**: epyc-root `c942728e` Stage-2a source audit established that the shipped API is `RecursiveSplitter`; selection remains paper-only reproduction code.
- [x] **DCC-only signal scoped ✅ 2026-07-29**: epyc-root `c942728e` recorded the no-dependency scope and the SC/BI saturation evidence.
- [x] **Offset-provenance prerequisite recorded ✅ 2026-07-29**: epyc-root `c942728e` established exact-substring offsets as the prerequisite before breadcrumbed `markdown_chunker.py` output can be evaluated.
- [x] **K2/ODL triggers verified fired ✅ 2026-07-29**: epyc-root `c942728e` recorded K2 certification and the ODL heading-chunking landing; this removes only the deferral premise, not the subsequent evaluation work.
- [x] **PageIndex complement evaluation recorded ✅ 2026-07-29**: epyc-root `c942728e` captured its within-document-only scope and independent timeout/cost evidence; no corpus-search adoption is implied.

## 2026-07-29 — intake Stage-2 dive corrections (intake-920, intake-925)

_Via `/research-intake` Stage-2 2026-07-29. Both items correct the record before it can mis-scope live K-track work; see the corrected Open-Question-1 bullet above._

- [x] **K-eval re-scoped ✅ 2026-07-29**: epyc-root `683f70de` corrected the GGUF-path/capability evidence and bounded the work to the K7 70-case probe under the 2pp noise floor; execution still requires a region claim.
- [x] **intake-925 retriever reading corrected ✅ 2026-07-29**: epyc-root `683f70de` recorded that the figures are shell-invocation counts and Table 2 favors dense retrieval; retrieval complements rather than replaces grep.

### Wiki compile watermark — a runtime file that a `git clean` can silently destroy (2026-08-16)

`wiki/.last_compile` was found **missing** on 2026-08-16, so `compile_sources.py` reported **844 new
sources** — effectively the entire repo. It is deliberately untracked (`f1717d80`, "actually untrack
the four generated/runtime files"), and the live `git clean` recorded in `82400787` (2026-08-16
10:57Z) is the most likely destroyer. Reconstructed from the last genuine `--touch` (`5fcad5e3`,
2026-08-13T08:55:55Z, preceded by a real compile at `05c97235`); restoring it took the count from
**844 to 51**.

The compile was then run against the correct 51 and the watermark advanced normally.

- [x] **KB-WM-1 — Make watermark LOSS distinguishable from "never compiled".** `get_last_compile()`
      returns `0.0` both when `wiki/.last_compile` is absent and when it fails to parse, so a destroyed
      watermark is indistinguishable from a virgin repo. The realistic next action for whoever sees
      "844 new" is to `--touch` it forward, which silently skips every genuinely uncompiled source —
      the precise silent knowledge loss the wrap-up lease exists to prevent. Fail loudly on
      absent-but-wiki-pages-exist instead of returning 0.0.
      ✅ 2026-09-16 **CLOSED SUPERSEDED, not implemented as written** (`sub-hs4`, verified on origin/main
      `61b005c4`). `0ea91f3e` moved incremental selection off `.last_compile` entirely: the default path is
      a content-hash diff against the TRACKED `wiki/source_manifest.json`
      (`compile_sources.py` `incremental_since_tracked_manifest` / `_drift_manifest`), so `.last_compile`
      loss no longer changes any count, and `get_last_compile()` now has **zero callers**. The failure
      shape the box names is closed at both ends: (1) the watermark is tracked, so `git clean` cannot
      remove it and a deletion shows in `git status` and is restorable from git; (2) the harmful
      follow-up is refused — bare `--touch` and scoped `--touch` (OP-34, `719ac638`) both raise "no
      tracked baseline manifest" when it is absent (`refresh_tracked_manifest`,
      `refresh_tracked_manifest_scoped`), and a corrupt manifest exits 1 via `read_manifest`. An absent
      manifest makes the incremental run emit the full set once, with a NOTE — over-inclusive, never a
      silent skip. Guards: `test_incremental_without_tracked_manifest_raises`,
      `test_refresh_tracked_manifest_refuses_without_baseline`, `test_scoped_touch_refuses_without_baseline`
      (21/21 pass in `tests/skills/test_project_wiki_compile_sources.py`). Residual → KB-WM-4.
- [x] **KB-WM-2 — Decide where the watermark should live, given it is fleet-shared but untracked.**
      It is documented as ONE watermark for the whole repo, yet it is untracked, so every lane
      worktree carries its own and any `git clean` removes it with no trace. Those two properties are
      inconsistent. Options: track it (reverses a deliberate hygiene decision taken three times);
      move it under `coordination/` runtime state alongside the other fleet-shared runtime files; or
      derive it from the last `--touch` commit instead of storing it. **Not resolved unilaterally —
      the untracking was another session's considered call.**
      ✅ 2026-09-16 **CLOSED SUPERSEDED** (`sub-hs4`). Decided by `0ea91f3e` (NIB2-68/OBS-13): the
      watermark is now the tracked content-hash manifest `wiki/source_manifest.json` (not gitignored;
      last advanced `0e97eee7`, 988 sources), described in its module docstring as "the one shared
      watermark". That keeps the `f1717d80` untracking of `.last_compile` intact (still `.gitignore:44`)
      while making the shared watermark identical across lane worktrees, and it advances only when a
      `--touch` is committed. Residual → KB-WM-4.
- [x] **KB-WM-4 — Retire `wiki/.last_compile`, or give it one format.** Residual of KB-WM-1/2
      (2026-09-16). It no longer drives selection, yet it still has two writers with **incompatible
      formats**: `compile_sources.py` `touch_last_compile()` writes an ISO timestamp, while
      `scripts/coordination/heavy_wrap.py` `step_7_compile_wiki` writes `"<request_id> <iso>"`. The
      readers expect ISO: `get_last_compile()` (zero callers, and still returns 0.0 on absence or
      parse failure) would read heavy_wrap's form as epoch, and `get_last_compile_iso()` copies the raw
      text into every emitted manifest's `last_compile` field. Pick one and land it with a test that
      fails before the fix: (a) retire it — delete `get_last_compile`/`get_last_compile_source`, stop
      both writers, and drop it from the shared-file lists in `worker_checkpoint.py`,
      `serialized_push.py`, `session_bus_coordinator.py` and `wrap-up.md`; or (b) keep it as the
      manifest's timestamp companion, with one ISO format that both writers share.
      ✅ 2026-09-16 **RETIRED, option (a)** (`sub-kbwm4`, epyc-root `40034bf1`). A grep of root,
      epyc-orchestrator and epyc-inference-research found one live reader: `build_manifest()` copied
      the raw file text into every emitted manifest's `last_compile`. The shared clone's copy read
      `2026-09-08T09:28:51Z` while the tracked manifest read `2026-09-16`. Removing that reader left
      no dependents, so both writers are gone. The five file helpers are deleted, and
      `build_manifest` reads the tracked manifest's `last_compile` through a tolerant ISO normalizer.
      Bare `--touch` stamps it with the current time and scoped `--touch` keeps the saved value.
      `heavy_wrap` keeps `watermark` only as a receipt field. Its file write had been failing in the
      real repo: the path is gitignored, so step 8's `git add --intent-to-add` exits 1. The path is
      dropped from the `worker_checkpoint`/`session_bus_coordinator` exact lists (their `wiki/`
      prefix rule still refuses it) and from `serialized_push`, the post-commit hook, `wiki.yaml`,
      `wrap-up.md`, the project-wiki `SKILL.md` and `wiki/knowledge-management.md`. `.gitignore`
      keeps one deduplicated entry, so a leftover copy stays inert. Guards:
      `test_stale_last_compile_file_never_leaks_into_manifest`,
      `test_last_compile_file_helpers_are_retired` and `test_manifest_last_compile_is_normalized_iso`
      failed before the fix (7 cases) and now pass, 31/31 in
      `tests/skills/test_project_wiki_compile_sources.py`. `test_full_wrap_transaction_end_to_end`
      asserts the file is never written or committed and failed before the fix. 97/97 pass across the
      compile_sources, heavy_wrap, worker_checkpoint, post-commit-hook and concurrent_wrapup suites.
- [x] **KB-WM-3 — Same audit for the other three files untracked by `f1717d80`.** If `.last_compile`
      had this failure shape, its siblings from the same commit should be checked for it rather than
      assumed safe.
      ✅ 2026-09-17 (`sub-small-audits`, root `4120af69`). Verdicts:
      - **`handoffs/active/.index-state.json`: SAFE.**
        - `index_state.py` builds it from tracked sources and `git log` only. It never reads the
          old copy.
        - No production code reads it. `refresh_hub_view.sh` regenerates it when it is missing.
      - **`handoffs/active/.index-graph.json`: PARTIAL.** The dashboard and `compute_ready` handle
        absence correctly: the dashboard shows it as degraded, and `compute_ready` refuses to run.
        - `backlog_row_check.index_graph_readiness` stays silent on an unusable graph by design
          (AIR-13). An empty result therefore meant either "not blocked" or "not screened".
          `index_graph_status()` now records `ok`, `absent`, `unreadable`, `no_nodes` or
          `no_readiness` in the premise screener's mechanical provenance. The model prompt is
          unchanged.
        - Handoffs in `blocked/` looked for the graph in their own directory. The only graph is in
          `active/`, so the advisory never fired for them. They now read `active/`.
        - A graph that was valid JSON but not an object crashed the reader.
        - 6 new tests, all failing before the fix.
      - **`logs/agent_audit.log`: PARTIAL.** Writers resolve `LOG_DIR` to the shared checkout from
        any lane worktree (`scripts/lib/env.sh`), so entries survive worktree removal.
        - `.gitignore` re-included `logs/agent_audit*.log`. The 46 live shards were untracked but
          not ignored, so a plain `git clean -fd` would delete them and `git add -A` would re-track
          them. The negation is removed.
        - The frozen legacy monolith was already gone from the shared checkout. It was restored from
          `f1717d80^` (4402 lines).
        - `agent_log_analyze.sh` now warns when that file is missing, where the loss was silent.
        - Also fixed: stale comments and docs (`agent_log.sh`, `session_init.sh`,
          `WORKTREE_MIGRATION.md`).
        - `test_agent_log_merge_format.sh` gains 6 checks and passes 11/11.
- [x] **KB-WM-5 — `logs/.current_session` is one file shared by every agent** (filed 2026-09-17,
      ✅ 2026-09-23 — epyc-root `c8dbb5d4`: session file sharded per AGENT_ID (`logs/.current_session.<id>`), legacy file left inert; 4-test two-writer suite.
      KB-WM-3 audit). Every writer puts its session id in the same `LOG_DIR` file
      (`scripts/utils/agent_log.sh`: `AGENT_SESSION_FILE`). Concurrent agents therefore log under
      each other's session ids, and `agent_session_end` deletes the file for everyone. Shard it per
      `AGENT_ID` like the log itself, with a test that runs two writers.
- [x] **KB-WM-6 — `.index-graph.json` freshness is unchecked** (filed 2026-09-17, KB-WM-3 audit). ✅ 2026-10-06 — MAIN closes option (b) as NI06-02, source `ec513cbe`; original CI37425524371 TRUE64/66, two existing live-artifact skips. Missing/malformed/stale graphs warn without changing hard-check exits; the row screener stays silent on absence.
      - **Historical unchecked scope (now closed).** Neither `index_state.py --check` nor
        `backlog_row_check.index_graph_readiness` compares the graph with the checkout it describes.
        Lane worktrees hold copies generated between 2026-08-12 and 2026-09-17, and five are still
        `index_graph.v1`.
      - **What to decide.** Should the premise screener show the model "graph not screened"
        (option a below)? That reverses AIR-13's documented silent-on-absence rule, which
        `test_no_graph_file_adds_no_reasons` pins.
      - **Options:**
        - (a) add an advisory reason;
        - (b) keep it provenance-only (as now), and add a non-fatal `--check` warning when the graph
          is missing or differs from `build_graph(state)`;
        - (c) read one canonical graph from the hub view through an environment variable.
      - **Recommendation:** (b).

## Research Intake Update — 2026-08-21 — is the ColBERT index earning its keep? (`intake-1239`)

_From `intake-1239#record` (GrepSeek, UMass CIIR, arXiv:2605.29307v1). A trained shell-command search agent
beats the best dense-retrieval baseline on micro-average F1 at **p<0.05**, winning 4 of 7 benchmarks, with
**NO pre-computed index of any kind** — and loses significantly on single-hop popularity QA. The result is
entirely **hardware-independent**, which makes it the rare intake item with zero GPU risk and a reason to
prioritise it against GPU-gated work._

**Why it lands harder here than the headline suggests.** Their corpus is 21M documents / ~14 GB, roughly
**three orders of magnitude larger** than our markdown KB — and grep's advantage grows as the index's
amortisation argument weakens, so on a corpus our size the index barely pays for itself. Their agent backbone
is Qwen3.5-9B with a Qwen3.5-27B tutor, and **we already serve the 27B**. And the most interesting number is
not the F1, it is **"0 A100-hours of indexing"**: our ColBERT index is a maintenance liability with a
**staleness** failure mode — an index built yesterday answers about a handoff row deleted today — and grep
has no staleness mode because there is nothing to stale. That is an operational argument independent of the
accuracy argument, and it may matter more to us than F1 does.

**The honest counterweight**, and it is why the verdict is `worth_investigating` and not `adopt_patterns`:
their stated failure modes — brittleness to spelling variation and diacritics, matches returned in FILE ORDER
with no relevance ranking, overloaded keywords — map onto **precisely our KB's weakest axis**, a corpus dense
with synonymous governance jargon in which at least one term ("duty cycle") already means two unrelated
things. Adopting on faith would be importing a Wikipedia-scale result onto a corpus where the mechanism that
produced it works differently.

- [ ] **KB-GS-1 — Run a four-arm retrieval A/B on our own corpus. Deliberately NOT a replication.** Steps (absorb KB-GS-2/3): build 40-60 questions mined from real session needs in the last 60 days of progress/, stratified, with ground truth BEFORE any arm runs; add a STALENESS arm (re-run the same set after a 200-commit drift) — that axis may decide the question regardless of F1.
      *2026-11-09:* premise stronger, not weaker: the "ColBERT as deployed" arm is currently broken and stale (`PIP04-KB-INDEX-BREAK`), so arm A must be the rebuilt `qd-v2` index and the staleness arm has a live data point (index frozen at 2026-10-31, hundreds of handoff files newer). Still to name: the date anchor for the 200-commit drift and who builds the ground truth. No Autopilot dependency; question-set work is doable now, arm runs are CPU.
      Replicating their GRPO training is weeks of work and answers a question we do not have. Arms: **ColBERT
      as deployed** / **untrained prompt-only `rg`** / **hybrid** / **GitNexus-only**. Note we already use the
      grep half constantly and informally — agents grep this repo all day — so the real question the A/B
      answers is not "should we add grep" but **"is the ColBERT index earning its keep on a corpus this
      small"**. Roughly one day, no GPU contention.
- **[declined: ws58 2026-11-03 content-review: merged into KB-GS-1 as its question-set step]** **KB-GS-2 — Build the question set and the ground truth BEFORE any arm runs, and stratify it.**
      40-60 questions mined from REAL session needs in the last 60 days of progress files and wrap-ups,
      stratified into four buckets **because the result is bucket-dependent and an unstratified aggregate
      would hide exactly the effect**: single-hop lookup (expect a tie), **multi-hop composition** (grep
      predicted to win — the discriminating bucket, and where their gains concentrate), synonym/semantic
      (ColBERT predicted to win — grep's stated weakness and our corpus's dominant idiom), and
      code-structural (GitNexus predicted to win outright, included so we do not replace the wrong tool).
      PRIMARY METRIC **recall@evidence against human-verified spans built BEFORE any arm runs** — never from
      an arm's output, or the ground truth inherits that arm's blind spots. n=40-60 per stratum is thin, so
      **report the minimum detectable effect up front and do not claim a null we are not powered to detect.**
- **[declined: ws58 2026-11-03 content-review: merged into KB-GS-1 as its staleness arm]** **KB-GS-3 — Add a STALENESS arm; that axis is invisible in the paper and may decide the question for
      us regardless of F1.** Re-run the same question set after a 200-commit window **without rebuilding the
      index**. Grep scores whatever the tree says today by construction; ColBERT scores whatever it was built
      against. If the staleness delta is large, the operational argument settles this independently of any
      accuracy result.
- **[declined: ws58 2026-11-03 content-review: conditional on adopting a sharded engine that nothing selects]** **KB-GS-4 — Exploit the hardware we actually have if the sharded engine is adopted.** The current GrepSeek v2 paper describes SPCS over its raw 14 GB corpus without a learned dense-retrieval index (`intake-1239#00`; `dive-1239/source.txt:L108`), and a separate optional PACE strategy that adds compact auxiliary structure (16.8 GB total; `intake-1239#04`; `dive-1239/source.txt:L146`). Do not generalize “no learned dense-retrieval index” into “no index of any kind.” The reported 7.6x at 32 shards and 91% generation are paper-workload results; they do not establish a local speedup or headroom on our 96-core EPYC. Preserve the conditional adoption task and keep local implementation/equivalence testing open.

_2026-10-06 source re-read: the current v2 scope above qualifies the earlier v1 introduction and summarizer-rendered HTML basis. The 0.5691 micro-F1 and seven-benchmark framing are historical; v2 reports macro 0.5226 across eight benchmarks, seven token-F1 plus BrowseComp-Plus judged accuracy, with five wins (`intake-1239#01`). The earlier “NO pre-computed index of any kind” premise is superseded by the SPCS/PACE distinction, and “entirely hardware-independent” does not establish a local hardware result. Corpus-size, indexing/staleness and latency arguments motivate KB-GS-1–3; they do not prove local ColBERT inferiority or a local speedup. Their arms, prebuilt human ground truth and staleness window remain unchanged. The predecessor arXiv:2605.05242 remains a historical companion lead; its training-recipe/paradigm comparison was not re-read here._

## Research Intake Update — 2026-08-21 (Stage-2b, intake-1278#record)

### Record corrections (Z)

- **[declined: ws58 2026-11-03 content-review: record correction; its substance (the 1.32 pp quality/cost question) lives in B6]** **C1 — the answerai→GTE retirement rationale on file is wrong.** `CHANGELOG.md` and
      `handoffs/completed/colbert-zero-research-integration.md` justify the Feb-2026 encoder swap with
      "**answerai unscored**". It was scored, on the **same BEIR-15**, on the successor's own model
      card, and had been since 2025-05-14. The controlled figures are **54.67 (GTE) vs 53.35
      (answerai, LightOn's own re-run of the published checkpoint)** = **1.32 pp** — *inside* the ~2 pp
      noise floor this handoff declares. **CORRECTED 2026-08-22: TWO harnesses, not three.** Vendor
      53.79 and LightOn's own re-run 53.35 are the only independent BEIR measurements of this model.
      The apparent third (mixedbread, arXiv 2510.14880) **transcribed both ColBERT baseline rows from
      LightOn's model card**, published 36 days earlier — 15/15 exact per-task match to LightOn's
      re-run column, 0/15 to the vendor-reported one. The 1.32 pp gap is unaffected, because it was
      always LightOn's own comparison.
      Correct the record, and state the **cost side the original decision never weighed**: 4.46×
      fewer parameters and a **measured −24.3 %** index footprint (0.757×, cross-validated against the
      stored `.npz` to 0.2 %; the saving is essentially the bare 96/128 dim ratio — the tokenizer swap
      is a wash at 1.026). This does **not** argue for reverting; it argues that the swap rests on a
      delta our own doctrine calls noise, which the record should say plainly.
- **[declined: ws58 2026-11-03 content-review: a rule, not a task]** **C2 — never record `54.89` as the incumbent's BEIR-15.** It does not exist on the model card
      (`grep -c` = 0 at rev `25f6f7bb`) or anywhere in the index. The comparable figure is **54.67**,
      over 15 named tasks, provenance: BEIR table added `78d50a16` (2025-05-14), FiQA corrected
      `6605e431` (2025-09-10). Note that `54.75` also circulates from a different source with no stated
      denominator — see the conflict flagged on intake-430.
- [x] **C7 (Z) — fix the stale `:8089` model attribution** in `src/repl_environment/code_search.py:12`,
      which still names an encoder retired 2026-02-20. ✅ 2026-09-16
      - Evidence: epyc-orchestrator `51b30f5e` on branch `sub/tooling-orch-20260916`, integrated by orchestrator merge `370dc715` (pushed in `753343f5`, 2026-09-16).
      - The docstring now names GTE-ModernColBERT-v1 (149M, 128-dim), which is what
        `orchestration/launch_manifest.yaml` `nextplaid-docs` mounts. It also points at the manifest as the
        authority.
      - The same stale name was also fixed in `scripts/nextplaid/index_codebase.py:9` and
        `reindex_changed.py:9`.
      - The change is comment-only. `test_code_search.py` passes 30/30.

### Code gaps (Z) — all three are small and one is blocking

- [x] **K1 — the ColBERT encoder cannot load ANY BERT-family late-interaction ONNX.** ✅ **LANDED
      2026-08-23**, `epyc-orchestrator` `4e5e84c0`. Such graphs declare `token_type_ids` as a
      required input with no initializer default, and `colbert_encoder.py` fed only `input_ids` and
      `attention_mask` → `InvalidArgument: Missing Input` on the first call. `ensure_loaded()` now
      captures `_input_names` from `session.get_inputs()` at load time and `encode()` feeds exactly
      the inputs the graph declares, with all-zero `token_type_ids` for single-segment input. An
      input it **cannot** satisfy raises instead of degrading to an empty index. Line hints
      re-resolved under the anchor-rot rule: the load-time capture pattern is
      `src/retrieval/cross_encoder.py:148` (previously uncited) and the conditional feed is
      `:183-191` (this row cited `169,188-190`). The same commit raised the swallowed failure from
      `logger.debug` to `logger.warning` with the exception type — `colbert_encoder.py:411-417`,
      formerly `:286` — so the exact `InvalidArgument` this row describes is now visible at default
      log level instead of presenting as an ordinary miss. Unblocks answerai-colbert-small-v1,
      ColBERTv2 and Jina-ColBERT-v2 **as a class**, not one model; the swap itself is **B6** below,
      and the mxbai family never needed it (see **H5**). Verified by the required mutation test — a
      graph whose third input is unsatisfiable must fail *loudly*, not merely a happy path that runs
      — plus 206 unit tests across retrieval / prefix_cache / cross_encoder, and checked against the
      deployed `gte-moderncolbert-v1-onnx` for no behaviour change. `4e5e84c0` touches only
      `colbert_encoder.py` and `kb_rag.py`, so those mutation checks are recorded in the commit
      message and are not yet regression-guarded in `tests/`.
- [x] **K2 — honour `onnx_config.json` instead of hard-coding.** ✅ 2026-11-07 — closed by `epyc-orchestrator` `d0a35287` (pushed to origin/main): declared `uses_token_type_ids` and `embedding_dim` are now validated against the loaded graph at load time and a contradiction or malformed value refuses the load (`_validate_graph_contract`, `colbert_encoder.py`; 9 new cases in `tests/unit/test_colbert_graph_contract.py`, 148 colbert/kb_rag unit tests pass; an absent key declares nothing, a dynamic output width is not refused). With `4e5e84c0` (config merge, lower-casing, `token_type_ids` feed), `ac668b9c` / NI07-02 (declared query/document caps) and the existing `do_query_expansion=true` refusal, every capability flag K2 named is now acted on. No ONNX/model execution; the two slots that ship `onnx_config.json` (LateOn, GTE-ModernColBERT-v1: `embedding_dim` 128, `uses_token_type_ids` false) match the documented 2-input / 128-wide graph signature (S4b), and the Reason slot declares neither key (so the check is a no-op until G14 ships its `onnx_config.json`). **Not exercised against a real ONNX session in this change**; the first real load of each slot is the live proof. [no-belief: software acceptance, unit tests] *(Original status line follows.)* **PARTIALLY LANDED 2026-08-23**,
      `epyc-orchestrator` `4e5e84c0` — deliberately **not ticked**, because this row's scope is wider
      than what shipped.
      **Shipped**: `_load_declared_config()` (`colbert_encoder.py:172`) reads `onnx_config.json`
      **and** `config_sentence_transformers.json` and merges them with the format-mandated
      `onnx_config.json` winning, so a freshly `pylate-onnx-export`ed checkpoint — which writes only
      `onnx_config.json` — is no longer a checkpoint we have no file for, and the "prefixes are read
      only from `config_sentence_transformers.json`" defect is closed. Also shipped, as the K8
      sub-item: `do_lower_case` is honoured (`colbert_encoder.py:307`, applied at `:379` to the
      **text only**, never to the prefix, which is a literal added token). Neither tokenizer carries
      a `Lowercase` normalizer and mxbai applies lower-casing *outside* the tokenizer, so before this
      change loading mxbai-32m fed cased text to a lower-case-trained model with no error anywhere.
      **Historical remaining scope (internal-KB caps closed by NI07-02 below; other capability flags remain open)**: the declared `query_length`, `document_length`, `embedding_dim`,
      `uses_token_type_ids` and `do_query_expansion` are now readable but are **not yet acted on**,
      and the fail-loud check is not implemented — `_QUERY_MAX_TOKENS = 48` (`kb_rag.py:66`) and
      `_MAX_QUERY_TOKENS = 48` (`src/tools/web/colbert_reranker.py:66`) remain hard-coded on both
      call sites.
      **Current source correction (2026-10-06; APP `79abe3eca50c911d89e5e9855bbd6392bae2b35d`):**
      the historical paragraph above does not describe the current web path. `_token_caps()` in
      `src/tools/web/colbert_reranker.py` obtains declared query/document caps from the shared
      encoder and clamps the document cap to the snippet budget. The encoder merges checkpoint
      declarations with `onnx_config.json` taking precedence, applies declared lower-casing,
      supplies `token_type_ids` when the graph requires them and refuses unsatisfied graph inputs.
      Declared `do_query_expansion=true` is refused; malformed declarations raise. Declared caps
      fall back only when unusable or absent. MAIN re-opened these source seams; no ONNX/model
      execution or new tests. K2's broader checkpoint/consumer acceptance remains open.
      **H3 — the three-slot `query_length` spread, verified from each model directory on disk
      2026-08-23**: LateOn **32** (`lateon-onnx-int8/onnx_config.json`), GTE-ModernColBERT-v1 **48**
      (`gte-moderncolbert-v1-onnx/onnx_config.json`), Reason-mxbai-32m **256**. An 8× spread across
      slots, so a declared query length is a per-checkpoint training parameter and not an
      architectural constant. Both call sites hard-code 48, so **LateOn is overrun by 16 tokens**
      while Reason-mxbai is under-used by 208. Provenance caveat: the 256 comes from
      `reason-mxbai-colbert-v0-32m-onnx-int8/config_sentence_transformers.json` — that directory
      ships **no `onnx_config.json` at all**, which is exactly what **G14** in
      `colbert-reranker-web-research.md` exists to fix. Where a local shipped value disagrees with the
      upstream card — the GTE checkpoint's local `48` against upstream's `32` — **the local shipped
      value is authoritative**, because it is the file the loader actually reads. Recorded as evidence
      folded into this row; **no new row**.
      Carry forward as a known no-op: PyLate sets `pad_token_id` to the MASK id (103), so a K2
      completion that blindly honours a declared pad id would change behaviour. Harmless today, since
      our loader pads with the tokenizer's own `[PAD]` and slices by `attention_mask`.
  - [x] **K2 remaining internal-KB cap plumbing** ✅ 2026-10-06 — MAIN accepted source `ac668b9c`, promoted APP main `7d3b840a`, original native CI37436700878 TRUE54/54 (39 cap fixtures and 15 unchanged tokenizer regressions). Stored positive caps remain authoritative; absent legacy keys keep historical defaults; malformed metadata refuses before mutation. Only fresh catalogs adopt declared helpers; telemetry and parallel parent/workers use matching caps/convention. [Original custody and MAIN review](../../artifacts/ni07/run-37436700878/README.md), three canonical observation frames. No OP-24 transition, re-embedding, live pool/model call, quality/performance or deployment claim. Broader K2 capability-flag scope remains open.
- [x] **K3 — stamp `embedding_dim` + a tokenizer hash into `index_meta`.** ✅ 2026-10-06 — remaining tokenizer scope owned/accepted by `codex-ni-main` as NI06-03: source `9d3a338a`, APP main `2a98c6f0`, original synthetic native CI37424571462 TRUE15/15. **HALF LANDED 2026-08-23**,
      `epyc-orchestrator` `4e5e84c0` — deliberately **not ticked**, because only the `embedding_dim`
      half shipped.
      **Shipped (the K9 escalation from hygiene to blocker)**: `_stamp_meta()` writes `embedding_dim`
      (`kb_rag.py:244`) and `_check_embedding_dim()` (`:203`), called from `_warn_on_encoder_drift()`
      (`:282-294`, formerly `:236-244`), now **raises** when the live encoder's width differs from the
      stored one; unknown width means cannot-check and never matches. Before this, a 128→64 swap left
      every other stamped key plausible and surfaced as a numpy shape error inside `maxsim()`,
      swallowed by `encode()`'s broad `except` (`colbert_encoder.py:411-417`) and reported as an
      ordinary miss. Mutation-tested with controls: a 128-index against a 64-encoder raises, while
      matching / unstamped / unknown widths do not.
      **Historical remaining scope (closed by NI06-03)**: the tokenizer sha256 was not stamped. `index_meta` carried
      `prefix_convention`, `query_prefix`, `document_prefix`, `encoder_model_dir`,
      `encoder_model_file`, `doc_max_tokens`, `query_max_tokens`, `embedding_dim` and `stamped_at` —
      nothing that would catch a same-dim, same-directory tokenizer swap. That is not hypothetical:
      mxbai-32m and the deployed GTE share a byte-identical 50,280-token vocabulary while their
      `tokenizer.json` files differ (see **H6**), so a swap in that direction is invisible to every
      key now stamped. The same non-vacuous verification bar applies — a test that passes both before
      and after the change proves nothing.
      **Completed implementation**: loader hashes the exact parsed byte buffer; refresh/load failures
      clear its cached identity. New catalogs stamp `tokenizer_sha256`; known stamps must match both
      loaded bytes and current file before query encoding or encoding-writer mutation. Tests mutate
      the same path, remove the file, disagree with the cache and preserve rows/stamps on refusal.
      Legacy unstamped catalogs retain compatibility; removal requires no model load. MAIN verified
      all 3,325 Git input bindings and two sealed runner contexts. This does not measure retrieval
      quality, run an encoder, migrate an index or deploy a process.

### Corpus figures look stale (Z, flag only — may belong to KB-WM-*)

This handoff's header records 577 files / 18,010 chunks / 1,227.6 MiB; the live index measured
2026-08-21 is **943 files / 28,110 chunks / 2,199.13 MiB**. Roughly 56 % understated. Flagging rather
than editing, since it may already be owned by the watermark items.

## Research Intake Update — 2026-08-23 (wave 2 Stage-2b: `intake-1289#record`, `intake-1293#record`, `intake-1294#record`)

Three dives land on this handoff: the mxbai-edge-colbert tech report, the LightOn ONNX mirror of
answerai-colbert-small-v1 plus the `pylate-onnx-export` tool that emits it, and the ConstBERT /
verbose-query reproduction. The **code** half of the wave shipped in `epyc-orchestrator` `4e5e84c0`
and is recorded on the K1/K2/K3 rows above. What follows is the record half, the two work items the
wave left uncovered, and the compute queue. Class key: **Z** zero-compute · **G** compute-gated ·
**B** blocked-on.

### Records (Z) — written down so they are not re-derived

**H4 — the ONNX file-selection rule for any BERT-family late-interaction checkpoint.** Take the
LightOn mirror's `model_int8.onnx`; failing that, upstream's **root** `model_int8.onnx`. **Never
anything under `onnx/`**, and **never `vespa_colbert.onnx`**. Upstream
`answerdotai/answerai-colbert-small-v1` @ `934fa8bb` holds **11 ONNX files / 10 distinct blobs** —
3 at root (`model.onnx`, `model_int8.onnx`, `vespa_colbert.onnx`) and 8 under `onnx/`, where
`onnx/model_int8.onnx` and `onnx/model_quantized.onnx` are the same blob. The `onnx/` family
terminates at `last_hidden_state [batch, seq, 384]`: no ColBERT projection, no L2 normalisation, and
`onnx/` is ir_version 10 against the root's 7. `vespa_colbert.onnx` names its output `contextual` —
a third naming convention; only the root exports and the mirror's end at `output`. **Picking by
folder name builds a silently wrong index and raises no error.** The mirror has no `onnx/`
subdirectory, so it eliminates the footgun by construction, and its
`config_sentence_transformers.json` and `onnx_config.json` are byte-identical to each other, which
upstream's are not.

**H5 — K1 was never a gate on the mxbai family.** Both mxbai configs declare
`uses_token_type_ids: false`, and the 33.2 MB `model_int8.onnx` contains zero `token_type` strings,
so the missing-third-input failure K1 describes cannot occur for that family. K1 was correct and has
now landed (`4e5e84c0`); what it unblocks is **answerai-colbert-small-v1 / ColBERTv2 /
Jina-ColBERT-v2**, whose graphs *do* declare `token_type_ids` as required with no initializer
default. The mxbai family's real blocker was a different one — `do_lower_case`, unhandled and
silent — also closed in `4e5e84c0` as the K2 sub-item above.

**H6 — tokenizer identity, and what it does to the index-footprint projection.**
`mxbai-edge-colbert-v0-32m` and the deployed GTE-ModernColBERT-v1 share a **byte-identical
50,280-token vocabulary**. Verified locally 2026-08-23: the deployed
`gte-moderncolbert-v1-onnx/tokenizer.json` is sha256
`23abe2a8f5640f8836c24cead7b76e77613b846824d7540151c6d90d7c2f4869` with 50,280 vocab entries, and
`mixedbread-ai/mxbai-edge-colbert-v0-32m@bb13a29ec9b1/tokenizer.json` is sha256
`594291000b476c98ed600cbb1914ff128c79642a9433aac86213c7a5562d7c1a`; the two files differ **only** in
a pre-baked truncation/padding block and their `model.vocab` maps are equal with zero differing
entries. Because the vocabularies are identical there is **no tokenizer correction factor**: the
index-footprint ratio is the bare dim ratio **64/128 = 0.500×**, so the 2,199 MiB index measured
2026-08-21 projects to **~1,100 MiB** — roughly double the 0.757× / −534 MiB measured for answerai at
dim 96. This is a **projection, not a measurement.** Two conditions on any adoption note:

- Pin the ONNX revision at **≥ `963e23afa147`** (2026-04-15). The 2026-02-14 ColGREP export
  (`f93964d3e660`) **omitted the Dense projection layers** and emitted the wrong output dimension, so
  any copy pulled inside that 60-day window is silently broken.
- The one open variable left in the 0.500× projection is the lower-casing effect on token counts
  (`do_lower_case: true` on mxbai, `false` on the incumbent). That is a pure-tokenizer measurement —
  no model, no ONNX session — filed as **Z13** in the wave plan.

### New work items

- [x] **H1 (Z to quantify; remedy is G13) — doc-side truncation is tracked by no work item, and it is the largest retrieval defect on this page.** Evidence: Research `f695d241f23b474204c7add056ecd59bc75fadc8` (Research main `4ca00be28956675d1796a44ecff2c624cc6aa2d5`); Git artifacts `repos/epyc-inference-research/artifacts/kb-rag-h1-20261031/{REPORT.md,SHA256SUMS,census.py,test_census.py}`. ✅ 2026-10-31 [belief: cc] [receipt-ack: pip02-r36-english-run-20261107b FAILED — false positive: the receipt reads pass rc=0, the word comes from the stop-rule text 'failed/timeout pages are censored'; run COMPLETE 65/65 ok both arms]
      `markdown_chunker.py:25` sets
      `DEFAULT_MAX_CHARS = 4000` (and `config/kb_rag_config.yaml:31` `max_chunk_chars: 4000`) while
      `kb_rag.py:67` sets `_DOC_MAX_TOKENS = 256`, roughly a 1,024-character budget — so a full-size
      chunk has ~75 % of its content silently dropped at embed time. **Measured first-party against
      the live catalog 2026-08-23** (`data/kb_rag/index-qd-v1/catalog.sqlite`, opened read-only):
      28,155 chunks over 944 files, mean `token_count` 170.3, and **11,410 chunks = 40.5 % sit at or
      above the 256-token cap**, i.e. are truncated. That corroborates the 39.6 %-of-chunks /
      57.2 %-character-coverage pair in `intake-1278#record` and **refutes the inverted 60 % / 43 %
      pair** repeated in `intake-1294#record`; the defect is identical either way, only the polarity
      of the figures differed. Note the catalog's `token_count` is `emb.shape[0]`, i.e.
      **post-truncation**, so it saturates at 256 and can report *that* a chunk was truncated but
      never *by how much* — any character-coverage figure must be re-derived by tokenizing with
      truncation disabled. Quantifying is zero-compute; the remedy arms need a full corpus re-embed
      and are **G13**.
  - *(2026-10-31, enrolled qd-v1 model-free census.)* On the frozen current catalog of 35,280 rows / 1,774 paths, 16,243 rows (46.040%) exceed 256 model-input tokens and 16,283 (46.154%) are at or above the cap; nearest-rank p50/p95/max are 229/1,111/1,929. Capped model-input tokens retain 6,347,102 / 12,378,893 (51.274%); tokenizer-offset-covered document codepoints retain 21,058,629 / 41,200,048 (51.113%). This is the declared `[D] ` + raw-text qd-v1 recipe replay, not the original historical vector-tokenizer identity or current qd-v2 behavior; retrieval quality and adoption are unmeasured, and G13 remains open. Two native controls and the independent 35,280-row join/hash plus aggregate-allowlist audit passed; raw text was not published. The capture's enrollment note honestly records the ROOT registry commit as pending at capture time.
  - **2026-10-30 preparation checkpoint (G13; full sweep not run):** READY packet
    `/mnt/raid0/llm/tmp/codex-ni-kbrag-g13-truncskip-20261030`, current ID
    `codex-ni-kbrag-g13-truncskip-r2-20261030`, rank 60, any CPU quarter, 21,600 s, 16 GiB,
    48 GiB output reservation. R2 supersedes R1, withdrawn before ARM/FILLERS/grant after the
    counter-field review; R2 pins source manifest `b4c1d90a670ebf147e17521dbe6b7cdbe87186a9ff8780da656e0174be28637f`. Final native smoke
    passed (32.061 s, rc 0); captured post-work cleanup returned 75 after 7.324 s. Full design is
    six arms (doc caps 256/300/rechunk 1,100 × punctuation skiplist off/on), 490 native
    query calls (7 indexes × 70 original K7 queries), eight pinned encoding workers, resumable chunks/cases, plus the canonical index
    scored separately. Inputs: 1,522 indexed paths, 34,221 4,000-char chunks / 61,353 1,100-char
    chunks, 39,382,114 bytes. 1,520 complete candidate snapshots reproduce the indexed chunk
    multisets, but historical whole-raw-file identity is unproved; these comprise 1,469 current
    files and 51 Git-recovered files. Two other paths use complete current fallback snapshots
    with changed-snapshot flags. Native atomic worker records support NEW=3 normal / NEW=2 cutoff, parent NEW=0 each;
    missing/invalid records remain unknown. Only doc-cap 256 has the matched new baseline; doc-cap 300, rechunk 1,100, and
    punctuation arms are candidate comparisons. June historical 0.5690 over 577 files / 18,010 chunks is not comparable, original gate is
    unassessable, and adoption is unsupported. The full sweep remains unrun; leave G13 open.
- [x] **H2 (Z) — no query-length instrumentation exists anywhere in the retrieval path.** We cannot
      today answer whether a live agent query has *ever* exceeded 48 tokens; every statement about the
      caps is inferred from a 90-case curated pool and never observed from traffic. Log the encoded
      query token count at the one call site that has it — `kb_rag.py:762`,
      `q_emb = colbert_encoder.encode(text, _QUERY_MAX_TOKENS, role=query_role)` (this was `:713`
      before `4e5e84c0` shifted the file by 49 lines) — and report **p50 / p95 / max / over-cap
      rate**. **The instrument must not be vacuous:** `encode()` calls
      `enable_truncation(max_length=max_tokens)` and `enable_padding(length=max_tokens)`
      (`colbert_encoder.py:373-374`), so a count taken from `encoded.ids` is *always* exactly
      `max_tokens` and the over-cap rate would read 0 % forever. Take the count from a
      truncation-disabled tokenization, or the metric measures the cap rather than the query. This is
      the only path by which the caps question becomes empirical instead of inferred, and it is what
      makes **B7** answerable at all.
      ✅ 2026-09-16 — instrument and reporter landed. Evidence: epyc-orchestrator `32336445`, branch
      `sub/tooling-orch-20260916`, integrated by orchestrator merge `370dc715` (pushed in `753343f5`, 2026-09-16). No measurement has been run.
      - `colbert_encoder.count_tokens(text, role=)` tokenizes on a private copy with truncation and
        padding off. It applies the same prefix, casing and specials as `encode()`, and never touches
        the shared tokenizer.
      - `kb_rag.query()` appends one record per query to `data/kb_rag/telemetry/query_lengths.jsonl`.
        Set `KB_RAG_QUERY_LENGTH_LOG` to redirect it, or to `off` to disable it. Records carry the
        query's sha256 and length, never its text. The test suite pins the log off.
      - `scripts/kb_rag/query_length_report.py` reports nearest-rank p50, p95, max and the over-cap rate
        per (encoder, cap, convention) group. An empty log reads UNKNOWN, not 0 %.
      - Non-vacuity test: with the shared tokenizer capped at 8, the encode-path count is 8 and
        `count_tokens` returns 32.
      - Tests: `test_kb_rag_query_telemetry.py`, 15 passed. Combined with the retrieval suites, 62
        passed.
      - Belief kernel: VB-KBRAG-QLEN (adapter at root `039a4f3b`, root merge `719ac638`).
      - Next step: once traffic accrues, run the reporter to answer B7.

### Compute-gated (G) — filed, not run; both compute planes were held by other sessions this wave

- [x] **G11 — ONNX INT8-vs-fp32 parity fixture.** ✅ 2026-11-02 (ws58 BRF-T3-2; result: **INT8 gate NOT met**). Top-1 is 59/70 for both FP32–INT8 pairs, and the recomputed MaxSim reproduces the stored top-1 exactly. In the 11 disagreements, the INT8 pick sits at FP32 rank 2 nine times, rank 3 once and rank 6 once. These are near-ties: the median FP32 relative top-2 margin is 0.00072 against 0.0070 for agreeing queries. Fidelity only; PREFIX-3 and adoption are not covered. [belief: cc] Evidence: `docs/design/backlog-refactor-2026-11/t3-evidence/kb-g11-disagreement-20261102.json` over `/mnt/raid0/llm/tmp/codex-ni-kbrag-g11-parity-r2-20261030/results` (KEEP). 200 real KB chunk texts, both roles, `model.onnx`
      vs `model_int8.onnx`; report per-token cosine distribution, max abs Δ, and **MaxSim top-1
      agreement** — the decision-relevant metric. Fold in the **mirror-vs-upstream-root** arm: same
      texts, same ORT process / EP / thread config, compared by cosine and max abs Δ and **never by
      byte hash** — the two graphs differ by 252 shape-plumbing nodes and a renamed projection module
      while their weight blobs are bit-identical, so a hash comparison returns a false negative by
      construction. **Owning handoff**: this one (`internal-kb-rag.md`). **Gate — what result opens
      it**: top-1 agreement ≥ the incumbent's **100 %** and max abs Δ within the same order as the
      **6.60e-03** already accepted (`colbert-reranker-web-research.md:506`). Replaces the vendor
      ">0.99 cosine" folklore with our own number — **do not treat the vendor figure as the
      baseline** (`MEASUREMENT.md`: no third-party number gates this stack). Belief-kernel caveat to
      carry in every tuple this produces: an INT8-vs-fp32 cosine is a **fidelity** claim about one
      graph pair, never a retrieval-quality claim.

  - **2026-10-30 preparation checkpoint (R2; no full result):** The final packet is
    `/mnt/raid0/llm/tmp/codex-ni-kbrag-g11-parity-r2-20261030`. It pins 200 real KB chunks, the
    four canonical mirror/upstream-root FP32/INT8 graphs, both encode roles, and the existing 70
    K7 queries for primary MaxSim top-1 fidelity. The actual native qualification passed 12
    encode operations with rc 0; the bounded cutoff retained four operations and returned rc 75
    with cleanup verified. A resume smoke reused 12 cached rows and performed zero new native
    operations. R1 was withdrawn before arm/grant after its missing mandatory resources helper and
    nonnumeric CPU metadata were found; R2 includes the helper and a read-only proof of actual
    CPU-fill behavior. The keeper accepted R2 as READY-WAIT at rank 58, any CPU quarter, with no
    quarter available; it was not armed or granted. The full 200-chunk run remains pending. The
    upstream literal-prefix tokenizer guard remains a separate serving refusal; numeric-token-ID
    parity does not imply serving adoption. No retrieval-quality or B6 decision follows.
  - **2026-10-30 G11 R2 result — reject the 100% INT8 top-1 gate.** The 70 existing K7 certification queries against the same 200 frozen real KB documents yielded **59/70** mirror FP32–INT8 and **59/70** upstream FP32–INT8; mirror–upstream same-precision pairs each **70/70**. The separate self-containing 200-chunk ranking agreed **200/200** for all four pairs and is not the primary test. Both query/document roles cover 200/200; all 1,880 expected per-item pair records and all 70/70 primary query records per pair are present; missing/shape/transport failures 0. For FP32–INT8, max absolute delta is **0.141253 query** and **0.184379 document**, respectively 21.402×/+0.134653 and 27.936×/+0.177779 vs accepted 0.00660; same-precision mirror–upstream maxabs 0. Per-token distributions and K7 values are in `progress/2026-10/2026-10-30-codex3-ni-native-filings.md`. No numerical same-order tolerance was predeclared, so no invented maxabs pass/fail; top-1 alone fails. This is graph fidelity, not retrieval quality, B6 adoption or promotion. Upstream literal-prefix tokenizer guard still refuses serving independently of numeric-ID diagnostic. Native records, pins, rankings and failure denominators: `/mnt/raid0/llm/tmp/codex-ni-kbrag-g11-parity-r2-20261030/`. [belief: cc]
  - **[declined: operator 2026-11-07 — investigation clause done (11 near-ties, `docs/design/backlog-refactor-2026-11/t3-evidence/kb-g11-disagreement-20261102.json`); the literal-prefix serving-guard clause is folded into B6's closure note below and is moot because B6 is closed 'Keep GTE']** Investigate the 11 FP32–INT8 K7 rank disagreements and resolve the independent upstream literal-prefix serving guard before any adoption decision; retain G11 open.

- [x] **G12 — structural query-shift evaluation.** Add a verbose/narrative arm (~20 cases, 60–150
      words) to the K7 pool and score the incumbent. Our current pool is **90 short well-formed
      queries** of 9–18 words (`scripts/kb_rag/k7_cert_cases.json` 70 + `k7_seed_cases.json` 20),
      median ~23 tokens, max 33, with **0 of 90 reaching the 48-token cap** — exactly the distribution
      the ConstBERT reproduction criticises BEIR for. **Owning handoff**: this one
      (`internal-kb-rag.md`). **Gate — what result opens it**: a verbose arm scoring **>2 pp below
      the short arm** would be the **first local evidence of query-length sensitivity**, which today
      exists nowhere in the repo. Opens **B7**.
  - **2026-10-30 preparation checkpoint (G12; no cohort result):** The final packet is
    `/mnt/raid0/llm/tmp/codex-ni-kbrag-g12-queryshift-20261030`. It freezes the 90 original short
    queries plus 20 paired 66–73-word narrative counterparts (certification indices 0–13 and
    50–55) against the unchanged full `index-qd-v1` incumbent (34,214 chunks, 1,522 files, GTE
    INT8, query/doc caps 48/256, optional weights zero). The two-query full-index smoke passed in
    56.70 s with 0.572 GiB sampled RSS; the one-query cutoff returned rc 75 in 27.88 s and
    verified cleanup. The keeper accepted rank 59, any CPU quarter, 8 GiB, 7,200 s; the row was
    not armed or granted. The full 110-query cohort and its 20-pair primary comparison remain
    pending, so there is no B7 verdict or cap/model decision. Existing truth coverage is preserved
    with missing/moved evidence paths disclosed (cert 74.76%, seed 72.5%); none is filtered or
    relabelled. See `G12`'s `PROTOCOL.md` and `READY.proposed.json` for exact cohort and pin
    definitions.
  - 2026-10-30: fixed 20 paired certification questions, short vs 66–73-word narratives, evidence-file recall@10 (higher is better): **37.50% vs 38.333%**, short-minus-verbose **−0.833 pp**, so the predeclared strictly >2 pp drop does **not** open B7. Full native 110/110 = 70 original cert + 20 seed short + 20 verbose on the unchanged 34,214-chunk/1,522-file gte INT8 qd-v1 index (query cap 48, document cap 256; optional weights zero). Secondary 90-short recall = 37.685% (70 cert 36.786%, 20 seed 40.833%). Uncapped tokens: cert 16–33, seed 20–29 (0/90 over cap); verbose 77–91 (20/20 over cap). Original evidence denominators and stale/missing paths are retained: catalog-missing evidence entries cert 53/201, seed 15/50, verbose 18/51; case records report every listed path missing in the execution environment. This limits local sensitivity and generalization; no path was dropped or relabelled. Fixed cohort is not live-traffic evidence, and the comparison does not isolate 48-token truncation as the cause. No cap/model adoption. All 110 case query/source/index hashes and metrics independently rechecked with the pinned scorer; 20 paired values and evidence: [filing artifact](../../artifacts/compute/results-filing-c3-g12-20261030.json), raw `/mnt/raid0/llm/tmp/codex-ni-kbrag-g12-queryshift-20261030/results/`. ✅ 2026-10-30 [belief: cc]

- [x] **G13 — doc-truncation recall sweep.** ✅ 2026-11-07 — answered by the 2026-10-31 native diagnostic recorded below: six re-embedded arms plus the stored index, recall@10 against the matched plain baseline 0.367857; no arm exceeded the +0.02 trigger (best: 256/punctuation-skiplist +0.007143; 300-token and 1,100-char arms were negative). The historical 0.5690 baseline used a different corpus and is unassessable, so the matched baseline is the comparator; no truncation or skiplist remedy is indicated by this evidence. Evidence: `artifacts/compute/codex3-g13-truncskip-20261031/SHA256SUMS`. [belief: cc] *(Original spec follows.)* recall@10 on the K7 70-case pool at `_DOC_MAX_TOKENS`
      **256** vs **300** (the incumbent's declared `document_length`, verified in
      `gte-moderncolbert-v1-onnx/onnx_config.json`) vs a chunker `max_chunk_chars` reduced to
      **~1,100**. Batch it with the **punctuation-skiplist arm** — the model ships a 32-entry
      `skiplist_words` list that we apply nowhere (`grep -rn skiplist src/retrieval/` returns
      nothing) — because both arms need a full corpus re-embed and should share one. **Owning
      handoff**: this one (`internal-kb-rag.md`). **Gate — what result opens it**: any arm beating the
      **0.5690** plain-`maxsim` recall@10 baseline by **>2 pp**, the declared noise floor. Directly
      remediates **H1**.

  - *(2026-10-31, G13 full native diagnostic.)* R2 rc0 collected 70 frozen truth cases for six re-embedded arms plus a separate canonical stored index (490 case records). Recall@10 higher better: newly re-embedded 4000/256/plain 0.367857; 4000/256/punctuation 0.375000 (+0.007143), 4000/300/plain 0.340476 (−0.027381), 4000/300/punctuation 0.327381 (−0.040476), 1100/256/plain 0.364286 (−0.003571), 1100/256/punctuation 0.353571 (−0.014286), each delta against the new matched plain baseline. No arm exceeds the strict +0.02 descriptive trigger. Canonical stored index scored separately 0.367857. The historical 0.5690 gate used a different 577-file/18,010-chunk corpus and is unassessable here; no original quality/adoption gate closes. All 490 truth/ranked-file metrics, 1,522 snapshot hashes and 1,520 unchanged chunk multisets against pinned catalog independently checked; two full current snapshots changed. Indexed-text equivalence is not historical whole-file identity. Eight native worker receipts aggregate 105,950 new encodes, 23,845 existence skips, 0 cache loads; stale/missing truths and original denominators remain. [Evidence and audit](../../artifacts/compute/codex3-g13-truncskip-20261031/SHA256SUMS). [belief: cc]
  - **Scratch** (retention, 2026-11-06, operator-adhoc-ops): `/mnt/raid0/llm/tmp/codex-ni-kbrag-g13-truncskip-20261030/` (~18 GB on disk; row `codex-ni-kbrag-g13-truncskip-r2-20261030` already FILED 2026-10-31, verdict = 6-arm +0.02 trigger unmet, historical 0.5690 gate unassessable). KEEP: `results/{RESULT.json,cases/,worker-summaries/,SKIPLIST.json}`, `PROTOCOL`/pin/SOURCE/CHUNKS JSON, `source_bytes/`, `src/`, `engine/`, smoke dirs (<200 MB total; the audit set is also committed under `artifacts/compute/codex3-g13-truncskip-20261031/`). RECLAIMABLE: `results/indexes/` (18.4 GB apparent; per-arm .npz embeddings + catalog.sqlite) and `results/raw/` (9.4 GB apparent; hardlink-shared with indexes) — regenerable by re-running the pinned engine; ~18 GB actual on-disk. Not deleted; deletion needs operator confirm. [no-belief: retention note]

### Blocked-on (B)

- **[declined: operator 2026-11-07 — decision 'Keep GTE': answerai's measured quality gain is nil (54.67 vs 53.35 BEIR = 1.32 pp, inside the ~2 pp noise floor) against 4.46x fewer parameters and a -24.3 % index footprint; the swap forces a full re-embed (qd-v2 refuses mixed indexes) and the upstream literal-prefix serving guard (folded in from the G11 child) would need work; G11's INT8 gate was not met (59/70). Revisit if index footprint becomes a real constraint]** **B6 — switch the KB encoder to answerai-colbert-small-v1.** **Blocked on G11** and on the open
      **quality/cost decision** recorded at C1/C2 above: 54.67 vs 53.35 = 1.32 pp, *inside* the ~2 pp
      noise floor this handoff declares, against 4.46× fewer parameters and a measured −24.3 % index
      footprint. Named here so it is not re-derived as new. **Two of its original four blockers have
      cleared**: the K1 port and the prefix-guard hardening both landed in `4e5e84c0`, and the K2
      widening is half-landed (`onnx_config.json` is read; declared caps are not yet enforced), which
      is enough to *load* such a graph but not enough to fail loudly on a mis-declared one. Do not
      attempt the swap before G11 returns a number, and note this is a **decision**, not a task: it
      trades 1.32 pp of BEIR against −24.3 % footprint on a corpus whose own noise floor is 2 pp.
- **[declined: ws58 2026-11-03 content-review: its own text: G12 did not meet the opening rule]** **B7 — raise `query_maxlen` above the checkpoint default and measure.** [too-big: G12 did not meet opening rule; owner must observe qualifying signal] **G12 did not meet its >2 pp opening rule; remains blocked on that signal.**
      Pointless without a verbose-query arm: our current pool never reaches even 33 tokens, so raising
      the cap today would measure padding rather than retrieval. Record the architectural disanalogy
      that most limits the reproduction paper's transfer to us — GTE-ModernColBERT-v1 is
      ModernBERT/RoPE with `max_position_embeddings: 8192`, so it is *architecturally* free to encode
      long queries, unlike the 512-position BERT-family checkpoints the paper studies. **H2** supplies
      the traffic distribution that says whether the question is live at all.

## MAIN-reviewed current-toolkit refinements — 2026-10-06

### S04-F1 — Finish KB-WM-6 as an advisory graph freshness check

- Completed NI06-02 (MAIN, 2026-10-06; source `ec513cbe`, original CI37425524371): compare the checkout `.index-graph.json` with `build_graph(state)` in `index_state.py --check` and emit a non-fatal warning for missing/stale graph files. Preserve provenance-only/silent-on-absence screener behavior. Add current/stale/missing fixtures; this is deterministic integrity checking, not a model decision or retrieval-quality claim.

### S04-F2 — Narrow K2 to the remaining hard-coded internal KB caps

**JEV-aware source narrowing (2026-10-06):** `_load_declared_config()` and `max_query_tokens()` / `max_document_tokens()` now exist; `src/tools/web/colbert_reranker.py` already uses the helper. Remaining fixed values are in `src/retrieval/kb_rag.py` (`_QUERY_MAX_TOKENS=48`, `_DOC_MAX_TOKENS=256`) and its encode call sites. Close only this KB-RAG cap plumbing with synthetic declared/absent/invalid-config fixtures and preserve index metadata/stamp semantics. Do not re-embed or claim retrieval improvement; any stored-index cap transition stays under OP-24.

**Completed bounded cap implementation:** NI07-02 above closes this source-corrected scope. Existing/partially stamped catalogs are not silently restamped; stored caps win and orphan vector files require catalog identity. Original synthetic acceptance is an observation only.

### S04-F3 — Complete the missing tokenizer identity half of K3

**JEV-aware source narrowing (2026-10-06):** `_stamp_meta()`/`_check_embedding_dim()` already guard width, but `_read_meta()` has no tokenizer digest and `colbert_encoder` loads `_TOKENIZER_PATH`. Finish only the missing tokenizer SHA-256 stamp/read check; test same hash, mismatch refusal, and legacy unstamped catalog behavior with temp files. This is deterministic encoder identity integrity, not a JEV/model decision or retrieval-quality claim.

### MAIN-reviewed writer follow-ons — 2026-10-06

- [x] **KB-REMOVE-ROLLBACK — preserve active vector bytes when catalog removal fails.** ✅ 2026-10-06 — Sourceefd67c52 promoted APPmaine2ad3dbf moves vector unlink after successful catalog/native commit and checks surviving references. Hash/commit failures retain rows and bytes; postcommit cleanup refusal returns an explicit orphan outcome. Ten new synthetic cases in [original108/108CI](../../artifacts/ni07/run-37441909661/README.md), independently reopened by MAIN. No model was loaded; cross-process writer safety remains outside scope.
- [x] **KB-FORCE-DEDUP — repeated force-builds must not accumulate duplicate chunk/FTS rows.** ✅ 2026-10-06 — [Accepted source/fixture contract](../../docs/reference/kb-force-build-identity-contract.md), APPmaine7257b4c, original TRUE113/113. Lowest existing exact identity reused after successful encode/write; touched duplicate/FTS reconciliation only. Nonforced/failure/cleanup/cap/tokenizer/native dependency behavior retained; no vector unlink or live embedding run.


- [x] **KB-K7-REPORT-DEPENDENCY — attach existing native catalog identity at report time.** ✅ 2026-10-06 — [Contract](../../docs/reference/k7-report-catalog-dependency-contract.md), APPmain1109ad39 and originalCI37450891733 TRUE11/11 after MAIN full custody review. Strict original identity once, absent/legacy null, stale/tamper refuses before publication; ranking/metrics/writers unchanged. Broader consumers and historical K7 algorithm posture remain separate.


- [x] **KB-VECTOR-STAGED-PUBLISH — preserve active vector bytes when serialization/publication fails.** ✅ 2026-10-06 — [Accepted staged writes](../../docs/reference/kb-vector-staged-publication-contract.md) promoted APPmainbb601d0b; originalCI37451221250 TRUE122/122 independently reopened. Both APIs close temporary NPZ before replace, preserve prior bytes/permissions on failure; native logical catalog scope unchanged. Post-replace SQL failure and broader crash/concurrent-writer guarantees remain outside this slice.


- [x] **KB-LAB-CONTEXT-DEPENDENCY — carry the original strict native catalog record in lab context artifacts.** ✅ 2026-10-06 — [Contract](../../docs/reference/lab-kb-context-catalog-dependency-contract.md) promoted APPmaineb066f71; originalCI37454908617 TRUE19/19 after MAIN source/API custody review. Explicit collection-time path/original record/null unknown, stale/tamper refuses before callbacks; public two-value API, normal fallback/non-KB/deterministic behavior retained. No frozen-query snapshot; original FALSE17/19 kept.

- [x] **KB-K2-QUERY-EXPANSION-REFUSAL — enforce the optional expansion declaration before model construction.** ✅ 2026-10-06 — [Contract](../../docs/reference/colbert-query-expansion-declaration-contract.md) promoted APPmain7980b229, originalCI37456357367 TRUE24/24 independently reviewed by MAIN. Fresh-load strict optional bool; false/absent unchanged, unsupported true/malformed explicit failure before constructors. Actual graph inputs/width/caps/lowercase retained; broader K2/web/live transition gates remain.


- **2026-10-31 Hy-MT2 Q4 recipe diagnostic:** `codex-ni-hymt-q4-recipe-r1-20261030` completed 16/16 native cases, all with nonempty outputs; the native template probe matched exactly, and the structured case recorded valid JSON with keys, model and count preserved. The writer reports children drained and server exit zero. This is a Q4_K_M alternative launch diagnostic only; it does not validate low-bit compatibility, speed, translation quality, downstream summaries or RAG, and does not authorize adoption. The mandatory same-model translation-control C and full ABC remain unrun. Evidence: `/mnt/raid0/llm/tmp/codex-ni-hymt-q4-recipe-r1-20261030/results/RESULT.json` SHA-256 `a869c2f21a1bc71b970762d151ac2d24d399a68898e9e8d672d1e2c7f181e650` and `template_probe.json` SHA-256 `b430c681d309248e8a9d3570e87efced808bb8b758f71d152784eecabc36d10d`. [belief: cc] [Bounded evidence](../../artifacts/compute/ni-filing-20261031-0230/MANIFEST.json).

## Wiki transparency from intake-2619/2620/2621 (ws58 intake 2026-11-02; operator approved "Approve, go to Stage 4", D9 acknowledged for scripts/coordination)

Plan: [knowledge-transparency.md](../../research/deep-dives/ws58-jev-20261102/knowledge-transparency.md). **Order (operator, 2026-11-02):** (1) SA-1 + JEV-1; (2) SA-2, SA-3, JEV-3; (3) JEV-5 phase A, KT-1, KT-3; (4) the rest (JEV-2, JEV-4, JEV-6, SA-4, KT-2, KT-4, KT-5). JEV-5 phases B/C only after the operator has used phase A.

- [x] **KT-1** ✅ 2026-11-02 ROOT `1eb5a93a7` (progress `36ece7c6e`) [no-belief: infrastructure, no measurement] [S] `.claude/skills/project-wiki/scripts/lint_wiki.py`: add wiki-page orphan, unsourced-bullet and conflicted/refuted-citation passes (the latter from cite-check); emit JSON for KT-3 (intake-2619#record). removes: manual hunting for orphan pages and uncited claims.
- [x] **KT-4** ✅ 2026-11-02 ROOT `1eb5a93a7` (progress `36ece7c6e`) [no-belief: infrastructure, no measurement] [M] Compiled pages readable: move each page's multi-KB "Last compiled" line into a log section and keep a one-line current-state summary per page in `wiki/INDEX.md`; generate the cross-store edge list (md links, `intake-NNN#claim` citations, ledger `depends_on`, handoff deps) as JSON for the KT-3 graph; an Obsidian stub vault is optional generated output only (intake-268#record). removes: the append-only history line at the top of every page.
- **[declined: ws58 2026-11-03 content-review: wiki hygiene bookkeeping at operator cadence]** **KT-1-FU** [S] First lint baseline: 575 unsourced-bullet warnings, 6 contradictory-status, 123 intake-disposition, 17 link-target issues; clean up at operator cadence together with the wiki sweep. removes: the standing lint backlog.

## Track: colbert-reranker-web-research
<!-- gate: none -->

> Folded from `handoffs/active/colbert-reranker-web-research.md` @ `ccf37cd0b6a4` on 2026-11-02 (BRF-T1-F8, route 1a, operator D1/D5; retired row PIP-01 → PIP-04). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### ColBERT Reranker for web_research Pipeline

**Scratch**: `/mnt/raid0/llm/tmp/codex-ni-g14-reason32m-20261030/` (KEEP-marked READY diagnostic and evidence); `/mnt/raid0/llm/tmp/codex-ni06-kb-20261006/`; owned APP worktrees `/mnt/raid0/llm/worktrees/codex-ni07-s9-20261006/`, `/mnt/raid0/llm/worktrees/codex-ni07-promote-s9-20261006/`.

**Status**: refreshed 2026-05-28; S5 gate rechecked 2026-06-14 — S1-S4 complete; zero-page telemetry defect repaired; targeted and representative direct-tool probes produced real fetched/synthesized counters. Current S5 request-path reranker decision is **NO-GO/HOLD**: representative direct-tool deep-research sentinel sample synthesized 55 pages with 0 irrelevant pages, below the >20% waste threshold. Live Gate-3 now passes hard telemetry plus the `web_research` soft structured-output probe after `epyc-orchestrator` `9a220b9`; keep instrumentation and reranker utilities available but do not add request-path reranking complexity.
**Created**: 2026-04-05 (extracted from `04-mirothinker-worker-eval.md` intake-174)
**Updated**: 2026-05-28
**Priority**: MEDIUM
**Effort**: Medium
**Depends on**: AR-3 autopilot data — S5 requires the post-AR-3 irrelevant-page analysis to confirm >20% waste rate before implementation proceeds. No infrastructure dependency; this is a data gate. See "Post-AR-3 Analysis" section below for the go/no-go script and thresholds.

#### 2026-05-28 Audit Reset — Executor Start Here

This handoff is not blocked on library or model setup anymore. It is blocked on a measurement decision: does `web_research` currently waste enough synthesis work to justify a reranker in the request path?

**Critique of older structure**: the file still read like a model-selection handoff, even though model setup and feature flag work already landed. The real ambiguity was the gate: implement S5 only if telemetry shows irrelevant-page synthesis is material. This reset puts that gate first and gives concrete forks.

**Verified implementation context**:

- Orchestrator commit `270d7317` added S1/S2 relevance instrumentation and `web_research_rerank` feature flag plumbing.
- Orchestrator commit `41624699` wired `search_backend` into telemetry for the post-AR-3 analysis path.
- Inference-research commit `f48dc05` added the baseline analyzer.
- No reranker code should be added until the gate below is answered.

**S5 go/no-go gate**:

Run the analyzer on the most recent AR-3 / web-research eval bundle:

```bash
cd /mnt/raid0/llm/epyc-inference-research
python3 scripts/benchmark/analyze_web_research_baseline.py benchmarks/results/eval
```

If the eval bundle is missing or too sparse, use production/orchestrator logs as a fallback:

```bash
rg -n "web_research relevance summary|irrelevant_rate|pages_irrelevant" \
  /mnt/raid0/llm/epyc-orchestrator /mnt/raid0/llm/epyc-inference-research/benchmarks/results
```

**Decision forks**:

| Observed irrelevant-page rate | Decision | Implementation path |
|---:|---|---|
| >20% with >=50 synthesized pages | GO | Implement S5 in `research.py` with lazy ONNX singleton, then run S6 A/B. |
| 10-20% or <50 pages | HOLD | Add more web_research sentinel traffic; do not add request-path complexity yet. |
| <10% with >=50 pages | NO-GO for S5 | Keep instrumentation; close this handoff as "reranker not justified"; optionally expose utility for offline analysis only. |

**2026-06-12 gate analysis (read-only):** ran
`python3 scripts/benchmark/analyze_web_research_baseline.py benchmarks/results/eval` in
`/mnt/raid0/llm/epyc-inference-research`.

- Questions with `web_research_baseline`: 1,274
- Questions triggering `web_research`: 771 (60.5%)
- Recorded `web_research` calls: 33,424
- Pass rate with web_research: 671/771 (87.0%)
- Pass rate without web_research: 440/503 (87.5%)
- Aggregated page telemetry across files with `web_research_telemetry`: fetched=0, synthesized=0, irrelevant=0
- No current orchestrator-log `web_research relevance summary` fallback rows were present.

**Decision:** HOLD. The gate requires >=50 synthesized pages before a GO/NO-GO irrelevant-page-rate decision.
This result also shows the existing analyzer-visible web_research data has source yield zero, so the next
useful work is fresh sentinel traffic or web_research fetch/telemetry repair, not S5 implementation.

**2026-06-14 telemetry repair/probe:** after `web_research` zero-page telemetry repair landed in
`epyc-orchestrator`, ran a targeted source/fetch/synthesis probe with SearXNG plus only the
`worker_general` quarter endpoint needed by `web_research` (`http://localhost:8082/completion`).

- Artifact: `/mnt/raid0/llm/epyc-orchestrator/benchmarks/results/eval/web-research-telemetry-serial-20260614T1908Z`
- Query set: 20 ColBERT/reranking-focused queries, `max_results=5`, `max_pages=3`
- Runtime setting: serial synthesis (`_MAX_SYNTH_WORKERS=1`) because the default 3 concurrent synth calls against a single `-np 1` worker quarter timed out.
- Results: 20/20 successful queries; 100 search results; 60/60 pages attempted, fetched, and synthesized; fetch failures 0; synthesis failures 0; irrelevant pages 0; search backend `searxng`.

Decision: the telemetry denominator is now healthy, but this targeted probe does **not** justify S5. It is biased toward relevant ColBERT pages and observed `irrelevant_rate=0.0`. Keep request-path reranking off. The next gate should be a representative web_research sentinel/eval sample using the same repaired counters; implement S5 only if that sample crosses the existing >20% irrelevant-page threshold.

**2026-06-14 representative direct-tool sentinel + synthesis hardening:** landed
in `epyc-orchestrator` `93c4a09` (`Harden web research telemetry probe`).

- Added `scripts/benchmark/web_research_telemetry_probe.py`, a direct
  tool-only probe for `web_research` counters. It can run the
  `orchestration/deep_research_sentinel.yaml` query set without invoking
  orchestrator role routing, emits metadata-only `records.jsonl` plus
  `summary.json`, supports `--shard-count/--shard-index`, and can pin a shard
  to a specific worker endpoint.
- Baseline representative run:
  `/mnt/raid0/llm/epyc-orchestrator/benchmarks/results/eval/web-research-direct-deep-sentinel-20260614T1936Z`.
  It ran all 20 deep-research sentinel prompts through SearXNG + the
  `http://localhost:8082/completion` worker with serial synthesis. Result:
  20/20 successful calls, 100 search results, 60 pages attempted, 57 pages
  fetched successfully, 55 pages synthesized, 3 fetch failures, 2 worker
  synthesis failures, 0 irrelevant pages (`irrelevant_rate=0.0`).
- Sharded mitigation validation:
  `web-research-direct-deep-sentinel-mitigated-s{0,1,2,3}-20260614T1953Z`.
  Four probe processes ran across `8082/8182/8282/8382`, serial within each
  worker. Result: 20/20 successful calls, 75 search results, 45 pages attempted,
  43 pages synthesized, 2 fetch failures, 0 synthesis failures, 0 irrelevant
  pages. This validated the faster tool-working pattern and the synthesis
  hardening, but it is not the canonical S5 denominator because parallel
  SearXNG returned fewer results.
- Validation policy: use serial single-slot runs only for canonical denominators,
  latency, reliability, or quality comparisons. For "does the tool work?"
  checks, prefer bounded parallel shards across independent worker slots/ports
  or explicitly multi-slot servers; keep at most one in-flight synthesis request
  per single-slot endpoint to avoid manufacturing timeout failures.
- Worker synthesis hardening: `_synthesize_page()` now logs bounded HTTP error
  detail and retries one worker HTTP 5xx with a reduced `n_predict=256`.
  Regression coverage proves a 500 on the primary 512-token call can recover on
  the reduced-cap retry.
- Live request-path check: Gate-3 hard telemetry initially passed after the HOT
  stack was started (`get_eval_secret` counted 8, all timing rows successful,
  no-tool isolation clean), while the old soft `web_research` structured-output
  probe timed out at 180s. Follow-up `epyc-orchestrator` `9a220b9` tightened the
  soft prompt to `max_results=1,max_pages=1` and made the soft classifier judge
  successful `web_research` telemetry before post-tool final-answer errors. A
  compact live role-path smoke then passed in 15.3s with one successful
  `web_research` call, and full Gate-3 passed end to end:
  `GATE3_HARD: PASS   WEB_RESEARCH: PASS`. The full run still over-called
  `web_research` five times, so repeated web_research calls are a
  prompt/control-efficiency follow-up, not a tool-plumbing blocker.

Decision update: representative direct-tool evidence now crosses the >=50
synthesized-page denominator with `<10%` irrelevant pages, so S5 request-path
reranking is a current **NO-GO**. Keep `web_research_rerank` default-off and do
not implement request-path reranking unless future AR-3/live role traffic shows
material irrelevant-page waste above the existing threshold. Next useful work is
role-loop efficiency around repeated `web_research` calls, not ColBERT
insertion.

**Risk controls if GO**:

- Keep `ORCHESTRATOR_WEB_RESEARCH_RERANK=0` default-off.
- Increase `max_results` only when the flag is on; legacy behavior must remain byte-for-byte close enough for existing tests.
- Cache the ONNX session at module scope and fail open to baseline DDG/SearXNG ranking if model load fails.

#### Objective

Add a reranking stage to the `web_research` pipeline between DuckDuckGo search and page fetch. Currently the explore worker receives all fetched pages and synthesizes directly, spending tokens on low-relevance pages that DuckDuckGo ranked highly by keyword match but are semantically weak for reasoning tasks.

#### Implementation Decision

##### Model

| Model | Params | BEIR NDCG@10 | License | Verdict |
|-------|--------|-------------|---------|---------|
| **ColBERT-Zero** (LightOn) | <150M | 55.43 | Verify from HF card (public data training) | **PRIMARY** |
| **mxbai-edge-colbert-v0-32m** (Mixedbread) | 32M | BEIR 0.521 / NanoBEIR 0.6520, dim 64 — beats the 17M sibling on both | Apache 2.0 | **FALLBACK** (re-pointed from 17M 2026-08-23) |
| ~~Reason-ModernColBERT~~ (LightOn) | 150M | 22.62/30.28 BRIGHT | CC-BY-NC-4.0 (non-commercial) | **ELIMINATED** |

**ColBERT-Zero** is the primary choice: strongest general-purpose BEIR score (55.43), same LightOn/ModernBERT family as our deployed GTE-ModernColBERT-v1, trained on public data only. License must be verified from HuggingFace model card during S3.

**mxbai-edge-colbert-v0-32m** is the fallback (**re-pointed from the 17M, 2026-08-23**): it beats the 17M sibling on full BEIR (**0.521 vs 0.490**) and on NanoBEIR (**0.6520 vs 0.6405**), carries dim **64 vs 48**, and is the base checkpoint of the derived Reason-mxbai-32m already wired into the three-slot selector (S5-amend below). The 17M's headline BEIR win over ColBERTv2 is **0.2 pp with significance testing explicitly declined** in the tech report itself, so the 17M was never the size that mattered here. Apache 2.0; ~3.2× faster CPU encoding than ColBERTv2 in the vendor's own single harness, with the scope limits recorded in §3 below. The slot is chosen on quality and dimension, not on licence.

**Reason-ModernColBERT** is eliminated: CC-BY-NC-4.0 prohibits commercial use. Self-training path exists (~2hr fine-tune on ReasonIR data) but is unnecessary overhead when ColBERT-Zero exists.

##### Library: ONNX Runtime (revised 2026-04-14)

**Why ONNX Runtime**: C++ engine with Python bindings, lightweight (no PyTorch), cp314-compatible, already-on-disk model (`model_int8.onnx`). Per-token 128-dim embeddings + MaxSim in numpy — the full pipeline is ~15 lines of code.

**Why NOT PyLate**: `fast-plaid` and `voyager` dependencies have no cp314 wheels. The orchestrator venv is Python 3.14. PyLate would require a separate venv or subprocess — unnecessary overhead when ONNX Runtime provides identical functionality.

**Why NOT alternatives**:
- **NextPLAID container**: Search-only API, no reranking endpoint. Designed for corpus-scale retrieval, not 10-snippet reranking.
- **RAGatouille**: Wraps ColBERT for LangChain/LlamaIndex integration. We use neither framework.
- **llama-server /reranking**: Would work (native C++ via HTTP) but requires GGUF conversion of the ColBERT model. ONNX model is already on disk.
- **sentence-transformers**: No cp314 wheels (same issue as PyLate). Would also pull PyTorch (~2GB).

##### Architecture: Snippet-level pre-fetch reranking

```
DDG/Brave search (8-10 results)         ← increase max_results when flag on
  → encode snippets + query via ColBERT  ← <1ms on EPYC for 10 snippets
  → rerank by MaxSim, take top 3         ← NEW: semantic filter
  → fetch top 3 pages (15s timeout each)
  → paragraph-level SHA256 dedup
  → synthesize via explore worker (45s each)
  → return combined summaries
```

**Why snippet-level, not page-level**: DDG already returns snippets for all results. Encoding snippets (not full pages) via ColBERT is sub-ms and avoids fetching irrelevant pages entirely. This saves both fetch time (15s timeout per page) AND synthesis time (45s per page).

**Why in-process, not container**: The task is encoding 10 short strings + 1 query and computing 10 MaxSim scores. This is a matrix multiplication, not a retrieval problem. Model loaded lazily on first call with flag enabled, stays in memory.

#### Existing Infrastructure

| Component | Location | Reuse? |
|-----------|----------|--------|
| NextPLAID containers (:8088/:8089) | `orchestrator_stack.py` lines 398-430 | Pattern reference only — NextPLAID is overkill for this task |
| `next_plaid_client` package | `code_search.py` lines 46-60 | Not needed (no NextPLAID container) |
| `sentence-transformers` | Already installed (CLIP vision pipeline) | PyLate builds on this — no new heavy dependency |
| `FeatureSpec` registry | `src/features.py` lines 75-129 | Use for `web_research_rerank` flag |
| GTE-ModernColBERT-v1 on :8089 | Deployed, 128-dim INT8 | Different use case (docs retrieval), validates ColBERT-family CPU feasibility |

#### Pipeline Analysis (2026-04-14)

Audited `epyc-orchestrator/src/tools/web/research.py` and `search.py`:

```
DDG/Brave search (5 results)
  → fetch top 3 pages (6000 chars each, 15s timeout, parallel)
  → paragraph-level SHA256 dedup
  → synthesize ALL 3 via explore worker (Qwen2.5-7B, 512 tok, 45s timeout)
  → return combined summaries
```

**Key finding: zero relevance filtering.** All 3 fetched pages get synthesized regardless of relevance. The worker prompt says "if not relevant, say so briefly" — so a 7B model doing a 45-second inference call is the only relevance gate. Each wasted synthesis costs ~45s of worker compute.

**Cost of NOT reranking:** With 3 pages synthesized per query, even 1 irrelevant page = 33% waste in worker inference. At scale (autopilot sessions with many web_research calls), this compounds.

#### combined_ops.py Relationship

`batch_web_search()` in `combined_ops.py` calls `web_search()` (DDG/Brave search returning titles/URLs/snippets), NOT `web_research()` (the full fetch+synthesize pipeline). Reranking in `research.py` does **not** automatically cover batch search in combined_ops.

**Future extension**: If reranker proves valuable, expose a `rerank_snippets(query, snippets)` utility function that `combined_ops.py` could also call.

#### Post-AR-3 Analysis

After AR-3 completes (or accumulates sufficient web_research trials), run the analysis script to extract the go/no-go decision:

```bash
cd /mnt/raid0/llm/epyc-inference-research
python3 scripts/benchmark/analyze_web_research_baseline.py /mnt/raid0/llm/epyc-inference-research/benchmarks/results/eval
```

The script reports:
- Total pages synthesized across all web_research calls
- Pages classified irrelevant (count + percentage)
- **Go/no-go recommendation**: `>20%` → proceed to S3, `10-20%` → marginal, `<10%` → skip

If checkpoint data is insufficient (few web_research calls), also grep orchestrator logs as a backup:

```bash
grep "web_research relevance summary" /path/to/orchestrator.log | tail -20
```

#### Work Items

- [x] **S1: Instrument relevance logging** ✅ 2026-04-14 — Added `_is_irrelevant_synthesis()` heuristic + per-page/summary logging to `_web_research_impl()`. Returns `pages_irrelevant` + `irrelevant_rate` in response dict. 5 tests added. **Data collection folded into AR-3 Package D** — AR-3 includes a `web_research` sentinel suite (50 questions) that will trigger this instrumentation automatically during autopilot runs.
  - File: `epyc-orchestrator/src/tools/web/research.py` (lines 44-69: detection, lines 376-400: instrumentation)
  - Tests: `epyc-orchestrator/tests/unit/test_web_research_dedup.py` (TestIrrelevantSynthesisDetection, 5 cases)

- [x] **S2: Register feature flag** ✅ 2026-04-14 — Added to `src/features.py` FeatureSpec registry + Features dataclass. Registry consistency test passes. Telemetry pipeline wired: `pages_irrelevant` + `irrelevant_rate` captured in `repl_executor.py`, `chat_delegation.py`, `WebResearchTelemetry`, and `analyze_web_research_baseline.py`.
  ```python
  FeatureSpec("web_research_rerank", False, False, "WEB_RESEARCH_RERANK",
              "ColBERT snippet reranking in web_research pipeline")
  ```
  Runtime: `ORCHESTRATOR_WEB_RESEARCH_RERANK=1`
  - File: `epyc-orchestrator/src/features.py`
  - Effort: ~15min

- [x] **S3: Model + encoding pipeline setup** ✅ 2026-04-14 — **REVISED**: PyLate eliminated. Using existing GTE-ModernColBERT-v1 ONNX (already on disk at `/mnt/raid0/llm/models/gte-moderncolbert-v1-onnx/`) + `onnxruntime` (installed in orchestrator venv). No download needed.
  - **License**: ColBERT-Zero = Apache-2.0 (verified from HF model card). mxbai-edge-colbert = Apache-2.0. GTE-ModernColBERT-v1 = already deployed. All clear for commercial use.
  - **PyLate eliminated**: `fast-plaid` and `voyager` dependencies have no cp314 wheels (orchestrator venv is Python 3.14). ONNX Runtime (1.24.4) has cp314 wheels and provides the same encoding capability with zero PyTorch dependency.
  - **Pipeline**: `onnxruntime` + `tokenizers` (both already in venv) → load `model_int8.onnx` (144MB INT8) → per-token 128-dim embeddings → MaxSim scoring in numpy.
  - **Model decision**: GTE-ModernColBERT-v1 (BEIR 54.67) vs ColBERT-Zero (BEIR 55.43) — <1pp difference. GTE already on disk, verified working. ColBERT-Zero download deferred unless accuracy issues emerge in S6.
  - Model path: `/mnt/raid0/llm/models/gte-moderncolbert-v1-onnx/model_int8.onnx`
  - Dependencies added: `onnxruntime==1.24.4` (+ flatbuffers, protobuf, sympy, mpmath)

- [x] **S4: Benchmark latency on EPYC** ✅ 2026-04-14 — Benchmark complete. Results:
  - **Encoding 1 query (48 tok) + 10 snippets (64 tok max)**: median 180ms, min 180ms, max 198ms
  - **MaxSim scoring**: <1ms for 10 documents
  - **Total**: ~180ms per reranking call
  - **Note**: 180ms is well above the original <10ms target, but that target assumed pre-encoded embeddings. The 180ms includes full ONNX encoding through 150M params. Acceptable because each irrelevant page saved = 45s of synthesis. ROI: ~750x.
  - **Ranking quality**: Perfect separation on test data — all 5 relevant snippets ranked top 5, all 5 irrelevant ranked bottom 5. Score spread: relevant 0.93-0.96, irrelevant 0.91-0.92.

- **[declined: ws58 2026-11-03 content-review: on HOLD since 2026-06-12 pending an analyzer run nothing schedules]** **S5: Implement reranker** — HOLD as of 2026-06-12 gate analysis. Add reranking to `research.py`, gated behind `web_research_rerank` flag, only if a fresh analyzer run has >=50 synthesized pages and >20% irrelevant-page rate. When flag is ON: increase `max_results` from 5 to 8-10, encode search snippets (from SearXNG JSON API when deployed per [`searxng-search-backend.md`](knowledge-pipelines.md#track-searxng-search-backend), else DDG HTML) via GTE-ModernColBERT ONNX, rerank by MaxSim, take top 3 for fetch. When using SearXNG, `engines[]`/`score` metadata available for multi-engine confidence weighting. Lazy model loading on first call.
  - File: `epyc-orchestrator/src/tools/web/research.py` (modify `_web_research_impl`)
  - Encoding module: new `src/tools/web/colbert_reranker.py` (ONNX session, tokenizer, MaxSim)
  - Effort: ~2h, depends on S3/S4 (done) and AR-3 go/no-go
  - **Integration note**: ONNX session should be loaded lazily (first call) and cached as module-level singleton. Session is thread-safe for inference.

- **[declined: ws58 2026-11-03 content-review: depends on S5, retired]** **S6: A/B test** — Compare reranked (10 results → top 3 by ColBERT) vs current (5 results → top 3 by DDG order) on web_research benchmark questions. Metrics: synthesis quality, irrelevant page rate, total latency.
  - Effort: ~2h inference time, depends on S5

#### Research Intake Update — 2026-04-18

##### Surprisal-Based Chunking for Retrieval Pipeline (intake-408/409 deep-dive)

Deep-dive analysis of EM-LLM (arXiv 2407.09450, ICLR 2025) and the Tulving Episodic Memory Benchmark (arXiv 2501.13121) revealed two findings relevant to this pipeline:

**1. RAG chunk granularity is critical for episodic tasks.** The Tulving benchmark tested RAG at paragraph-level vs chapter-level chunking. Paragraph-level RAG *degrades* single-event recall from 0.81 (in-context) to 0.60, because event information is distributed across paragraphs. Chapter-level RAG (event-boundary-aligned) recovers to 0.82, matching in-context. **Implication for web_research**: when fetching pages for synthesis, paragraph-level extraction (current 6000-char chunks) may split relevant context. Event-boundary-aligned chunking would preserve coherent information units.

**2. Surprisal-based chunking (EM-LLM Option D — low effort, partial benefit).** EM-LLM's full architecture requires deep llama.cpp modifications (not viable). But its core segmentation insight is extractable: use per-token log-probability surprisal from llama.cpp `/completion` (logprobs already available) to detect event boundaries. Boundary = where surprisal exceeds µ + γσ (rolling window statistics). Feed these semantically-coherent chunks into ColBERT reranker instead of fixed-size splits.

**Proposed S7 (future, post-S6 validation):**
- **[declined: ws58 2026-11-03 content-review: curiosity with no measured retrieval gap it would close]** **S7: Surprisal-based page chunking** — After fetching pages, run through llama.cpp `/tokenize` + `/completion` with `n_probs`, compute per-token surprisal, split at surprise spikes. Feed chunks to ColBERT MaxSim instead of raw paragraphs. Tests whether event-boundary chunking improves synthesis quality on real web pages (where structure is less clean than synthetic narratives). Depends on S5/S6 confirming ColBERT reranking adds value.

#### Key Files

| Resource | Path | Role |
|----------|------|------|
| web_research tool | `epyc-orchestrator/src/tools/web/research.py` (468 lines) | Primary implementation target |
| web_search (DDG/Brave) | `epyc-orchestrator/src/tools/web/search.py` (223 lines) | Returns snippets used for reranking |
| fetch + extract | `epyc-orchestrator/src/tools/web/fetch.py` | Page fetching (unchanged) |
| feature flags | `epyc-orchestrator/src/features.py` | Register `web_research_rerank` flag |
| tool manifest | `epyc-orchestrator/src/tools/web/manifest.json` | Tool registration (unchanged) |
| Explore worker config | `epyc-orchestrator/orchestration/model_registry.yaml` | Worker model reference |
| Web research baseline | `epyc-inference-research/scripts/benchmark/analyze_web_research_baseline.py` | A/B test analysis |
| Combined ops | `epyc-orchestrator/src/repl_environment/combined_ops.py` | Uses `web_search` not `web_research` — future extension only |

#### Literature Survey (2026-04-14)

##### 1. Reason-ModernColBERT Status

150M params, 128-dim multi-vector, cc-by-nc-4.0 license (non-commercial; reproducible under Apache via independent ReasonIR data gen, ~2hr fine-tune). BRIGHT full-mean 22.62 NDCG@10 without reasoning traces, 30.28 with GPT-4 traces -- outperforms all models up to 7B (45x its size). Claims top spot on BrowseComp-Plus (agentic search benchmark) with 54x fewer params. No CPU latency numbers published. **Verdict: ELIMINATED** — license prohibits commercial use. ColBERT-Zero achieves stronger general retrieval without license constraints.

- [HuggingFace model card](https://huggingface.co/lightonai/Reason-ModernColBERT)
- [LightOn blog](https://lighton.ai/lighton-blogs/lighton-deep-tech-simple-delivery)

##### 2. Competing Late-Interaction Models

| Model | Params | Key Result | Verdict |
|-------|--------|-----------|---------|
| **ColBERT-Zero** (LightOn, Feb 2026) | <150M | 55.43 NDCG@10 on BEIR, outperforms GTE-ModernColBERT. Fully pre-trained on public data only. | **PRIMARY — strongest general-purpose ColBERT, open data** |
| **GTE-ModernColBERT-v1** (LightOn) | ~150M | 54.67 BEIR avg, 88.39 LongEmbed. Base for Reason variant. | Already deployed on :8089 — validates CPU feasibility |
| **mxbai-edge-colbert** (Mixedbread, Oct 2025) | 17M/32M | **32M is the slot**: BEIR 0.521, NanoBEIR 0.6520, dim 64. The 17M's BEIR win over ColBERTv2 (110M) is 0.490 vs 0.488 — 0.2 pp, no significance testing. ~3.2× faster CPU encoding than ColBERTv2 in the vendor's own PyLate harness. | **FALLBACK (32M) — latency-critical CPU path, Apache 2.0** |
| **Jina-ColBERT-v2** (Jina AI) | ~110M | +6.5% over ColBERTv2, 89-language multilingual, Matryoshka dims (128/96/64). | Not needed — no multilingual requirement |
| **SauerkrautLM-Multi-Reason-ModernColBERT** (VAGO) | ~150M | Community multilingual fork of Reason-ModernColBERT. | monitor_only |

Key paper: Chaffin et al., "ColBERT-Zero: To Pre-train Or Not To Pre-train ColBERT models," arXiv:2602.16609, Feb 2026.

- [ColBERT-Zero on HuggingFace](https://huggingface.co/lightonai/ColBERT-Zero)
- [mxbai-edge-colbert tech report](https://arxiv.org/html/2510.14880v1)
- [Jina-ColBERT-v2](https://huggingface.co/jinaai/jina-colbert-v2)

##### 3. CPU Inference Feasibility

No published PyLate CPU benchmarks for ColBERT-Zero specifically. Proxy data:

- **PLAID engine** (ColBERTv2): 45x speedup on CPU vs vanilla; tens-of-ms for 140M passage corpus.
- **mxbai-edge-colbert 17M**: **487 s** whole-pipeline NanoBEIR runtime on an **unnamed CPU** (vs ColBERTv2 **1540 s**) — mean of 10 runs over **~67,000 documents + 650 queries**, arXiv:2510.14880v1 Table 13. **CORRECTED 2026-08-23**: this line previously read "~49s per 50K docs … vs ColBERTv2 ~154s", which is Table 13's CPU column **divided by 10**, over a corpus misstated as 50K. The ~3.2× ratio survives; the absolute numbers did not. Two further limits on Table 13: the CPU is never named and no variance, min or max is reported for any of the ten runs; and the paper's stack is **PyLate/PyTorch — it never mentions ONNX** — so these figures are a within-stack ratio and are **not** transferable to our ONNX-Runtime INT8 serving path. Reranking 20 pre-encoded pages is still sub-ms MaxSim.
- **TurkColBERT study**: ColmmBERT-base achieved 0.54ms query latency under MUVERA indexing.
- **Key insight**: For reranking (not full retrieval), only MaxSim scoring over pre-computed embeddings is needed. 20 pages x 128-dim tokens = trivially fast on 192-thread EPYC. **Target <10ms is achievable with any model in this class.**

##### 4. Integration Patterns

- **RAGatouille** (AnswerDotAI): Wraps ColBERT for LangChain/LlamaIndex. Supports rerank-only mode (no index build needed). Latest: v0.0.9, May 2025.
- **PyLate** (LightOn): Native library for all ModernColBERT variants. Voyager HNSW indexing. More control but less framework integration.
- **LlamaIndex**: NodePostprocessor API accepts any reranker. Standard pattern: retrieve top-20/30, rerank, pass top-K to LLM.
- **Production consensus (2026)**: Hybrid retrieval (BM25 + dense) -> rerank top-20-30 -> LLM. Cross-encoders on full index cause p99 blowup; late-interaction on small candidate sets is the sweet spot.
- **No DuckDuckGo-specific patterns found** -- DDG returns pre-ranked HTML pages, not embeddings. Our pipeline would encode fetched page text at rerank time.

Rivera & Menolascina, "ModernBERT + ColBERT: Enhancing biomedical RAG," arXiv:2510.04757, Oct 2025 -- confirms ColBERT reranker improves Recall@3 by 4.2pp but requires joint fine-tuning of retriever+reranker.

##### 5. Alternatives to Late-Interaction Reranking

- **SPLADE** (learned sparse): Acts as "smarter BM25" with term expansion. Inverted-index compatible. Best as first-stage retriever, not reranker. Does not replace ColBERT for reranking.
- **Dense rerankers (cross-encoders)**: Higher quality ceiling but 2 orders of magnitude slower than ColBERT. Unusable at our latency target.
- **BrowseComp-Plus findings**: Dense reasoning-specialized retrievers (Qwen3-8B) dramatically outperform BM25 for agentic search. But 8B models compete for inference slots -- ColBERT at 150M does not.
- **Verdict**: Late-interaction is the correct architecture for our use case (CPU reranking of 10-20 web snippets, no GPU budget, no inference slot competition).

#### References

- intake-174: Reason-ModernColBERT analysis (eliminated — license)
- intake-175: PyLate library evaluation (MIT, selected)
- [BRIGHT benchmark](https://github.com/xlang-ai/BRIGHT) — reasoning-intensive retrieval benchmark
- [PyLate](https://github.com/lightonai/pylate) — late-interaction retrieval library
- [BrowseComp-Plus](https://github.com/texttron/BrowseComp-Plus) — agentic search benchmark (ACL 2026)
- [ColBERT-Zero paper](https://arxiv.org/abs/2602.16609) — Feb 2026, SOTA ColBERT pre-training
- [mxbai-edge-colbert report](https://arxiv.org/html/2510.14880v1) — Oct 2025, tiny ColBERT for edge/CPU
- [ModernBERT+ColBERT biomedical RAG](https://arxiv.org/abs/2510.04757) — Oct 2025
- [Jina-ColBERT-v2 paper](https://arxiv.org/abs/2408.16672) — multilingual late-interaction
- [RAGatouille](https://github.com/AnswerDotAI/RAGatouille) — ColBERT wrapper for LangChain/LlamaIndex

#### Research Intake Update — 2026-04-14

##### New Related Research
- **[intake-359] "SearXNG: Privacy-respecting metasearch engine"** (github:searxng/searxng)
  - Relevance: SearXNG could replace the DDG HTML scraping + Brave fallback in `search.py` with a self-hosted JSON API aggregating 250+ engines. Eliminates bot detection / rate limiting issues at the scraping layer. JSON response includes `engines[]`, `positions[]`, and `score` fields providing richer signal than bare HTML parsing.
  - Key technique: Self-hosted metasearch with JSON API (`GET /search?q=...&format=json`). Cross-engine result merging with score boosting. Per-engine timeout/weight/retry/proxy config.
  - Reported results: 28.3k GitHub stars, Docker ~183MB, ~70 public instances.
  - Delta from current approach: Replaces 112 lines of fragile regex HTML parsing with ~15-line JSON API call. SearXNG handles URL-level dedup across engines (same URL merged with provenance tracking); existing `_dedup_pages()` handles paragraph-level dedup post-fetch. Caveats: Google blocks SearXNG via TLS fingerprinting; limiter API_MAX=4/hr must be disabled; JSON format not enabled by default.
  - **Handoff created**: [`searxng-search-backend.md`](knowledge-pipelines.md#track-searxng-search-backend) — full deployment plan + implementation sketch.
- **[intake-360] "SearXNG Documentation"** (docs.searxng.org)
  - Relevance: API reference for SearXNG integration — documents endpoints, parameters, JSON response structure, engine configuration, and deployment.
  - Key detail: `engines=` API param allows per-request engine selection — could route different query types to different engine sets.
- **[intake-361] "mcp-searxng: MCP Server for SearXNG"** (github:ihor-sokoliuk/mcp-searxng)
  - Relevance: 635-star MCP bridge with `searxng_web_search` + `web_url_read` tools. Alternative integration path for Claude Code sessions (separate from orchestrator backend).

#### Research Intake Update — 2026-04-17

##### New Related Research
- **[intake-405] "Witchcraft: Rust XTR-Warp Semantic Search Engine"** (github:dropbox/witchcraft)
  - Relevance: Alternative retrieval architecture in the same multi-vector space. XTR (token retrieval) vs ColBERT (late interaction) represents a different accuracy/speed tradeoff. Witchcraft packages XTR-Warp as zero-dependency Rust binary with SQLite persistence.
  - Key technique: XTR contextualized token retrieval with GGUF-quantized T5 (candle), hybrid BM25+semantic search in SQLite FTS, single-file deployment.
  - Reported results: 21ms p95 (M2 Max), 33% NDCG@10 (NFCorpus), 2x faster than original XTR-WARP.
  - Delta from current approach: XTR trades accuracy for speed — 33% NDCG@10 vs ColBERT-Zero 55.43. Our ColBERT reranking decision is validated: ColBERT-family is substantially more accurate for the 10-snippet reranking use case. Witchcraft's embedded/serverless model is interesting for different use cases (session search, offline doc indexing) but not competitive for pipeline reranking.
- **[intake-406] "WARP: An Efficient Engine for Multi-Vector Retrieval"** (arxiv:2501.17788)
  - Relevance: SIGIR'25 paper showing 3x speedup over ColBERTv2/PLAID and 41x over XTR reference. Confirms multi-vector retrieval efficiency is an active research area. The WARP_SELECT (dynamic similarity imputation) and implicit decompression techniques are potentially applicable to future retrieval optimization.
  - Delta from current approach: WARP optimizes corpus-scale retrieval (millions of passages); our ColBERT use case is snippet-level reranking (10 items) where these optimizations have minimal impact.
- **[intake-407] "XTR: Rethinking the Role of Token Retrieval in Multi-Vector Retrieval"** (arxiv:2304.01982)
  - Relevance: Foundational XTR paper from Google DeepMind. Token retrieval (score from subset) vs late interaction (score from all tokens) is the architectural fork between XTR and ColBERT. XTR claims 100-1000x cheaper inference at modest accuracy cost — confirmed by Witchcraft's speed/accuracy profile.

#### Research Intake Update — 2026-04-22

##### New Related Research (LightOn DenseOn/LateOn release)

- **[intake-428] "DenseOn with the LateOn: Open State-of-the-Art Single and Multi-Vector Models"** (HF blog, LightOn, Apache 2.0)
  - Relevance: Direct successor to ColBERT-Zero from the same LightOn team. Both models Apache 2.0 (vs Reason-ModernColBERT's CC-BY-NC-4.0, which previously forced elimination). LateOn is multi-vector reranker; DenseOn is dense retriever.
  - Key technique: Two-stage contrastive training (665M curated pairs) + NV-Retriever hard negatives + decontaminated BEIR evaluation protocol.
  - Reported results: LateOn BEIR 57.22 / decontaminated 60.36; DenseOn BEIR 56.20 / decontaminated 57.71. Both at <150M parameters, outperforming 4x larger models.
  - Delta from current approach: GTE-ModernColBERT-v1 (54.67 BEIR, 180ms/10 snippets, currently deployed on :8089) is same architecture family. LateOn is +2.55pp BEIR drop-in candidate. DenseOn is secondary candidate for probe-first pool alternative to BGE-small.

- **[intake-430] "LateOn" model card** — ModernBERT (149M), 128-dim per-token multi-vector, MaxSim scoring via PyLate.
- **[intake-431] "DenseOn" model card** — ModernBERT (149M), CLS pooling + asymmetric query/document prompts.

##### Next Actions (scoped for this handoff)

- [x] Verify ONNX INT8 variant availability for LateOn on HF Hub ✅ 2026-07-14 — S3b confirmed: LightOn ships `model_int8.onnx` pre-quantized on `lightonai/LateOn`
- [x] Benchmark LateOn CPU latency vs GTE-ModernColBERT-v1 baseline (target: <200ms for 10 snippets) ✅ 2026-08-12 — LateOn 200.2 ms vs GTE 202.7 ms (S4b section below)
- [x] ~~If latency acceptable: A/B test LateOn vs current model on web_research sentinel queries (when AR-3 Package D data accumulates)~~ (closed 2026-10-29 audit: DUPLICATE → same A/B as colbert-reranker-web-research.md:426 (S5 amended: LateOn vs GTE on sentinel queries, gated on AR-3 Package D); keep :426)
- **[declined: ws58 2026-11-03 content-review: conditional on a bottleneck nobody has measured]** Secondary: evaluate DenseOn for probe-first pool if BGE-small retention becomes a bottleneck

#### S3b / S4b / S7 — LateOn Drop-in Upgrade (2026-04-22, DD1)

**Source**: `/workspace/research/deep-dives/lighton-denseon-lateon-retrieval-upgrade.md` (415 lines). LateOn (intake-430) is a same-architecture drop-in for currently-deployed GTE-ModernColBERT-v1 with **+2.55pp BEIR** (57.22 vs 54.67) and +1.83pp vs ColBERT-Zero. Same backbone (ModernBERT), same parameter class (149M), same 128-dim output, same Apache 2.0 license.

**Target**: NIB2-47 (ONNX export) + inference-gated follow-ups.

**Amended S5 plan**: LateOn becomes primary candidate for the reranker swap. GTE-ModernColBERT-v1 remains the fallback baseline. ColBERT-Zero (earlier primary candidate) is now secondary — LateOn wins by same-family comparison.

Tasks:

- [x] **S3b**: ONNX INT8 export of LateOn + parity test vs PyLate reference (NIB2-47, ~1h, non-inference). Unblocked today independent of AR-3. **DONE 2026-04-22 (code)**: LightOn ships `model_int8.onnx` pre-quantized on the `lightonai/LateOn` HF repo — no local Torch→ONNX export needed. Delivered `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/colbert/export_lateon_onnx_int8.py` (~180 LoC): downloads 17 files (model_int8.onnx + model.onnx + safetensors + tokenizer + 3 dense heads + configs) then runs 20-snippet parity vs PyLate reference with `PARITY_TOLERANCE=1e-2`. Extended `src/tools/web/colbert_reranker.py` with `LATEON_MODEL_PATH` env var override (single-env-var activation). Added `[colbert-export]` optional extras to `pyproject.toml`. 13/13 colbert_reranker tests pass (+2 new). Execution run deferred: `pip install -e '.[colbert-export]'` + `python -m scripts.benchmark.colbert.export_lateon_onnx_int8` when a python env with onnxruntime + torch + transformers + pylate is available.
- [x] **S4b**: Re-run CPU latency benchmark with LateOn INT8 (DD1-A2, ~30min + 2h inference). Target: latency ≤ 200ms for 10 snippets (GTE baseline 180ms). **Harness unblocked 2026-06-14**: `epyc-orchestrator` `b37de4a` added `scripts/benchmark/bench_colbert_rerank.py`, so this is now a model/runtime measurement task rather than harness work. ✅ 2026-08-12 — artifact downloaded and measured; see "S4b measurement (2026-08-12)" below. **LateOn 200.2 ms median / 10 snippets, target MET**, and latency-neutral vs the same-harness GTE baseline (202.7 ms, −1.2%) as the same-backbone/same-parameter-class prediction required.
- [x] **S7**: Adopt LightOn's decontamination protocol (xxhash64 + 13-gram containment, threshold 0.5) as EPYC-internal retrieval-eval standard. ✅ 2026-07-29 — `epyc-orchestrator` `bdfb6c63` adds `scripts/benchmark/decontaminate_against_embeddings_training.py`: normalized exact xxHash64 first, then word-level 13-gram containment at ≥0.5, with per-row provenance and retained-row output. Focused synthetic coverage validates official hash vectors plus exact/near-duplicate rejection. Decontaminate AR-3 Package D sentinel suite before running E3. Guards against "new model wins because it saw the test" failure mode.
- **[declined: operator 2026-11-07 — superseded: S5 request-path reranking is a NO-GO since 2026-06-14 (<10 % irrelevant pages over >=50 synthesized pages) so there is no S5 to A/B; AR-3 Package D was archived 2026-05-27; the three-slot selector (S5-amend, `107a8db`) stays landed. Reopen only if live role traffic shows >20 % irrelevant-page waste]** **S5** (amended): A/B test LateOn vs GTE-ModernColBERT-v1 on decontaminated web_research sentinel queries. Gated on AR-3 Package D completion.

##### S4b measurement (2026-08-12) — LateOn staged + the ONNX thread bound

**Artifact staged**: `lightonai/LateOn` downloaded to `/mnt/raid0/llm/models/lateon-onnx-int8`
(1.39 GB, all 17 planned files) via the sanctioned
`epyc-orchestrator/scripts/benchmark/colbert/export_lateon_onnx_int8.py --profile lateon --no-parity`.
ONNX I/O signature matches the deployed GTE graph exactly — inputs `input_ids`/`attention_mask`,
output `(batch, sequence, 128)` — so LateOn is a literal drop-in for the existing three-slot
selector, no reranker code change needed to swap it in.

**Protocol**: `scripts/benchmark/bench_colbert_rerank.py`, 10 snippets/call, 25 measured calls,
3 warmup, 3 interleaved rounds per cell, all three slots and both thread settings measured in one
session so the comparison is internally valid. Host control: `scaling_governor=performance`,
observed max core frequency 4.53 GHz — not throttled. Bench artifact:
`epyc-orchestrator/benchmarks/results/runs/colbert_rerank_threads/20260812T162052Z/summary.json`.

| Slot | median, 8 intra-op threads | median, 192 (pre-fix default) | speedup |
|---|---:|---:|---:|
| LateOn INT8 | **200.2 ms** | 354.7 ms | 1.77× |
| GTE-ModernColBERT-v1 INT8 (baseline) | 202.7 ms | 367.8 ms | 1.82× |
| Reason-mxbai-32M INT8 | **49.1 ms** | 115.4 ms | 2.35× |

**S4b verdict: PASS.** LateOn meets the ≤200 ms target and is latency-neutral vs GTE (−1.2%),
which is what the same-ModernBERT-backbone / same-149M-parameter-class prediction demanded. LateOn's
+2.55pp BEIR therefore comes at no measured CPU cost, so the model-slot question is decided on
quality alone whenever the A/B unblocks.

**Root cause found while benchmarking — ORT thread oversubscription.** One rerank call is `1 + N`
*sequential single-row* forward passes over ≤64 padded tokens. ONNX Runtime's default intra-op pool
is one thread per visible core, i.e. 192 here, so nearly all of that pool is coordination overhead:
bounding it to 8 is **1.8–2.3× faster on every slot** and it also stops each rerank call spinning up
a 192-thread pool that contends with co-resident CPU benchmarks on this shared host. Landed in
`src/tools/web/colbert_reranker.py` as an explicit `SessionOptions`
(`intra_op_num_threads=8`, `inter_op_num_threads=1`), env-overridable via
`COLBERT_RERANK_ONNX_THREADS`, with a mutation-tested regression guard in
`tests/unit/test_colbert_reranker.py::TestOnnxThreadBound`. Rerank output is **bit-identical** at 8
vs 192 threads (order match, max score delta 0.0) — this is a pure latency/footprint change, not a
quality tradeoff.

**Correction to two numbers this handoff has been carrying:**

1. **"GTE baseline 180 ms" (S4, 2026-04-14) is not comparable to any harness figure** and must not
   be used as a target or a regression reference. It predates
   `bench_colbert_rerank.py` (`b37de4a`, 2026-06-14) and was produced by an ad-hoc script. Under the
   canonical harness GTE is 202.7 ms bounded / 367.8 ms unbounded. The control that rules out
   machine drift as the explanation: Reason-mxbai reproduces its own 2026-06-14 harness number
   (104.4 → 115.4 ms unbounded, same configuration) on the same runs where GTE reads 368 ms.
2. **S4c's "misses the ≤80 ms target" is superseded.** The recorded 104.4 ms was an unbounded-pool
   measurement. With the thread bound Reason-mxbai-32M measures **49.1 ms**, comfortably inside the
   ≤80 ms gate, so the CPU-latency-budget slot now passes its gate and the "promising-but-not-yet-
   accepted" caveat on it is retired as far as latency is concerned. Its open gates are now parity
   (already passed, 2.72e-03 max cosine divergence) and the inference-gated A/B — nothing else.

- [x] **S4d**: Carry the same ONNX intra-op bound to the two *live* retrieval encoders —
  `src/retrieval/colbert_encoder.py` (KB-RAG first-stage MaxSim) and `src/retrieval/cross_encoder.py`
  (K9 rerank). ✅ 2026-08-12 — orchestrator `faee5e75`. **The two bounds deliberately DIFFER and must not
  be unified**: the optimum is call-shape dependent. `colbert_encoder.encode()` is one single-row pass
  (best 4, 8 within 3%); `cross_encoder.score_pairs()` feeds N rows in one `run()` and measures best at
  **16**, where copying the sibling's 8 costs ~40% at batch=50. Output is bit-identical bounded vs
  unbounded. A test guards against a future "harmonisation" of the constants.

- [x] **S3b-parity**: LateOn ONNX↔PyLate numerical parity, previously skipped with `--no-parity`
  ✅ 2026-08-12. **PASS** — max per-token cosine divergence **8.24e-03** against the `PARITY_TOLERANCE
  = 1e-2` the sibling Reason-mxbai export was judged at. The decisive step was decomposing FP32 from
  INT8: the **FP32 export matches the reference at 2.38e-07** (float32 epsilon), which proves the graph
  computes what the reference computes and attributes 100% of the INT8 residual to quantization noise
  rather than a wrong graph. Verified against genuine `pylate.models.ColBERT`, not a reimplementation.
  Negative control: the deployed GTE graph on identical ids diverges by 1.19–1.25, ~1000× the observed
  figure, so a graph agreeing to 1e-3 cannot be GTE. One caveat recorded: under *pylate-native*
  tokenization the per-token tail reaches 1.98e-02 on a single outlier token; production does not use
  that regime and FP32 parity attributes it to quantization.

- [x] **PREFIX-1 — the encoder never applies the trained `[Q]`/`[D]` prefix tokens, and this is
  larger than everything else on this page.** `colbert_encoder.encode(text, max_tokens)` has **no
  query/document parameter at all**, so it cannot express the distinction even in principle; it feeds
  raw tokenized text straight to the graph. Both LateOn and the deployed GTE declare
  `query_prefix "[Q] "` / `document_prefix "[D] "` with dedicated **trained** token ids (50368/50369)
  that pylate inserts at index 1. Measured on the reference model, no ONNX involved:

  | perturbation | max abs ΔMaxSim | top-1 agreement |
  |---|---|---|
  | INT8 quantization | 6.60e-03 | 100% |
  | **missing `[Q]`/`[D]` prefix** | **1.63e-01** | **62.5%** |

  Dropping the prefix is **25× more perturbing than quantization** and changes top-1 on **37.5%** of
  queries. **Do NOT fix one side only.** Indexing (`kb_rag.py:311`, `:434`) and query (`kb_rag.py:567`)
  both go through the same prefix-less path, so they are mutually *consistent* — just off-distribution
  from training. Adding `[Q]` to queries alone would mismatch the stored index and make retrieval
  strictly worse. Correct adoption requires **re-embedding the entire KB corpus**, which is why this is
  an operator decision (OP-24) and not a code fix.

  **WEB HALF CLOSED 2026-09-14** — `epyc-orchestrator` `f876d989`. The KB side gained the role
  plumbing in `fe55b228`/`4e5e84c0` but `src/tools/web/colbert_reranker.py` kept its own prefix-less
  `_encode` (`:153-196`), so no KB-side fix ever reached the web path: no `[Q]`/`[D]`, a two-input
  feed that returned `None` on any graph declaring `token_type_ids`, no `do_lower_case`, and
  `_MAX_QUERY_TOKENS = 48` against LateOn's declared `query_length: 32`. It now routes through
  `colbert_encoder.encode(role=...)` with model-declared caps (`max_query_tokens()` /
  `max_document_tokens()`); **no re-embed was required — there is no stored web index**, so both sides
  move together. Tests 51 → 74 passed, encoder mocked, four guards mutation-tested
  (`TestRoleContract`, `TestTokenCaps`, `TestNoDuplicatedEncoder`). **Still open**: the KB corpus
  re-embed (OP-24) — this changes nothing about that decision.
  ✅ 2026-09-16 — verified landed on both sides (sub-tooling, read-only checks, zero inference):
  - **KB side:** `fe55b228` ("kb-rag OP-24: require explicit ColBERT role…"). `encode()` now takes a
    required keyword-only `role=`, and `index_meta.prefix_convention` decides both sides.
  - **Web side:** `f876d989` ("web reranker PREFIX-1…"). `colbert_reranker.py:198,213` encodes the query
    with `role=query_role` and the documents with `role=doc_role`, through the shared encoder.
  - **Both are merged:** `git merge-base --is-ancestor` confirms each commit is on epyc-orchestrator `main`.
  - **Re-embedding done:** the live store `data/kb_rag/index-qd-v1/catalog.sqlite` (the `DEFAULT_INDEX_DIR`)
    was opened read-only.
    - `index_meta` shows `prefix_convention=qd-v1`, `query_prefix='[Q] '`, `document_prefix='[D] '`,
      the `gte-moderncolbert-v1-onnx` / `model_int8.onnx` encoder, and `stamped_at=2026-08-12T21:32:15Z`.
    - The store holds 29,611 chunks, and the prefix-free `index/` store is kept as the rollback.
    - **2026-11-09 correction:** this stamp is now the problem, not the proof. Orchestrator `7d92b1a8` (2026-10-31) moved the contract to `qd-v2` and the code rejects a `qd-v1` store; see `PIP04-KB-INDEX-BREAK` at the top. The live index is broken until the separately dispatched rebuild lands.
  - PREFIX-2, whether published BEIR deltas transfer, stays open. It is a separate question.

- [x] **PREFIX-4 — fix the encoder-contract mismatch PREFIX-3 found, then rerun the same 44-row parity (filed 2026-10-31, ws58 wrap-up derived actionable).** `colbert_encoder.encode(role=ROLE_DOCUMENT)` disagrees with native PyLate 1.4 `ColBERT.encode` before any numerics: Reason 22/22 `OUTPUT_CONTRACT_MISMATCH`, LateOn 22/22 `TOKEN_OR_POSITION_MISMATCH` (e.g. 18x128 vs 17x128 at cap 64; input IDs, masks, retained positions differ). Find the divergence (prefix/marker tokens, special-token handling, skiplist/punctuation masking, length cap), fix it in the orchestrator encoder, and rerun the unchanged 20-snippet harness until cosine is computable. Zero-to-light CPU, no model change. ✅ 2026-10-31 — APP `7d92b1a8c198c2b3cd86e0920bc7f1c54364454f`; `tests/unit/test_colbert_native_contract.py` and 76 tracked tests pass. Same native 44 rows now all cosine-computable; Reason 19 PASS / 3 NUMERIC_FAIL and LateOn 22 PASS at unchanged 1e-2. This closes contract repair/computability only, with no Reason parity, adoption, deployment or index rebuild. [Validation artifact](../../artifacts/compute/colbert-prefix4-20261031/SUMMARY.json). [belief: cc]
- **2026-11-01 tick correction (PREFIX-3): reopened; original task text and 2026-10-30 evidence preserved.** The 44-row rerun ended with Reason 22/22 `OUTPUT_CONTRACT_MISMATCH` and LateOn 22/22 `TOKEN_OR_POSITION_MISMATCH`; cosine was not computed. This is unknown/nonterminal completion and does not satisfy the parity task. No parity, model-comparison, or adoption claim is supported; PREFIX-3 remains open. [Audit](../../docs/reports/tick-science-audit-20261031.md).

- **[declined: ws58 2026-11-03 content-review: merged into the LateOn A/B (the transfer check is that A/B)]** **PREFIX-2 — confirm whether the published BEIR deltas transfer before banking any model swap.**
  The BEIR figures on this page (GTE 54.67, ColBERT-Zero 55.43, and the LateOn delta) are **published
  vendor scores**, measured with the models used as designed, i.e. **with** the prefixes. Production runs
  them without. So a swap chosen on those deltas would be chasing a gain measured under conditions our
  deployment does not reproduce. This does not necessarily bias the *relative* A/B — the defect hits both
  arms — but it does mean the absolute gain is unproven here. Resolve PREFIX-1 before treating any BEIR
  delta as a production forecast.

- [x] **PREFIX-3 — re-run the banked ONNX↔PyLate parity through `colbert_encoder.encode(role=ROLE_DOCUMENT)` [belief: cc] — negative/unknown completion: 44 rows; cosine unknown; no parity/adoption claim.
  before S3b's 8.24e-03 or S3c's 2.72e-03 is cited again** ✅ 2026-11-07 — completed by PREFIX-4 (ticked above; APP `7d92b1a8`, `artifacts/compute/colbert-prefix4-20261031/REPORT.md`): the same 44 rows are now cosine-computable through `colbert_encoder.encode(role=ROLE_DOCUMENT)` against untouched native PyLate 1.4 — LateOn 22 PASS (max per-token divergence 0.001205), Reason 19 PASS / 3 NUMERIC_FAIL (max 0.012337 against the unchanged 1e-2 threshold). The old 8.24e-03/2.72e-03 figures stay unusable. Parity only: no retrieval-quality, adoption or Reason-parity claim. [belief: cc] Original 2026-10-30 outcome: ✅ 2026-10-30 — unchanged APP `de6c56e3` rerun: Reason 22 `OUTPUT_CONTRACT_MISMATCH`, LateOn 22 `TOKEN_OR_POSITION_MISMATCH`; cosine was not computed. Because `_encode_onnx` fed raw text (no `[D]`,
  hardcoded two-input feed, no `do_lower_case`) while `_encode_pylate` inserted `[D]`, so both figures are
  prefix-free-vs-prefixed rather than like-for-like and mean pooling (`_pooled_vec:462`) plus reference
  truncation (`:519`) were forgiving enough to pass it; needs the ONNX encoder, so not zero-inference
  (`scripts/benchmark/colbert/export_lateon_onnx_int8.py:465-494`) (found 2026-09-14, noninf sweep).
- [x] **S9 — give the `colbert_encoder` module singleton a locking contract** ✅ 2026-10-06 — MAIN accepted source `7825ab09`, promoted APP main `fd0a8dbc`, original off-host CI37439049934 TRUE68/68 (14 new locking cases plus 54 unchanged cap/tokenizer cases); [custody and review](../../artifacts/ni07/run-37439049934/README.md). Reentrant per-process transactions span state load/refresh, KB validation/encode/writers, reranker query/documents, telemetry and worker output publication; fake interleavings prove competing acquisition blocks, and no lock crosses Pool construction. Loader publishes a complete generation or clears failed state. No cross-process/catalog concurrency, activation, live performance or deployment claim. Original requirement: before the reranker is ever
  enabled concurrently with KB-RAG, since `_MODEL_DIR` is import-time state that `kb_rag` stamps into
  `index_meta` and a KB query in flight during a `refresh_model_dir()` re-point would see `_session is None`
  and return an ordinary miss (`src/retrieval/colbert_encoder.py`) (found 2026-09-14, noninf sweep).

*Declined 2026-09-14: the hardcoded `_QUERY_MAX_TOKENS = 48` / `_DOC_MAX_TOKENS = 256` in `src/retrieval/kb_rag.py:66-67`
(48 is GTE's number while LateOn declares 32) — not filed because both are stamped into `index_meta` (`:236-237`),
so changing them alters retrieval against every stored index and the change belongs to the open **PREFIX-1** box's
OP-24 re-embed decision, where the stamp makes it detectable.*

*Declined 2026-09-14: `src/retrieval/cross_encoder.py:188-189` handles `token_type_ids` correctly and is a
cross-encoder, so `[Q]`/`[D]` roles do not apply — not filed because it is a recorded no-defect observation with no
action, kept here only so it is not re-investigated.*

##### Expand — Local fine-tune (newly unblocked)

LightOn released the full 665M curated pre-training corpus + 1.69M fine-tuning corpus under Apache 2.0. Previously blocked by Reason-ModernColBERT's CC-BY-NC-4.0 license; this release makes an EPYC-domain-specialized reranker a ~1-day experiment once primary adoption is stable.

- **[declined: operator 2026-11-03 model-audit: DGX Spark GPU premise absent on this host; parked since 2026-04]** **S8** (park until primary S5 stable + GPU available): local NV-Retriever fine-tune on REPL+sentinel queries. GPU-gated to DGX Spark. Worth revisiting as a Phase 2+ enhancement.

#### S3c / S4c / S5-amend — Reason-mxbai-colbert-v0-32m Edge-Reasoning Fallback (2026-04-24, intake-453)

Source: [`research/deep-dives/reason-mxbai-colbert-32m-edge-retriever.md`](../../research/deep-dives/reason-mxbai-colbert-32m-edge-retriever.md). 32M ColBERT fine-tuned on BGE-reasoner + ReasonIR-HQ hard negatives. On BRIGHT natural-language splits (biology, earth_science, sustainable_living, pony) it matches or beats the 150M Reason-ModernColBERT sibling — those are exactly our web_research workload pattern. The −3.6 BRIGHT full-mean gap is entirely from symbol-dense splits (leetcode, aops, theoremqa) that are not our queries.

**Amended S5 plan (now 3-slot)**: GTE-ModernColBERT-v1 baseline / **LateOn primary** (general BEIR strength) / **Reason-mxbai-32m fallback** (CPU-latency-budget slot). Three-way `MODEL_PATH` env-var selector. Conditional adoption on three gates: (1) ONNX INT8 parity (<1e-2 L2 vs PyLate), (2) EPYC median latency ≤80 ms @ 48 threads for 10 snippets, (3) A/B within 1pp of LateOn on natural-language web_research queries.

CPU latency estimate ~40–50 ms p50 per 10-snippet call (optimistic 20 ms, pessimistic 60–80 ms). Derived by scaling the measured 180 ms GTE-150M-INT8 number by the backbone ratio (10 × 384²) / (22 × 768²) ≈ 0.113 and discounting the FLOP ratio to 25% realization under the BW-bound heuristic from `feedback_cpu_decode_bw_bound`.

Tasks:

- [x] **S3c**: ONNX INT8 export of `Reason-mxbai-colbert-v0-32m` + parity test vs PyLate reference (~1 h, non-inference). Unblocked independent of AR-3. **Artifact-profile step LANDED 2026-06-14** in `epyc-orchestrator` `ea29d79`: `export_lateon_onnx_int8.py` now has `lateon` and `reason-mxbai` profiles, verifies from HF metadata that Reason-mxbai is source-only (no `model_int8.onnx` shipped), can print/download the Reason-mxbai source artifact set, and fails fast with an actionable `model_int8.onnx` requirement before parity/latency. **Source artifacts staged 2026-06-14**: `/mnt/raid0/llm/models/reason-mxbai-colbert-v0-32m-onnx-int8` now contains the expected 67 MB safetensors/tokenizer/config/dense-head file set. **Export scaffold LANDED 2026-06-14** in `epyc-orchestrator` `8711c60`: the helper now has a concrete `--export-int8` path, stable PyLate feature-dict wrapper, ONNX contract (`input_ids`/`attention_mask` → `token_embeddings`, opset 18, dynamic batch/sequence axes), dynamic INT8 quantization helper, and dependency preflight. **Artifact generated 2026-06-14**: after adding `onnx`, `onnxruntime`, and `onnxscript` to the isolated reranker/export environments, `model.onnx` + `model.onnx.data` + `model_int8.onnx` were produced under `/mnt/raid0/llm/models/reason-mxbai-colbert-v0-32m-onnx-int8`. ONNX checker accepts both graphs with inputs `input_ids`/`attention_mask` and output `token_embeddings`; parity vs PyLate passed with max cosine divergence `2.7212e-03` and mean `1.2388e-03` at tolerance `1e-2`. Follow-up `epyc-orchestrator` `7c1e41e` adds `onnxscript` to the export preflight and makes reranker availability require actual model loadability instead of file presence only.
- [x] **S4c**: CPU latency benchmark with Reason-mxbai INT8 at 48 threads for 10 snippets (~30 min). Target median ≤80 ms. **Harness prereq DONE 2026-06-14**: `epyc-orchestrator` `b37de4a` added `scripts/benchmark/bench_colbert_rerank.py` with warmup-separated latency metrics, JSON output, explicit LateOn/Reason-mxbai model-slot overrides, and no-model skip behavior. **Measured 2026-06-14** on the real ONNX Runtime path after `7c1e41e` hardened availability checks: artifact `/mnt/raid0/llm/models/reason-mxbai-colbert-v0-32m-onnx-int8`, 50 measured calls, 5 warmup calls, 10 snippets/call, median `104.434 ms`, mean `104.301 ms`, p95 `105.237 ms`, first call `107.838 ms`, throughput `95.876 snippets/s`. Result: latency is faster than the older ~180 ms GTE baseline but misses the original ≤80 ms target; treat Reason-mxbai as promising-but-not-yet-accepted until request-path A/B and any optimization pass. **Superseded 2026-08-12** — that 104 ms was an unbounded-ONNX-thread-pool measurement; with the intra-op bound the same harness reads **49.1 ms**, inside the ≤80 ms gate. See "S4b measurement (2026-08-12)" below.
- [x] **S5-amend**: **LANDED 2026-06-14** in `epyc-orchestrator` `107a8db`. `src/tools/web/colbert_reranker.py` now has a three-slot selector documented in code comments: `LATEON_MODEL_PATH` primary, `REASON_MXBAI_MODEL_PATH` 32M fallback, and GTE-ModernColBERT-v1 default. Unit coverage verifies default, Reason-mxbai-only, and LateOn-over-Reason precedence. Full A/B remains inference-gated on AR-3 Package D, same gate as S5.
- [ ] **G14 (compute-gated) — re-export `Reason-mxbai-colbert-v0-32m` with `pylate-onnx-export` 1.7.0 so the slot finally has an `onnx_config.json`.** The staged artifact at `/mnt/raid0/llm/models/reason-mxbai-colbert-v0-32m-onnx-int8` ships `config_sentence_transformers.json` but **no `onnx_config.json`** — the file the NextPlaid Rust reader requires and the one `colbert_encoder._load_declared_config()` now prefers (`epyc-orchestrator` `4e5e84c0`). Install **from git**: `pip install "pylate-onnx-export @ git+https://github.com/lightonai/next-plaid.git#subdirectory=next-plaid-onnx/python"` — **not** the model card's `onnx/python` path, which 404s at head and at `00e26aae`, and **not** PyPI 0.1.0, which takes the projection from `pylate_model[1].linear` while reading the output dimension from `pylate_model[-1]`: on this **3-Dense** checkpoint (`1_Dense` 384→768, `2_Dense` 768→768, `3_Dense` 768→128) that emits a **truncated graph with a mislabelled `embedding_dim`**. Pin a PyLate ceiling as well — `query_prefix_id` gained a `None` return at 1.6.0 that `export.py:264-265`'s bare `int()` would crash on. **Compute is one CPU trace of a 32M model — seconds.** **Owning handoff**: this one (`colbert-reranker-web-research.md`). **What opens the gate**: the real blocker is an **environment prerequisite, not compute** — 1.7.0 declares `requires-python ">=3.10,<3.13"` and this host is Python 3.13.7, so a **Python 3.10–3.12 venv must exist first**. Once it does, the gate opens when the exported graph's declared `embedding_dim` matches the last Dense's `out_features` (**128** here) **and** parity holds against the existing **92 MB** (92,079,820 B) `model_int8.onnx`. The older cp314 / `fast-plaid` / `voyager` objection on file is **stale**: `voyager` is an optional extra gated `python_version < 3.14`, `fast-plaid` ships cp310–cp314 manylinux wheels, and `pylate/__init__.py` never imports `pylate/indexes/`, so neither is imported on this path. [2026-11-09 apr2 rtg08-evl47-pip04-code: install NOT done. Writing into `/mnt/raid0/llm/models/reason-mxbai-colbert-v0-32m-onnx-int8` is a model-dir write with the 2026-11-01 path-custody incident behind it, the box itself requires a separately reviewed step, and the parity check needs the onnx runtime; not plain file staging.]
  - **2026-11-09 status (verified):** the export is DONE. Row `pip04-g14-reason32m-reexport-r2-20261107` ended rc0 2026-11-07T20:52:41Z and was filed PASS 2026-11-08 (`filing-done/pip04-g14-reason32m-reexport-r2-20261107.verdict.json`): `onnx_config.json` written (sha `82e42d67`), `embedding_dim` 128, `uses_token_type_ids` false, INT8 candidate sha `3e5657a2`, baseline INT8 sha `6081f8b6` unchanged. The "compute-gated" and "needs a Python 3.10-3.12 venv" text above is stale. **What remains (doable now, no inference):** the separately reviewed install of the candidate into `/mnt/raid0/llm/models/reason-mxbai-colbert-v0-32m-onnx-int8` (that dir still has no `onnx_config.json`) plus a parity check; the box stays OPEN until then. Low consumer value: operator "Keep GTE" 2026-11-07 and the seed "keep `web_research_rerank` disabled" mean nothing consumes this slot soon. [no-belief: status note]
  - **G14 r2 published 2026-11-07 (operator: publish the runnable drafted rows):** row `pip04-g14-reason32m-reexport-r2-20261107` (CPU quarter, 300 s min window) — keeper smoke PASS (preflight + FP32 export unit written: `embedding_dim` 128, `uses_token_type_ids` false, 2-input graph). `run.py` carries the incident's required path safety (fresh create-once candidate inside the row's scratch root, never under `/mnt/raid0/llm/models`, distinct from every protected path/inode, baseline INT8 sha `6081f8b6…` pinned before/after). Stays OPEN until the row's TERMINAL verdict is PASS and the file is installed by a separate reviewed step. [no-belief: row publication]
  - **G14 failed run — 2026-11-01:** A path-custody error modified ten prior experimental candidate paths; the original candidate graph bytes were not recovered. All 32 canonical source-model files in the prior SHA-256 manifest matched, including the 92,079,820-byte INT8 baseline `6081f8b64cac5415300c034d8a5440631dbb293a43c113f9d5c9ba1552f07ece`. Original 110-row and new 15-row diagnostic evidence remain separate; the native process identities and final drain receipt were not captured, so cleanup cannot be proven retrospectively. MAIN read NI's reply that four known sibling backups had no exact match; it does not accept measurement validity. The run is FAILED-RUN with no scientific verdict, qualification or G14 credit. [Reviewed incident and evidence](../../artifacts/incidents/g14-export-codex3-20261101/INCIDENT.md), ROOT source `35cb389190cd87b01e4cb64a497a187a3a75bf1a`. [belief: cc]


**G14 preparation checkpoint — 2026-10-30 (task remains open):** READY packet
`codex-ni-g14-reason32m-r1-20261030` is published at rank 74, `any-cpu-quarter`,
8 GiB, with **300 s minimum / 600 s booked window**. The public manifest SHA-256
is `c8547a4e05987da8a01c47d72560274b4e313db0582ae27c94630342dc38876b`;
`SOURCE.sha256` is `857000058e6a990051db8f11774eac92333895a65321cfceb6d3afc732e72f39`
and all listed files verify. The preserved `PUBLISHED.json` keeper-scan stdout's
600 field is the booked window, not the minimum; the explicit manifest fields
above govern. Packet and receipts:
`/mnt/raid0/llm/tmp/codex-ni-g14-reason32m-20261030`.

Python 3.12, PyLate 1.4.0 and exporter 1.7.0 at
`00e26aae0006b322727db277672211d9a0e3ccec` now produce experimental FP32/INT8
ONNX and declared dimension 128, exercising all Dense projections
384→768→768→128. The original 92,079,820-byte graph is unchanged. Final native
smoke (`smoke-final/RESULT.json`) covers **one banked snippet, 15 rows and six
pairwise graph comparisons**, not the full 20-snippet/110-row run. Lower maxabs
and cosine divergence mean better fidelity. Candidate FP32 vs independently
aligned PyLate.forward has maxabs `1.7881393432617188e-7`; candidate INT8 max
cosine divergence is `0.0006961226463317871`. With matching real token IDs and
full masks, corrected-contract old INT8 vs PyLate.forward has max cosine
divergence `0.006514549255371094`, `0.00673598051071167`, `0.007153213024139404`
at caps 32/64/128. These are scoped smoke observations; masked-padding ID
0 versus 50284 is explicitly retained in the native record. Raw original
Reason preprocessing omits trained lowercasing: TOKEN_MISMATCH, **no cosine
computed**. Native full output is 18×128 while independent PyLate.encode
punctuation pruning returns 17×128. At this earlier smoke checkpoint, the full
PREFIX-3 rerun remained outstanding; its canonical unchanged-APP closeout is
recorded below. Historical pooled prefix-free numbers cannot establish parity.
No retrieval-quality or adoption evaluation ran.

Final same-entry resource receipt (`QUALIFIED-NATIVE-SMOKE.log`): child runtime
24.9707 s; supervisor runtime 26.8240 s; sampled peak process-tree RSS
1,982,087,168 bytes; child rc 0, children drained. Post-work cutoff qualification
retains four rows with child rc 75 after 8.9393 s supervisor time, children
drained. The then-planned 110-row candidate diagnostic was superseded for
PREFIX-3 by the 44-row unchanged-APP rerun below; retain candidate diagnostics
as separate evidence. Existing SC50 covers this source family; future projection
must carry baseline/candidate pins, native token/mask/shape refusals, cohort
coverage and run phase through its existing ClaimTuple ladder. No adapter/canary
completion or new measurement warrant is claimed. At this preparation checkpoint,
G14 and PREFIX-3 were still unchecked; no artificial preparation checkbox was
added. [no-belief: compute-preparation]

**PREFIX-3 canonical unchanged-APP rerun closeout — 2026-10-30:** the original
task is complete as a negative/unknown pipeline finding, not as a parity pass.
The exact APP source from `de6c56e34f5f23c2155d2b7dc839554ae692f771` (git blob
`2562a78b7a60fb832dd1a95ae6187651ab2259cd`, SHA-256
`23bee710f784bdcdbf7e67be82be3f186c82695bb185098313377b684bd39510`) was run
unchanged through `colbert_encoder.encode(role=ROLE_DOCUMENT)` against untouched
native PyLate 1.4 public `ColBERT.encode` for all 20 banked snippets: 44 rows in
27.348 s. Reason's 22 rows are `OUTPUT_CONTRACT_MISMATCH`; LateOn's 22 rows are
`TOKEN_OR_POSITION_MISMATCH`. For the first snippet at cap 64, both actual
matrices are 18×128 versus 17×128 native references. Full input IDs, masks and
retained positions do not match, so cosine was never computed (numeric comparisons
0); the acceptance threshold was not evaluated. Original model graphs, native
weights, relevant JSON and APP source passed before/after pin checks. The old
8.24e-3 and 2.72e-3 pooled/prefix-mismatched figures remain unusable for current
pipeline parity. This closes the rerun task only: no retrieval-quality, parity,
adoption, deployment, or stored-index compatibility result is claimed. The
separate private candidate's 66 rows are excluded from this canonical finding.
Evidence: `/mnt/raid0/llm/tmp/codex-ni-prefix3-native-20261030/baseline-current-app/REPORT.md`
and `results/RESULT.json`. Existing SC50 covers this source family; no new source,
adapter, ladder, or retrospective measurement warrant was created. Further
canonical encoder changes require caller and stored-index provenance review before
integration.

##### Independence note

S3c/S4c/S5-amend do not require AR-3. AR-3 only gates the **A/B rollout** (S5 / S6). Implementation, export, and latency probing can land on the next non-inference work session and slot directly into the existing 3-slot selector when AR-3 unblocks.

##### Cross-references

- `/workspace/research/deep-dives/lighton-denseon-lateon-retrieval-upgrade.md`
- Intake sources: 428 (blog), 430 (LateOn card), 431 (DenseOn card)
- `wiki/search-retrieval.md` (updated 2026-04-22 with LateOn/DenseOn rows + decontaminated-BEIR column)

#### Research Intake Update — 2026-04-24

##### New Related Research

- **[intake-453] "Reason-mxbai-colbert-v0-32m: Edge-Scale Reasoning ColBERT (32M params)"** (`huggingface.co/DataScience-UIBK/Reason-mxbai-colbert-v0-32m`)
  - Relevance: 32M-param ColBERT fine-tuned on BGE-reasoner + ReasonIR-HQ hard negatives, built on mxbai-edge-colbert-v0-32m (our explicitly named S5 CPU-latency fallback candidate). Edge-scale sibling of Reason-ModernColBERT (intake-174, 150M).
  - Reported results: BRIGHT nDCG@10 full-mean **19.00** (vs Reason-ModernColBERT 150M = 22.62, −3.6 pts); beats or matches 150M on natural-language splits (biology 32.71, earth_science 43.88, sustainable_living 20.77); lags on symbol-dense splits (leetcode, aops, theoremqa) due to case-insensitive tokenizer + sans_pos + 10-layer depth.
  - Key technique: widened projection head 64→128 dim preserving base weights on first 64 dims (matches GTE-ModernColBERT-v1 128-dim output currently deployed on :8089); two-stage curriculum (VL warmup → BGE-reasoner/ReasonIR-HQ hard negatives); CachedContrastive loss, 8×H100 training.
  - Delta from current approach: at ~5× smaller than Reason-ModernColBERT-150M, this is the direct CPU-latency fallback candidate the S5 plan already names. A targeted CPU-latency probe + BRIGHT-style A/B against LateOn and GTE-ModernColBERT-v1 is the cheapest next experiment. Current GTE-ONNX-INT8 is ~180 ms/call; 5× smaller backbone should drop to ~40 ms if PyLate→ONNX export path works.
  - Caveats (Tier 2b): (1) README has a **license conflict** (frontmatter Apache-2.0 vs body "CC-BY-NC-4.0 inherited from training data") — must be resolved before any commercial-adjacent deployment. (2) No ONNX INT8 variant shipped — PyLate→ONNX export is an unvalidated dependency. (3) Base mxbai-edge-colbert-v0 authors self-describe it as a "proof-of-concept baseline" (arxiv 2510.14880); architectural ceiling on symbol-dense retrieval inherited. (4) Model released 2026-04-22 — no independent third-party replication yet.
  - Action: queue S5 as A/B candidate after AR-3 web_research sentinel data lands. Treat BRIGHT 19.00 as ceiling — web_research queries are mostly natural-language, which is the model's strong suit, but verify before committing to ONNX export work.

#### Research Intake Update — 2026-04-28

##### New Related Research

- **[intake-494] "Contexts are Never Long Enough: Structured Reasoning for Scalable Question Answering over Long Document Sets"** (arxiv:2604.22294, Stanford OVAL/Genie) — **out of scope for this handoff**. SLIDERS targets 3.9M–36M-token *corpus-level* QA via DB+SQL extraction; this handoff scopes web-research reranking at single-query scale (~10–100 docs). Different scaling axis. See `internal-kb-rag.md` 2026-04-28 section for the SLIDERS context relevant to KB retrieval. Cross-reference left in for index completeness only.

#### Research Intake Update — 2026-04-30

##### New Related Research

- **[intake-519] "Granite-Embedding-97M-Multilingual-R2"** (HF `ibm-granite/granite-embedding-97m-multilingual-r2`, Apache 2.0, IBM, released 2026-04-29)
  - Relevance to web-research pipeline: **MEDIUM**. Candidate dense first-stage retriever feeding the ColBERT reranker. 97M params (sub-100M class), ModernBERT backbone, 32K context, 384-dim embeddings, claimed 2,894 docs/s on reference HW (≈3× gte-multilingual-base 305M at matched quality). MTEB Multilingual Retrieval (18 tasks) = 59.6 — claimed best open <100M-param multilingual score (vs multilingual-e5-small 50.9, +8.7 pts). Apache 2.0, ONNX/OpenVINO INT8 ship targets, GGUF convertible (no native release).
  - Why it matters here: SearXNG returns mixed-language snippets and our ColBERT pipeline currently has no production-grade dense first stage. Granite-97M-r2 is small enough (97M / ~370 MB FP32) to run on CPU with sub-millisecond per-doc latency — fits trivially on EPYC 9655 alongside the reranker.
  - Tier 2b: BGE-M3 (305M-class, ~63.0 MTEB) outscores Granite-97M-r2 in raw retrieval quality but is 3× larger; the trade is throughput-vs-quality. The 59.6 vs 50.9 vs e5-small claim is on the IBM card and not yet independently verified outside of the HF leaderboard. No GGUF native release — quantized CPU deployment requires our own ONNX→GGUF or direct OpenVINO INT8 path.
  - Action: small bench when S5 unblocks — measure Granite-97M-r2 vs multilingual-e5-base (current implicit baseline if any) on a representative slice from active SearXNG corpus, encode latency at 32K-context, decide whether to adopt as the dense retriever before ColBERT. Cross-ref `internal-kb-rag.md` 2026-04-30 update where the same model is evaluated for the KB-retrieval side.
  - Verdict: `worth_investigating`. Not new_opportunity — retrieval architecture decisions for this handoff still in flight pending S5 data.

###### Deep-dive refinement (2026-04-30) — bench plan persisted

Deep-dive at [`/workspace/research/deep-dives/granite-embedding-97m-r2-evaluation.md`](../../research/deep-dives/granite-embedding-97m-r2-evaluation.md). Bench handoff at [`granite-97m-r2-bench-plan.md`](../completed/granite-97m-r2-bench-plan-completed-through-2026-08-23.md) — gated on K2 chunker activation (currently STUB in `internal-kb-rag.md`).

**Two corrections to the intake-update notes above**:

1. **ModernBERT IS supported in llama.cpp** — `convert_hf_to_gguf.py:12452` registers `ModernBertModel(BertModel)` with `MODEL_ARCH.MODERN_BERT`. The "Ollama unsupported" note refers ONLY to Ollama's wrapper. GGUF + `llama-embedding` HTTP server on port `:8096` is the recommended deployment path (matches existing BGE-large `:8090–:8095` pattern).
2. **2,894 docs/s is GPU (H100), NOT CPU.** Reset CPU expectations before benching.

**Bench scope expanded** vs the original "1-day" framing: 2-3 inference-free engineering days (Phase A: GGUF conversion + comparator deployment + corpus build) + 1 inference day (Phase B: throughput + nDCG@10 + 32K context probe). Comparators: granite-97m-r2 Q8_0 + Q4_K_M, multilingual-e5-base, BGE-M3 (dense path only), BGE-large-en (reference). Eval corpus is the binding prerequisite — likely 100 code snippets + 30 NL queries with manual labels until a K2-produced KB slice exists.

For S5 specifically: the dense first-stage choice in front of ColBERT will come out of this bench; defer S5 architecture decisions until Phase B completes.

**Phase-C correction (2026-07-29):** Phase B is complete. Granite records
0.9222 NDCG@10 versus BGE-M3's 0.9150, at 1.614s versus 7.037s wall-clock
(4.36× lower), satisfying the bench's Granite promotion rule. If S5 activates
a multilingual dense candidate stage before ColBERT, use Granite as its default
encoder; this does not unblock S5's separate AR-3/decontamination requirements
or alter the current snippet-only pipeline.

#### Research Intake Update — 2026-06-10

##### New Related Research
- **[intake-689] "OBLIQ-Bench: Exposing Overlooked Bottlenecks in Modern Retrievers with Latent and Implicit Queries"** (arxiv:2605.06235, Tchuindjo/Shah/Khattab, MIT)
  - Relevance: directly informs the reranker bench design here. Core finding is a **retrieval-verification asymmetry** — reasoning LLMs reliably *verify* relevance once a doc is surfaced, but single-stage retrievers fail to *surface* most relevant docs, so BEIR/BRIGHT-style saturation hides a real gap. Notably **LateOn (LightOn) is one of its evaluated baselines** — the same retriever EPYC is assessing in the DenseOn/LateOn upgrade deep-dive.
  - Key technique: oblique-query taxonomy (descriptive / analogue / tip-of-the-tongue), a formal retrieval-verification gap metric gap(t)=V_t−R_t, and a tournament listwise-rerank verification ceiling.
  - Reported results: best single-stage retriever NDCG@10 far below the LLM-rerank oracle (e.g. 0.102→0.913 on Congress Hearings); iterative query rewriting *harms* when relevance is orthogonal to topic.
  - Delta from current approach: argues for **keeping/strengthening the LLM-rerank stage we already run** (the bottleneck is first-stage recall, not verification). The oblique-query dataset is a sharper eval than HotpotQA/LoCoMo for the KB-RAG flywheel — consider folding a slice into the Phase-B eval corpus. Caveat: oracle uses closed GPT-5.2, so absolute gap magnitudes are not reproducible on a CPU/open stack.

##### Deep-Dive Refinement (2026-06-12) — methodology-reuse, not dataset-reuse
OBLIQ-Bench IS released (HF `dianetc/OBLIQ-Bench`, CC-BY-4.0) but its corpora (tweets / WildChat / Congress / writing-style) are **out-of-domain** for our code/doc retrieval — **do NOT fold OBLIQ rows into the Phase-B eval corpus**. Reuse only the `gap(t)=V_t−R_t` metric + 5-stage oblique-query construction recipe to author an oblique **code/KB** slice on the Phase-B corpus. **LateOn's OBLIQ scores (NDCG@10 0.003–0.149) are floor-level/out-of-domain and must NOT be cited against LateOn adoption** — the S3b/S4b/S5 gates are unchanged (LateOn evidence stays BEIR 57.22 / decontaminated 60.36). Core thesis (bottleneck = first-stage **recall**, not verification) supports keeping/strengthening the LLM-rerank stage. Oracle is closed GPT-5.2; reproduce only a lower-bound `gap_open` via an open verifier route (architect_general/frontdoor, `enable_thinking=False`). Full: `research/deep-dives/2026-06-12-obliq-bench-retrieval-eval.md`.

#### MAIN-reviewed current-toolkit refinements — 2026-10-06

##### S04-F4 — Add the ColBERT singleton locking contract before concurrent slots are enabled

**Source verification (JEV audit, 2026-10-06):** `refresh_model_dir()` clears `_session`/`_tokenizer` and `ensure_loaded()` repopulates the globals without synchronization. Before any concurrent KB-RAG/reranker enablement, define a narrow lock contract covering refresh/load/encode and test deterministic fake-object interleavings. This is local state integrity only; no reranker activation or runtime performance claim.

**S04-F4 bounded implementation completed:** S9 above supplies the per-process synchronization contract; concurrent serving activation and its real performance remain separately gated.


- **2026-10-31 G14 scoped fidelity diagnostic:** `codex-ni-g14-reason32m-r1-20261030` reports 110 rows: five arms across 22 snippet/cap cases, including all 20 banked snippets and 128 dimensions. The 22 raw old-Reason rows report TOKEN_MISMATCH and no cosine because the original contract omits lowercasing; the corrected 92,079,820-byte old graph under explicit 1.7 configuration and new FP32/INT8 are compared per position. All 44 graph-pair comparisons are retained, including substantial divergences; this is not a parity or adoption verdict. Real-token IDs and masks gate strict forward comparisons; the masked padding difference 0 versus 50284 is retained. Independent PyLate.encode punctuation pruning produces a shape mismatch; PREFIX-3 remains unmet. Old pooled/truncated metrics do not apply. Evidence: `/mnt/raid0/llm/tmp/codex-ni-g14-reason32m-20261030/results/RESULT.json` SHA-256 `76ba7a99aba1bf422fbc2e97c55f66718b3728167bcf5e34edb84bf2dd031792`; `PAIRWISE.json` SHA-256 `447cd214e514fd5778699624bd30411a382d6644eabf613c249a9e2f12b7aead`. [belief: cc] [Bounded evidence](../../artifacts/compute/ni-filing-20261031-0230/MANIFEST.json).

## Track: document-parser-table-bench
<!-- gate: none -->

> Folded from `handoffs/active/document-parser-table-bench.md` @ `ccf37cd0b6a4` on 2026-11-02 (BRF-T1-F8, route 1a, operator D1/D5; retired row PIP-02 → PIP-04). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Document Parser Table-Extraction Benchmark — PaddleOCR-VL-1.6 pipeline vs ODL

**Scratch**: `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/pip02-current-provenance-source-20261007`, `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/pip02-selected-library-native-root-20261007`, `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/pip02-current-original-run-37602237437`, `/mnt/raid0/llm/tmp/codex3-pip-t1-r27-20261030`, `/mnt/raid0/llm/tmp/codex3-pip-head-r26-20261030`, `/mnt/raid0/llm/tmp/codex3-pip-relocatable-r25-20261030` · codex3 review: `/mnt/raid0/llm/tmp/codex3-pip-exposure-recheck-20261101`

**Status**: active
**Created**: 2026-07-20 (via research intake deep dive — intake-864/865 reassessment)
**Priority**: P1 — unblocks the long-open "stronger parser comparison" question in [`opendataloader-pipeline-integration.md`](knowledge-pipelines.md#track-opendataloader-pipeline-integration) (task K35.18)
**Categories**: document_processing, multimodal, benchmark_methodology
**Parent**: [`opendataloader-pipeline-integration.md`](knowledge-pipelines.md#track-opendataloader-pipeline-integration) · [`gemma-challenge-kernel-techniques-v7.md`](rocm-kernel-authoring.md#track-gemma-challenge-kernel-techniques-v7) K35.18

#### Objective

Establish, for the first time on a competent instrument, whether we have a table-extraction quality gap — and if so, close it by running **PaddleOCR-VL-1.6 in its real three-stage pipeline configuration** rather than the off-label single-shot invocation that produced meaningless results on 2026-07-17/18.

#### Why this exists — three broken instruments, one void result

The 2026-07-17/18 PaddleOCR-VL runs and the conclusions drawn from them are **retracted**. Root causes, all verified 2026-07-20:

1. **Off-label invocation (void result).** PaddleOCR-VL-1.6 is a *three-stage pipeline* (arxiv:2606.03264 §2): **PP-DocLayoutV3** layout analysis → the 0.9B VLM recognizing **cropped regions** under **element-specific prompts** → a post-processing assembler handling markdown, cross-page table merging and heading hierarchy. Its official card ships exactly six prompts (`"OCR:"`, `"Table Recognition:"`, `"Formula Recognition:"`, `"Chart Recognition:"`, `"Spotting:"`, `"Seal Recognition:"`) and **no page-level markdown prompt**; the VLM was trained on isolated element crops, never on full-page→markdown. We fed whole pages with a generic markdown prompt, so layout detection, table-crop dispatch and assembly never ran. `table TEDS = 0.0` with **zero** `<table>` tags *and* **zero** markdown pipe rows across all 9 table-bearing pages is the expected off-label behaviour, not a model defect. **Do not re-cite the 0.0 / 0.058333 TEDS figures.**
2. **Benchmark subset too small and unrepresentative.** Scoring used `OmniDocBench_demo.json` — **18 pages, 10 `table` regions, 64% simplified Chinese**. Under MEASUREMENT.md that is an observation, not a decision-gating number. ODL's oft-quoted `table.TEDS = 0.783813` rests on **n=10**.
3. **Production corpus cannot measure tables.** The 8-PDF `local-valid-pdf-8` set behind the "zero ODL tables despite 1195 table-like lines" finding is **half figure exports**: `Imgs/overview.pdf` (1p), `Imgs/Statistics.pdf` (1p), `Imgs/RQ5.pdf` (1p) and `llama-star/idea-arch.pdf` (2p) are charts/diagrams; only `HY_MT2_0_Report.pdf` (15p) and `echo.pdf` (13p) are substantial documents. Most contain no tables, so `structured_tables=0` is correct, not a failure. `table_like_line_count` is a whitespace/numeric heuristic, **not** a table count.

**Net: we have no evidence of a table-extraction gap — only evidence that we never measured one.**

#### What changed — the instrument is now fixed

Full OmniDocBench acquired and integrity-verified 2026-07-20 at `/mnt/raid0/llm/datasets/omnidocbench/` (1662 files, 1.55 GB, HF `main`, 1651-page release, annotations last corrected 2026-04-09; 1651 images, 1651 JSON pages, 0 missing image refs, 0 `.part`).

| | demo (all prior numbers) | full (now local) |
|---|---|---|
| Pages | 18 | **1651** |
| `table` regions | **10** | **665** (on 458 pages) |
| Language | 64% simplified Chinese | 755 EN / 765 ZH / 116 mixed / 13 trad |

The full set carries a per-page `language` attribute, so an **English-only view** matching our actual PDF workload is scoreable. n=665 makes table TEDS a defensible gating metric for the first time.

Fetch script: `/mnt/raid0/llm/tmp/fetch_omnidocbench.py` (idempotent, skip-if-complete by size, no `curl -C -` resume semantics).

#### Assets already on disk — no new downloads required

- `/mnt/raid0/llm/models/PaddleOCR-VL-1.6-GGUF/PaddleOCR-VL-1.6-GGUF.gguf` (936 MB) + `-mmproj.gguf` (882 MB), SHA-verified 2026-07-17, revision `511b09642bb324401f15f97cc23bc67e8f0a291d`.
- Dedicated venv `/mnt/raid0/llm/venvs/paddleocr` (Python 3.12) — deliberately isolated from `epyc-inference-research/.venv`, since `odl_bench` only needs to invoke PaddleOCR as a subprocess and PaddlePaddle is a heavy framework that should not enter the research env.
- Scorer + producer: `epyc-inference-research/scripts/benchmark/odl_bench/` (`paddleocr_vl.py`, `compare-existing`, `run-model`).

#### Architecture note — this is the *wanted* design, not a workaround

Operator direction 2026-07-20: **the Python orchestrator is desired for the document pipeline precisely because it avoids inference when unnecessary.** PaddleOCR-VL's three-stage shape is therefore a feature: PP-DocLayoutV3 decides *what* needs the VLM, so plain-text pages never trigger inference and only table/formula/chart regions are dispatched. Our `llama-server` remains the compute engine via `--vl_rec_backend llama-cpp-server`. This supersedes the earlier framing that treated "needs a Python pipeline" as a disqualifier.

#### Task list

##### Phase A — environment (no inference)

- [x] **PIP02-SELECTED-LIBRARY-SOURCE** — complete the prospectively enrolled `VB-PIP02-SELECTED-LIBRARY-CONFORMANCE` source gate: derive the launcher library directory from the selected resolved experimental executable and retain the complete original whole-module controls. No actual model/kernel/linkage, table quality or speed acceptance. ✅ 2026-10-07 — [MAIN current-source/original30/30 acceptance](../../artifacts/ni08/pip02-current-provenance-source-acceptance-20261007/README.md); exact current-provenance two-file publication5fd103e8.

Accepted PIP02 selected-binary library source correction: **VB-PIP02-SELECTED-LIBRARY-CONFORMANCE** owns the bounded source/native gate. The published launcher derives LD_LIBRARY_PATH from the selected resolved binary parent. The fresh original whole module passed30/30, preserving current raw-byte/FIFO/provenance guards and real temporary symlink argv controls, with hosted-only deterministic PDF and flock controls. No local import/test/model/kernel execution and no parser-quality or linkage/residency acceptance are claimed. Existing table/three-stage/corpus tasks remain open.

- [x] **Install ✅ 2026-07-20**: `paddlepaddle==3.2.2` + `paddleocr==3.7.0` (paddlex 3.7.2) into `/mnt/raid0/llm/venvs/paddleocr` (Python 3.12.13, uv). Venv total **1.4 GB**. **Gotcha recorded**: the resolver pulls `opencv-contrib-python`, which needs `libGL.so.1` — absent in this container, so `import paddleocr` fails with `ImportError: libGL.so.1`. Fixed by swapping to `opencv-contrib-python-headless==4.10.0.84` (uninstall the non-headless first); no system packages required. Re-run this swap after any dependency upgrade that reinstates the GUI build.
- [x] **CLI verified ✅ 2026-07-20**: `paddleocr doc_parser -i ... --vl_rec_backend llama-cpp-server --vl_rec_server_url http://host:port/v1` is available and **`llama-cpp-server` is an explicitly supported backend** (full set: `native`, `vllm-server`, `sglang-server`, `fastdeploy-server`, `mlx-vlm-server`, `llama-cpp-server`). **Do not be misled by `paddleocr --help`** — it lists only `doc2md` and `api` because pipeline subparsers are registered without a `help=` kwarg and argparse omits those from the listing. The subcommand exists and works. Equivalent Python API is `paddleocr.PaddleOCRVL(...)` exposing `layout_detection_model_name`, `vl_rec_backend`, `vl_rec_server_url`, `use_layout_detection`, `merge_layout_blocks` — prefer this for `odl_bench` integration over shelling out.
- **[declined: operator 2026-11-03 model-audit: satisfied: PP-DocLayoutV3-paddle3.0.0 is on disk and Phase B ran the real three-stage pipeline (gate MET 2026-10-29)]** Trigger PP-DocLayoutV3 weight resolution and record the cache path + size (a *separate* download from the GGUF, not yet performed).
- **[declined: operator 2026-11-03 model-audit: satisfied: PIP02-PHASEB-CPU-DIAGNOSTIC ran the three-stage pipeline on CPU 24-47, rc0, 2026-10-29]** Confirm the CPU-only path works on EPYC (no GPU assumptions in the layout stage).

##### Phase B — correct invocation smoke (bounded inference — **requires operator approval**)
- [x] **PIP02-PHASEB-CPU-DIAGNOSTIC — bounded three-stage CPU pipeline on the two scheduled English table pages.** ✅ 2026-10-29 — The scheduler accepted `pip02-phaseb-20261028` at 00:03:03 UTC; the real grant run ended rc0 at 00:04:58. Native output reports two completed pages, partial=false, 67.84 s and drained children; both original page artifacts contain HTML `<table>` markup. Retained result `/mnt/raid0/llm/tmp/pip02-phaseb-20261028/results/real-*/`, completion marker `/mnt/raid0/llm/tmp/pip02-phaseb-20261028/DONE`, launcher log `/mnt/raid0/llm/tmp/compute-flags/ready/pip02-phaseb-20261028.launcher.out`. This run used the private experimental-v9 CPU server, not the v7 server specified below. It establishes this bounded pipeline execution and cleanup, not table quality or a decision-grade benchmark. Phase C and the prospective `VB-PIP02-PIPELINE-WIRE` remain open. [no-belief: unsealed diagnostic, no decision warrant]
- **[declined: operator 2026-11-03 model-audit: satisfied: Phase B real-pipeline run completed 2026-10-29 (gate MET); v7 launch text is obsolete]** Start experimental-v7 `llama-server` with the PaddleOCR-VL GGUF + mmproj on a high port, `--temp 0`.
- [x] Run the documented pipeline on a handful of **table-bearing** pages from the full set:
      `paddleocr doc_parser -i <page>.png --pipeline_version v1.6 --vl_rec_backend llama-cpp-server --vl_rec_server_url http://127.0.0.1:<port>/v1`
- [x] **Gate**: confirm HTML `<table>` markup is actually emitted. If still zero, stop — the problem is the harness, not the model, and no full run should be spent. ✅ 2026-10-29
  - 2026-10-29 `pip02-phaseb-20261028` (rc0 complete 00:04:58Z, CPU 24-47, 67.8 s, `/mnt/raid0/llm/tmp/pip02-phaseb-20261028/results/real-*`): **gate MET.** Two annotated English table pages (first two in OmniDocBench order; `pages.json`), three-stage PaddleOCR-VL-1.6 via the llama-cpp-server backend on the experimental `build-v9-cpu` llama-server (`-ngl 0 -np 1 -c 8192`, GGUF + mmproj). Both pages emitted real HTML: page-1 one `<table>` (7 rows, 35 cells), page-2 one `<table>` (6 rows, 12 cells), each present in `page.md` and `native.json`; `completed=2`, `partial=false`, `children_drained=true`, server exited cleanly (PID confirmed gone). The gate was predeclared as binary (FILLERS row: "HTML markup presence is a binary invocation gate, not a quality comparison"), so this is invocation evidence only: no TEDS, structure or cell-content correctness, and n=2 says nothing about speed or the 665-table set. Harness-not-model suspicion is cleared, so Phase C is no longer blocked on the gate (it still needs its own operator approval). Caveats: the server was launched without `--temp 0` (the first Phase B box stays open), the run used the Python pipeline rather than the `paddleocr doc_parser` CLI, and the row's `VALIDATION-INCIDENT.md` records an unguarded 23:12-23:17Z OCR-weight hash overlapping INF-12 r6 / LB4.9 FU04 runs (impact not established; irrelevant to a binary gate). [belief: cc]
  - **[declined: ws58 2026-11-03 content-review: merged into the Phase C run as a pre-check]** Follow-up: spot-read both `page.md` tables against the OmniDocBench GT cells (descriptive only; Phase C owns scoring) before treating the markup as faithful, since page-2 equation cells contain dropped-operator OCR (e.g. `d_{0}\quad S^{\prime}`).
  - **[declined: ws58 2026-11-03 content-review: merged into the Phase C run]** Follow-up: record the cleanup proof box from retained evidence (`server-vm.jsonl`, `server_before_cleanup`, `children_drained`) and re-run with `--temp 0` only if Phase C needs a temperature-pinned smoke.
- **[declined: operator 2026-11-03 model-audit: duplicate of the open Phase B follow-up 'record the cleanup proof box from retained evidence']** Capture cleanup proof (no stray `llama-server`, 0% VRAM / no KFD PIDs) per existing K35 discipline.

##### Phase C — full benchmark (**requires operator approval**; long-running)
- [x] **Operator approval: Phase C APPROVED, English-only.** ✅ 2026-10-29 — The operator approved Phase C on 2026-10-29 after Phase B passed (5947aef8c). The scope is the 755 English pages (`language: english`) only, with both arms: the ODL end-to-end re-baseline and the PaddleOCR-VL-1.6 full pipeline. The Phase D decision is gated on English-only table TEDS. The full 1651-page set and the all-language split below are out of this approval, so their boxes stay open and unrun. [no-belief: not-a-result]
- [x] **PIP02-PHASEC-ENGLISH-RUN** — stage and run the approved English-only comparison on the pages that are actually eligible: **65 `CANDIDATE_NO_OBSERVED_START` pages** (the other 690 are `PROTECTED_SCOPE_UNKNOWN`, permanently excluded and never redrawn), ODL 2.5.0 + Docling plus PaddleOCR-VL-1.6, same scorer and GT for both arms, table TEDS with structure-only TEDS alongside, under v3 **keeper custody** (the legacy custody stack is retired). Done when the paired 65-page result is filed as an observation. ✅ 2026-11-09 — grant `pip02-r36-english-run-20261107b` rc0; `/mnt/raid0/llm/tmp/pip02-r36-20261107/out/results.jsonl` final record 2026-11-08T16:51:02Z: 65/65 paired pages, 52 GT tables, ODL table TEDS 0.2654 (structure-only 0.4169), PaddleOCR-VL 0.9105 (0.9707), text-block edit distance 0.157 vs 0.040, reading-order 0.235 vs 0.096; the record is labelled "operational/diagnostic observation, not a Phase D gate verdict". [no-belief: operational observation, no claim tuple] *(Original 2026-10-29 text, 755 pages, table TEDS at n=665, all-language and 1651-page re-baseline, is out of reach after the custody review; those rows were merged or declined above.)*
  - [x] **PIP02-PHASEC-65PAGE-FILE — commit the 65-page result durably (found 2026-11-09).** The final record and per-arm scores live only in scratch (`/mnt/raid0/llm/tmp/pip02-r36-20261107/out/`). Copy `results.jsonl` (final record), `score-final` and the linkage record under `artifacts/compute/pip02-r36-65page-20261108/` with hashes, and persist via `odl_bench compare-existing`. Doable now, no compute. [2026-11-09 apr2 rtg08-evl47-pip04-code: PARTIAL. Copied (160 KB, text only) to `artifacts/compute/pip02-r36-65page-20261108/`: `results.jsonl` (133 records, final = 65/65 pages, ODL TEDS 0.2654 vs Paddle 0.9105 on 52 GT tables), `COMPLETE`, `linkage.txt`, the two `*-Lfinal_quick_match_metric_result.json` and score yamls, plus `SHA256.json` binding every file under the raw dir (per-page predictions, state, score-26/52, gt-subset.json stay on raid). `odl_bench compare-existing` persistence NOT run (research-repo tool, not run from this session). Box stays open for that step. [no-belief: evidence copy]] ✅ 2026-11-10 pipeline-mgmt: the remaining step is done. `odl_bench compare-existing` (research repo, file-only renderer, no scoring) rendered both arms' final metric results into `artifacts/compute/pip02-r36-65page-20261108/compare-existing/` (`existing_comparison.json` / `.md` + `SHA256SUMS`): table TEDS ODL 0.265413 vs PaddleOCR-VL 0.910479, text Edit_dist 0.157 vs 0.040, reading-order 0.235 vs 0.096, matching the final record in `results.jsonl`. Run filed PASS as `pip02-r36-english-run-20261107b` (diagnostic observation, not a Phase D gate verdict). [no-belief: evidence persistence of an already-filed run, no new measurement]
  - **[declined: superseded 2026-11-09 by the v3 keeper custody rebuild (legacy custody stack retired 2026-11-07, root `e783b4e09`; 690 pages permanently UNKNOWN, 65 ran under keeper custody; see PIP02-PHASEC-ENGLISH-RUN)]** **PIP02-PHASEC-CUSTODY-20261101 — establish a safe legacy cutover before selecting remaining pages.** The [review](../../artifacts/compute/codex3-pip-custody-review-20261101/ACTIONABILITY.md) classifies 690 pages as protected scope UNKNOWN and 65 as no observed start, not eligible. The old shard lock closes on exec, so establish legacy writer and descendant drain, prevent reentry, retain a canonical lock through child drain, refresh the inventory and obtain a matching 24-thread end-to-end rate plus real keeper qualification. Preserve original exposures and the approved 755-page English scope; no new TEDS verdict is implied.
  - **2026-11-07 R36 triage (operator E3 'R36 rebuild + SLIDERS as filler'; zero inference):** of the 1,052 r35 source pins, 39 raid0 files are gone; 7 are recoverable by content hash from committed artifacts, 22 are forensic/unreferenced, and **10 are Python modules the pool imports at run time (`owned_window_v7`, `external_monitor`, `grant_gate`, `source_witness_v2`, `cpu_witness_v5`, `bounded_writer`, `venv_witness`, `trace_capture`, `server_witness`, `cpu_projector_witness`) that no longer exist anywhere searched** — so a pins-only R36 would die at import. A runnable R36 needs those ten modules re-authored, or the legacy custody stack replaced by the v3 keeper's grants/region-lock/STOP/disk-pause with a plain per-page job. Exposure ledger recorded per the decision: the 690 PROTECTED_SCOPE_UNKNOWN pages are permanently UNKNOWN (never redrawn); the 65 never-started pages stay in scope. No English-run row published. Evidence: `artifacts/compute/pip04-r36-pin-triage-20261107/`. [belief: cc]
  - **2026-11-07 R36 rebuild (operator decision "R36 rebuild", exposure ledger as decided: 690 UNKNOWN permanent and never redrawn, 65 never-started stay in scope, 39 forensic pins non-load-bearing):** the legacy custody stack is RETIRED in favour of v3 keeper custody (grants, region-lock, STOP, disk-pause, `job_fence` write allowlist). Reason: ten Python custody modules the legacy pool imports at run time (`owned_window_v7`, `external_monitor`, `grant_gate`, `source_witness_v2`, `cpu_witness_v5`, `bounded_writer`, `venv_witness`, `trace_capture`, `server_witness`, `cpu_projector_witness`) no longer exist on disk, so R35/R36 cannot start, and re-authoring them would rebuild what the keeper already provides. Replacement is a plain per-page job (`/mnt/raid0/llm/tmp/pip02-r36-20261107/`, row `pip02-r36-english-run-20261107`): ODL 2.5.0+Docling and PaddleOCR-VL-1.6 on the **65 never-started pages only** (13 shards, 52 GT table regions; the 690 are never run, so the 755-page Phase D coverage is NOT reachable and every result is an operational/diagnostic observation with explicit censoring), same scorer and GT subset for both arms, table TEDS with structure-only beside it, resume per page, production-consolidated-v10 kernel from the kernel store with its own `LD_LIBRARY_PATH` proved by `verify_ggml_linkage.sh`. Estimate 14400 s (provisional). **Publish status 2026-11-07 19:47Z: row published, smoke NOT yet PASS.** Smoke 1 failed in 10 s (paddlex wants `opencv-contrib-python`, the venv ships the -headless build: fixed with a dist-info shim `opencv-overlay/`, republished once); smoke 2 failed in 15 s (the private ODL bootstrap `private_boot_v2.py` mkdirs under the read-only legacy tree: fixed with `odl_boot.py`, a copy with a writable runtime dir, edit on disk, NOT yet republished: the one-republish budget of this session was spent). Next action: `python3 scripts/coordination/rowflow/publish_row.py /mnt/raid0/llm/tmp/pip02-r36-20261107/spec.json`, then watch `dryrun/pip02-r36-english-run-20261107/`. The box stays open until the filed result: persist via `odl_bench compare-existing`, then file against the Phase D gate. [belief: cc]
  - **2026-11-07 19:55Z (pipeline wrap-up): the R36 smoke is NOT pending, it FAILED a third time.** `dryrun/pip02-r36-english-run-20261107/FAIL-1.json` (19:53:06Z, rc1 after 15 s): the ODL sidecar exits during import with `PermissionError: [Errno 13] Permission denied: '/dev/null'` (`dill._dill.get_file_type` does `open(os.devnull, 'r+b')`). Cause: the `job_fence` Landlock write allowlist in `fence` mode grants only the declared dirs and not `/dev/null` (`job_fence.py` `smoke_main` adds `/dev/null WRITE_FILE|TRUNCATE`, `fence_main` does not). The bootstrap fix (`odl_boot.py`) did work, this is the next layer. The row also reports OVER-DECLARED busy_fraction (0.7 declared, 0.001 measured; an artefact of the 15 s run, re-check after a real smoke). [belief: cc]
  - [x] **PIP02-R36-DEVNULL-FENCE — get the R36 smoke to PASS: make `/dev/null` writable inside the job fence.** **Fix (b) LANDED 2026-11-07 as root 8b3706f3b (`job_fence` `fence` mode now allows `/dev/null` read-write, with a test); what remains is the republish.** Two fixes were possible, (b) is done: (a) job-local, no shared code: in `/mnt/raid0/llm/tmp/pip02-r36-20261107/odl_boot.py` create `work/devnull` and set `os.devnull` to it before the first import (dill reads `os.devnull` at import); (b) shared: add `/dev/null` to `job_fence.fence_main` as `smoke_main` already does. Next: `publish_row.py /mnt/raid0/llm/tmp/pip02-r36-20261107/spec.json` and watch `dryrun/pip02-r36-english-run-20261107/`. Done when the smoke ends PASS with a first progress record in `out/results.jsonl`. [no-belief: filed task] ✅ 2026-11-07 (fence fix 8b3706f3b installed live; row re-published, smoke PASS 20:01Z (first per-page record in out/results.jsonl); row in ready/ awaiting grant [no-belief: tooling])
  - 2026-11-02 BRF-T3 custody re-read (ws58, zero inference, read-only; OBSERVATION): the filed v8 snapshot (`/mnt/raid0/llm/tmp/codex3-pip-exposure-recheck-20261101/all-shards-inventory-v8.json`, SHA-256 `329575a52b3f502e`, plan `63028e74950b…` verified) re-derives exactly 755 pages = 690 PROTECTED_SCOPE_UNKNOWN + 65 CANDIDATE_NO_OBSERVED_START. The 65 are 13 whole shards (101, 102, 122-124, 137-139, 146-150), none in a scope-unknown shard, none with any start, region or finish record, and all 13 shard directories are absent from the surviving phasec root. Absence is not eligibility. 2,108 of 2,108 captures lack a verified complete result (2,095 unbound/incomplete, 13 with no result). **A fresh inventory cannot be regenerated in this session's namespace:** 6 of 7 campaign roots (all under `/mnt/micron`) and 1,581 of 2,108 capture files are not visible, and `inventory_all.py` refuses on an inaccessible root. So the replay covers the page-eligibility classification only. **This box stays open**; the residual is legacy writer and descendant drain, reentry prevention, a canonical lock retained through child drain, a refreshed inventory (needs the micron roots visible), the matching 24-thread end-to-end rate and real keeper qualification. Evidence: `docs/design/backlog-refactor-2026-11/t3-evidence/exp06-custody-reread-20261102.json` (SHA-256 `899e431ec4572c37`). [belief: cc]
  - 2026-11-01 public-fixture diagnostic: one native Paddle region returned HTTP 200 with 634 prompt tokens; the crop matched the pinned non-cohort image and 12-slot split-KV geometry was logged. The worker intentionally stopped after that response; no page, rate or qualification verdict. [Retained evidence](../../artifacts/compute/codex3-pip-public-fixture-diagnostic-20261101/README.md). [belief: cc]
  - 2026-10-29 r7 group14 first partial ended23:17:28Z rc75: four assembled original pages have validated start/result/markdown hashes; remaining original region starts/responses and unmatched exposures are retained separately. The final native attempt explicitly reports disk floor and no new factory. Later automatic resumes are separate captures. The waiting r7 group107 dispatch was canceled before start for its relocatable r8 successor. [Original partial snapshot](../../artifacts/compute/results-filing-20261029-2328.json). No table-quality/full-cohort tick. [belief: cc]
  - 2026-10-29 keeperv6 is live (PID257469, started22:37:02Z). Published five Paddle r8 and five ODL r2 packets as `any-cpu-quarter`; each launcher takes `WS58_REGIONS` for its CPU claim and `FILLER_CPUS` for taskset. Both exact native smokes passed and drained (Paddle76.60s/fiveHTTP200 responses; ODL71.89s/markdown+projection+DONE). New ODL starts capture producer row/source-manifest identity before the client request. Only unstarted/waiting predecessor packets were replaced; the running r7 group14 continues. [Source/publication evidence](../../artifacts/compute/codex3-relocatable-and-sala-z9-20261029.json). Collection and full quality gate remain open. [belief: cc]
  - 2026-10-29 ODL parallel shard7 completed25/25 native pages at22:23:52Z; page result/DONE/prediction hashes and drained status verified. Paddle r4 group11 ended22:17:24Z rc78; its last native attempt explicitly records disk-floor admission, following earlier saved-layout refusals. R7 passed a58.80s real native smoke (five HTTP200 responses,5.31GB sampled RSS, rc75 partial and drained), then four immutable replacements were published two on q2 and two on q3. Excess pending q0/q1 manifests and five waiting PIP pollers were withdrawn at the operator's queue-cap boundary, without stopping a live grant; the310 recovery stays prepared and unexposed. [Original events, page hashes and native disk trace](../../artifacts/compute/results-filing-20261029-2239.json). No quality/full-cohort tick. [belief: cc]
  - 2026-10-29 23:40 filing: relocatable ODL shards16/17/5/8/9 each completed25/25 original fresh English pages,125 newly verified total. Every original image/PDF, pre-client plan/protocol/producer source pin, prediction, result and matching DONE digest was reopened; all native children drained. This meets those native collection criteria only. Phase C full matched scoring and its coverage/source-lineage follow-up stay open. Current waiting Paddle packets g5/g11 target q2 and g8/g26 target q3 under the latest direct operator placement instruction, at most2 queued per quarter; unchanged launchers use WS58_REGIONS and FILLER_CPUS. Original waiting any-quarter JSON copies are archived; g107 had already armed and was left unchanged. [Native results and placement](../../artifacts/compute/results-filing-20261029-2340.json). [belief: cc]
  - 2026-10-29 first common scoring snapshot: ODL435/755 completed pages and131/243 tables, available-output table-weighted TEDS0.656652 and structure-only0.799800. Paddle1 completed page/zero scored tables, so the comparison is undefined. Native output hashes pass; current source-lineage reader supports97 ODL pages/35 tables and explicitly refuses unregistered generic/parallel origins. All decision cells remain null; missing/censored outputs are not scored zero. [Preserved report and native compare-existing artifacts](../../artifacts/compute/pip02-partial-teds-20261029/README.md). Phase C remains open. [belief: cc]
  - 2026-10-29 Paddle parallel group107 ended22:04:05Z rc78 after six partial batches: 25 original RPC starts have25 retained responses across shards107/109, no unmatched RPCs, but zero assembled pages. The terminal batch refused all15 saved layouts. A model-free-dispatch native layout rerun found identical pixels and54 identical regions except36 confidence scores differing in their final decimal places; strict full-layout equality caused the refusal. Queued46 affected r4 packets were withdrawn, active grants retained, and an immutable r5 repair preserves original scores while still requiring exact pixels/geometry/order/labels and exact original request bytes. Native smoke remains in progress; this is a harness finding, no table-quality verdict and no Phase C tick. [Evidence](../../artifacts/compute/results-filing-20261029-2222.json). [belief: cc]
  - 2026-10-29 `codex3-pip02-fresh-odl-s0-20261029` first attempt ended 19:17:11Z rc75: 7/25 cohort ordinals complete (0–6), one unknown (7), 17 missing (8–24), from native `odl-batch-attempts/9311e5ef-77b1-4d42-b726-d1a3078526a1.json` under `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029`. Preserve per-page original input/source/grant/result records; unknown ordinal7 is never redrawn. Later 19:20–20:20 grant is a separate resume, not a rewrite of this snapshot. No TEDS/quality verdict or full-cohort completion; the existing Phase C collection and common scoring task remains open. [belief: cc]
  - **Operator decisions, 2026-10-29:** use a newly declared full 755-page English cohort (243 annotated table regions), reusing no earlier diagnostic outputs or warrants, including for the eleven formerly unknown pages. Preserve completed and unknown exposures within this new cohort without redraw. The comparator is ODL 2.5.0 + Docling 2.91.0 docling-fast hybrid full mode on lossless image-only PDF wrappers of the same canonical images; this warrants raster hybrid behavior only. Paddle remains native layout → region recognition → assembly. Use the same GT and scorer for both arms, reporting TEDS, structure-only TEDS and explicit coverage/censoring. Declaration: `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/NEW-COHORT.md`; plan SHA-256 `63028e74950ba7250f33cbce13f4f0bdd165bba2a075242db4475c26f645ed68`. [no-belief: operator-approved prospective scope]

- **[declined: ws58 2026-11-03 content-review: merged into the Phase C run spec]** Re-baseline **ODL end-to-end** on the full 1651-page set. This supersedes `table.TEDS = 0.783813` everywhere it is quoted.
- **[declined: ws58 2026-11-03 content-review: merged into the Phase C run spec]** Score **PaddleOCR-VL-1.6 full pipeline** on the same set.
- **[declined: ws58 2026-11-03 content-review: merged into the Phase C run spec]** Report **both** an all-language and an **English-only** (`language: english`, 755 pages) split for every metric. The demo set's 64%-Chinese skew is why prior numbers were misleading.
- **[declined: ws58 2026-11-03 content-review: merged into the Phase C run spec]** Report table TEDS at **n=665** with TEDS-structure-only alongside, plus text-block edit distance and reading-order edit distance.
- **[declined: ws58 2026-11-03 content-review: merged into the Phase C run spec]** Persist via `odl_bench compare-existing` into `epyc-inference-research/data/odl_existing_comparison/`.

##### Phase D — decision
- [x] Decide the table path: ODL alone / ODL + PaddleOCR-VL for table regions / PaddleOCR-VL pipeline wholesale. Gate on the **English-only table TEDS**, with latency and the inference-avoidance property as secondary criteria. ✅ 2026-11-10 — **PaddleOCR-VL wins** on the 65-page English run (`pip02-r36-english-run-20261107b`): paired mean table-TEDS difference (paddle − ODL) = **+0.645** (paddle 0.910 vs ODL 0.265), page-clustered bootstrap 95 % CI **[0.257, 0.769]**, lower bound > 0.20 margin; n = 52 GT tables on 10 table-bearing pages, 10,000 resamples, seed 20261110, percentile CI; 51/52 tables favour paddle. Decision: PaddleOCR-VL for table regions only, ODL unchanged elsewhere (secondary latency/inference-avoidance criteria still apply; n=10 clusters is small, so the new-era run re-checks). Script/output: `artifacts/compute/pip02-r36-65page-20261108/teds-ci/` (`teds_ci.py`, `teds_ci_result.json`, `SHA256SUMS`). (operator 2026-11-10: 0.20 margin, 10k resamples) [belief: cc]
  - **Decision needed (operator), 2026-11-09 — what rule governs a 65-page result?** The gate above says "English-only table TEDS" and was written for 755 pages (n=665 tables); the achievable evidence is 65 pages / 52 GT tables (ODL 0.265 vs PaddleOCR-VL 0.910 table TEDS, structure-only 0.417 vs 0.971; 690 pages are permanently unobservable). P-DOCPARSE-1 covers LiteParse vs ODL, not this. Options: **(a)** ratify a reduced-n rule: accept the 65-page paired result for the table-path choice if the paired-bootstrap 95 % CI of the TEDS difference (clustered by page) excludes 0 and a minimum-effect margin (for example 0.20) holds, with latency and inference-avoidance secondary; **(b)** treat the 65 pages as hypothesis-generating only and require a fresh, newly declared, exposure-clean page draw (new cohort, new warrant) before any table-path change; **(c)** decide now by judgment on the observation (PaddleOCR-VL for table regions, ODL elsewhere) with the rule's limits written down. Tradeoffs: (a) is cheapest and the gap is large enough to clear any sensible margin, but it sets a precedent for small-n gating; (b) is cleanest but costs a new cohort run and delays the decision; (c) is fastest but ungated. **Recommendation: (a)**, with a conservative scope (PaddleOCR-VL for table regions only, ODL unchanged elsewhere), re-checked by the new-era run. Until ratified the default is unchanged. This blocks only this box.
  - **2026-11-09 operator decision (decision tool): option (a), a reduced-n rule on the 65 pages, with a paired CI against a pre-set margin.** **PROPOSED margin, FOR OPERATOR CONFIRMATION (not yet ratified):** the table-path rule is met iff the paired-bootstrap 95 % CI of the table-TEDS difference (PaddleOCR-VL minus ODL, resampled by page, not by table) has a lower bound above 0 AND a lower bound at or above a minimum-effect margin of **0.20 TEDS**; the margin and the bootstrap settings (resamples, seed) are fixed in the scorer BEFORE the CI is computed, and latency and inference-avoidance stay secondary. 0.20 is the example figure from the decision request, chosen as an effect large enough that 52 tables from 65 pages cannot plausibly produce it by chance; confirm or replace it. **No path decision is stated here.** The paired page-clustered CI has not been computed (only the point estimates in the option text exist, and the final record is still scratch-only pending PIP02-PHASEC-65PAGE-FILE), so the rule is not met on the record; the default stays ODL until the rule is confirmed and met. Scope if it is met: PaddleOCR-VL for table regions only, ODL unchanged elsewhere, re-checked by the new-era run. Next: commit the 65-page result durably (PIP02-PHASEC-65PAGE-FILE), then compute the CI once with the confirmed margin. [no-belief: rule proposal, no measurement claim]
- *Moved to [`model-evaluation-queue.md`](model-evaluation-queue.md) § Track: meq-carve-document-parser-table-bench on 2026-11-03 (BRF-T1-MEQ, operator D2): "Only if PaddleOCR-VL underperforms: consider MinerU2.5-Pro or GLM-OCR. Architecture …".*
- **[declined: ws58 2026-11-03 content-review: "not a blocker" by its own text; refile if Phase D picks a parser]** Domain-transfer refinement (**not** a blocker): assemble a modest corpus of the PDF types the orchestrator actually ingests and confirm the OmniDocBench-chosen parser holds up. OmniDocBench's English subset is a legitimate gating instrument on its own; this only checks transfer.

#### Success criteria

1. PaddleOCR-VL-1.6 emits real HTML tables under its documented pipeline (binary gate, Phase B).
2. A table TEDS number for ODL and for PaddleOCR-VL at **n=665**, English-split, both from the same scorer and GT.
3. A defensible answer to "do we have a table-extraction gap, and does a VLM parser close it?" — replacing today's three void instruments.

#### Guardrails

- **No inference without explicit per-run operator approval** (`feedback_no_concurrent_inference`). Phases B and C are inference; Phase A is not.
- **Production kernels are frozen.** Any llama.cpp work uses the experimental tree only.
- Pair every speed number with a correctness check (`feedback_pair_speed_with_correctness_check`).
- Published leaderboard scores are **priors, not results** — neither PaddleOCR-VL's 96.33 nor Unlimited-OCR's 93.92 appears on the official OmniDocBench leaderboard; both are vendor self-reports. Only our own scored runs gate the decision.

#### Reporting

On completion of each phase: flip the checkbox with `✅ YYYY-MM-DD`, cite the artifact path, and mirror the outcome into `opendataloader-pipeline-integration.md` (task K35.18) and today's `progress/YYYY-MM/`. Record any newly discovered work as a fresh `- [ ]` line rather than prose.

#### Key file locations

| Purpose | Path |
|---|---|
| Full benchmark | `/mnt/raid0/llm/datasets/omnidocbench/` |
| Annotations | `/mnt/raid0/llm/datasets/omnidocbench/OmniDocBench.json` |
| Model weights | `/mnt/raid0/llm/models/PaddleOCR-VL-1.6-GGUF/` |
| PaddleOCR venv | `/mnt/raid0/llm/venvs/paddleocr` |
| Producer/scorer | `epyc-inference-research/scripts/benchmark/odl_bench/` |
| Eval suite + leaderboard | `/mnt/raid0/llm/omnidocbench/` |
| Prior (void) artifacts | `/mnt/raid0/llm/tmp/odl-paddleocr-vl-*` |

#### Research context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-864 | Unlimited OCR Works (Baidu, arxiv:2606.23050) | high | worth_investigating |
| intake-865 | DeepSeek-OCR: Contexts Optical Compression (arxiv:2510.18234) | medium | worth_investigating |

Official OmniDocBench **v1.6_full** leaderboard (shipped in `/mnt/raid0/llm/omnidocbench/README.md`), for priors only:

| Model | Size | Overall ↑ | TableTEDS ↑ |
|---|---|---|---|
| MinerU2.5-Pro | 1.2B | 95.75 | 93.42 |
| GLM-OCR | 0.9B | 95.22 | 92.83 |
| PaddleOCR-VL-1.5 | 0.9B | 94.93 | 91.67 |
| PaddleOCR-VL | 0.9B | 94.18 | 90.65 |
| *PaddleOCR-VL-1.6 (self-reported, arxiv:2606.03264)* | *0.9B* | *96.33* | *94.76* |
| *Unlimited-OCR (self-reported)* | *3B-A0.5B* | *93.92* | *90.16* |
| dots.ocr | 3B | 90.77 | 87.18 |
| DeepSeek-OCR 2 | 3B | 90.25 | 83.89 |

#### Architecture pre-check — MinerU2.5-Pro and GLM-OCR (2026-07-20, no downloads)

Run *before* downloading, because architecture — not leaderboard rank — is what decided the 2026-07-17 failure. **Verdict: NEITHER is a single-pass whole-page parser.** Both are element-level recognition models whose published scores come from a Python pipeline (layout → per-element crops → element-specific prompts → assembler). Handing either a full page image would reproduce the exact PaddleOCR-VL mistake.

##### MinerU2.5-Pro — the only candidate that keeps us on ONE kernel
- **Two-stage, but both stages are the SAME weights, prompt-selected**: `"\nLayout Detection:"` on a 1036×1036 downsample emits bboxes as text; Python then crops at native resolution and re-calls with `"\nTable Recognition:"` / `"\nFormula Recognition:"` / `"\nText Recognition:"` / `"\nImage Analysis:"`. **There is no second model to download** — this is the key differentiator vs PaddleOCR-VL and GLM-OCR.
- `mineru-vl-utils` `two_step_extract()` is the *only* parsing entrypoint; no single-pass method exists in the API. A 30-block page = **31 model calls** plus client-side crop/rotate/mask, per-block-type sampling params, and a ~20-module post-processor (tables emit **OTSL**, not HTML — needs conversion for TEDS).
- `config.json` is generic `Qwen2VLForConditionalGeneration` / `qwen2_vl`, already supported by llama.cpp `conversion/qwenvl.py` + `PROJECTOR_TYPE_QWEN2VL`. **But zero upstream awareness** (`repo:ggml-org/llama.cpp MinerU` → 0 hits), no official GGUF, and no correctness attestation on any community GGUF. Some community GGUFs ship **no mmproj — unusable**.
- License **Apache-2.0** for Pro-2604/2605; the older 2509 is **AGPL-3.0** and most GGUFs are of *that* one — check provenance carefully.
- Size: GGUF Q8_0 531 MB + mmproj Q8_0 709 MB ≈ **1.24 GB** (mmproj is larger than the decoder — 675M vision tower vs 0.5B LLM). Genuinely bilingual; olmOCR-bench (English-only) **75.2**.

##### GLM-OCR — better llama.cpp citizenship, worse architecture for us
- **Requires an EXTERNAL detector**: `glmocr/layout/layout_detector.py` imports `PPDocLayoutV3ForObjectDetection` — a separate 133 MB **PaddlePaddle** model llama.cpp will never run. Same shape as PaddleOCR-VL. llama.cpp discussion #19721 states plainly it "can only recognize text"; you must run PP-DocLayoutV3 yourself.
- Its published English score is self-declared as measured through the **hosted API** (`.eval_results/olmocrbench.yaml`: `value: 75.2`, `notes: "... Using ZAI API"`) — i.e. the full pipeline, not standalone weights.
- Upside: **merged upstream support** ([PR #19677](https://github.com/ggml-org/llama.cpp/pull/19677), 2026-02-18), dedicated `clip_graph_glm4v`, and an **official first-party GGUF** (`ggml-org/GLM-OCR-GGUF`, Q8_0 950 MB + mmproj 484 MB). License **MIT**.
- Operational: **`--flash-attn off` is required**; PR notes degraded quality via Web UI (use the API with specific prompts); bbox prediction reported unreliable; vLLM/SGLang/transformers support is nightly/git-only.

##### Bearing on the MTP track (separate finding, worth carrying over)
GLM-OCR ships `num_nextn_predict_layers: 1`, but llama.cpp `src/models/glm4.cpp` comments the NextN/MTP tensors as *"preserved but unused"*. Its headline decoder speedup is **not realized under llama.cpp** — we would carry the tensors and get plain autoregressive decode. This is a banked-but-unexploited MTP lever; cross-reference [`speculative-decoding-mtp-refresh.md`](speculative-decoding.md#track-speculative-decoding-mtp-refresh).

##### Consequence
- **[declined: ws58 2026-11-03 content-review: resolved 2026-07-29 by its own text]** **Do not download MinerU2.5-Pro or GLM-OCR as `odl_bench` model swaps** — the harness invokes models single-pass and both would produce void results. ✅ 2026-07-29 — this guardrail is now the operative Phase-D condition; either candidate requires a separately scoped multi-call pipeline harness before any download or benchmark.  *(Restored to `- [ ]` 2026-08-11 by `mainC` — standing constraint with no completion state; the dated evidence below is kept, the rule is live again.)*
- **[declined: ws58 2026-11-03 content-review: conditional on a concept proof that Phase D decides; refile then]** If PaddleOCR-VL's pipeline proves the concept and we want a one-kernel alternative, scope **MinerU2.5-Pro-2605 as a separate pipeline-harness project** (multi-call orchestration + OTSL→HTML assembler). Its in-model layout stage is the reason it is the right target: `llama-server` + mmproj can serve *both* stages, with pure Python glue and no second inference runtime. `mineru-vl-utils` has an `http-client` backend for OpenAI-compatible servers that llama-server plausibly drops into, though it is not a listed/tested backend.

2026-10-30 results filing: ODL relocatable shard20 completed25/25 original English pages; all image/PDF/source/result/prediction/DONE hashes and cleanup were reopened. This meets its collection criterion, not Phase C quality. Six further ODL packets were published23:44 with the unchanged qualified launcher. Own delegated scorer tests without bytecode suppression then created21pyc files in three shared-venv cache directories and correctly tripped R8g107 and later R7g14 integrity guards. All22613 original files and4links were verified unchanged. The affected pending packets were withdrawn, own failed groups stopped at their boundaries, and original accepted/unknown records retained. R9 uses a fresh complete runtime inventory and explicit isolated bytecode lookup; its70.259s real smoke retained five matched HTTP200 responses,5.364GBsampledRSS and verified cleanup. Six R9 successors are published: two fixed q2, two fixed q3, and two relocatable continuations; no fixed quarter has more than2queued manifests. Native prospective page-finish receipts now bind capture/source/grant/result/markdown, without historical backfill. [Evidence](../../artifacts/compute/results-filing-20261030-0000.json). [belief: cc]

2026-10-30 00:20 filing: original ODLs21 completed25/25 fresh English pages (525–549), with original image/PDF pixel identity, plan/source/grant, prediction/result/DONE and page-level cleanup reopened. Original first partials s24/s25 at00:01 ands28/s29 at00:03 each recorded25missing,0complete,0unknown; contemporaneous logs show25pre-output151GiBadmissionrefusals per shard. Later rearms are separate snapshots and may change present coverage. No unknown is redrawn and no TEDS/full-cohort gate is claimed. R9group5 is liveq2; five other R9packets were rejected before engine launch because owner publication omitted packet engine/DONE links. Links are fixed; fresh-ID R11replacement is being real-smoked after the known hourly backup interval, with R9g5 untouched. R10 controls retained2HTTP200 and2unknown requests before00:17diskreserveinterruption and are not reused. [Native evidence](../../artifacts/compute/results-filing-20261030-0020.json). [belief: cc]

R11 replacements passed real58.883s smoke (5nativeHTTP200,0unmatched,5.917GBsampledRSS,cleanupverified) andfive newIDs arepublished withfullychecked filesystemclosure; liveR9g5 isunchanged. [no-belief: dispatch and bounded diagnostic qualification]

2026-10-30 event-bound Paddle filing: originalR9g5 andR11g107 each retained10newRPCstarts/10matchedHTTP200/0unmatchedRPCs overtwofive-requestbatches, thenexplicitdisk-floorstop; originalR11g11 had0RPCs beforedisk-floorstartupstop. No attributablepage-finishreceipts wereproduced; existingpage-levelunresolvedjournals remainunknown and laterrearms areseparate. Nativeownerresult lacks anexplicitcleanupboolean, so no cleanupclaim is inferredfromrc75. SDKfixture provesbudgetTimeoutErrorcanbe wrapped asConnectionerror, but originalworkererrorcause remainsunproven and isnot called aserveroutage. [Audit](../../artifacts/compute/results-filing-20261030-0038.json). [belief: cc]

Strictlineage implementation shipped Researchmain46244248728c: registeredpre-clientODLsource andnativeR9–R11finishbinding replace mtime/overlapinference. Nineoffline tests andfreshsourcepinpreflight pass; TEDS/matching/denominator/thresholds unchanged. Legacyinsufficientlineageremainsunverified; fullcohortqualitygate staysopen. FivefurtherR11groups17/23/29/32/35 werepublishedany-cpu-quarter withsamequalifiedlauncher andcompletepacketclosure afterfreshoriginal-exposure/portchecks;75newpages notduplicatecohortwork. [no-belief: code/tests anddispatch, notcohortquality]


2026-10-30 original Paddle R11 g14 completed all15 native page results; exact input/result/markdown hashes validate. All214 retained RPC origin chains pass source, grant-interval and body-hash checks (185 from R7,29 fromR11). Seven completed pages have original R11 finisher receipts; eight remain assembler-lineage unverified and are never retrospectively backfilled. This is collection, not a full755-page TEDS or parser-selection verdict. Existing full-cohort gate remains open. [Native audit](../../artifacts/compute/results-filing-20261030-0102.json). [belief: cc]


##### 2026-10-30 original seven Paddle continuation partials


Each outer job exited rc75; the last capture started before that exit reports disk floor. Attempt result JSON does not record finished_at, so pairing that last pre-end capture with the outer end is inferred from sequential launcher execution, not a separately timestamped native finish. RPC counts below use native originated_at/completed_at and original capture hashes, at each outer end; they are not the later 00:52 cumulative snapshot. Unknowns remain unknown and are never redrawn. No TEDS or parser quality claim.

| Group | Outer end UTC | Last capture start UTC | Result SHA256 | RPC starts / matched / unmatched | Later captures excluded |
|---|---|---|---|---|---|
| 17 | 2026-10-30T00:41:29Z | 2026-10-30T00:39:31Z | 4d586aa6c4332afec4e753eeb727ed5d158a3f79f3e3e6a9fb2cafc16f113e82 | 10 / 5 / 5 | 0 |
| 23 | 2026-10-30T00:41:24Z | 2026-10-30T00:40:43Z | 3d933176729a49e9b9327b3dc3532ca533a27ef3e4cb082a2101bb9dd599353c | 5 / 5 / 0 | 0 |
| 29 | 2026-10-30T00:41:41Z | 2026-10-30T00:41:15Z | 030ede2987d5d89d01f1c2658a5eb9d176fa49a426eee7cc93a4e1068eb72f7d | 10 / 10 / 0 | 0 |
| 26 | 2026-10-30T00:42:25Z | 2026-10-30T00:42:01Z | a9b135ae459d73889f0cd84faccc18abc9d914d6ace652de14f13d0d066c273a | 0 / 0 / 0 | 2 |
| 32 | 2026-10-30T00:44:24Z | 2026-10-30T00:44:00Z | d22b9ec090f362e3ed92e50107172e53c94844aea2dc489842fb1448bbb0ac08 | 0 / 0 / 0 | 0 |
| 35 | 2026-10-30T00:44:25Z | 2026-10-30T00:44:01Z | 36e4f2a4e36eb72542b473cc5821a6aedca15f4b1fea454d84b2ec47e85f605b | 0 / 0 / 0 | 0 |
| 8 | 2026-10-30T00:46:42Z | 2026-10-30T00:46:18Z | dc3b5c60abd6ebccc341d8db968935f599732410115c0e51eb322d05abed2839 | 0 / 0 / 0 | 1 |

All seven last pre-end results record `reason: disk floor`; g17/g23 also report timeout deadline/admission/output limit; g29/g26/g32/g35/g8 report timeout admission. Full native result paths, hashes, capture-bound start receipts, later capture identities and exact end_line evidence are in original-seven-events.json. Matched means the native result carries the matching start hash and completed by the event; it is not a source-grade or quality assertion.

[Committed original audit](../../artifacts/compute/results-filing-20261030-0107.json). Existing collection/full-cohort boxes remain open. [belief: cc]


##### 2026-10-30 original eight Paddle collection partials


Each outer job exited rc75. The last capture started before each exit reports disk floor and TimeoutError: admission. Attempt result JSON has no finished_at: pairing that last pre-end capture with the outer end is inferred from sequential launcher execution, not a separately timestamped native finish. RPC counts use originated_at/completed_at and original capture hashes at each event end; matched means native result has matching start hash and completed by then, not a quality or full source-grade claim. Unknown remains unknown; no redraw.

| Group | Outer end UTC | Last capture start UTC | Result SHA256 | RPC starts / matched / unmatched | Later captures excluded |
|---|---|---|---|---|---|
| 38 | 2026-10-30T01:12:11Z | 2026-10-30T01:11:44Z | bcf50dbfc8d8bde3369100c26891d3993b8c5c43a0eac1b009215516389b83aa | 20 / 20 / 0 | 0 |
| 41 | 2026-10-30T01:12:00Z | 2026-10-30T01:11:36Z | b6b6720907778b35b95f9ba013286e9f78c09e9554605d81534de39b9b205316 | 0 / 0 / 0 | 0 |
| 44 | 2026-10-30T01:15:04Z | 2026-10-30T01:14:40Z | ac7f3dee9269038959a882960739bdf540b2f9605ed0d3424c8d6e5cef3b16fa | 0 / 0 / 0 | 0 |
| 47 | 2026-10-30T01:15:06Z | 2026-10-30T01:14:42Z | ccd0b132022f27db012961ff958d2ee0aa42ef805f4607cc9b60a0f4f66a0dde | 0 / 0 / 0 | 0 |
| 50 | 2026-10-30T01:15:07Z | 2026-10-30T01:14:43Z | 8379d2d768c14470a1ac49ce2322a43385310c3431d5c5ccaa514cf43fb22279 | 0 / 0 / 0 | 0 |
| 53 | 2026-10-30T01:15:09Z | 2026-10-30T01:14:45Z | 87de7abb1ef069e7b4e0d983759e5b8bb5462e75bec535655f3dba1423fd3e8d | 0 / 0 / 0 | 0 |
| 56 | 2026-10-30T01:20:16Z | 2026-10-30T01:19:52Z | 02cc7d71893cc4d0b02095a040280596c897d2ac9c4220729bcb8377f7d0d767 | 0 / 0 / 0 | 0 |
| 59 | 2026-10-30T01:20:17Z | 2026-10-30T01:19:53Z | 26a59f5f9809e4c26249c089d24c111b3858ef272da4b0e19596cb13f2a28166 | 0 / 0 / 0 | 0 |

Full exact native paths, capture SHA256, source registry, grant, result SHA256 and individual request-origin files are in original-eight-events.json. Native collection partial only; no TEDS, parser comparison, adoption, or completed scientific-cohort claim.

[Committed native audit](../../artifacts/compute/results-filing-20261030-0138.json). [belief: cc]


##### 2026-10-30 three first-client recoveries and partial QC


Original scheduled `codex3-pip02-odl-recover-50-118-310-r1-20261030` completed rc0 at 2026-10-30T01:28:32Z. Its native batch DONE reports three complete first-client pages, 3 workers, 17,177,640,960-byte sampled tree RSS and no batch error. Native results and DONE, prediction hashes, canonical page image/PDF identity, prospective captured source/plan/protocol, grant interval, drained children and the original pre-client evidence were reopened and verified. Ordinals 50, 118 and 310 have respectively 0, 1 and 0 ground-truth tables. Original source branch and logs place the prior failures before the HTTP client; prior files remain retained. This is image-only PDF ODL2.5 + Docling2.91 hybrid collection, not original-PDF performance.

The pinned dependency manifest and source assert the canonical CPU Docling asset set; the original producer calls its asset-digest verification before the first-client start. This observation does not invent a separate per-model runtime receipt. Native per-page audit: `recovery-native-audit.json` SHA256 `08f78a15aa64de56404a4eef2df3f9d4ef9ab794c8563ea5da00bbfe6a5ab9dc`. Source manifest `b2ce8fc980bba8d6aaca2bfc73508e24db33e798baa799e55d782af78ef449cd`.

Fresh offline scorer pin `pins.json` SHA256 `1a71361536d7dc2a5abde8366f565888a844d24c1f5740ed05b13c59d71e4c7c` includes current producer registries plus original recovery producer, failure-log and input evidence. Common scorer completed rc0 under SMT126/127 and pair mutex; 94.94 s, sampled peak 450,068,480 bytes, no model calls. Raw snapshot (`report/coverage-and-scores.json` SHA256 `44478bba72b2221160c8617629a9a5fae6d80bfea19e04828514ddae83f35fe3`): ODL 638/755 complete pages and 224/243 GT tables scored, with source lineage verified for 178 of 638 complete pages; Paddle 17/755 pages and 1/243 tables, lineage verified for 7 of 17. Missing or unverified records remain unverified. These are observational coverage counts, not a matched complete comparison.

The one GT table on recovered ordinal 118 has descriptive native TEDS 0.4005603400 and structure-only TEDS 0.9287020110 (higher is better); ordinals 50 and 310 have no GT tables. The raw aggregate ODL table-weighted values 0.5236367252 and 0.6641641385 include pages without verified source lineage and are descriptive only. Paddle raw 1.0/1.0 is from one table, not a cohort comparison. Both full-population and gate eligibility flags are false; all decision metric values in `report/row_set.json` remain null. No parser-quality, adoption, full-755 or production-performance verdict follows.

[Committed native audit and frozen QC files](../../artifacts/compute/results-filing-20261030-0157.json). Existing full-population/adoption gate remains open. [belief: cc]


##### 2026-10-30 original Paddle groups62/65/68/71


All four original outer events exited rc75. Their last captures before those ends record disk floor and TimeoutError: deadline, admission or output limit. Pairing each native result with its outer event is inferred from sequential capture starts and the outer end; result.json has no finished_at. No new quality or completed-cohort claim.

| Group | Original end UTC | Last capture start UTC | Result SHA256 | Original RPC starts/matched/unmatched | Later captures excluded |
|---|---|---|---|---|---|
| 62 | 2026-10-30T01:36:25Z | 2026-10-30T01:35:19Z | 11abe846ab210a39f0e2fe7de9301ef6ccc287e88618895eb4c8f3e7525b73cf | 0/0/0 | 12 |
| 65 | 2026-10-30T01:36:23Z | 2026-10-30T01:35:20Z | 27e4280ce2f64c39b9f557b8cc73d916aa1a03ad7b209b72f04945b190a85364 | 0/0/0 | 2 |
| 68 | 2026-10-30T01:36:25Z | 2026-10-30T01:35:22Z | ba44e2d13e04f18d442407526944abfde5c78bf8b1395cf4f6a0350cec154a10 | 0/0/0 | 12 |
| 71 | 2026-10-30T01:36:23Z | 2026-10-30T01:35:23Z | 74a384cb815ca891b9eac40f4e90fd1a068f77c57a24b2f25ce897d410262d16 | 0/0/0 | 12 |

RPC counts use native originated_at/completed_at and capture hash at the original end, not later cumulative state. Later captures are retained separately. Full original paths, grant/source identities and hashes are in original-four-events.json. Unknowns are never redrawn.

[Committed original audit](../../artifacts/compute/results-filing-20261030-0206.json). [belief: cc]


##### 2026-10-30 R4 original collection outcomes


The original `codex3-pip02-odl-relocatable-r4-s24-20261030` and `...-s25-20261030` scheduled runs completed rc0 at 02:29:48Z and 02:29:50Z on 2026-10-30, respectively. Each native batch DONE has 25/25 completed pages; their complete DONE SHA256 values are `715cf83af802c4ee6274f3579d18b2b3f760d8eee187483557d51ce5d1edce1b` and `cc35eac49a886459d459b28c757e10df3bb58a277eaf7e7ba469008613f7afee`. The 50 original page records were individually checked against canonical image hashes, frozen plan, PDF identity, result and DONE/prediction links, captured grant intervals and the registered R4 producer/source manifest `af6262aaf380b3a69031fc5b7f5b11ec0f8b697f314c410c159568bccf4cc62a`. They cover respectively 5 and 0 GT tables. Sampled peak tree RSS was 62,442,586,112 and 94,929,620,992 bytes. This is native collection on image-only wrappers, not a TEDS, parser-selection or original-PDF performance verdict.

The original `...-s28-20261030` ended rc75 at 02:27:57Z. Its original batch result `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/odl-relocatable-r4-20261030/attempts/2aa57e09ad5a4f37afe39545d9694784.json` SHA256 `2de7d4d14a24efce05f767bf664bca848f9f88d208d8971e217d5c96d257a543` recorded 12 unknown pages (ordinals 700–711), 13 missing pages (712–724), no completed page and zero GT tables across these positions at the original boundary. All 12 partial result writers report forced cutoff after owned-subtree drain; original pre-client producer/grant/plan start captures were checked. Unknown exposure remains unknown and cannot be redrawn. The later 02:29 grant is a separate continuation and is not used to reconstruct this original result.

The original s28 sampled tree-RSS peak was 103,174,090,752 bytes, 94,875,648 bytes above the 96 GiB threshold (103,079,215,104 bytes). The batch record has `error: null` and does not capture which stop predicate fired; a unique stop cause or disk-floor attribution is not established. Native audit with all page paths and digests is `/dev/shm/codex3-pip02-r4-original-audit-20261030/native-audit.json`. Audit ran model-free on SMT126/127 under the pair mutex with a sampled peak of 26,296,320 bytes and rc0. No quality or full-755 completion claim.



`codex3-pip02-odl-relocatable-r4-s29-20261030` ended rc78 at 2026-10-30T02:40:04Z, observed 02:40:41Z. The final native batch result `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/odl-relocatable-r4-20261030/attempts/4617a9016a1d45e9b5c6b7248569071d.json` SHA256 `c9d4a37bd89f1ec34c86cbcde7010d23c9ad71a9860a2cd722ade9fb3c286003` records 13 complete pages, 12 unknown and no missing pages; `error` is null. The result is partial, not completed cohort or parser quality.

The earlier grant at 02:31 produced the separate rc75 batch `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/odl-relocatable-r4-20261030/attempts/959d4b96101b4415973af23ef6135b49.json` SHA256 `652519dbe64376bb77ec885a09519f5d703df467642bd83b90a64a107996e35b`, with ordinals 725–736 unknown and 737–749 unstarted at that boundary. Its sampled tree-RSS peak was 103,783,727,104 bytes, above the 96 GiB threshold; the native record does not identify a unique stopping predicate. All 12 unknown pages have client backend-routing and sidecar document-processing evidence; their captured partial writers report forced cutoff after owned subtree drain. No unknown page may be redrawn.

The later 02:37 grant completed ordinals 737–749, preserving the 12 earlier unknowns; its sampled tree-RSS peak was 62,807,142,400 bytes. All 25 images, PDF identity, plan, pre-client start, producer/source and grant links were checked; all 13 completed pages also passed result, prediction and DONE bindings and registered source lineage. These 13 pages contain 3 GT tables; the 12 unknown pages contain 1. There are no remaining unexposed pages to repair or schedule in this shard. The safe next action is to retain its terminal partial and unknown evidence; the full-cohort gate remains open. No quality verdict or TEDS is asserted.

Per-page native audit: `/dev/shm/codex3-pip02-s29-original-audit-20261030/native-audit.json` SHA256 `bd5132a6b0365f4a02f6ccb7a8e3fdbe2148bd5e5c0ee39fef41ad2306b7c846`. Model-free audit ran on SMT126/127 under pair mutex, rc0, sampled peak 27,877,376 bytes.

[Committed native audits](../../artifacts/compute/results-filing-20261030-0252.json). Preserve terminal unknowns; no replacement when all pages exposed. [belief: cc]


2026-10-30 original Paddle groups74/77/80:

Each original outer job exited rc75. The last pre-end capture reports disk floor; results have no finished_at, so attribution to the outer event uses sequential capture start order and the launcher end, and is an inference. Request counts use native origin/completion times and matching start hash by the original boundary; they are not later cumulative snapshots.

| Group | Original end UTC | Last capture started UTC | Result SHA256 | RPC started / matched / unmatched | Later captures excluded |
|---|---|---|---|---|---|
| 74 | 2026-10-30T03:00:13Z | 2026-10-30T02:59:21Z | d721ee391ffe3f3014acab54d6fcc22db07a8f043812836bc45978d37834ebb8 | 65 / 65 / 0 | 1 |
| 77 | 2026-10-30T03:00:21Z | 2026-10-30T02:59:53Z | e2e9368b9d33a6ae66c8e4fda69b6020e6dc8538ee16e50e95055da099ef2861 | 65 / 65 / 0 | 1 |
| 80 | 2026-10-30T03:00:15Z | 2026-10-30T02:59:47Z | 0ab2d32b262302deac8f308bc34690e339568ec2bde9cc93c370dd8651768cb9 | 45 / 45 / 0 | 1 |

g74 final native error was `TimeoutError: deadline, admission or output limit`; g77 and g80 recorded `TimeoutError: admission`. All original captures match the 74-file prospective source registry `20b60b7ac3fb6fcd4db6d49163eea7d3158a4be0c6b4a94e04a2fab850226ebb`, protocol and recorded grant interval. Each group has zero original-capture-bound page finish receipts among its 15 pages. One g80 finish belongs to a later capture and is excluded; the finish record itself has no finish timestamp. Preserve all unknowns; no full-page completeness, TEDS, quality, adoption or full-cohort claim.

Native capture/hash/time details: `original-three-events.json`; exact page-finisher classification: `original-finish-audit.json`; source/grant audit: `source-capture-audit.json`.


[belief: cc] [Durable audit references](../../artifacts/compute/20261030-0310/results.json).


2026-10-30 original Paddle g104/g89/g95 windows:

Each original outer job exited rc75. Its last pre-end capture reports disk floor and TimeoutError: admission. Result JSON has no finished_at; association with the outer event follows sequential capture start order and launcher end and remains an inference. Request counts use native timestamps and matching start hash at the original boundary; later captures are separate.

| Group | Original end UTC | Last capture start UTC | Result SHA256 | RPC started / matched / unmatched | Later captures excluded |
|---|---|---|---|---|---|
| 104 | 2026-10-30T03:11:36Z | 2026-10-30T03:11:12Z | 53cae3967f30c2494e069052e1971319d46f75bc4d1e95577e3bf8e39a05d31f | 0 / 0 / 0 | 2 |
| 89 | 2026-10-30T03:14:44Z | 2026-10-30T03:14:20Z | 2722b981fd8f0d07157aee2c2a4ed53551d8edc3415a0167a8f4218ab68d9132 | 0 / 0 / 0 | 0 |
| 95 | 2026-10-30T03:14:45Z | 2026-10-30T03:14:21Z | c553cd3bc2681e411eb1f30f57589cbd172488d4794294bb6c9d503b453ecd55 | 0 / 0 / 0 | 0 |

All original captures match the 74-file R11 source registry `20b60b7ac3fb6fcd4db6d49163eea7d3158a4be0c6b4a94e04a2fab850226ebb`, protocol and captured grant intervals. No original-capture-bound page finish receipts exist among the 15 pages of each group. Preserve unknowns, no redraw; no page-completeness, TEDS, quality, adoption or full-cohort claim.

Native details in original-three-events.json, original-finish-audit.json and source-capture-audit.json.


[belief: cc]

[Original native audit references](../../artifacts/compute/results-filing-20261030-0320.json).


##### Original Paddle R11 partial events — 2026-10-30

Each original attempt ended rc75 after `TimeoutError: admission`; its native owner result records `disk floor`, `partial=true`, and `factory=null`. Exact event-block source and grant captures were checked against original end time. In each attempt the worker and server logs were absent, and no region start, response or source-bound page finish was attributed to that capture. These are original-event counts, not a claim about later rearmed attempts; preserve any previously exposed or unknown requests without redraw. [belief: cc]

- `codex3-pip02-paddle-relocatable-r11-g110-20261029`: capture 2026-10-30T03:16:32Z, rc=75 time=2026-10-30T03:16:56Z reason=job-rc-75:exited; attempt result SHA256 `523a35d52ff64d1c18ee6c674755dc15620fa362b5b32dfc05b2e5b6d199e208`, capture SHA256 `9621eb66d24f4b55fa67248948bf648fcc3d36c3e25e6e743448c53ec14ec327`; source pins verified (74). Original-event counts: 0 starts, 0 responses, 0 finish receipts.
- `codex3-pip02-paddle-relocatable-r11-g113-20261029`: capture 2026-10-30T03:16:33Z, rc=75 time=2026-10-30T03:16:57Z reason=job-rc-75:exited; attempt result SHA256 `199367e2d9f3cfb02b715a4573a31f706f4e2b8858f928fc175eb5f215d7e04b`, capture SHA256 `e0392410d24aafc9eb1ad8b20d7caf969ecb87cbce708083116236fef94b2099`; source pins verified (74). Original-event counts: 0 starts, 0 responses, 0 finish receipts.
- `codex3-pip02-paddle-relocatable-r11-g119-20261029`: capture 2026-10-30T03:20:29Z, rc=75 time=2026-10-30T03:20:53Z reason=job-rc-75:exited; attempt result SHA256 `1cf991c00793f5b1ea19a15f534425de1626090af1f0349efef65f14bcf32dc7`, capture SHA256 `218b14745f4e208d50c4754089571fb39d1b5180f05a99adcad93a88848c8ab5`; source pins verified (74). Original-event counts: 0 starts, 0 responses, 0 finish receipts.
- `codex3-pip02-paddle-relocatable-r11-g83-20261029`: capture 2026-10-30T03:20:21Z, rc=75 time=2026-10-30T03:20:45Z reason=job-rc-75:exited; attempt result SHA256 `cb3f16c78ceade53ef25d43c67718c2f615161fe92b9103f66616590c70ba1f4`, capture SHA256 `4fc3e86d8da150651812b2c12481c13427d25f70d626df1f7cb523072c1ebd9c`; source pins verified (74). Original-event counts: 0 starts, 0 responses, 0 finish receipts.

No quality, TEDS or adoption verdict. Full native paths, captured grants, exact boundary and file hashes: `[durable audit references](../../artifacts/compute/results-filing-20261030-0343.json)`; model-free sampled peak 18,220 KiB, cleanup verified.


##### Original Paddle R11 partial events — 2026-10-30

Both original attempts ended rc75 after `TimeoutError: admission`; their native owner results record `disk floor`, `partial=true`, and `factory=null`. Source and captured grant bindings were verified against each exact original event block and end time. Neither original attempt has worker or server logs; no region start, response, or source-bound page finish was attributed to its capture. These counts concern the original attempts only; later rearmed attempts remain separate. Preserve any previously exposed or unknown requests without redraw. [belief: cc]

- `codex3-pip02-paddle-relocatable-r11-g92-20261029`: capture 03:20:26Z; ended 03:20:50Z rc75; result SHA256 `4f91a3f47cbec9de1da3ff2c42dc71427428e5e0384e88cf04bf71a24da000f6`; capture SHA256 `5a5e3007d97408f6b52afbedea9a3299791dd837593e1e16a44f724a478ad2f6`; 74 source pins verified. Original capture: 0 starts, 0 responses, 0 finish receipts.
- `codex3-pip02-paddle-relocatable-r11-g98-20261029`: capture 03:20:28Z; ended 03:20:52Z rc75; result SHA256 `82a6fcbb7bf67752c6ef6e8607b03faeb15a09d94d8ddf47bff45c0664222e9e`; capture SHA256 `4aab48bffdd1fac6839f972f36aab1b4c17e806fb01ec0afc13d7e0475d34c74`; 74 source pins verified. Original capture: 0 starts, 0 responses, 0 finish receipts.

No TEDS, quality, adoption or full-cohort verdict. Exact native paths, grants and hashes: `[durable audit references](../../artifacts/compute/results-filing-20261030-0343.json)`. Model-free sampled peak 45,756,416 bytes; descendants drained.


##### Original Paddle R11 events — 2026-10-30 04:03 UTC

- `codex3-pip02-paddle-relocatable-r11-g125-20261029`: original event ended 04:03:27 rc75; seven attempt captures within that event, with 30 capture-bound region starts and 30 matching HTTP 200 responses before the end, zero unmatched starts at that boundary, and no timestamp-proven page finish receipt. Final native partial records disk floor. [belief: cc]
- `codex3-pip02-paddle-relocatable-r11-g86-20261029`: original event ended 04:03:26 rc75; seven attempt captures within that event, with 30 capture-bound region starts and 30 matching HTTP 200 responses before the end, zero unmatched starts at that boundary, and no timestamp-proven page finish receipt. Final native partial records disk floor. [belief: cc]

Each original event was isolated by its exact start/end log block and attempt capture hashes; request/response body and lineage hashes and source pins were checked, and any later rearm was excluded. These are region-request counts, not complete-page, whole-cohort, TEDS or adoption results. Preserve all original requests and any unknowns without redraw. Full native paths and hashes: [durable original audit references](../../artifacts/compute/results-filing-20261030-0415.json); sampled guard peak 36,240 KiB, cleanup verified.

Prospective R13 source projection is published in research commit569b3b6336f0: exact source registry, nine permitted producer IDs and their27 exact shard bindings, all existing native request/grant/finish checks retained. Fifteen actual tests pass, including rejection of old R4 origins missing their original warrant fields. No scoring formula, population, denominator or grade changed; no missing historical warrant was backfilled. [belief: cc]


##### 2026-10-30 overdue original-event filing (HIL, Paddle R14, FA4 and DCA)

Correction to the earlier R14 admission inference: R14 did receive actual CPU grants; a manifest output estimate alone does not establish admission refusal. Original events for pool0, pool2, pool1 and pool3 each contain native `TimeoutError: admission`, `reason: disk floor`, `factory: null` partial records and zero capture-bound region starts or finishes. Pool1 and pool3 each have two separately recorded original events. Later attempts, including native compute, are separate. No per-grant credit sample or cohort-quality conclusion is established. Original filing deadlines had elapsed before this audit. [Native event audit](../../artifacts/compute/results-filing-20261030-0520.json). [belief: cc]


2026-10-30 05:26Z operator quarter rebalance: withdrew seven captured own ungranted PIP pollers and verified all dead, preserving native outputs and source. Actual remaining waiting registrations are q0=0, q1=0, q2=2 and q3=2. Retained pool0/pool2 on q2 and pool1/head on q3; own armed manifests and staged row artifacts now name those exact regions with unchanged verified launcher hashes. No scheduler queue, grant, or canonical FILLERS edits. A separately declared pool3 successor is being prepared to replace the head registration within the same two-item q3 cap; it is not yet smoke-qualified or published. [Placement receipts](../../artifacts/compute/pip02-quarter-rebalance-20261030-0523.json). [belief: cc]


2026-10-30 05:33Z: research source projection `55e24b6fd2dc` pushed and verified for exactly four R15 producer IDs, all 49 declared groups and their 146 shards, including the two-shard tail. Parent supervised 18 tests passed, including incorrect pool/group/source/grant refusal and legacy missing-warrant refusal; sampled peak260012KiB and cleanup verified. Scoring, fixed population/denominators and grade rules are unchanged. [belief: cc]

Fresh five-second quarter verification found q0/q1 waiting0/0 and q2/q3 waiting2/2 with exact actual48–71/72–95 arguments and zero active PIP grants. Mean CPU utilization including SMT siblings was2.13%,4.69%,3.80%,3.47%; queue placement does not establish useful inference progress. None of60 previously retired IDs reappeared. Full snapshot is bound by the placement artifact's durable reference. [belief: cc]


##### 2026-10-30 06:05 original EVL, Paddle and YaRN resource events

- Paddle R15 pool1 original grant ended 05:53:51Z rc75. Its `[8,9,10]` native attempt recorded `TimeoutError: admission`, `reason=disk floor`, `factory=null`; no region starts were bound to that attempt's capture hash. Prior group evidence and later rearm events are distinct. No whole-cohort quality verdict. [Native event audit](../../artifacts/compute/results-filing-20261030-0605.json).
  - [belief: cc] Original native records and unchanged criteria are linked above.


PIP split-storage R22 published all four disjoint logical pools: pool0/pool2 targetq2 and pool1/pool3 targetq3, maximum two queued offers per quarter. One identical-outer61.026s native control produced five matched HTTP responses with durable result markers,5.508GB sampled RSS, rc75/partial and verified descendant drain. Sampled native Micron growth442368bytes and RAID metadata12288bytes; each declared per-grant budget remains1GiB Micron and0.125GiB RAID above independent150GiB floors. The exact original read-only measurement recipe uses the source-pinned v9 binary10125, explicitly distinguished from production-store v10 version10303. Original checkpoint bytes and unknowns remain retained; missing lock metadata was initialized with same-inode flock and directory fsync. Individual publications followed natural old-producer boundaries, with no aggregate-capacity publication gate. The49 original group starts cover730 pages; the25-page head is separate, and this is not a whole-cohort completion or TEDS verdict. [Publication/native proof references](../../artifacts/compute/results-filing-20261030-0605.json). [belief: cc]


Runtime cleanup: the full2a172b09 phase-C linked checkout was removed through the gate. Its required source files remain byte-identical and at the same inodes in a small compatibility directory; R22/R24 full source checks passed after removal, without modifying their manifests or historical launchers. The exact commit capsule and490-launcher restore index are retained under `/mnt/micron/codex3-pip02-phasec-capsule-20261030`. Reusable analysis edits now use `/mnt/micron/codex3-lanes/research`; the old temporary research tree was removed after its wrapper was migrated and both CLI help checks passed. This is operational custody, not a new cohort-quality or lineage verdict. [no-belief: checkout cleanup]

**2026-10-30 Codex3 R25 relocatable cutover:** pools 0 and 3 were published after a final same-entry control: five matched HTTP200 responses, no unmatched RPCs, rc75 partial and verified drain. They request `any-cpu-quarter`; fixed-quarter R24 predecessors were archived before native exposure. R25 pools 1 and 2 remain prepared behind live R22 predecessors; their zero-token watcher refuses cutover while the owner keeper can rearm those predecessors. The R26 head successor retains all 25 pages through group starts 0 and 3, verifies 49 historical response bindings and preserves unknown starts; its final control has five matched durable responses and verified drain. See [publication audit](../../artifacts/compute/codex3-publications-20261030-1415.json). These are preparation results; quality grading still requires explicit source registration and complete native coverage. The legacy PIP binary remains version10125, distinct from production10303. [no-belief: bounded admission and source-custody checkpoint]

**2026-10-30 final T1 successors:** PIP R27 pools 0, 3, and head have final relocatable packets. Pool1/pool2 registrations remain unchanged behind live R22 predecessors; successor rows stay held by the owner watcher until those predecessors are retired. No pool1/pool2 cutover or quality result is claimed. The NEMO C3 and KPF item-4 r2 entries are model-free build packets only; each still requires the full linked build and its declared help/linkage/knob checks. At the 15:54:53Z keeper snapshot, candidate rows were READY-WAIT for lack of a free CPU quarter. [T1 successor ledger](../../artifacts/compute/codex3-t1-successors-20261030.json). [no-belief: packet preparation and admission only]

##### PIP-02 running English shard TEDS — 2026-10-30
  - *(2026-10-31, R28 pool3 READY preparation.)* The unarmed own R27 pool3 was withdrawn for the stale R25 identity guard. R28 retains original groups and checkpoints; isolated real-model smoke yielded five durable HTTP 200s, intentional rc75 partial and drained; active STOP likewise rc75 and drained; 22 control-source files match original. Real normal-grant entry is untested; no original cohort coverage or quality verdict. [Evidence](../../artifacts/codex3-pip-r28-pool3-ready-20261031/SHA256SUMS). [belief: cc]
  - *(2026-10-31, R28 head and pool0 READY preparation.)* Final launchers each completed isolated R11 real-model smoke with five durable HTTP 200s and intentional rc75 partial; active STOP rc75 drained, source parity verified. Original full groups, checkpoints and exposed unknowns retained. Full normal real-grant entry remains untested; isolated controls add no 755-page cohort coverage or quality claim. R27 failures remain filed. [Evidence](../../artifacts/codex3-pip-r28-ready-20261031/SHA256SUMS). [belief: cc]
  - *(2026-10-31, Paddle R27 head and pool0.)* **FAILED-RUN `codex3-pip02-paddle-relocatable-r27-head-20261030`** and **FAILED-RUN `codex3-pip02-paddle-relocatable-r27-pool0-20261030`**, class=harness, both outer rc1 before page processing: the head pool identity guard hardcoded R26 and pool0 hardcoded R25 while the actual grants were R27. These are harness failures; neither is a page or quality verdict. Preserve prior outputs, exposed unknowns, original group lists and checkpoints; successor must use a fresh identity and validate real launcher normal/STOP/drain. No full 755-page verdict. [belief: cc]

Same Phase C native scorer and ground truth, locked fresh English cohort `pip02-english-fresh-20261029` (755 pages/243 GT tables). Both metrics are table-weighted means; higher is better. These are descriptive partial-cohort scores; full-cohort and paired parser-selection gates remain open. Complete pages with no GT table do not enter the table mean. Missing/error pages remain visible in coverage and are not silently counted as successful pages.

| Arm / shard | Complete pages | GT tables scored / planned | Table TEDS ↑ | Structure-only TEDS ↑ |
|---|---:|---:|---:|---:|
| ODL+Docling hybrid fresh s05 | 25/25 | 8/8 | 0.554871 | 0.640090 |
| ODL+Docling hybrid fresh s08 | 25/25 | 10/10 | 0.733307 | 0.815572 |
| ODL+Docling hybrid fresh s09 | 25/25 | 7/7 | 0.842202 | 0.916755 |
| ODL+Docling hybrid fresh s16 | 25/25 | 7/7 | 0.243788 | 0.562940 |
| ODL+Docling hybrid fresh s17 | 25/25 | 1/1 | 0.951119 | 1.000000 |
| ODL+Docling hybrid fresh s20 | 25/25 | 47/47 | 0.137642 | 0.290202 |
| ODL+Docling hybrid fresh s21 | 25/25 | 8/8 | 0.078004 | 0.116914 |
| ODL+Docling hybrid fresh s24 | 25/25 | 5/5 | 0.518804 | 0.538788 |
| ODL+Docling hybrid fresh s25 | 25/25 | 0/0 | — | — |
| ODL+Docling hybrid fresh s28 | 4/25 | 0/0 | — | — |
| ODL+Docling hybrid fresh s29 | 13/25 | 3/4 | 0.312108 | 0.333333 |

Native complete-page records passed prediction/output, original source/protocol/dependency/input and frozen plan bindings. PlanSHA `63028e74950ba7250f33cbce13f4f0bdd165bba2a075242db4475c26f645ed68`; GTSHA `a45cd84b04ad8b793e775089640e6b681209abea33ead54c1828ddca35fae496`; scorerSHA `27f0b630b6812aecad35d1c65329841a5011e421326e81f9f14c8c66a6fdbe5e`; pinmanifest `262462c58402db48aa88063cdb1817915dcdef0c1933e72869682dd905c34cf0`. English inputs, native matched GT/prediction indices and every per-table score are committed in [s20](../../artifacts/compute/pip02-shard-teds-20261030/odl-s20.json) and [s21](../../artifacts/compute/pip02-shard-teds-20261030/odl-s21.json). An independent repeat under the correct original26-27 mutex on admitted SMT122/123 reproduced both files byte-for-byte;17.466s, sampled503,226,368 bytes and descendants drained. [belief: cc]

- [x] **PIP-02 incremental score filing: ODL s20/s21.** Both verified25-page shards scored with the unchanged Phase C English scorer/GT and filed above; this closes only their incremental score reporting. ✅ 2026-10-30 [belief: cc]
- **[declined: ws58 2026-11-03 content-review: merged into the Phase C run as its reporting rule]** Continue this table for every verified completed ODL/Paddle shard as it finishes, with epoch/source and coverage preserved. Do not wait for the755-page full-cohort gate.

Incremental scoring also verified completed s05/s08/s09 (originalR2 source) and s24/s25 (originalR4 source `af6262aaf380b3a69031fc5b7f5b11ec0f8b697f314c410c159568bccf4cc62a`), with the same scorer/GT. Their per-table records are committed in the same artifact directory; s25 has no GT table and therefore no table mean. The first seven filed rows cover175complete pages/85GTtables, as a descriptive partial cohort only. [belief: cc]


###### Paddle English scores by original finish epoch

At the 2026-10-31 05:45 post-freeze replay, the deduplicated Paddle union is **359 unique verified pages / 84 GT tables**, TEDS **0.9284350145629875** and structure-only **0.9581974688886165**. This adds 15 pages and two tables to the filed 344/82 snapshot; original strict receipts, GT and old paths remain intact. Pages 0 and 34 were prospectively reassembled from 15 and 13 authenticated original region responses: a new START preceded no-network/no-model recovery, which reproduced each original markdown byte-for-byte and created a new finish; no historical finishing receipt or process identity is inferred. The other 13 newly eligible pages are original native results. Both new strict native_rows score receipts replay with the same GT. The full 755-page and paired gates remain open. [Recovery, score receipts and union](../../artifacts/compute/codex3-pip-head-recovery-20261031/). [belief: cc]

At the 2026-10-31 04:56 post-freeze replay, the strict deduplicated Paddle union contains **344 unique verified pages / 82 GT tables**, up 10 zero-GT pages from the previously filed 334/82. TEDS is **0.9274766122818409**, structure-only **0.9571778949590706** (unchanged because the additional pages have no GT tables). The original per-epoch rows below retain their planned denominators and historical snapshots. The full 755-page and paired-parser gates remain open. Final-source scoring and receipt replay use research commits `4fd00eb02d4a034bc37006e58c8dde84e657c38f` and `d2b95912cedd` at the immutable deployment; [post-freeze union, table and receipts](../../artifacts/compute/codex3-pip-r29-score-20261031/) retain original capture bindings. At 05:00:53 UTC the dedicated host watcher was active under its bounded systemd unit with writer lock, expiring by timer at 2026-11-01 04:59:08 UTC; this is a dated service observation, not a promise of continuing liveness. [belief: cc]

The 2026-10-30 full151-shard snapshot had251 verified complete pages and78 scored GT tables. At that snapshot the other504 pages were476 unknown,20 errors and8 with request origins but no verified finishing-capture binding. All755 original page IDs and243 planned GT tables remain represented. Per-epoch rows below are components of fixed shards: their repeated planned denominators must not be summed. A case is deduplicated only when original prediction/finish hashes and native table values match; conflicting complete snapshots refuse, and later partials cannot erase an earlier complete observation.

| Paddle shard | Finish epoch | Verified pages / planned | GT tables scored / planned | TEDS | Structure-only TEDS | Case artifact |
|---|---|---:|---:|---:|---:|---|
| s000 | headrec | 1/5 | 0/2 | — | — | [new recovery score](../../artifacts/compute/codex3-pip-head-recovery-20261031/s000.json) |
| s000 | r28 | 4/5 | 2/2 | 0.967730 | 1.000000 | [strict score](../../artifacts/compute/codex3-pip-head-recovery-20261031/s000.json) |
| s002 | headrec | 1/5 | 0/0 | — | — | [new recovery score](../../artifacts/compute/codex3-pip-head-recovery-20261031/s002.json) |
| s002 | r28 | 4/5 | 0/0 | — | — | [strict score](../../artifacts/compute/codex3-pip-head-recovery-20261031/s002.json) |
| s004 | r29 | 5/5 | 0/0 | — | — | [epoch reference](../../artifacts/compute/codex3-pip-head-recovery-20261031/paddle-running-table.md) |
| s001 | r28 | 5/5 | 0/0 | — | — | [final-source case data](../../artifacts/compute/codex3-pip-r29-score-20261031/s001.json) |
| s003 | r29 | 5/5 | 0/0 | — | — | [epoch reference and running table](../../artifacts/compute/codex3-pip-r29-score-20261031/d2-paddle-running-table.md) |
| s008 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s008.json) |
| s009 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s009.json) |
| s010 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s010.json) |
| s011 | r22 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s011.json) |
| s012 | r22 | 4/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s012.json) |
| s013 | r22 | 1/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s013.json) |
| s014 | r11 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s014.json) |
| s015 | r11 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s015.json) |
| s016 | r11 | 3/5 | 0/1 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s016.json) |
| s020 | r22 | 3/5 | 3/5 | 0.959600 | 0.979550 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s020.json) |
| s021 | r22 | 5/5 | 5/5 | 0.966403 | 0.995597 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s021.json) |
| s022 | r22 | 2/5 | 3/6 | 0.946595 | 0.973352 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s022.json) |
| s023 | r22 | 5/5 | 5/5 | 0.969951 | 0.986704 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s023.json) |
| s024 | r22 | 5/5 | 6/6 | 0.985741 | 0.999556 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s024.json) |
| s025 | r22 | 4/5 | 5/5 | 0.900181 | 0.952941 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s025.json) |
| s026 | r14 | 3/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s026.json) |
| s026 | r22 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s026.json) |
| s027 | r14 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s027.json) |
| s027 | r22 | 3/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s027.json) |
| s028 | r14 | 2/5 | 0/3 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s028.json) |
| s028 | r22 | 3/5 | 3/3 | 0.990874 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s028.json) |
| s032 | r22 | 5/5 | 3/3 | 0.417395 | 0.424469 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s032.json) |
| s033 | r22 | 3/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s033.json) |
| s034 | r22 | 3/5 | 0/5 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s034.json) |
| s035 | r22 | 5/5 | 4/4 | 0.909152 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s035.json) |
| s036 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s036.json) |
| s037 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s037.json) |
| s038 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s038.json) |
| s039 | r22 | 1/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s039.json) |
| s040 | r22 | 4/5 | 2/2 | 0.900544 | 0.925306 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s040.json) |
| s047 | r22 | 5/5 | 1/1 | 0.997619 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s047.json) |
| s048 | r22 | 3/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s048.json) |
| s049 | r22 | 2/5 | 1/3 | 0.997727 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s049.json) |
| s050 | r22 | 3/5 | 6/7 | 0.950152 | 0.985481 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s050.json) |
| s051 | r22 | 5/5 | 7/7 | 0.948362 | 0.957008 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s051.json) |
| s052 | r22 | 3/5 | 4/6 | 0.997927 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s052.json) |
| s056 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s056.json) |
| s057 | r22 | 5/5 | 1/1 | 1.000000 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s057.json) |
| s058 | r22 | 5/5 | 3/3 | 0.938161 | 0.950000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s058.json) |
| s059 | r22 | 5/5 | 4/4 | 0.964214 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s059.json) |
| s060 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s060.json) |
| s061 | r22 | 5/5 | 1/1 | 1.000000 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s061.json) |
| s064 | r11 | 3/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s064.json) |
| s077 | r11 | 1/5 | 2/3 | 0.969781 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s077.json) |
| s080 | r22 | 4/5 | 2/2 | 0.667766 | 0.740260 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s080.json) |
| s081 | r11 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s081.json) |
| s081 | r22 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s081.json) |
| s082 | r11 | 1/5 | 1/3 | 0.851760 | 0.933333 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s082.json) |
| s082 | r22 | 3/5 | 1/3 | 0.909740 | 0.956522 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s082.json) |
| s083 | r22 | 5/5 | 2/2 | 0.931377 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s083.json) |
| s084 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s084.json) |
| s085 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s085.json) |
| s086 | r11 | 4/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s086.json) |
| s087 | r11 | 4/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s087.json) |
| s088 | r11 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s088.json) |
| s092 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s092.json) |
| s093 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s093.json) |
| s094 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s094.json) |
| s095 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s095.json) |
| s096 | r22 | 5/5 | 1/1 | 0.952341 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s096.json) |
| s097 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s097.json) |
| s098 | r11 | 3/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s098.json) |
| s099 | r11 | 2/5 | 2/2 | 0.935813 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s099.json) |
| s100 | r11 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s100.json) |
| s105 | r22 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s105.json) |
| s108 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s108.json) |
| s109 | r22 | 1/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s109.json) |
| s119 | r11 | 1/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s119.json) |
| s119 | r22 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s119.json) |
| s120 | r11 | 1/5 | 0/1 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s120.json) |
| s120 | r22 | 1/5 | 0/1 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s120.json) |
| s121 | r11 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s121.json) |
| s121 | r22 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s121.json) |
| s126 | r11 | 1/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s126.json) |

Descriptive English fresh cohort snapshots, table weighted, higher better; denominators repeat where a shard spans epochs and must not be summed. Native request origins may span earlier epochs and are preserved per case. Each case is counted once; matching completed snapshots deduplicate by prediction, finisher and table values, while conflicting completions are refused. Current non-complete cases and every historical non-complete event are retained in [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-running-refusals.json); no paired or full-population claim.


The native Phase C TEDS scorer, GT, table matcher and English cohort remain unchanged. Research main `243067bed40d0ed5e08827ed4c7c760a0250b196` adds only strict original capture/finish joins across RAID/R14/R22/R25/R26/R27 layers;18 lineage controls and actual mixed-epoch cases passed. Missing original R4 warrant and orphan/native-finish failures remain refused, not repaired by guessing. These partial descriptive observations do not establish a full755-page quality gate or paired parser winner. [Full151-shard inventory](../../artifacts/compute/pip02-shard-teds-20261030/inventory-1840.json). [belief: cc]

Both source-bound, bounded scoring watchers are active: ODL PID2373051 and Paddle PID2341453 at this checkpoint. They score newly finished shards through the same native scorer/GT, with the standing R6 mutex, admission, memory and wall limits. The original case snapshots and all earlier unknown/error events remain in the declared KEEP root. Future outputs still need incremental filing here; the full cohort is not a filing prerequisite.


##### 2026-10-30 incremental scorer and watcher checkpoint

The incremental writer and strict projection are landed in root 55bbca49e9e8b87e8d020f52b3e655336da5ee7c; research source 6d2ab2803c6cc742a102ed18021247427d6b7be4 supplies the writer. Immutable begin/end inputs and selected native warrants are bound by hashes, including image warrant and original request/finish lineage. The real Paddle r3 receipt at /mnt/raid0/llm/tmp/pip02-vidya-draft/actual-paddle-s21-r3/s021.score-receipt.json (SHA-256 dd41924d02e279cb76eae7c56fc388bf1818199d543de2015bbe2eb5884c599d) covers five pages and five tables, table-weighted TEDS 0.9664026497276218 and structure-only 0.9955969634230504; runtime was 14.6s and peak RSS 573 MB. It is a model-scoped Paddle observation, not a full-cohort result.

Across 20 native ODL DONE batches, 9 are strict-eligible. Eleven batches (255 pages) lack original producer_source_manifest_path/id; retain these as separately audited UNVERIFIED ordinary native TEDS rows, never project or include them in strict totals. Receipts without model-scope identity remain explicitly UNPROJECTED; raw ODL TEDS remains valid. Do not invent weight identity or add a pipeline filter. Shard widths are not matched-arm comparisons: ODL r25 uses 25-page s20/s21 shards at positions 500–524 and 525–549, while Paddle uses a five-page s21 shard at positions 105–109. Same shard number does not identify the same cohort slice. The approved eligible Paddle model-scoped planning-context canary passed. Both scoring watchers have since finished; outputs added after watcher repair need a fresh canary before extending the wired/complete claim. The v2 epoch-watcher checkpoint and restart/runtime set are preserved at [epochwatch-v2](../../artifacts/compute/pip02-shard-teds-20261030/epochwatch-v2/): it records the 20 ODL completed batches, 11 separately unverified 255-page snapshots, five partial Paddle snapshots, and replacement watcher births/PIDs. At 20:35Z, ODL PID 790668 (birth 151477532) and Paddle PID 793354 (birth 151478825) were verified active. Five new Paddle epoch generations had been processed; none created a newly eligible completed shard, and unchanged inputs are not replayed. This is an as-of checkpoint, not a future liveness promise. Preserve immutable partial snapshots and the running/refusal history. The full 755-page quality gate remains open.

##### Completed ODL shards with unverified producer provenance

The exact 11-row, 255-page UNVERIFIED inventory follows; all native page inputs, plan/GT/images/predictions, start/DONE custody, and native weighted means were rechecked, but the missing original source binds keep these records outside the strict-source-verified aggregate. Zero-GT-table rows have undefined means. [Inventory JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-completed-inventory-20261030.json) · [source-custody audit v2](../../artifacts/compute/pip02-shard-teds-20261030/odl-new-shards-strict-audit-20261030-v2.json)

| ODL shard | Native pages | GT tables | TEDS | Structure-only TEDS | Producer provenance | Native score artifact / SHA-256 |
|---|---:|---:|---:|---:|---|---|
| s03 | 25/25 | 7/7 | 0.544025 | 0.760523 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s03.json) / 146684bb1e3f918289d7aa64cd54545dc553762644ffff3092bd00665653c8dc |
| s06 | 25/25 | 10/10 | 0.853327 | 0.888682 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s06.json) / b30075d67bad6cd5384a80014d5d93ab7452f8ac5415ccb6754f10e71185f66b |
| s07 | 25/25 | 4/4 | 0.863587 | 0.965278 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s07.json) / 1747fc697d5db7a3ac431b6fab3adde34d5d757c6dca6b09977f5a007734db57 |
| s10 | 25/25 | 36/36 | 0.603236 | 0.767011 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s10.json) / e2ea4cf3510782cecff325d1e5c3fa6cce8ee00fbbbc0382ddbb392d197369fc |
| s13 | 25/25 | 5/5 | 0.591423 | 0.701263 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s13.json) / 841f3dd5e4ad32433321a59c218245099f71faacc38902a0cb2f65a5a41bf787 |
| s18 | 25/25 | 0/0 | — | — | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s18.json) / b96643f7b2be90c0b0641ea4240b95b29b0316bb472ca3e56593b95a33c3b895 |
| s19 | 25/25 | 3/3 | 0.387989 | 0.666667 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s19.json) / 9c82822b495150764eb744cdfed5d5cf97bb222819a361bf0df8e19e534ca070 |
| s23 | 25/25 | 0/0 | — | — | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s23.json) / 383e7b5253305984c313471c5237612e28707b4896ae81b3ededc8a030cd9b7b |
| s26 | 25/25 | 0/0 | — | — | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s26.json) / 74f769136b621bedf69879a30eca71456bbda0cca5e1fc6c166950218a4c1505 |
| s27 | 25/25 | 5/5 | 0.795710 | 0.964456 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s27.json) / 713d9df128fac71ac85580b2e177d0615b658809feee19bdb43dc80333c2f129 |
| s30 | 5/5 | 0/0 | — | — | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s30.json) / ffb4a78e49901bfd8ce56c60d17fb74b3a9c858eded1a992fd08292bcadc52a2 |

##### 2026-10-30 22:18 incremental Paddle filing

Four more completed English Paddle shards have been scored with the unchanged Phase C scorer, GT and matcher. Each has five verified pages and zero GT tables, so both TEDS means are undefined rather than zero or a passing score. Deduplicated verified coverage is now **271 pages and 78 GT tables**, up20 pages from251; repeated native epochs are never summed. Higher TEDS remains better where defined. The755-page and paired-parser quality gates remain open. [Running table](../../artifacts/compute/pip02-shard-teds-20261030/epochwatch-v2/paddle-running-table.md), [refusal history](../../artifacts/compute/pip02-shard-teds-20261030/epochwatch-v2/paddle-running-refusals.json), [hash-checked transfer audit](../../artifacts/compute/pip02-shard-teds-20261030/TRANSFER-AUDIT-2218.json). [belief: cc]

| Paddle shard | Verified pages | GT tables | TEDS | Structure-only TEDS | Native score artifact |
|---|---:|---:|---:|---:|---|
| s104 | 5/5 | 0/0 | — | — | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s104/e76b365d2845b1cf299fe7dbc17a0212ab5014722084ccc1d5ce21b692b0f8ee/s104.json) |
| s131 | 5/5 | 0/0 | — | — | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s131/769b96c0920aa2e2860c79006548fdb85e9c9ea6f71cdccacccf3b1de7a2625c/s131.json) |
| s132 | 5/5 | 0/0 | — | — | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s132/174cbd8d3c96ebc3d1153df28796a35b0ee8140a8688846fb25eb3b34be70e4a/s132.json) |
| s133 | 5/5 | 0/0 | — | — | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s133/58ff5bb791fbb48b33fdccd4a9e52ea6c978c855a5123543df00542c64234c74/s133.json) |


##### 2026-10-30 23:26 incremental Paddle filing

Five newly completed shard generations add **23 unique verified pages and 4 GT tables** to the prior 271/78: **294 pages and 82 GT tables**. s105 replaces its prior two verified pages, adding three; the other four add five each. Counts use unique positions and completed native status, never summed epoch planned denominators. Zero GT means undefined. The 755-page and paired-parser gates stay open; the 11 ODL unverified batches remain ordinary results outside strict totals. [Current running table](../../artifacts/compute/pip02-shard-teds-20261030/epochwatch-v3/paddle-running-table.md), [refusals](../../artifacts/compute/pip02-shard-teds-20261030/epochwatch-v3/paddle-running-refusals.json), [verified transfer hashes](../../artifacts/compute/codex3-speech-v2-transfer-20261030.json). [belief: cc]

| Shard | Verified pages | GT tables | TEDS | Structure TEDS | Native score |
|---|---:|---:|---:|---:|---|
| s044 | 5/5 | 1 | 1.000000 | 1.000000 | [case](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s044/df426e627327e1f3d1fb4b2f92416b3e5b7cecfb565eaa6dc9b3aeed65e47d13/s044.json) |
| s045 | 5/5 | 3 | 0.951240 | 1.000000 | [case](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s045/fe4cf9daf2cf012dfb5d55b8c992c82e85d8c053b370064379bbf1b90558ebf1/s045.json) |
| s046 | 5/5 | 0 | — | — | [case](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s046/d42d08f38d8573fd248239bab7a7dd28cd5ea7b8440212f683295f6edbb1988c/s046.json) |
| s105 | 5/5 | 0 | — | — | [case](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s105/f8c50b4963e8367751cab661018557839054d926a5df0a21808208a4828ef792/s105.json) |
| s106 | 5/5 | 0 | — | — | [case](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s106/d12a280efc1778d807567d40e9cc574ff28979e25b3f9c1026e61d5c51fdbf63/s106.json) |


- [x] **PIP02-INCREMENTAL-FILING-20261031-0105** — original Phase C English scorer/GT and existing strict receipt reader verified newly completed Paddle r22 shards s116, s117 and s118 (5/5 pages each, zero GT tables each). Current selected generations cover **309 unique completed pages / 82 GT tables**, up from 294/82; no repeated epoch denominator is summed. Zero-table shards have no TEDS or structure-only mean; the existing 82-table means are unchanged. [Running table](../../artifacts/compute/codex3-ready-checkpoint-20261031-0105/pip/paddle-running-table.md) and [native-receipt delta](../../artifacts/compute/codex3-ready-checkpoint-20261031-0105/pip/DELTA.json) preserve prior refusal/generation history. Full 755-page and paired-parser gates remain open. ✅ 2026-10-31 [belief: cc]

##### 2026-10-31 incremental Paddle filing (scores through 03:19 UTC)

Five additional selected Paddle r22 generations cover **334 unique completed pages and 82 GT tables** (previously 309/82). The 82-table weighted TEDS is **0.927477**, structure-only **0.957178**; higher is better. Each new shard has zero GT tables and undefined TEDS means, so neither aggregate mean changed. Strict receipt replay checks the original inputs, source and result hashes; the same English GT and scorer pins apply. The 11 ODL batches with unknown original producer provenance remain outside strict-source totals; no new ODL completion or full paired gate is asserted. [Delta audit](../../artifacts/compute/codex3-pip-incremental-20261031-0345/DELTA.json) · [running table](../../artifacts/compute/codex3-pip-incremental-20261031-0345/paddle-running-table.md) · [refusals](../../artifacts/compute/codex3-pip-incremental-20261031-0345/paddle-running-refusals.json). [belief: cc]

| Shard | Pages | GT tables | TEDS | Structure TEDS | Case / receipt |
|---|---:|---:|---:|---:|---|
| s128 | 5/5 | 0/0 | — | — | [case](../../artifacts/compute/codex3-pip-incremental-20261031-0345/paddle-watch/epochs/s128/0b63474b8e91a70781f6c7b6ead76fe42a6ab7480578da468106c9f2b0723dc3/s128.json) · [receipt](../../artifacts/compute/codex3-pip-incremental-20261031-0345/paddle-watch/epochs/s128/0b63474b8e91a70781f6c7b6ead76fe42a6ab7480578da468106c9f2b0723dc3/s128.score-receipt.json) |
| s130 | 5/5 | 0/0 | — | — | [case](../../artifacts/compute/codex3-pip-incremental-20261031-0345/paddle-watch/epochs/s130/851b90b99a7e6d849fda97662397c4d307294338e690a6b4cb2e73d8f2be6a60/s130.json) · [receipt](../../artifacts/compute/codex3-pip-incremental-20261031-0345/paddle-watch/epochs/s130/851b90b99a7e6d849fda97662397c4d307294338e690a6b4cb2e73d8f2be6a60/s130.score-receipt.json) |
| s143 | 5/5 | 0/0 | — | — | [case](../../artifacts/compute/codex3-pip-incremental-20261031-0345/paddle-watch/epochs/s143/6ed3fc9b9f4bccfb3bafc6b4cf1e864943d9b6d84cfe57326556777fbea1703c/s143.json) · [receipt](../../artifacts/compute/codex3-pip-incremental-20261031-0345/paddle-watch/epochs/s143/6ed3fc9b9f4bccfb3bafc6b4cf1e864943d9b6d84cfe57326556777fbea1703c/s143.score-receipt.json) |
| s144 | 5/5 | 0/0 | — | — | [case](../../artifacts/compute/codex3-pip-incremental-20261031-0345/paddle-watch/epochs/s144/21b45800060df9ef39c71fe2b52b485742591b4299ccad57f38bb162e77d5262/s144.json) · [receipt](../../artifacts/compute/codex3-pip-incremental-20261031-0345/paddle-watch/epochs/s144/21b45800060df9ef39c71fe2b52b485742591b4299ccad57f38bb162e77d5262/s144.score-receipt.json) |
| s145 | 5/5 | 0/0 | — | — | [case](../../artifacts/compute/codex3-pip-incremental-20261031-0345/paddle-watch/epochs/s145/e6625ef313777d015d50ba2d64bf38727db8cd361b395433d5683c1bacbac8a2/s145.json) · [receipt](../../artifacts/compute/codex3-pip-incremental-20261031-0345/paddle-watch/epochs/s145/e6625ef313777d015d50ba2d64bf38727db8cd361b395433d5683c1bacbac8a2/s145.score-receipt.json) |

##### 2026-10-31 R28 head attempt: incomplete

- **FAILED-RUN, class harness:** `codex3-pip02-paddle-relocatable-r28-head-20261031` ended pool rc78. The recorded pool reports group 0 rc0 and group 3 rc78. The layered page journal records 15 complete pages and 10 unknown pages (indices 39–48); all ten have page-start and layout records. Pages 39, 40, 44, 46 and 48 each have one region start, durable result and sent marker; the other five have no region starts. An exploratory region classifier reports pending, not proven terminal exhaustion; preserve and replay durable results rather than redraw them. In the retained group 3 attempt, the native Paddle worker segfaulted during PIR dialect registration (`worker_rc=-11`); its owner returned rc75 with null error/reason, and the pool ultimately reported rc78. The underlying cause of the native crash is not established. Owner action: investigate the native crash and correct failure propagation and terminal-state handling while preserving the page and region journal and unresolved exposures; do not redraw unknown work. The head cohort has no complete quality verdict and the full 755-page and paired gates remain open. [Bounded records](../../artifacts/compute/codex3-paw-pip-filing-20261031-0415/) retain the crash, pool events, source pins and journal snapshot. [belief: cc]

##### R29 continuation checkpoint — 2026-10-31

R28's rc78 and Paddle worker SIGSEGV remain filed at `626c03b306f3c9b7b17ea6269b4adb20cdd23c83`. Its head inventory has 15 structurally complete native journals and 10 unfinished page journals with saved layouts. Five of the unfinished pages contain one original started region apiece, each backed by its original capture, pinned source, request digest, durable HTTP 200 response and matching response digest. A native transport replay with R29 source pins returned all five cached responses byte-for-byte while a fail-on-network transport observed zero new requests. The other region ordinals have no start record; all ten pages remain pending under the native region classifier. Two of the 15 completed journals lack a strict finish/capture proof in the selected corpus; their historical custody remains unknown and they are not rerun. [belief: cc]

The earlier `HEAD-CENSORED-DIAGNOSTIC.json` is retained as a dated pre-clarification snapshot. Its page-wide prohibition is superseded by the clarified original checkpoint rule: unknown exposed region attempts are never redrawn, while never-started regions on partially completed pages may continue. R29 recomputes layout as a real stage and requires saved pixel and geometry identity before model requests; it replays matching cached region responses and refuses unmatched starts, request/provenance drift or layout mismatch. It serializes page work to avoid concurrent Paddle predictor initialization and propagates unexpected native worker failures instead of treating them as partial. No OCR model, crop or threshold was changed. [belief: cc]

Published READY `codex3-pip02-paddle-relocatable-r29-head-20261031`, publication-time manifest SHA-256 `49b25a1932872e8ad0fa125d3e7de4b97246b2b33bebd6e222d11f857f9ba3b1`, exact launcher `dbe28a4f43d0890a14a80037a80ebc2b52d49ab8ac3fee13b960f62e1b20fbbd`. Its same-launcher isolated real-model normal control produced five verified durable HTTP 200 responses with one worker in 65.91 s, sampled tree RSS 4.941 GB; an active STOP control returned rc75 and drained in 40.95 s. Both used public control pages; neither measures original cohort quality, and the normal calendar-grant branch was untested at this control. HEAD-DONE and any full 755-page quality verdict remain unclaimed. Bounded source, receipts and audit evidence: `artifacts/codex3-pip-head-r29-continuation-20261031/` (publisher copies the prepared capsule). [belief: cc]

At 04:24:42 UTC the keeper started the actual CPU grant; at the 04:36 filing snapshot the launcher had emitted partial attempts and no completion was asserted. The armed manifest SHA-256 was `7c8e5ebf1facc1b1fe6ee31bc6029c13dd1047b7121791587090ac5687e8f28c`; the original publication hash above describes the earlier state. [belief: cc]

##### 2026-10-31 01:28 R22 pool2 later terminal event

**FAILED-RUN, class unknown:** the distinct later `codex3-pip02-paddle-relocatable-r22-pool2-20261030` event ended rc78 at 01:28:55 UTC. The existing FILED receipt describes the separate 2026-10-30 06:17 rc75 event and is preserved. Groups 23, 47, 71 and 119 ended rc78; groups 131 and 143 subsequently returned rc0, and six other groups were already marked complete. The layered inventory reports group 23 with 14 completed page journals and one page-start pending without layout or region start; group 71 has 15 such pending starts. Groups 47 and 119 each have ten complete page journals and five unknown pages. Original R11 and R22 capture proofs verify all 24 unmatched region starts across those ten unknown pages; preserve them without redraw. For the 16 no-layout starts, original producer-window correlation is corroboration only, not per-page proof of exposure or later history. An earlier unmatched ordinal and later different-ordinal starts in group 119 are a custody discrepancy, not proof of same-ordinal redraw. A group 47 worker recorded connection errors, but the overall failure cause remains unknown. Owner action: preserve all original captures and unmatched requests, investigate custody and safe continuation using the original policy. No quality or 755-page verdict follows. [Bounded event receipts](../../artifacts/codex3-pip-pool2-r22-0128-v2-20261031/). [belief: cc]

##### 2026-10-31 R29 head collection terminal

`codex3-pip02-paddle-relocatable-r29-head-20261031` ended rc0 and wrote HEAD-DONE; group 0 and group 3 completion markers exist and group 3's final worker returned rc0. Read-only layered audit finds **25/25 page journals complete**. Strict original finish/capture verification passes 23/25 in the selected capture corpus, including all ten newly completed pages 39–48; older pages 0 and 34 retain unresolved strict custody and must not be promoted by this collection marker. The five prior durable region start/result hashes are unchanged and their prior no-network replay evidence remains retained. This is collection completion only: no 755-page coverage or quality verdict follows. [Bounded terminal and proof records](../../artifacts/compute/codex3-pip-r29-c6-gpu-r2-20261031/). [belief: cc]

##### 2026-10-31 PIP R30 scorer correction and pool2 preparation

Correction to earlier d2 portability language: the deployed `d2b95912cedd` epoch watcher still imports the ROOT lane adapter at line 93 and does not load its own R29 epochs as legacy baselines. Keep the old lane and all receipt-bound absolute paths. Previously strict-replayed receipts and the deduplicated 344-page/82-table union remain valid; no prior score is regraded. Research `261f7804a0378aee8f7d2c01e443847169b3a97d` supplies a separate immutable R30 scorer with the same metric and GT, bundled adapter, actual R29 baselines and literal R30 producer checks. Original R28/R29/fresh controls and final-source s001 replay passed; the R30 positive registration control is synthetic, not a real R30 cohort result.

Pool2 R30 READY (manifest `3ba1aeac5012b7a48c8b63d8ee5ce332319c54c891adc6dd7059ce35da648912`) preserves 24 unmatched region starts and ten mixed pages as UNKNOWN. Its 16 no-layout page starts require the pinned custody and absence checks before layout continuation; output-root/time correlation alone does not identify an intrinsic producer PID. The full R30 cohort and normal real-grant branch remain unrun. No full 755-page or paired quality gate follows. [Correction, controls and custody capsule](../../artifacts/compute/codex3-vkq3-pip-r30-20261031/). [belief: cc]

- *(2026-10-31, R31 pool3 tail READY.)* `codex3-pip02-paddle-relocatable-r31-pool3-20261031` manifest SHA-256 `02932f4953894f59b163956f3a90acb27bb91740c1a13103bc509d0ebfa82a96` covers only original groups 110/122/134/146: an independently pinned inventory found 60 original pages with no starts in the three checked original checkpoint roots. Shared shard locks and per-page source/inventory guards refuse unexpected starts or orphan regions; R31 continuations replay durable results, and unmatched starts are never redrawn. Nineteen structurally unmatched starts in other pool3 groups stay untouched. Same-entry public controls captured five durable HTTP 200 responses and drained rc75, with STOP/drain and no-grant refusal also checked; the normal real-grant cohort remains untested at publication. The subset marker is not a full-pool completion or quality verdict. Research `e27883ff25cfb10887fdc51be86018f15c7b5344` adds this producer to a separate scorer catalog; original scorer paths remain intact. [Bounded receipt](../../artifacts/compute/codex3-pip-r31-pool3-ready-20261031/SHA256SUMS-capsule). [no-belief: preparation only]

- *(2026-10-31, R32 pool1 continuation READY.)* `codex3-pip02-paddle-relocatable-r32-pool1-20261031` manifest SHA-256 `c94d86f508ea6d6c1f62c49a11e9f0d7c213df8dd3187daef54f16c8e6fccc59` prepares continuation within the original pool1 campaign: 26 candidates (16 no-layout and 10 saved-layout pages with authenticated successful responses); 30 unmatched region starts across 13 other pages remain protected. Original shared campaign and shard locks, layout binding and request replay preserve existing responses. The obsolete R22 poller remains alive with cooperative STOP; exact native `.grant` absence was verified after STOP, not before it. Final same-entry public controls obtained five durable HTTP 200 responses and drained rc75; active STOP drained, and no-grant invocation refused. The real-grant cohort was untested at publication. Research `3da40c0942c1` registers the exact producer in a separate immutable scorer catalog; the prior 359-page/84-GT snapshot and full quality gate remain unchanged. [Bounded evidence](../../artifacts/compute/codex3-pip-r32-pool1-ready-20261031/SHA256SUMS). [no-belief: preparation only]
  - *(2026-10-31, ws58 filing: R32 pool1 run ended.)* `codex3-pip02-paddle-relocatable-r32-pool1-20261031` ended rc=78 at 22:56:30Z after 2h40m of a 9h grant (job-rc-78:exited). Launcher log: 7 attempts `parallel_complete` rc0, 82 `parallel_partial` rc75 (cooperative drain). Class PARTIAL/diagnostic; no quality verdict per rule. Host-namespace correction (2026-11-01): the attempts directory exists on host Micron; container `/mnt/micron` is a different namespace. Native `attempts/codex3-pip02-paddle-relocatable-r32-pool1-20261031-1793477784800543758.jsonl` records exhausted unknown groups 20, 32, 80, 128 and 140, and 89 attempt results comprise 7 rc0 and 82 rc75. The entry maps an rc75 without error/reason and no observed progress to rc78; the pool returns rc78 after accumulating exhausted groups. `DONE-1` is absent, consistent with incomplete pool. The group 20 worker logged no new requests, 10 completed pages and five unknown pages; group 128 logged no new requests and a `native page layout geometry changed` exception for `exam_paper_en-file-putnam-archive_2000_Solutions_2000s_page_001.png`, masked by the owner result's null reason/error. The five final worker summaries report 61 complete pages, 13 unknown and one geometry error, with zero missing pages and zero new requests in each group; seven other groups have DONE markers. These are distinct conditions, not a full-pool completion. Preserve the 13 unknowns and the geometry error without redraw; this snapshot does not by itself prove the exposure history of every unknown. No new pool run or quality verdict follows. Preserve exposed starts and never redraw unmatched regions; qualify any successor before rearm. [no-belief: partial diagnostic, no measurement]

- *(2026-10-31, Unlimited-OCR READY.)* The qualified manifest SHA-256 `d6f5efde5d7b3d45c65891a949779c163c3fe46ba55a4f42da06057c3944ef33` binds source enrollment `e0817fc3e478175d3364cd3eedd342fe2fd2ccfa`. The final HOST launcher exercised two target-model profiles and an active STOP75/drain; scorer control used its reference fixture. The original 36 page/profile requests remain unrun at publication, so no CER, TEDS or model-quality result follows. The separate artifact tensor audit is bounded to source/model identity. [Publication metadata](../../artifacts/compute/codex3-unlimited-ocr-ready-20261031/SHA256SUMS). [no-belief: preparation only]

- *(2026-10-31, R33 pool0 tail READY.)* `codex3-pip02-paddle-relocatable-r33-pool0-20261031` manifest SHA-256 `ad2b352c68b0659a4618d5209189c044b968757dfdfb9475705bf154dbb595f5` selects 85 original no-start page identities from groups 41/53/89/113/137/149; five unmatched starts elsewhere stay protected. Original shared locks and source-pinned guard recheck each page. The old R27 poller remained alive under cooperative STOP; no process-death claim. Public smoke deliberately stopped after five durable HTTP 200 region responses, rc75 with request-budget partial and **zero completed pages**; separate active STOP returned rc75 and drained. The normal real-grant cohort path remained untested at publication. Its subset marker cannot establish full-pool completion or quality. Research `12b17bacab26` registers the exact producer in a separate scorer catalog. [Evidence](../../artifacts/compute/codex3-pip-r33-pool0-ready-20261031/SHA256SUMS). [no-belief: preparation only]

- *(2026-10-31, R35 merged pool0 continuation READY.)* `codex3-pip02-paddle-relocatable-r35-pool0-20261031` manifest SHA-256 `4bca38650a5a110e26b58e1a645621a4a9101874a7dc1853a402bc6de78410dc` supersedes the unarmed R33 tail packet. It covers 159 original pages: 115 no-start and 44 saved-layout pages with authenticated successful responses; other partial or unmatched-start pages stay excluded. Original locks, pinned source, response replay and geometry checks remain required. The R27 poller remained alive under cooperative STOP; the old group125 stale ARMED record was ignored only with its separate terminal/death/no-grant evidence. Public smoke deliberately captured five durable HTTP 200 region results and stopped at its finite budget, rc75 with **zero completed pages**; separate active STOP drained rc75. The real-grant cohort was untested at publication. Research `067aaee46466` registers this producer in a separate scorer catalog; no full-pool or quality verdict follows. [Evidence](../../artifacts/compute/codex3-pip-r35-pool0-ready-20261031/SHA256SUMS). [no-belief: preparation only]
  - *(2026-11-05, operator-adhoc-takeover-20261105.)* The R35 revival from the micron import was refused and no successor was published. The import `/mnt/raid0/llm/tmp/micron-import-20261105/codex3-pip-pool0-merged-r35-20261031` verifies (`source.sha256` self-hash `85ef3757…` OK, every r35 pin OK; the 29 r25 pins match the raid0 copy `codex3-pip-relocatable-r25-20261030`). But `pool.py` asserts all 1,052 `source-pins.json` digests at start, and 39 raid0 pinned files are gone (reaped `pip02-pipeline-prep-20261029/`, `rtg56-td29-m0a-raw-v5-20261029/`, `codex3-pip-pool0-recovery-20261031-0638/`, r14 smoke captures, among others), so the job would die `pool source changed`. Its interpreter `/usr/bin/python3.12` exists only in the host root, so the `sudo chroot /proc/1/root` must stay. The rc=78 in history comes from `launch-p0.sh --smoke`: `mkdir control-once-N || exit 78`, a one-shot smoke latch that fires once `control-once-0/1` exist. It is a config refusal, not a job failure. rc=75 is already resume (`parallel_partial`) in the R35 log. Next: rebuild source-pins without the reaped forensic inputs, as a reviewed R36. [no-belief: triage only]


**PARTIAL — R35 pool0 original grant** ended 2026-11-01 01:03:40Z rc75. Three group DONEs (5/17/29); latest pre-cut native worker summaries across the 46 selected pages in visited groups 5/17/29/41 show 36 complete, 9 missing and one no-redraw budget refusal before exposure; complete entries can include retained/replayed prior work, net-new unknown. Last owner record reports timeout as deadline/admission/output limit, factory null; cause unresolved. Later same-ID relaunch excluded. Other 113 selected pages are not covered by these summaries. No full-pool, TEDS or quality verdict. [Evidence](../../artifacts/compute/codex3-pip-r35-original-20261101/README.md). [belief: cc]

## Track: opendataloader-pipeline-integration
<!-- gate: none -->

> Folded from `handoffs/active/opendataloader-pipeline-integration.md` @ `ccf37cd0b6a4` on 2026-11-02 (BRF-T1-F8, route 1a, operator D1/D5; retired row PIP-05 → PIP-04). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### OpenDataLoader PDF — Pipeline Integration

**Status**: Active. The default ODL extractor and structured-context substrate are landed; parser-quality, routing, intrinsic-metric, LiteParse, and model-backed comparison gates remain open.
**Created**: 2026-03-17 (via research-intake deep dive)
**Priority**: P2 — medium effort, high document-quality payoff
**Categories**: document_processing, multimodal

#### Executor Start Here

1. Implement ODL-011's non-coreference Ekimetrics and contradictory HOPE arms against one digest-pinned fixture and downstream RAG endpoint.
2. Acquire or construct the immutable GT-page-to-source-PDF bridge needed for the full OmniDocBench rebaseline.
3. ~~Run the ODL-013 observation~~ ✅ **DONE 2026-08-13** (inference-granted window and LiteParse-aware scoring). The result does not authorize adoption or a routing-default change; make the evidence durable and protocol-admissible before using it for either.
4. Do not promote a parser or flip a routing default from the existing July artifacts: they are scaffolding/observations, not representative decision evidence.

The domain router is [PIP-05](pipeline-integration-index.md). The full completed implementation and evidence ledger is in [the completed-through-2026-08-13 sibling](../completed/opendataloader-pipeline-integration-completed-through-2026-08-13.md).

#### Objective

Use OpenDataLoader PDF as the structured document path, preserve a cheap born-digital fast path, and route scanned or structurally difficult pages to model-backed parsing. Any parser choice must report reading order, table fidelity, structure, speed, deploy footprint, and a workload-relevant downstream endpoint under the project measurement constitution.

#### Current Decision Gates

| Gate | Current state | What closes it |
|---|---|---|
| ODL-011 chunk metrics | **SC/BI/ICC/DCC registered + first real run 2026-08-13** | Contradictory HOPE scores and common RAG correctness on the digest-pinned Phase-2 fixture (HOPE arm row below). |
| ODL-013 LiteParse comparison | **Observation complete 2026-08-13; decision gate open** | Preserve or rerun it as durable, protocol-admissible evidence with a precommitted decision rule. LiteParse leads the aggregate point estimates, but the current scratch artifact cannot authorize adoption or routing. |
| Full ODL baseline | Input blocked | Immutable source-PDF manifest or explicit page/document scoring bridge for the 1,651-page / 665-table corpus. |
| PaddleOCR-VL | Prior arm void | Official pipeline or official cropped-element prompts; never reuse the off-label full-page numbers. |
| Unlimited-OCR | **18-page observation complete (18/18 pages, 0 errors; median 5857 ms/page, ~392 t/s decode; text_block edit_dist 0.3624, table TEDS 0.0117, reading_order 0.2165 — run detail in `progress/2026-08/2026-08-13-mainD.md`); evidence correction open** | Correct the causal claim and mutex receipt, then run the canonical-profile A/B after the operator lifts the all-inference-stop order. |
| Routing policy | Default unchanged | Matched quality + latency evidence for local ODL, hybrid ODL, LiteParse/pdftotext, and model-backed arms. |

#### Outstanding Tasks

- [x] **ODL-PARSE-SCHEMA (production defect, found 2026-11-10 via AGG-0.2 r2).** With `PDF_EXTRACTOR=opendataloader ORCHESTRATOR_ODL_STRUCTURED=1`, the live document flow (`document_preprocessor.preprocess` → `document_client._ocr_result_from_pdf_extraction` → `pdf_router.extract_opendataloader_structured` → `ODLStructuredDocument.from_json` → `document_chunker`) returned **zero tables, zero ODL headings and one page per document** for every real PDF: `from_json` read top-level `page_count/headings/figures/tables` keys that opendataloader-pdf 2.x never emits (it emits `"number of pages"` + a `"kids"` element tree; the unit fixture was hand-shaped to the wrong schema), and the adapter put all text on page 1 with the page count from PyMuPDF, which the orchestrator venv lacks. All 10 AGG-0.2 r2 cached parses show `tables: []`, `total_pages: 1`. Fixed in epyc-orchestrator `5354fc0b` (kids-tree parser: headings, tables via `rows[].cells[].kids`, figures, lists, per-page text; adapter builds real pages; legacy shape still read; 2 real-schema tests, 146 passed in the 4 related files). Slice proof (AWK 10-K pp. 80-83, production preprocess path): `total_pages=4`, 4 heading sections with page ranges, per-page text 3813/1091/1581/1245 chars. [no-belief: code fix + 4-page smoke, no measurement claim]
- [ ] **ODL-LOCAL-NO-BORDERLESS-TABLES**: on the same 4-page AWK balance-sheet slice, ODL local finds **0 tables** with both `table_method` default and `cluster`; the statements come out as paragraphs (`Total assets $ 27,787 $ 26,075`). So the L3 table layer stays empty on 10-K statements even after ODL-PARSE-SCHEMA. Route: a table backend for table regions (ODL hybrid or PaddleOCR-VL, the 65-page table-path rule above), or an L3 text-row extractor over per-page text. Next: decide which with AGG-0.2's owner; no inference needed for the text-row option. [no-belief: 4-page observation]
  - Progress 2026-11-10 (not ticked; the table-backend question stays open): the zero-LLM text-row option is built, orchestrator `08d1f0af4236` (`src/aggregation/facts_det.py`, extractor `l3_textrow.v1`, wired into `extract_corpus_facts` via `CorpusStore.document_pages`; 17 tests pass). Label plus 2-3 numbers, `$`/commas/parentheses/em-dash/footnotes, year columns from the nearest 2-3 year header, unit from the nearest `(In millions...)` header, exact normalised US-GAAP synonym table, unknown labels label-only, high confidence only for canonical label + resolved period + known unit. One-slice proof (AWK pages 80-83, production ODL path, 0 tables, 4 pages, ~1 s): 24 high-confidence canonical facts, e.g. `total_assets` 2022 27787 / 2021 26075 USD_millions, `revenue` 3792/3930/3777. Finding: ODL emits a whole statement as ONE paragraph with rows joined by spaces, so the extractor reads a token stream, not lines. Not yet measured on the corpus; r3 job dir rebuilt from `08d1f0af4236`. Per-document `l3_doc` counts in l3_load.py use its own table/regex path and will not count text rows (the final `l3_facts_det` build and the M1 report do). [no-belief: unit tests + one-slice check, no corpus measurement]

##### Routing and representative parser evidence

- [ ] Parser-quality comparison (**rescoped 2026-11-09**): the pdftotext, `legacy_router`, ODL local and LiteParse arms already ran on the 200 PDFs in ODL-013 r2 (grants complete 2026-11-07T20:59Z, filed 2026-11-08; NO DECISION, see the ODL-013 box below), so the remaining arms are only **docling, marker, ODL hybrid and LightOnOCR-2-1B**, run on the same 200 PDFs and scored for structure/table/reading order first and latency second under the P-DOCPARSE-1 rule (note `legacy_router` equals pdftotext and 43 documents are flagged `needs_ocr`, so the OCR leg was never exercised). Publish in the dated progress log with immutable artifacts and metric directions; only if the scores say the swap is useful, implement the three-way routing (ODL local -> ODL hybrid for tables -> LightOnOCR for scanned). Needs inference (model arms) via normal grants. *(Original text: LightOnOCR-2-1B only as a structural/table/reading-order parser candidate against docling-fast; baseline = pdftotext + LightOnOCR; absorbs the five rows below.)*
  - **2026-11-09 prep (prep-kbctx; box stays open):** arm jobs written on the shared `/mnt/raid0/llm/tmp/parser-quality-common-20261109/` (template `pip02-r36-english-run-20261107b`; upstream evaluator, 200 single-page PDFs, NID/TEDS/MHS higher=better): rows `parser-docling-200pdf-20261109` (rank 25), `parser-odl-hybrid-200pdf-20261109` (26), `parser-lighton-200pdf-20261109` (28, LightOnOCR-2-1B F16 + F16 mmproj on the v10 CPU kernel); each published, smoke pending, estimates conservative with an in-job pilot record. **Marker arm:** row `parser-marker-200pdf-20261109` published at rank 27 after disk recovered to 224 GiB free (venv `/mnt/raid0/llm/tmp/marker-venv-20261109`: marker-pdf 1.7.1, surya-ocr 0.14.1, torch 2.6.0+cpu, transformers pinned to 4.51.3 because 4.57 lacks `QuantizedCacheConfig`; 2.3 GB model set in `/mnt/raid0/llm/models/marker-datalab-20261109` pinned per file by sha256 in the common dir, verified at job start); smoke PASS 2026-11-09, awaiting a grant (box stays open). The docling, odl-hybrid and lighton rows have since ended and await filing (2026-11-09 queue_status). [no-belief: prep, no measurement]
  - **2026-11-09 FILED (rows `parser-docling-200pdf-20261109`, `parser-odl-hybrid-200pdf-20261109`, `parser-lighton-200pdf-20261109`; box stays OPEN: marker is still ungranted and ODL hybrid is incomplete).** Same 200 single-page PDFs, upstream evaluator, NID/TEDS/MHS higher = better, overall = their mean, latency lower = better; failed docs censored, never zero. Observation, no routing or adoption decision follows from one arm. **docling 2.91.0** (rc 0, COMPLETE, 200/200 scored, 0 failed): NID 0.9053, TEDS 0.9245 (42 table docs), MHS 0.8295 (107 heading docs), **overall 0.8910**, median 1.25 s/doc. **LightOnOCR-2-1B F16** (rc 0, COMPLETE, 200/200 scored, 0 failed, v10 CPU kernel): NID 0.9364, TEDS 0.8704, MHS 0.7873, **overall 0.8963**, median 19.89 s/doc (21.5 s/doc mean, 4,291 s total on a CPU quarter). **ODL hybrid (docling-fast): NO RESULT.** Ended rc=75 `partial-native-incomplete` at 13:45Z, about 5 min in: 199 of 200 documents parsed, one document (the 141st in sorted order) returned an empty prediction on attempt 1 of 2 and was never retried; no `final` record and no scoring ran, so there are no NID/TEDS/MHS numbers (pilot: 0.56 s/doc). Why the job stopped at rc 75 rather than retrying is not recorded in the row output. Context, ODL-013 r2 on the same corpus (overall, from the committed report): pdftotext 0.5705, ODL local 0.8419, LiteParse 0.8804. Reading: docling and LightOnOCR are within 0.6 points overall (0.8910 vs 0.8963, no paired CI computed; per-doc scores are kept in each arm's `evaluation-final.json`), LightOnOCR wins reading order (+3.1 pts NID) and docling wins tables (+5.4 pts TEDS) and headings (+4.2 pts MHS) at about 16x lower latency; both sit above LiteParse's 0.8804 overall, so the paired per-doc comparison the box asks for is the next analysis (zero inference, doable now from the per-doc scores). [belief: cc]
  - [ ] **PARSER-ODL-HYBRID-R2 — re-run the ODL hybrid arm (resumable): retry the one empty-prediction document, then score.** The 199 finished predictions are resume-skipped; expected cost minutes (pilot 0.56 s/doc). Row `parser-odl-hybrid-200pdf-20261109` ended rc=75 with no final record; republish as `-r2` with `supersedes` after finding why it did not retry. Done when `results.jsonl` has the `final` record with NID/TEDS/MHS over 200 docs. [no-belief: native-pending:VB-ROWFILE-20261109-WIRE]
    - 2026-11-09 apr2 rerun-fixes (partial, box stays open): why no retry. `common.Job.main` walked its todo list once; document no. 141 of 200 failed attempt 1 ("empty prediction"), the loop moved on with attempts=1 < MAX_ATTEMPTS=2, the end test `ok + failed_final == 200` saw 199 + 0 and skipped scoring, so the row exited rc=0 and the launcher ended it rc=75 `partial-native-incomplete`. Fix: in-run retry up to MAX_ATTEMPTS per doc, then censor and always score; copy `/mnt/raid0/llm/tmp/parser-quality-common-20261109-r2/` (tracked as `scripts/row_jobs/parser_quality_common.py`, 4 tests pass). Row `parser-odl-hybrid-200pdf-r2-20261109` (rank 26, supersedes r1, fresh out dir so all 200 re-run, ~0.6 s/doc) published, smoke queued. The docling, marker and lighton arms still import the unfixed `-20261109` copy and carry the same defect. [no-belief: not-a-result]
    - **2026-11-09 FILED, box stays OPEN (row `parser-odl-hybrid-200pdf-r2-20261109`, rc=0 COMPLETE 16:36Z; observation, no routing or adoption decision):** the in-run retry fix worked: doc no. 141 (stem ending 0141) (empty prediction, attempt 1) was retried and failed again, so it was censored (`failed_final` 1, never scored zero) and scoring ran. ODL hybrid docling-fast (opendataloader-pdf 2.5.0, docling 2.91.0, java 17.0.21), upstream evaluator, 199 of 200 docs scored: NID 0.9335 (199 docs), TEDS 0.8740 (42 table docs), MHS 0.8268 (106 heading docs), **overall 0.9035**, median 0.56 s/doc (higher = better for scores, lower = better for latency). Acceptance 'final record over 200 docs' is NOT literally met (199 scored, 1 censored); doc 141 is anomalous in every arm (docling overall 0.052, marker 0.410, ODL empty twice), and the one-document scoring defect noted for the marker arm is unfixed, so the 199-doc comparison against the 200-doc arms is not like-for-like until doc 141 is understood. Raw record: `/mnt/raid0/llm/tmp/parser-odl-hybrid-200pdf-r2-20261109/out/` (`results.jsonl`, `evaluation-final.json`). [belief: cc]
  - [ ] **PARSER-PAIRED-COMPARISON — paired per-document bootstrap across the finished arms (zero inference).** From the per-doc scores in the docling and LightOnOCR `evaluation-final.json` and the ODL-013 r2 arms, report paired overall differences with CI95 (docling vs LightOnOCR, each vs LiteParse); add ODL hybrid and marker when they finish. [no-belief: not-a-result, task]
    - **2026-11-09 FILED, box stays OPEN: parent Parser-quality comparison, marker arm (row `parser-marker-200pdf-20261109`, rc=0 COMPLETE 16:03Z; NOT A FINDING).** marker-pdf 1.7.1 + surya-ocr 0.14.1, CPU, 200/200 docs `ok`, 0 failed; the run's own scorer output was NID 0.8885, TEDS 0.8665, MHS 0.7903, overall 0.8623, median 0.88 s/doc. Per the filing brief this arm shares an unfixed one-document scoring defect (doc no. 141 (stem ending 0141) is anomalous in every arm), so these numbers are recorded for provenance only and must not enter the PARSER-PAIRED-COMPARISON or any ranking until the defect is fixed and the arm re-scored (scoring is zero-inference; predictions are retained in `out/prediction/marker/markdown/`). The 0.88 s/doc CPU latency for a surya-based pipeline is also implausibly low next to docling's 1.25 s/doc and was not checked; read it as unverified. Raw record: `/mnt/raid0/llm/tmp/parser-marker-200pdf-20261109/out/`. [no-belief: marker score withheld, one-document scoring defect unfixed]
- **[declined: ws58 2026-11-03 content-review: merged as a secondary metric]** Measure LightOnOCR latency only inside the parser-quality comparison above, after structural/table/reading-order scoring says the swap is useful.
- **[declined: ws58 2026-11-03 content-review: merged as the conditional follow-on]** Implement three-way routing: ODL local (simple) → ODL hybrid (tables) → LightOnOCR (scanned).
- **[declined: ws58 2026-11-03 content-review: merged as the run]** Run comparison on 200 PDFs: our pipeline vs ODL local vs ODL hybrid vs docling vs marker.
- **[declined: ws58 2026-11-03 content-review: merged as the reporting step]** Publish results in the dated progress log with immutable artifacts and metric directions.
- [x] **Make ODL-013 decision-capable before any adoption or routing-default change**: preserve the corpus/evaluator/engine hashes and raw outputs in durable in-repo evidence; use an existing or operator-ratified document-parser protocol with the full claim tuple and a precommitted decision rule. Keep the current default unchanged until that gate closes. **Row published 2026-11-07, keeper smoke PASS (19:25Z: preflight with pdftotext 24.02.0 + private JRE 17.0.21, corpus manifest, pdftotext/legacy_router/opendataloader parse units; `bin/` shims = pdftotext via the host-root pattern, java = the pinned private JRE).** **Re-run authorised 2026-11-07 (operator E2 'Ratify + Re-run')**: row `pip04-odl013-rerun-r2-20261107` runs four arms on the 200-PDF corpus — pdftotext (poppler), `legacy_router` (the orchestrator's ORIGINAL pdftotext + quality-gate PDF router, orchestrator `f92a89b80`, added as a baseline arm in research `b839143bb`), opendataloader-pdf==2.5.0, liteparse==2.12.0 — against the draft protocol P-DOCPARSE-1 (`artifacts/operator/p-docparse-1-annex-draft-20261107.md`; ratification through the operator's script is pending, until then the result is graded an observation). Precommitted rule: ADOPT iff the lower bound of the paired-bootstrap 95 % interval of (LiteParse - ODL) overall > 0 and LiteParse median latency <= ODL; REJECT iff the upper bound < 0; else NO DECISION. Stop rule: one sequential run over all 200 documents, fail closed on any failed document, stop on the verdict (no repeat). [2026-11-09 apr2 rtg08-evl47-pip04-code: evidence copy BLOCKED by the commit PII hook, not routed around. The 652 KB text copy (results.jsonl, TERMINAL.json, report.md, corpus.sha256, logs, per-arm summary/evaluation/routing, SHA256.json over all 821 raw files) is staged-out and left UNTRACKED in worktree `/mnt/raid0/llm/worktrees/apr2-rtg08-evl47-pip04-code-root-20261109/artifacts/compute/pip04-odl013-r2-20261107/`; `pii_precommit.sh` flags the 14-digit corpus `document_id` values as `[account_number]` in every evaluation.json, summary.json and the manifest. Needs either an allowlist entry for that document-id shape (a hook-config change, not mine) or a copy that hashes the ids. Box stays open. [no-belief: evidence copy blocked]]
  - **2026-11-09 status (verified):** r2 ran (rc0, 2026-11-07T20:59:08Z), was filed 2026-11-08 and **P-DOCPARSE-1 was ratified 2026-11-08** (`artifacts/operator/ratify_p_docparse_1_20261108.json`, commit `4c6565a27`, ancestor of origin/main), so "ratification pending" above is stale. Outcome: 200 docs, 0 failed in 4 arms; LiteParse minus ODL +0.0385, 95 % CI [0.0176, 0.0614], but LiteParse median latency 676.9 ms vs ODL 237.2 ms fails the ADOPT latency clause, so the formal result is **NO DECISION, routing default unchanged**. Remaining (doable now): copy the corpus/evaluator/engine hashes and raw outputs from `/mnt/raid0/llm/tmp/pip04-odl013-rerun-r2-20261107/out/` into durable in-repo evidence (the filing said this box is not closed). [no-belief: status note; verdict filed, no claim tuple committed]
  - **2026-11-09 apr2 decided-rows (operator: commit a pseudonymized copy, PII hook unchanged): DONE (operator then decided the raw files: digests in repo, raw on durable storage outside git).** Committed `artifacts/compute/pip04-odl013-r2-20261107/` (22 files, 652 KB: results.jsonl, TERMINAL.json, report.md, corpus.sha256, logs, per-arm summary/evaluation/routing, SHA256.json) with the 200 14-digit document IDs replaced by `doc-` + first 16 hex of unsalted SHA-256, consistently (4,711 substitutions, 0 originals left); `PSEUDONYMIZATION-NOTE.md` says so. The id mapping is outside git at `/mnt/raid0/llm/tmp/pip04-odl013-idmap-20261109/idmap.json`. The raw outputs (855 files, 4.3 MB, including the 800+ per-document predictions) are copied to durable storage OUTSIDE git and tmp at `/mnt/raid0/llm/archives/pip04-odl013-r2-20261107/` (read-only); the committed `SHA256.json` digests describe those original bytes (not the pseudonymized text files) and all 855 were re-verified against the archive through the id map (855 match, 0 mismatch, 0 missing). Acceptance met: corpus/evaluator/engine hashes and raw outputs preserved durably, protocol ratified, default unchanged. ✅ 2026-11-09 [no-belief: evidence copy]
- [x] **Harden the ODL three-way harness and timing record** ✅ 2026-08-25 (mainA PIP-05): fail closed on non-zero pdftotext return codes, missing ODL candidates, and empty liteparse/phase predictions (failed docs leave no prediction file, `failed_stems` recorded, exit 2); ODL engine pinned (`opendataloader-pdf==2.5.0`, `liteparse==2.12.0`) via `importlib.metadata` with fail-closed exit 2 on mismatch/unresolvable, recorded in summary.json; raw per-document latencies persisted (`per_doc_latency_ms`) so median/p90 are independently reproducible, report gains a p90 column; score phase exits 3 on missing/empty predictions or missing evaluation.json. Research `run_three_way_bench.py` + 13 new tests; suite 69 passed/1 skipped.
- [x] **Resolve the dataset name collision explicitly** ✅ 2026-08-25 (mainA PIP-05): the OmniDocBench clone was renamed `/mnt/raid0/llm/opendataloader-bench` → `/mnt/raid0/llm/omnidocbench` (no live processes; venv activate scripts + console shebangs migrated); every in-repo path reference repointed (research odl_bench + document_extraction_adapter + validate_pool, orchestrator corpus_v1/common.py, root handoffs/wiki/op-bundle/backlog-queue/amend_e8 script); bare-name references now fail loudly. `/mnt/raid0/llm/opendataloader-bench-upstream` remains the 200-PDF OpenDataLoader benchmark. Historical progress records left as dated.
- **[declined: ws58 2026-11-03 content-review: merged as the baseline arm]** Run baseline: our current pipeline (pdftotext + LightOnOCR) on the 200 PDFs.
- **[declined: ws58 2026-11-03 content-review: a citation note, not a task]** Cite W-RAC as Phase-2 hybrid-routing prior art if measured cost becomes a bottleneck.

##### ODL-011 — chunk-quality instruments

- [x] During Phase 3 benchmark integration, add intrinsic chunk-quality scores beside the committed `odl_bench` structural text edit distance, table TEDS, reading-order edit distance, and speed rows; explicitly bridge/co-report sibling NID/MHS if those names remain in the parent contract. ✅ 2026-11-01 — Research `1421b578ae4d5c9afbf3b2199f89893b093a0819` on `origin/main`; 62 model-free tests passed under R6. Ekimetrics rows are informational stand-in chunk diagnostics with source-bound prediction hashes; sibling NID/MHS source fields and directions are mapped without conversion. Evidence: [ODL-011 artifact](../../artifacts/engineering/odl011-intrinsic-report-integration-20261101/README.md). [belief: cc]
- [x] **ODL-011 integrate and test the non-coref Ekimetrics arm ✅ 2026-08-13**: registered SC/BI/ICC/DCC in `odl_bench` (`intrinsic.py`, research `f24b8aa9` + `cd329746`); upstream MIT provenance pinned (intake-580, FMRE/RC excluded per license + contract); 30 intrinsic tests cover metric direction + degenerate inputs; unavailable-embedder evidence preserved (`value=None` + reason). First real run complete: sentence-transformers 5.7.0 installed under inference grant (msg-84), all-MiniLM-L6-v2 over the ODL-013 dirs (200 docs/engine) — pdftotext ICC 0.651/DCC 0.672, opendataloader ICC 0.643/DCC 0.654, liteparse ICC 0.552/DCC 0.654. Evidence: `/mnt/raid0/llm/tmp/odl013-bench-20260813T1336Z/intrinsic/intrinsic-*-embed.json`. HOPE arm + common RAG endpoint remain open (row below).
- **[declined: operator 2026-11-07 — intrinsic chunk scores 'cannot gate alone' by this track's own text and the routing default is unchanged; it needs an LLM judge plus a RAG answer-correctness endpoint with no current consumer. Re-file if the ODL-013 P-DOCPARSE-1 verdict leads to a routing change]** **ODL-011 add the contradictory HOPE arm and common endpoint**: score both intrinsic families on the digest-pinned Phase-2 fixture and report the same downstream RAG answer-correctness endpoint before either family informs routing.

##### ODL-013 — LiteParse fast path

- [x] Bench LiteParse-local vs OpenDataLoader-local vs pdftotext on a representative born-digital corpus: reading order, table fidelity, speed, and JVM-free deploy footprint. Use LiteParse-aware scoring and decide `adopt_component` vs ODL-only. ✅ **EXECUTION COMPLETE 2026-08-13; OBSERVATION ONLY** — the same 200 PDFs and prediction stems were scored with the upstream NID/TEDS/MHS evaluator, and all 600 stored outputs reproduce exactly. LiteParse leads the aggregate point estimates (overall 0.8804 vs ODL 0.8419 and pdftotext 0.5705), but NID and MHS paired exploratory intervals cross zero and no decision rule was precommitted. The scratch-only artifact lacks a document-parser protocol/category/attestation and cannot gate adoption, routing, promotion, or closure. Harness: `odl_bench/run_three_way_bench.py` (research `a16aa0d9`); local artifact `/mnt/raid0/llm/tmp/odl013-bench-20260813T1336Z/`.
- [x] **ODL-013 execute and record the representative comparison** under an inference-owned CPU window, with an explicit page/document scoring bridge, pinned transient dependencies, and a fast-path policy verdict. ✅ **EXECUTION COMPLETE 2026-08-13; REQUESTED VERDICT NOT LICENSED** — completed 13:36–13:38Z under the recorded inference grant using the upstream GT/evaluator and pinned LiteParse/OpenDataLoader/poppler dependencies. The independent audit accepts the quality output as reproducible comparative evidence, but rejects `ADOPT` because the record is scratch-only and has no applicable measurement protocol or precommitted selection rule. Timing remains summary-only, ODL's version is `?`, and prospective failure accounting is not fail closed.
- [x] **Independent ODL-013 and matched-parser audit.** ✅ 2026-08-13 — accepted both stored comparisons with follow-ups as sound observations, corrected the comparison report's `matched, decision-grade fixture` phrase by explicit supersession here, and kept all parser/routing defaults unchanged. The audit found 200 non-empty predictions per engine with exact upstream-evaluator replay; it did not find decision-grade warrant.
- [ ] Route complex, dense-table, and scanned documents away from LiteParse; it is a born-digital fast-path backend only. [too-big: future LiteParse routing policy requires handoff-owned classification and validation]
  - *2026-11-09:* no trigger while ODL-013 r2 is a NO DECISION and the routing default is unchanged; refile with a done criterion only after a real routing change, same stance as the declined ODL-011 rows. Left open.

##### Model-backed parser arms and full rebaseline

- [x] **PaddleOCR-VL stronger parser / LightOnOCR comparison ✅ 2026-08-13**: a matched 200-PDF scored fixture was obtained for LiteParse, ODL, and pdftotext. The point estimates are useful comparative observations, not a promotion or routing decision: the local comparison report's `matched, decision-grade fixture` wording is superseded by the independent audit above. PaddleOCR-VL remains retracted off-label; LightOnOCR remains scanned-document scope; the n=665 rebaseline and a protocol-admissible decision record remain open.
- **[declined: operator 2026-11-03 model-audit: superseded by PIP02-PHASEC-ENGLISH-RUN (English-only approved run supersedes the full-set rebaseline)]** **Re-baseline ODL end-to-end on the full set**: acquire the missing source PDFs/immutable manifest, then report table TEDS at n=665 with all-language and English-only splits.
- **[declined: operator 2026-11-03 model-audit: superseded by PIP02-PHASEC-ENGLISH-RUN (real PaddleOCRVL pipeline already run in Phase B and is the Phase C arm)]** **Void and re-run the PaddleOCR-VL arm** through the real `PaddleOCRVL` pipeline with `vl_rec_backend="llama-cpp-server"`, or restrict llama.cpp-only testing to cropped elements with the official six prompts. Do not cite the prior `0.0`/`0.058` TEDS numbers.
- *Moved to [`model-evaluation-queue.md`](model-evaluation-queue.md) § Track: meq-carve-opendataloader-pipeline-integration on 2026-11-03 (BRF-T1-MEQ, operator D2): "P1 — evaluate MinerU2.5-Pro and GLM-OCR : check single-pass …".*
- **[declined: merged 2026-11-09 into the canonical-profile A/B and the 18-page demo boxes below as acceptance constraints; the R-SWA clause is consistent with the v10 freeze]** **P2 — Unlimited-OCR as a single-pass arm**: preserve the stock full-MHA path, Q5_K_M-or-better body, `lm_head >= Q8_0`, and conservative loop guard; do not take draft R-SWA PR #24975 into the production kernel.
- [x] **Correct the P2 observation record before using it** ✅ 2026-08-25 (mainA PIP-05): `progress/2026-08/2026-08-13-mainD.md` carries a supersession note — 18-page run retained as an observation; "root cause" → demonstrated prompt/profile mismatch (bare-passthrough GGUF chat template verified; "coordinate output regardless of prompt" NOT — llama.cpp canonical `tools/mtmd/tests/test-deepseek-ocr.py` records prompt-dependent behavior). Timing narrative corrected: stored receipt reports only `held_s=1.002881998` (pre-`aca459d9` ~1s post-health snapshot), not full-interval proof, and the run dir artifact is no longer on disk (`aca459d9` fixes future runs only). Remaining: canonical-profile A/B (row below), gated on inference-stop order lifting.
- [ ] **Run the canonical Unlimited-OCR profile as a fresh matched A/B after inference resumes**: use `document parsing.`, `n_predict=4096`, `n_ctx=16384`, DRY, and grounding-strip exactly as `tools/mtmd/tests/test-deepseek-ocr.py` specifies; preserve both profiles, score the stripped output, and require a new inference-window receipt spanning server launch through termination. The all-inference-stop order is NOT in force (corrected 2026-08-26; grants flowing 2026-11-07); row `pip04-unlimited-ocr18-paired-r2-20261107` (operator 2026-11-07) re-publishes the sealed packet. Model/build: Unlimited-OCR Q5_K_M-outq8 GGUF (sha256 b4c9ba49de7364b1e89767a19566cef618304d01cf030a45b0e5416978c926e2) + F16 mmproj, v10 production CPU kernel (production-consolidated-v10). Stop rule: stop-on-answer when both profiles have completed all 18 pages and been scored; stop-on-futility on a failed arm, a drain, or the grant deadline (exposed unknowns are never redrawn); gate-class = futility-only.
  - **2026-11-09 status (verified):** row `pip04-unlimited-ocr18-paired-r2-20261107` ran rc0 2026-11-07T20:33:54Z and was filed PASS 2026-11-08: 2 profiles x 18 pages = 36 records, 0 unknown, 0 scorer fallbacks, 6 `length_finish`. Original scorer text edit 0.359 / table TEDS 0.0120 / reading order 0.238; canonical profile 0.297 / 0.0114 / 0.173 (canonical better on text and reading order, TEDS about 0.01 in both; diagnostic only). **Not ticked:** the filing did not verify digests, linkage/residency, latency and cleanup receipts or adjudicate the A/B, and the scratch run directory is gone (only `r2-out/results.jsonl` with 3 unit lines survives; no vault archive found for this row id). Next (doable now): locate the `run/` data or declare it lost, record the adjudication, then tick this box and the demo box below together (same run). "After inference resumes" is stale: grants flow.
- [x] **Make the default Unlimited-OCR artifact quant-compliant** ✅ 2026-11-07 — `Unlimited-OCR-Q5_K_M-outq8.gguf` re-hashed today: SHA-256 `b4c9ba49de7364b1e89767a19566cef618304d01cf030a45b0e5416978c926e2`, equal to the recorded `ARTIFACT-GATE.md` value (root `6f8ff3a96`); per-tensor audit (155 tensors; only `output.weight` changed Q6_K→Q8_0, 154 byte-identical to the Q5_K_M source) is `artifacts/compute/codex3-unlimited-ocr-ready-20261031/TENSOR-AUDIT.json`; `DEFAULT_MODEL` points at the outq8 path on research origin/main (`scripts/benchmark/odl_bench/unlimited_ocr.py:84`). Artifact identity only: no generation, CER/TEDS or residency result. [no-belief: artifact identity record] *(Original row:)* replace/requantize the default model so `output.weight`/`lm_head` is at least Q8_0, record immutable SHA-256 plus tensor audit, and update `DEFAULT_MODEL`. *(2026-08-13 lane/mainD `a08b24dc`: a requantized `Unlimited-OCR-Q5_K_M-outq8.gguf` (2.26 GB, `output.weight` → q8_0 via `llama-quantize --allow-requantize --output-tensor-type q8_0`, other 154 tensors byte-copied, verified via `llama-gguf`) exists under `/mnt/raid0/llm/models/Unlimited-OCR-GGUF/` and `DEFAULT_MODEL` was repointed — research `c733e1ee`; the 22:18Z demo ran on it. Still missing: the immutable SHA-256 + tensor-audit record this row requires.)*
- [ ] **Run and score the 18-page OmniDocBench demo** (artifact gate cleared 2026-11-07, see above; row `pip04-unlimited-ocr18-paired-r2-20261107` published, keeper smoke PASS = real-model packet smoke rc 0; the row covers this box and the canonical-profile A/B) only after an inference grant: capture binary/model/mmproj digests, server argv, linkage/residency during the window, responses, CER/TEDS/reading-order/latency, failures, manifest contract, and cleanup proof.
  - *2026-11-09:* same run as the canonical-profile A/B above (done, filed PASS, receipts unadjudicated); tick both together once adjudicated. "Only after an inference grant" is satisfied.

#### Completed Scope

| Scope | Durable outcome |
|---|---|
| Phase 1 extractor | ODL is the availability-aware default with pdftotext fallback, quality checks, batch support, and attribution. |
| Phase 2 structured substrate | Headings, figures, tables, cache/TaskIR carriers, injection scanning, and hybrid SDK routing are wired behind explicit gates. |
| Fast-path scaffolding | Local ODL/LiteParse/pdftotext/hybrid probe and July observations exist; they do not close policy. |
| Benchmark scaffolding | `odl_bench`, sibling NID/TEDS/MHS scorer, model-producer interface, and representative manifests are committed. |
| 2026-08-13 audits | ODL-013 is a reproducible full-corpus observation, not a decision record: no parser protocol/category/attestation, no precommitted selection rule, scratch-only durability, and summary-only timing. A14's exact patch was accepted. Unlimited-OCR's 18-page run is mechanically real, but its causal claim and mutex evidence need correction before a canonical rerun. |

See [completed implementation/evidence ledger](../completed/opendataloader-pipeline-integration-completed-through-2026-08-13.md) for commits, historical measurements, corrections, and closed checkpoints.

#### Dependencies and Constraints

- Production orchestrator: `/workspace/repos/epyc-orchestrator`; benchmark code: `/workspace/repos/epyc-inference-research/scripts/benchmark/odl_bench/`.
- OpenDataLoader benchmark: `/mnt/raid0/llm/opendataloader-bench-upstream` (200 PDFs). OmniDocBench checkout: `/mnt/raid0/llm/omnidocbench` (renamed 2026-08-25 from the colliding `/mnt/raid0/llm/opendataloader-bench`) and page dataset `/mnt/raid0/llm/datasets/omnidocbench/`.
- Full-corpus ODL replay needs source PDFs or a deliberate document/page bridge; annotations and page images alone cannot reproduce PDF extraction.
- Live model-backed comparisons require an inference-owned window. Non-compute implementation, dependency pinning, artifact audits, and scoring-bridge work do not.
- Production llama.cpp v9 is frozen. Experimental kernel work must follow the version-past-production workflow; the current Unlimited-OCR scaffold needs no kernel patch.
- The ten-document Phase-2 chunk fixture and downstream RAG answer-correctness endpoint are mandatory. Ekimetrics/HOPE intrinsic scores cannot gate alone; RC/FMRE stay excluded until independently verified/licensed.

#### Key Files

- Orchestrator: `src/services/pdf_router.py`, `src/services/document_preprocessor.py`, `src/services/document_chunker.py`, `src/services/figure_analyzer.py`, `src/models/odl_structured.py`.
- Research: `scripts/benchmark/odl_bench/`, `scripts/benchmark/document_extraction_adapter.py`.
- Related handoff: [Document Parser Table Bench](knowledge-pipelines.md#track-document-parser-table-bench).
- Evidence review: [2026-08-13 auditor progress](../../progress/2026-08/2026-08-13-auditor.md).

#### Reporting Contract

For every run, record corpus/manifest digest, exact engine/dependencies/model/binary, metric direction and denominator, per-document failures, latency distribution, environment/residency proof during the observation window, and cleanup. Treat vendor numbers and unmatched historical artifacts as context, never as promotion evidence.

## Track: searxng-search-backend
<!-- gate: none -->

> Folded from `handoffs/active/searxng-search-backend.md` @ `ccf37cd0b6a4` on 2026-11-02 (BRF-T1-F8, route 1a, operator D1/D5; retired row RTG-33 → PIP-04). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Web Research Pipeline — SearXNG + Crawl4AI

**Status**: SX-1–4 done; root CLI fallback semantics hardened in `epyc-root` `fa75cfa`; CA-1–7 landed/validated in `epyc-orchestrator` `0dadb2e` + `38ddc97` + `6424d05`; 2026-07-06 pre-deploy audit confirms the live SearXNG endpoint is operational, with engine-mix drift noted below; SX-5/6 + CA-6 gated on AR-3 / Camofox
**Created**: 2026-04-14 (via research intake, deep-dive enriched)
**Updated**: 2026-07-06 (Crawl4AI backend landed on host/container port 11235; limited CA-7 Crawl4AI docs crawl helper landed; old 8086 hint conflicts with `worker_vision`; root `searx.sh` fallback hardening landed; SearXNG pre-deploy audit refreshed live runtime state)
**Categories**: search_retrieval, tool_implementation
**Tracked in**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P12

#### Four-Step Chain

```
Step 1: SearXNG  (host port 8888) — search, returns candidate URLs      SX-1–4 done, SX-5/6 gated on AR-3
Step 2: Crawl4AI (port 11235) — single-page markdown extraction        CA-1–5 landed/smoked
Step 3: Crawl4AI (port 11235) — limited multi-page crawl (docs/logs)   CA-7 landed/tested
Step 4: Camofox  (port 9377) — full browser, last resort only           CA-6 (deferred, intake-524)
```

Policy: **Camofox last.** Only open a real browser when the page forces it. Each step must be exhausted before escalating.

#### Objective

Replace the brittle DDG HTML scraping + Brave fallback in `epyc-orchestrator/src/tools/web/search.py` (lines 31-142) with a self-hosted SearXNG instance providing a structured JSON API that aggregates 250+ search engines without HTML parsing, bot detection workarounds, or per-engine rate limiting code.

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-359 | SearXNG (metasearch engine) | high | new_opportunity |
| intake-360 | SearXNG Documentation | high | new_opportunity |
| intake-361 | mcp-searxng (MCP bridge) | medium | worth_investigating |

#### Current State (search.py)

```
_search_duckduckgo() — 112 lines of fragile HTML parsing:
  curl → DDG HTML → regex parse result__a/snippet classes → fallback to Brave HTML → regex parse snippet-content
  Rate limiting: 2s hardcoded sleep between requests
  Failure mode: "result__a" class check for bot detection; falls through to Brave if DDG returns empty
```

Problems: (1) Layout changes break regex parsers, (2) Bot detection blocks after repeated queries, (3) Only 2 engines, (4) No structured metadata, (5) subprocess curl dependency.

#### Proposed Architecture

```
SearXNG Docker container (host port 8888, container port 8080, ~183MB)
  GET /search?q=...&format=json&engines=duckduckgo,brave,wikipedia,qwant
  → JSON: {results: [{url, title, content, engines[], positions[], score}], suggestions[], unresponsive_engines[]}
  → ColBERT reranker (S5): MaxSim on snippet content field, top-3
  → fetch + synthesize (existing research.py pipeline)
```

#### Deployment Plan

##### Docker (fits orchestrator_stack.py pattern)

Add to `DOCKER_SERVICES` list alongside NextPLAID containers:
```python
{
    "name": "searxng",
    "port": 8888,
    "image": "docker.io/searxng/searxng:latest",
    "description": "Metasearch aggregator (JSON API)",
    "volumes": [
        f"{_PATHS['project_root']}/config/searxng:/etc/searxng:Z",
    ],
    "args": [],  # Config via settings.yml, not CLI args
}
```

##### Minimal settings.yml

```yaml
use_default_settings: true
server:
  secret_key: "<generate with openssl rand -hex 32>"
  bind_address: "0.0.0.0"
  limiter: false              # MUST be false — API_MAX=4/hr blocks programmatic use
  public_instance: false
  image_proxy: false
search:
  formats:
    - html
    - json                    # MUST be present or JSON API returns 403
  default_lang: "en"
outgoing:
  request_timeout: 3.0
  max_request_timeout: 10.0
  enable_http2: true
```

Valkey sidecar NOT needed when limiter is disabled.

##### Engine Tuning

SearXNG supports per-engine configuration (finding #5). Each engine accepts: `timeout` (override global), `weight` (result scoring multiplier), `disabled` (user-toggleable) vs `inactive` (completely removed), `retry_on_http_error` (bool or specific codes like `[403, 429]`), per-engine proxy config, `api_key` for premium engines.

Initial tuning targets:
- Set engine weights favoring DDG and Brave (proven reliable in current `search.py`)
- Per-engine timeout to `3.0s` (matching `outgoing.request_timeout`)
- `retry_on_http_error: [429]` for rate-limited engines
- Disable Google engine explicitly (`inactive: true`) — TLS fingerprint blocking (issue #2515)
- Enable DDG, Brave, Wikipedia, Qwant, Startpage as primary engine set

The `engines=` API parameter also allows per-request engine selection — could route different query types to different engine sets in future.

##### _search_searxng() implementation (~15 lines)

```python
def _search_searxng(query: str, max_results: int = 5) -> list[dict[str, str]]:
    params = {"q": query, "format": "json"}
    resp = urllib.request.urlopen(
        urllib.request.Request(f"http://localhost:8888/search?{urllib.parse.urlencode(params)}"),
        timeout=10,
    )
    data = json.loads(resp.read())
    return [
        {"title": r["title"], "url": r["url"], "snippet": r.get("content", ""),
         "score": r.get("score", 0), "engines": r.get("engines", [])}
        for r in data.get("results", [])[:max_results]
    ]
```

#### Pre-Deployment Checklist

- [x] Verify `limiter: false` in settings.yml (finding #1: API_MAX=4/hr blocks all programmatic use when enabled) ✅ 2026-07-06
- [x] Verify `json` in `search.formats` list (finding: returns 403 without it — not enabled by default) ✅ 2026-07-06
- [x] Confirm Granian ASGI server running, NOT uWSGI (finding #4: Granian replaced uWSGI in recent builds; do NOT configure uWSGI workers) ✅ 2026-07-06
- [x] Test with python urllib/requests user-agent succeeds (finding #2: bot detection disabled when limiter is false) ✅ 2026-07-06
- [x] Reconcile configured engine profile before SX-6 default swap: the live runtime disables DDG/Qwant/Startpage, uses Bing as a primary engine, and sees Brave rate-limit noise under repeated probes. Decision: accept the current Bing/Brave/Wikipedia profile rather than reverting to blocked engines; `searxng_health_report.py` now uses `{"bing", "brave", "wikipedia"}` as the bad-query denominator and reports the configured engine set in JSON/human output. ✅ 2026-07-06

##### 2026-07-06 Runtime Audit

A `gpt-5.4-mini` sidecar ran a read-only pre-deploy audit against the live
container. Findings:

- Runtime config is bind-mounted from
  `/mnt/raid0/llm/epyc-orchestrator/config/searxng/settings.yml` and matches
  the checked-in config for `server.limiter: false` and
  `search.formats: [html, json]`.
- `GET http://127.0.0.1:8888/search?q=epyc&format=json` returns `200 OK`,
  `content-type: application/json`, and `server: granian`.
- The container process tree shows a `searxng` master/worker, not uWSGI.
- Default Python `urllib` and `python-requests/2.32.3` user agents both receive
  `200` JSON responses.
- Five sequential query probes returned `200` in about `0.92s` to `2.70s`, under
  the configured `outgoing.request_timeout: 3.0`.
- Engine health is usable but not clean: probes usually report one
  `unresponsive_engines` entry, most often Brave rate limiting or suspension.
  The first probe also saw Wikidata HTTP error noise.

Verdict: endpoint operational; engine-mix/signoff remains open.

#### Post-Deployment Monitoring

Wire `unresponsive_engines[]` from JSON response into orchestrator telemetry (finding #6). The JSON API reports `[["engine_name", "error message"], ...]` for every failed engine per query — useful for diagnosing upstream blocking without checking container logs.

- Log `unresponsive_engines` on every `_search_searxng()` call (same telemetry path as DS-1 queue depth in `routing_meta`)
- Alert when >50% of configured engines appear in `unresponsive_engines` for 3+ consecutive queries
- Track engine failure rate over time to detect gradual degradation (DDG CAPTCHA, Brave rate limiting)

##### Post-AR-3 Analysis Script (NIB2-31, 2026-04-21)

`scripts/analysis/searxng_health_report.py` aggregates SX-4 telemetry + `web_search` tool latency into a go/no-go verdict for the SX-6 default swap.

```bash
# Last 7 days (default window)
python3 scripts/analysis/searxng_health_report.py

# Specific day
python3 scripts/analysis/searxng_health_report.py --date 2026-04-21

# Date range
python3 scripts/analysis/searxng_health_report.py --from 2026-04-14 --to 2026-04-21

# Machine-readable (CI / dashboards)
python3 scripts/analysis/searxng_health_report.py --json
```

Verdict is `PROCEED` / `HOLD` / `INSUFFICIENT_DATA`. Thresholds: bad-query rate >5% (engines >50% down), fallback rate >10%, SearXNG p95 > 2× DDG p95, or <20 observed queries. Exit code 0 for PROCEED/INSUFFICIENT_DATA, 1 for HOLD — suitable for pre-swap CI gate.

#### Critical Caveats (from deep-dive)

1. **Google blocks SearXNG** via TLS/HTTP2 fingerprinting (issue #2515). Expect Google engine to be unreliable. Mitigation: rely on DDG/Brave/Wikipedia/Qwant.
2. **Limiter MUST be disabled** for backend use. API_MAX=4/hr is a hard blocker. Bot detection also blocks python-requests/curl user-agents. `limiter: false` disables both.
3. **JSON format not enabled by default** — must add `json` to `search.formats` or GET /search?format=json returns 403.
4. **No max_results API parameter** — fixed ~20 results/page, client-side truncation needed.
5. **Single-user instances** more easily fingerprinted by upstream engines than multi-user public instances.
6. **Granian ASGI server has replaced uWSGI** — the docs reference architecture still shows uWSGI but the actual container uses Granian. Do not configure uWSGI workers.

#### Open Questions

- Does SearXNG reliably return DDG/Brave results under EPYC's query volume (~50-200 searches/session) when Google is excluded?
- Should SearXNG run in the orchestrator_stack.py Docker management (alongside NextPLAID) or as a standalone docker-compose service?
- Is the `engines[]` multi-provenance data useful for the ColBERT reranker's confidence scoring?
- Can the `suggestions[]` response field enhance query reformulation in the web_research pipeline?
- Should the MCP server pattern (intake-361) be deployed for Claude Code sessions as a separate concern?

#### Work Items

Mirrors P12 in [`routing-and-optimization-index.md`](routing-and-optimization-index.md). Both locations must stay in sync.

- [x] **SX-1: Docker container deployment** — ✅ 2026-04-14; port drift audited 2026-06-13. SearXNG in `DOCKER_SERVICES` on host port `8888` (container port `8080`, ~183MB). Config: `config/searxng/settings.yml`. Health check fix: `health_path: "/"` (SearXNG has no `/health`). **TESTED**: Container starts, health check passes, serves JSON on `/search?format=json`. **Launch hygiene note**: do not use host port `8090`; `8090-8095` are BGE embedding servers and return llama-server 404s for `/search`.
- [x] **SX-2: `_search_searxng()` implementation** — ✅ 2026-04-14. Added to `search.py`. Returns `{title, url, snippet, score, engines[]}` from JSON API. `web_search()` wrapper tries SearXNG first when flag enabled, falls back to DDG on failure. **TESTED**: 3/3 query types pass (normal 908ms, domain-filtered 653ms, niche 836ms). Multi-engine consensus confirmed (3-engine score ~9.9, 2-engine ~3.3, 1-engine <1).
- [x] **SX-3: Engine tuning** — ✅ 2026-04-14. `config/searxng/settings.yml`: Google `inactive: true`, DDG weight 1.2, Brave 1.1, Wikipedia 1.0, Qwant 0.9. Per-engine timeout 3.0s, Qwant `retry_on_http_error: true`.
- [x] **SX-4: `unresponsive_engines[]` telemetry** — ✅ 2026-04-14. `_search_searxng()` logs `searxng unresponsive_engines: ...` on every call with failures. Folded into AR-3 Package D Phase 6b for production validation.
- [x] **SX-4b: Root SearXNG CLI fallback hardening** — ✅ 2026-06-14 in `epyc-root` `fa75cfa`. `scripts/search/searx.sh` now treats valid JSON without a `.results` array as an invalid SearXNG endpoint and exits documented fallback code `2`, matching the wrong-port `8090` / BGE-server case. Validation: `bash -n scripts/search/searx.sh`; `git diff --check -- scripts/search/searx.sh`; healthy `bash scripts/search/searx.sh 'Python programming language' --top 2`; wrong-port `SEARX_URL=http://localhost:8090 ...` returned fallback stderr/code `2`; orchestrator `uv run pytest -q tests/unit/test_web_search_searxng_config.py tests/unit/test_autopilot_preflight_audit.py` -> 12 passed.
- **[declined: ws58 2026-11-03 content-review: folded into AR-3 Package D by its own text]** **SX-5: Load test** — Folded into AR-3 Package D. Web_research sentinel suite (50q) provides realistic load validation. Post-AR-3: analyze engine failure rates + latency via Phase 6b checks.
- [ ] **SX-6: Swap default** (**retitled 2026-11-09: SX-6 sentinel measurement; the default swap itself is DONE, `src/tools/web/search.py:31` defaults `ORCHESTRATOR_SEARXNG_DEFAULT` to "1"**) — **TRIGGER NOTE 2026-11-07:** the code default is already ON (`src/tools/web/search.py:31`, `522696d4b`), so this box is a measurement, and it cannot run now: `searxng_health_report.py` over 2026-04-14..2026-11-07 returns INSUFFICIENT_DATA (0 SearXNG and 0 DDG queries in 208 days of logs) and no SearXNG container is running (nothing on :8888). TRIGGER = the stack brings SearXNG up via `orchestrator_stack.py` (operator/stack-lifecycle action; the stack stays down for now). THEN publish the drafted row `/mnt/raid0/llm/tmp/pip04-rows/pip04-sx6-searxng-sentinel.spec.json` (needs its driver script written) and run the report: PROCEED iff bad-query <=5 %, fallback <=10 %, p95 <=2x DDG, n>=20. Feature flag `ORCHESTRATOR_SEARXNG_DEFAULT=1` implemented. (Stale 2026-11-09: the AR-3 / Autopilot gate no longer applies; the measurement needs only the stack up with SearXNG on :8888 plus the driver script, which is doable now.) Original: confirm no regression → lock in swap. See bulk-inference-campaign.md Phase 6b. [2026-11-09 apr2 rtg08-evl47-pip04-code: driver WRITTEN on orchestrator branch `apr2/rtg08-evl47-pip04-code-20261109` (85832ecb): `scripts/benchmark/sx6_sentinel_driver.py` runs the research `web_research.yaml` queries through `web_search` into a driver-owned log root (tool_use jsonl + SX-4 logger lines), optional `--ddg-baseline` for the p95 gate; refuses without SearXNG up, flag off, or <20 queries; `searxng_health_report.py --log-root` reads that root. Tests `tests/unit/test_sx6_sentinel_driver.py` + `test_searxng_health_report.py`: 7 passed. Never run live (no SearXNG). Remaining: stack brings SearXNG up, the row launcher wraps this driver, run the report. [no-belief: driver code, no measurement]]

#### Crawl4AI Work Items (Steps 2+3)

Chosen over Firecrawl after deep-dive (2026-05-05): single container, Apache-2.0, ~1–2 GB idle, undetected Chrome mode self-hosted, BM25 `fit_markdown`, no external SDK. Full detail: [`research/deep-dives/firecrawl-vs-crawl4ai-web-pipeline-steps-2-3.md`](../../research/deep-dives/firecrawl-vs-crawl4ai-web-pipeline-steps-2-3.md)

- [x] **CA-1**: Add Docker launcher support for `container_port`, `--shm-size`, sorted `env` flags, per-service `run_timeout`, and timeout cleanup in `scripts/server/stack_docker.py` — ✅ 2026-06-14 in `epyc-orchestrator` `0dadb2e` + `38ddc97`.
- [x] **CA-2**: Add Crawl4AI to `DOCKER_SERVICES` — ✅ 2026-06-14 in `0dadb2e` + `38ddc97`; host/container port is `11235`, not the earlier `8086` plan, because the current stack already assigns `8086` to `worker_vision`; Crawl4AI has `run_timeout: 180` for first-run image startup.
- [x] **CA-3**: Implement `_fetch_page_crawl4ai()`, `_is_blocked_page()`, `_poll_crawl4ai_task()`, flexible Crawl4AI response parsing, cache helpers, and provenance-preserving fetch envelopes in `src/tools/web/research.py` — ✅ 2026-06-14 in `0dadb2e`.
- [x] **CA-4**: Route `_fetch_page()` through Crawl4AI `/crawl` first when enabled; keep urllib / `html.parser` fallback if Crawl4AI is disabled, unreachable, blocked, or returns no extractable content — ✅ 2026-06-14 in `0dadb2e`.
- [x] **CA-5**: Live smoke / activation — ✅ 2026-06-14. After `38ddc97`, the real `unclecode/crawl4ai:latest` container started through the stack helper on port `11235`; `/health` returned ok; `POST /crawl` extracted `https://example.com`; and `_fetch_page("https://example.com", max_length=500)` returned `success=True`, `fetch_backend="crawl4ai"`, and non-empty Example Domain markdown. The ad hoc smoke container was removed afterward and `docker inspect crawl4ai` confirmed no such object.
- **[declined: ws58 2026-11-03 content-review: deferred on Camofox, which nothing schedules]** **CA-6** *(deferred — needs Camofox, intake-524)*: Wire `escalate_to_camofox` signal from `_is_blocked_page()` into step 4 call [2h]
- [x] **CA-7**: `_fetch_docs_crawl_crawl4ai()` for step 3 limited BFS crawl — ✅ 2026-06-14 in `epyc-orchestrator` `6424d05`. Opt-in helper builds a bounded `BFSDeepCrawlStrategy` payload with default `limit=5`, default `max_depth=2`, `include_external=false`, and hard caps at `limit<=20` / `max_depth<=3`; returns provenance-rich page records and preserves default `_fetch_page()` / `web_research` behavior. Validation used mocked Crawl4AI responses because the service was not running during this pass.

CA-6 waits for Camofox. CA-7 helper is present but not wired into default synthesis; the single-page backend smoke is complete.

##### Implementation Update — 2026-06-14 (`epyc-orchestrator` `0dadb2e`)

`0dadb2e` adds Crawl4AI as the browser-backed `web_research` fetch backend and refreshes generated stack priors/descriptors. `_fetch_page()` now checks cache first, tries local Crawl4AI `POST /crawl` at `ORCHESTRATOR_CRAWL4AI_URL` (default `http://localhost:11235`), preserves `retrieved` / `content_sha256` / `fetch_backend` provenance, and falls back to urllib extraction on Crawl4AI failure. Crawl4AI can be disabled with `ORCHESTRATOR_CRAWL4AI_DISABLE=1`; timeout override is `ORCHESTRATOR_CRAWL4AI_TIMEOUT_SECONDS`.

Validation recorded by the main lane:
- `python3 -m py_compile` on touched web/docker files and tests passed.
- Focused ruff on touched files passed.
- Web/docker focused pytest passed 31 tests.
- Adjacent manifest/web/docker pytest passed 84 tests.
- `stack_change_pipeline.py check --run-promotion-gate` passed with promotion gate 48 tests and known warnings only.

##### Launch Timeout Follow-Up — 2026-06-14 (`epyc-orchestrator` `38ddc97`)

The first live smoke attempt hit a launch-hygiene blocker before Crawl4AI could be evaluated: first-run `docker run` for `unclecode/crawl4ai:latest` exceeded the old hardcoded 30s timeout and raised `subprocess.TimeoutExpired`. No container or image was left behind. `38ddc97` adds per-service `run_timeout` metadata support, sets Crawl4AI `run_timeout: 180`, cleans up on timeout, returns `None` instead of crashing, and adds focused unit coverage.

Additional validation recorded by the main lane:
- `python3 -m py_compile` on touched Docker/manifest test files passed.
- Focused ruff on touched files passed.
- `tests/unit/test_stack_docker.py` -> 12 passed.
- Adjacent manifest/web/docker pytest passed 85 tests.
- `stack_change_pipeline.py check --run-promotion-gate` passed with promotion gate 48 tests and known warnings only.

##### Live Smoke — 2026-06-14

After `38ddc97`, the real Crawl4AI container started successfully through the stack helper:

- `curl -fsS http://localhost:11235/health` returned `{"status":"ok", ...}` with Crawl4AI `version: 0.8.9`.
- `POST http://localhost:11235/crawl` against `https://example.com` returned `success: True` with extracted content.
- `PYTHONDONTWRITEBYTECODE=1 uv run python` smoke calling `_fetch_page("https://example.com", max_length=500)` returned `success=True`, `fetch_backend="crawl4ai"`, `cached=False`, and non-empty Example Domain markdown.
- Cleanup: `docker rm -f crawl4ai` succeeded, `docker ps -a --filter name=crawl4ai` returned no rows, and `docker inspect crawl4ai` returned `no such object`.

##### Limited Crawl Helper — 2026-06-14 (`epyc-orchestrator` `6424d05`)

`6424d05` adds opt-in `_fetch_docs_crawl_crawl4ai()` in `src/tools/web/research.py` for step-3 docs/log crawls without changing the default `_fetch_page()` or `web_research` synthesis path. The helper builds a bounded Crawl4AI `BFSDeepCrawlStrategy` payload (`max_pages=limit`, `max_depth`, `include_external=False`) with defaults `limit=5` and `max_depth=2`, hard caps `limit<=20` and `max_depth<=3`, and polls async task ids when `/crawl` returns a task envelope.

The result parser walks common Crawl4AI response shapes, normalizes relative URLs, deduplicates URLs, skips blocked pages, truncates per-page content, and records `url`, `success`, `retrieved`, `content_sha256`, `fetch_backend="crawl4ai_crawl"`, and `depth` per page. Live smoke was not rerun because no Crawl4AI service was listening on `localhost:11235` in this window.

Validation recorded by the main lane:
- GitNexus impact for `_fetch_page_crawl4ai`, `_extract_crawl4ai_markdown`, and the test file was LOW.
- Focused ruff on `src/tools/web/research.py` and `tests/unit/test_web_research_crawl4ai.py` passed.
- `tests/unit/test_web_research_crawl4ai.py` passed 7 tests.
- Adjacent web/docker/manifest suite passed 77 tests.
- `py_compile` and `git diff --check` passed.
- `epyc-orchestrator` GitNexus refreshed after commit at `53,173 nodes`, `91,274 edges`, `1117 clusters`, `300 flows`.

#### Dependencies

- **Blocks**: CA-6 blocked on intake-524 Camofox; SX-5/6 remain AR-3 gated; CA-7 live service smoke or integration into synthesis remains optional/future if needed
- **Composes with**: `colbert-reranker-web-research.md` S5 (SearXNG snippets → ColBERT reranking → Crawl4AI fetch)
- **Replaces**: `_search_duckduckgo()` in `search.py` (SX) and `html.parser` fetch in `research.py` (CA)

#### Notes

AGPL-3.0 license — no issue for self-hosted internal tool use (no distribution). Python 80.5%, 9340+ commits, actively maintained (docs version 2026.4.13). LiteLLM has first-class SearXNG integration as reference pattern. Docker image from DockerHub or GHCR.

#### Research Intake Update — 2026-04-14

##### New Related Research
- **[intake-364/365] "Firecrawl: Web Data API for AI"** (firecrawl.dev / github.com/firecrawl)
  - Relevance: Web scraping/crawling API (108K+ GitHub stars) that converts websites to LLM-ready markdown — complementary to SearXNG which handles search but not deep scraping
  - Key technique: Scrape, crawl, map, interact (click/type/scroll) APIs; P95 latency 3.4s; 96% web coverage; MCP server for Claude Code
  - Delta from SearXNG: SearXNG = search aggregation (250+ engines → JSON). Firecrawl = deep page scraping (HTML → markdown/JSON). Different roles — SearXNG finds URLs, Firecrawl extracts their content. Currently used as disabled cloud tool in hermes-outer-shell.
  - Caveats: AGPL-3.0 license. Self-hosted version lacks cloud parity (/agent, /browser not supported). Credit-based pricing on cloud (unpredictable with JSON mode +4 credits, stealth +4 credits per page).
- **[intake-372] "Crawl4AI: Open-Source Web Crawler for LLMs"** (github.com/unclecode/crawl4ai)
  - Relevance: Fully self-hosted Firecrawl alternative (51K+ stars, Apache-2.0). Local LLM integration via Ollama. No API keys required.
  - Key technique: Async Playwright-based crawler; BM25 content filtering; LLM extraction with local models (Llama 3, Mistral); browser pool management
  - Delta from SearXNG: Same relationship as Firecrawl — page content extraction, not search. But self-hosted and free, matching our infrastructure philosophy.
  - Integration path: If research intake pipeline needs page scraping beyond WebFetch (e.g., for JS-heavy pages, PDFs), Crawl4AI could be deployed alongside SearXNG. Docker deployment available. Worth evaluating for ColBERT reranker fetch step (colbert-reranker-web-research.md S5).

**Policy note (2026-04-14)**: Given open-source-only infrastructure preference, Crawl4AI (intake-372, Apache-2.0) is the preferred evaluation target for deep page scraping. Firecrawl (intake-364/365) evaluation deferred — cloud-first SaaS model conflicts with self-hosted philosophy. Evaluate Crawl4AI after AR-3 when web_research sentinel data quantifies JS-heavy fetch failure rates. If WebFetch suffices for >90% of pages, neither tool is needed short-term.

#### Research Intake Update — 2026-04-24

##### New Related Research

- **[intake-453] "Reason-mxbai-colbert-v0-32m: Edge-Scale Reasoning ColBERT (32M params)"** (`huggingface.co/DataScience-UIBK/Reason-mxbai-colbert-v0-32m`)
  - Relevance: candidate CPU-latency-friendly reranker over SearXNG top-K results. 32M params ≈ 5× smaller than current 150M GTE-ModernColBERT-v1 on :8089; could drop reranker call from ~180 ms → ~40 ms if PyLate→ONNX export path works.
  - Delta: this sharpens the reranker choice behind SearXNG output but does not change the search-engine tuning or SX-5/6 work items. Tracked primarily in `colbert-reranker-web-research.md` — flagged here so SX-5 analysis factors in the latency/quality trade.

#### Research Intake Update — 2026-04-30

##### New Related Research

- **[intake-519] "Granite-Embedding-97M-Multilingual-R2"** (HF `ibm-granite/granite-embedding-97m-multilingual-r2`, Apache 2.0, IBM, released 2026-04-29)
  - Relevance to SearXNG backend: **MEDIUM**, primarily as the candidate dense first-stage retriever for a SearXNG → dense-rerank → ColBERT-rerank pipeline. SearXNG returns mixed-language web snippets; a 200+-language 97M ModernBERT encoder with 32K context (vs e5-small's 512) handles longer snippets without chunking and runs CPU-fast (~2.9k docs/s claimed).
  - Delta to current SearXNG work: no change to SX-5/6 items, but if the team chooses a dense first stage to bound the candidate set fed to ColBERT, Granite-97M-r2 is the new size-class baseline to beat — replaces or supersedes any implicit multilingual-e5-small assumption.
  - Tracked primarily in `colbert-reranker-web-research.md` and `internal-kb-rag.md` 2026-04-30 updates. Flagged here so SX-5 analysis factors in dense-stage latency/quality trade.

###### Deep-dive refinement (2026-04-30) — bench owned by granite-97m-r2-bench-plan

Bench handoff at [`granite-97m-r2-bench-plan.md`](../completed/granite-97m-r2-bench-plan-completed-through-2026-08-23.md). For SearXNG SX-5/6 specifically: the dense first-stage choice (granite-97m-r2 vs BGE-M3 vs multilingual-e5-base) will come out of that bench. Defer SX-5 dense-stage decisions until Phase B completes. Note that the bench's eval corpus is currently planned as code-snippets-plus-handoffs, NOT mixed-language web snippets — if SearXNG-specific quality matters, add a SearXNG-output slice to the bench's eval-corpus engineering (Phase A-4).

**Phase-C correction (2026-07-29):** Phase B selected Granite conditionally:
0.9222 NDCG@10 versus BGE-M3's 0.9150 at 4.36× lower wall-clock (1.614s versus
7.037s). If SX-5 introduces a multilingual dense first stage, Granite is the
default encoder. This does not change SX-5/SX-6 activation gates or establish
mixed-language-web quality; a SearXNG-output extension slice is still required
before making that stronger claim.

#### Research Intake Update — 2026-05-04

##### New Related Research
- **[intake-524] "camofox-browser — Stealth headless browser REST API for AI agents"** (github.com/jo-inc/camofox-browser)
  - Relevance: Camofox is the **browser interaction** layer in the SearXNG→Firecrawl→Camofox three-tool stack — the same architecture this handoff's SearXNG component anchors. When SearXNG returns URLs and Firecrawl/direct-fetch returns 429/403/CAPTCHA, Camofox is the fallback that opens a real browser.
  - Key technique: REST API (port 9377) wrapping Camoufox (Firefox fork with C++ fingerprint spoofing). Tools: `browser_open`, `snapshot`, `click`, `navigate`, `screenshot`. Accessibility snapshots are ~90% smaller than raw HTML with stable element refs for LLM interaction.
  - Reported results: ~40MB idle memory, confirmed bypass of Cloudflare and Google bot detection, ~90% token reduction vs raw HTML.
  - Delta from current approach: the canonical four-step fallback chain is **Search (SearXNG) → Scrape (Firecrawl single-page) → Crawl (Firecrawl limited) → Browse (Camofox)**. Camofox is the last resort — "expensive, stateful fallback" per the source doc — only opened when the page forces interaction. Firecrawl covers two steps (scrape + crawl-limited) before Camofox is invoked. This is different from a simple "Firecrawl fails → Camofox" trigger; the crawl-limited step (small page cap for docs/changelogs) should also be attempted first.
  - Action item: after AR-3 data is available (SX-5/6 gate), check fetch-failure rate in web_research logs. If >15% of fetches fail with 403/429/CAPTCHA **after both Firecrawl scrape and crawl-limited attempts**, add camofox-browser to `orchestrator_stack.py` DOCKER_SERVICES at port 9377 and wire `_fetch_camofox()` as the terminal fallback in `web/research.py`. Do not short-circuit to Camofox before Firecrawl crawl-limited is tried.

#### Research Intake Update — 2026-05-05

##### New Related Research — Crawl4AI (Steps 2+3 resolved)
- **[intake-372] "Crawl4AI — Open-Source LLM-Friendly Web Crawler"** (github.com/unclecode/crawl4ai)
  - Relevance: **HIGH** — deep-dive (2026-05-05) resolved the step 2+3 question in the four-step chain. Crawl4AI is the chosen scraper; Firecrawl (intake-364/365) was evaluated and ruled out (verdict updated to `not_applicable`).
  - Key finding from deep-dive: Firecrawl self-hosted lacks fire-engine (cloud-only anti-bot), requires 5-service docker-compose (incompatible with `start_docker_container()`), and uses 4–8 GB idle RAM. Crawl4AI is a single container, Apache-2.0, ~1–2 GB idle, with undetected Chrome mode self-hosted.
  - Integration: the [Crawl4AI Work Items](#crawl4ai-work-items-steps-23) section above has the current implementation plan (CA-1 through CA-7, port 11235 after the 2026-06-14 port correction).
  - Deep-dive: [`research/deep-dives/firecrawl-vs-crawl4ai-web-pipeline-steps-2-3.md`](../../research/deep-dives/firecrawl-vs-crawl4ai-web-pipeline-steps-2-3.md)
  - **Sequencing**: CA-1 through CA-4 landed in `0dadb2e`; CA-5 live smoke remains independent of SX-5/6 (ColBERT gate). CA-6 (Camofox escalation wiring) waits for intake-524 Camofox integration.

##### 2026-07-14 Runtime Audit — engine-pool degradation (blocked a research-intake Tier-2b sweep)

Reproducible this date: `/healthz` returns 200 (instance up), but the usable engine pool is effectively dead for our egress IP —
- `brave` → "too many requests"; `mojeek` → "access denied" (both land in `unresponsive_engines`).
- `bing` (the sole responder) returns **off-topic filler** for technical queries — e.g. `"lossless weight compression DFloat11"` returned DaFont font pages and Chinese TikTok how-to guides; `wikipedia` added nothing relevant.
- Net effect: `searx.sh` exits 0 with valid JSON but junk results (it does **not** trip the exit-2 fallback), which silently defeated a research-intake Tier-2b contradiction sweep on 2026-07-14 (all 6 queries returned dictionary/clock/homepage noise).

**Mitigation landed same day**: `scripts/search/searx.sh` now emits a `⚠ DEGRADED` stderr warning when ≥ half the requested engines are unresponsive (keyed on the response's own `unresponsive_engines`; exit code unchanged so partial results still flow). Surfaces the degradation instead of returning silent junk.

**Still open (operator)**: brave/mojeek rate-limits/blocks and bing junk-for-our-IP are an instance/egress-IP problem, not fixable in the bash bridge. Options: rotate egress IP, add SearXNG engine keys/credentials, or widen the default engine set to ones that respond from this IP. Until then, prefer built-in WebSearch for correctness-critical sweeps.


#### 2026-07-25 — intake Stage-2a dive: Firecrawl verdict label correction

_Via `/research-intake` Stage-2 2026-07-25; see [`intake-derived-work-2026-07-25.md`](../completed/frontier-lab-automation.md)._

- **[declined: ws58 2026-11-03 content-review: intake bookkeeping]** **Change the intake-364 / intake-365 verdict from `not_applicable` to `superseded`** (by intake-372, Crawl4AI). Firecrawl is **AGPL-3.0 open-source and fully self-hostable** (`SELF_HOST.md` + `docker-compose.yaml` stand up `/v1/scrape`, `/v1/crawl`, `/v1/map` locally) — it is in scope and was **out-competed**, not out-of-scope. EPYC policy treats `not_applicable` as the verdict requiring the most justification; here the justification exists (a 322-line deep dive) but the label misstates it, which is how a well-reasoned rejection gets re-litigated.
- [x] **Correct two now-outdated objections in the notes** ✅ 2026-07-29 — verified against upstream Firecrawl `7bd7f66de8a5b9dc391eae2fe382d3392631c3c3`, `SELF_HOST.md:57-79` and `docker-compose.yaml:39-42,55-57`: self-hosted `/search` can use a JSON-capable SearXNG endpoint through `SEARXNG_ENDPOINT` / `SEARXNG_ENGINES` / `SEARXNG_CATEGORIES`, while `/extract` accepts `OPENAI_BASE_URL` / `OLLAMA_BASE_URL` / `MODEL_NAME`. This corrects the facts only; it does not change the Crawl4AI decision.
- [x] **The decisive objection strengthened** ✅ 2026-07-29 — verified against upstream Firecrawl `7bd7f66de8a5b9dc391eae2fe382d3392631c3c3`: `docker-compose.yaml:62-207` defines seven services, including the optional FoundationDB runtime pair, while its two explicit resource limits already reserve 6 CPUs / 12 GB (`:63-119`). `SELF_HOST.md:21-24` still states that self-hosted instances lack Fire-engine and require manual configuration beyond fetch/Playwright. That maintains the resource-cost objection and the conclusion that the self-hosted engine ladder tops out at Playwright.
- [x] For **CA-6 (Camofox escalation)**, consider Firecrawl's **ranked engine-waterfall** pattern — numeric per-engine quality scores plus a per-request ordered fallback list — instead of extending the substring blocklist in `_is_blocked_page()`. ✅ 2026-07-29 — decision recorded from upstream Firecrawl `7bd7f66de8a5b9dc391eae2fe382d3392631c3c3`, `apps/api/src/scraper/scrapeURL/engines/index.ts:221-229,730-801` and `ENGINE_FORCING.md:11-25`: when CA-6 is unblocked, preserve `_is_blocked_page()` as a narrow detector and model escalation as an ordered, provenance-logged backend chain (Crawl4AI scrape → bounded crawl where applicable → Camofox). Carry the terminal reason and each attempted backend; do not add markers merely to encode routing policy. CA-6 remains open pending Camofox and its >15% terminal-failure gate.

## Track: sliders-local-validation
<!-- gate: none -->

> **2026-11-10 — Phase 0 gate 0.4 closed as superseded** (operator design audit): the call-count gate was never measurable and the r4 run is an observation, not a verdict. Nothing is concluded about SLIDERS' viability or structured-DB QA. Continues in `## Track: integrated-aggregation` below; design: [`docs/design/integrated-document-aggregation-plan-20261110.md`](../../docs/design/integrated-document-aggregation-plan-20261110.md). `data/sliders_validation/01_*` and `02_*` stay as reference.

> Folded from `handoffs/active/sliders-local-validation.md` @ `ccf37cd0b6a4` on 2026-11-02 (BRF-T1-F8, route 1a, operator D1/D5; retired row EVL-43 → PIP-04). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Handoff: SLIDERS Local-LLM Validation

**Status**: REFRESHED 2026-05-28 — parked Phase 0 falsification gate; does not block KB-RAG
**Created**: 2026-04-28 (from intake-494, refined deep-dive 2026-04-28)
**Updated**: 2026-05-28 (executor gate clarified; no integration before KB-RAG K7)
**Priority**: LOW (speculative — does NOT block any production work)
**Categories**: rag_alternatives, knowledge_management, context_management
**Related**: [`internal-kb-rag.md`](knowledge-pipelines.md), [`context-folding-progressive.md`](context-and-token-economy.md), [`research-evaluation-index.md`](research-evaluation-index.md)
**Source paper**: SLIDERS (arxiv:2604.22294, Stanford OVAL/Genie group, Joshi/Shethia/Dao/Lam, submitted 2026-04-24)
**Source code**: `github.com/stanford-oval/sliders` (MIT, also on PyPI as `sliders-genie`)

> **Does NOT block `internal-kb-rag.md`. KB-RAG K1–K7 ships independently. SLIDERS is an ALTERNATIVE architecture (DB+SQL replacing retrieval), not an upgrade lane on the ColBERT path. Sequential evaluation only after KB-RAG K7 ships, and only if Phase 0 below passes.**

> **🔔 Reopen-PRECONDITION fired — 2026-07-18 stale-open audit.** The first reopen precondition (KB-RAG K1–K7 ships) FIRED: KB-RAG **K7 CERTIFIED 2026-06-13**. This does NOT auto-reactivate — SLIDERS stays parked (LOW/speculative) pending an **explicit operator decision** to evaluate the DB+SQL alternative. Surfaced so the fired precondition isn't silently missed. See [`stale-open-audit-2026-07-18.md`](../completed/frontier-lab-automation.md#track-stale-open-audit-2026-07-18).

- [x] Operator decision: KB-RAG K7 precondition fired — evaluate SLIDERS DB+SQL alternative (Phase 0 falsification) now, or keep parked? ✅ 2026-11-07 — ANSWERED by the operator: "evaluate now, low-priority filler" (E4 'R36 rebuild + SLIDERS as filler'). Box 0.4 below is the open work item. [no-belief: operator decision]

#### 2026-05-28 Audit Reset — Executor Start Here

This remains a bounded falsification gate, not a speculative integration project.

| Condition | Action |
|---|---|
| KB-RAG K7 has not shipped | Do not prioritize SLIDERS unless the operator explicitly asks for a structured-DB alternative now. |
| Phase 0 starts | Use upstream MIT SLIDERS in `/mnt/raid0/llm/scratch/sliders/`; do not vendor code. |
| Coder-30B substitution fails API plumbing | Fix the adapter and rerun; do not call the verdict inconclusive. |
| EDGAR is unreachable | Document the specific failure and propose one bounded replacement corpus before running 0.3. |
| Schema hallucination >20% or call count >5x | Close `not_viable_local`; do not prompt-engineer around the gate. |

Decision artifact must be `data/sliders_validation/04_phase0_verdict.md`. The closure claim is narrow: "SLIDERS as released on local Coder-30B at this corpus scale," not "structured DB QA is bad."

#### Agent Operating Instructions

- This handoff is gated by a Phase 0 falsification test. Do NOT begin Phase 1 until Phase 0 produces a written GO verdict.
- Phase 0 is bounded — if either gate condition trips, CLOSE the handoff as `not_viable_local` and document the closure with the failing measurement. Do not iterate trying to make it work.
- All Phase 0 work happens against the upstream MIT-licensed `github.com/stanford-oval/sliders` repo, in a scratch directory. **Do not vendor SLIDERS into our repos until Phase 1 passes.**
- Closure-inflation policy (per `feedback_closure_inflation.md`): on close, enumerate which gate(s) tripped and which did not. Do not generalize to "structured-DB QA architectures are not viable on local LLMs" — only "SLIDERS as released, on Coder-30B at this corpus scale, fails gate X".
- After Phase 0 completes (either verdict): update `progress/YYYY-MM/YYYY-MM-DD.md`, update the row in `research-evaluation-index.md`, and update the entry in `master-handoff-index.md`.

#### Objective

Determine whether SLIDERS — a structured-DB+SQL alternative to retrieval-based RAG that replaces text-concatenation reasoning with persistent relational state — can run on EPYC's local Coder-30B-class models. The released SLIDERS code is hard-wired to GPT-4.1 / GPT-4.1-mini via the OpenAI / Azure OpenAI APIs at every stage. Local-model adoption requires both endpoint substitution and validation that small-model SQL-agent-loop quality survives.

#### Why this is gated, not an active workstream

- **Frontier-API-only by construction**: every stage (schema induction, relevance gating, extraction with quote+rationale columns, primary-key selection, reconciliation controller+executor, SQL generation, answer synthesis, citation generation) calls GPT-4.1 / GPT-4.1-mini. There is no local-model code path in the released repo.
- **Schema hallucination risk**: schema hallucination is the #1 production failure mode for LLM-to-SQL pipelines (web evidence: production failures dominated by schema hallucinations + incorrect join paths). SLIDERS' per-question schema induction (from the fixed `sliders_taxonomy.json` library) partially mitigates this, but the schema is still LLM-driven. Coder-30B may schema-hallucinate at a rate that breaks the controller/executor loop (5 iter × 5 SQL × 3 retries × 20 inspections — brittle to small-model errors).
- **Scale gap**: SLIDERS' headline gains (+~32 pp / +~50 pp on 36M-token FinQ100) are at corpus scales 100× our wiki+handoff corpus. The headline gain likely does not materialize at our scale even if local-model substitution works.
- **Stronger architectural alternatives exist for our scale**: the ColBERT-based KB-RAG (`internal-kb-rag.md` K1–K7) is the sized-appropriate architecture for our 24 wiki articles + 70 active handoffs + 30 research notes + 246 source documents. SLIDERS is for orders-of-magnitude-larger corpora.

#### Phase 0 — Falsification Gate (mandatory before any Phase 1+ work)

Goal: a single written verdict, GO or `not_viable_local`. ~2–3 sessions of work. No production code, no integration with KB-RAG.

- **[declined: ws58 2026-11-03 content-review: merged into the Phase-0 gate as its step]** **0.1 Catalogue GPT-4.1 call sites**: clone `github.com/stanford-oval/sliders` (MIT) into a scratch directory under `/mnt/raid0/llm/scratch/sliders/`. Read every Python file. Produce `data/sliders_validation/01_call_site_catalog.md` listing every distinct LLM call site with: stage name (one of: schema_induction, relevance_gating, extraction, primary_key_selection, reconciliation_controller, reconciliation_executor, sql_generation, answer_synthesis, citation_generation), file path + line number, model expected (GPT-4.1 vs GPT-4.1-mini), prompt template length (tokens), output structure (free-form vs JSON vs SQL).
- **[declined: ws58 2026-11-03 content-review: merged into the Phase-0 gate as its step]** **0.2 Local-model substitution**: substitute the OpenAI client at all sites with our local OpenAI-compatible Coder-30B endpoint. Use the existing `epyc-orchestrator` Coder-30B wrapper as the Python adapter (do not vendor a new client). Produce `data/sliders_validation/02_substitution_diff.md` showing the unified diff. Do NOT modify any prompt templates yet — first measure the unmodified-prompt baseline.
- **[declined: ws58 2026-11-03 content-review: merged into the Phase-0 gate as its step]** **0.3 FinQ5 end-to-end run**: pick the first 5 questions from FinQ100 (we will need to regenerate the corpus from SEC EDGAR via SLIDERS' `experiments/sec_10q.py` — this is bounded, ~30 minutes if EDGAR is reachable). Run SLIDERS end-to-end on each question with the Coder-30B substitution. Record per-question, per-stage:
  - Pass/fail vs expected answer (FinQ100 ships with ground-truth)
  - Total LLM call count (target: ≤ 5× the GPT-4.1 baseline reported in the paper, since we're API-free)
  - Schema hallucination rate (defined: SQL emitted by Coder-30B references columns / tables that were not in the per-question schema spec). Detect via repo's existing schema-validation step.
  - Wall-clock time per question
  - Output: `data/sliders_validation/03_finq5_results.json`
- **[declined: superseded 2026-11-10 by AGG track; the call-count gate was unmeasurable (the paper reports no per-question call counts); Coder-30B left the stack. Observation: r4 FB5 Q1 used >=757 LLM calls / 4.05M prompt tokens without finishing (~9.7 h on one CPU quarter); /mnt/raid0/llm/tmp/sliders-phase0-fb5-coder30b-r4-20261109] [no-belief: superseded, no verdict]** **0.4 Gate decision**: write `data/sliders_validation/04_phase0_verdict.md` containing one of: Steps (absorb 0.1-0.3): clone stanford-oval/sliders into scratch and catalogue every GPT-4.1 call site; substitute the local OpenAI-compatible coder endpoint at all sites; run FinQ5 end to end; then write the verdict. Runs only if the operator answers the SLIDERS decision above with "evaluate now". **ANSWERED 2026-11-07: evaluate now, low-priority filler** — steps 0.1-0.3 are non-inference prep (scratch clone, call-site catalogue, substitution diff) followed by one CPU Coder-30B filler row. [2026-11-09 apr2 rtg08-evl47-pip04-code: 0.1 and 0.2 DONE as documents on the root branch: `data/sliders_validation/01_call_site_catalog.md` (all call sites, one factory `llm.py:145`) and `02_substitution_diff.md` (substitution is configuration: provider `openai` + `OPENAI_BASE_URL`, zero source diff, prompts untouched). 0.3 NOT started and its premise is wrong: `experiments/sec_10q.py` has no EDGAR downloader, no questions file is shipped, and FinQ100 is 36M tokens; the FinQ5 corpus must be supplied or an alternative bounded set chosen (decision needed, see 02). The filler row is not written. Box stays open. [no-belief: prep documents, no run]]
  - *2026-11-09:* `data/sliders_validation/` does not exist in root or orchestrator; a scratch clone exists at `/mnt/raid0/llm/scratch/sliders` (cloned 2026-11-02), so 0.1 may be partly done but nothing is recorded. Steps 0.1-0.3 are doable now; the final CPU Coder-30B row is a normal filler grant. No Autopilot dependency.
  - **`not_viable_local`** if EITHER schema hallucination > 20% (averaged over 5 questions × all SQL emissions) OR per-question call count > 5× the GPT-4.1 baseline. State which gate(s) tripped, with the actual measured numbers. CLOSE this handoff. Do NOT generalize to "structured-DB QA architectures are not viable on local LLMs" — the closure is specific to SLIDERS as released, on Coder-30B, at FinQ5 scale.
  - **`go_phase_1`** if BOTH gates met. Document the FinQ5 pass rate and per-stage call counts. Proceed to Phase 1.
  - **`inconclusive`** is NOT an allowed verdict. If the run was incomplete or the substitution failed at the API layer, fix the bug and re-run; do not close the gate as inconclusive. (The single exception: if EDGAR is unreachable and FinQ regeneration is impossible, document that and propose an alternative bounded test set in 0.3.)


  - **2026-11-09 prep (prep-kbctx; nothing ticked, box stays open):** EDGAR returned HTTP 403 (AkamaiGHost) to a default-UA client, and the FinQ100 corpus + questions file are not shipped in the upstream repo (`configs/sec_10q_sliders.yaml` points at `/path/to/datasets/...`), so step 0.3 as written cannot start. Per this handoff's own rule the bounded replacement is **FB5**: the first 5 distinct-document FinanceBench open-source questions (data and PDFs fetched from `patronus-ai/financebench`, pins in `/mnt/raid0/llm/datasets/financebench-20261109/fb5_pins.json`, jsonl sha256 `a5a2aa67...71877`). The verdict stays narrow: SLIDERS as released on Coder-30B at FB5 scale. Built: venv `/mnt/raid0/llm/venvs/sliders-20261109` (no docling; markdown input via ODL local), adapter `sliders_q.py` (model-name substitution in a config copy, prompts untouched; counting proxy for LLM calls; DuckDB Binder/Catalog errors = schema hallucination), job + launcher in `/mnt/raid0/llm/tmp/sliders-phase0-fb5-coder30b-20261109/` (Qwen3-Coder-30B-A3B Q4_K_M sha256 `fadc3e5f...`, v10 CPU kernel from the kernel store with `verify_ggml_linkage.sh`). Row `sliders-phase0-fb5-coder30b-20261109` published at rank 24; smoke not yet passed. The >5x call gate needs the paper's GPT-4.1 per-question call count, which the verdict step must supply. [no-belief: prep, no measurement]
  - **2026-11-09 FILED, box stays OPEN, n = 0 (row `sliders-phase0-fb5-coder30b-20261109`):** never granted. Its keeper dry run (4 cores, 13:44Z) started the Qwen3-Coder-30B-A3B server (identity and preflight reply OK in 19 s) but wrote no measured record within the 1,500 s first-progress limit (`out/results.jsonl` holds only the non-numeric identity and preflight records), was terminated at 14:09Z (rc 143, `launcher-signalled`), and the row was unpublished (`dryrun/<id>/FAIL-1.json`). No FB5 question ran, so there is no schema-hallucination rate, call count or wall-clock. Either the first question takes longer than 25 min on 4 cores or it hung; the log is `/mnt/raid0/llm/tmp/sliders-phase0-fb5-coder30b-20261109/work/q-financebench_id_00005.log`. [no-belief: no measurement]
  - [declined: superseded 2026-11-10 by the integrated-aggregation track (AGG-0.x); the verdict step states why the first question cannot finish: released SLIDERS on Coder-30B used >=757 calls / 4.05M prompt tokens on FB5 Q1 without finishing (r4, ~9.7 h on one CPU quarter); see box 0.4] **SLIDERS-0.3-R2 — read the q-financebench_id_00005 log, make the job write a numeric per-question record early (or declare `unit_key`/`smoke_predicate` in the spec), and republish.** Done when a granted run records the FB5 gates or the verdict step states why the first question cannot finish. [no-belief: native-pending:VB-ROWFILE-20261109-WIRE]
    - 2026-11-09 apr2 rerun-fixes (partial, box stays open): log read. The question was running, not hung: 119 LLM calls, 148,280 prompt and 7,491 completion tokens in 25 min on 4 cores, `sql_total` still 0 (extraction stage; the only traceback is a BrokenPipe in the counting proxy when the smoke killed the client). The smoke failed only because the preflight record was all strings. Fix: the preflight record now carries numeric `server_ready_s`, `preflight_tokens`, `n_questions_planned` (`scripts/row_jobs/sliders_phase0_job.py`, 3 tests pass). Row `sliders-phase0-fb5-coder30b-r2-20261109` (rank 24, supersedes r1, port 19472) published, smoke queued. Whether one question finishes inside the 9000 s per-question cap on 24 cores is still unmeasured. [no-belief: not-a-result]
    - 2026-11-09 SLIDERS r2 -> r3 -> r4 (box stays open, n = 0, no FB5 gate recorded): r2 was stopped (STOP file) and filed withdrawn; r3 (`sliders-phase0-fb5-coder30b-r3-20261109`, a copy of r2 on one quarter, about 13 h booked) was STOPPED after its first question: `financebench_id_00005` took 5,516 s, 100 LLM calls, 0 SQL executions, answer `[Error] Request timed out.` yet recorded `status: ok`. Cause: SLIDERS hard-codes a 200 s client timeout and sends up to 16 concurrent calls to a 2-slot server, so requests expired in the queue (76 abandoned in that question). r4 (`sliders-phase0-fb5-coder30b-r4-20261109`, quarters q1+q2, 48 threads, `-np 4` with the same context per slot, estimate 8 h not 12 h) patches the client timeout to 3,600 s in the `sliders.llm` `get_llm_client` wrapper on BOTH import paths (verified both receive it), prompts unchanged, and scores an `[Error]` answer as `fail`, not `ok`. In flight, do not report as done: the smoke only proves the server starts; the first real question shows whether timeouts are gone. The keeper printed "over contract quarter by 0 cores" at booking; check the granted shape. Process lesson recorded in `.claude/skills/inference-backlog-scheduling/SKILL.md` section 4. [no-belief: not-a-result]

#### Phase 1 — Conditional: FinanceBench Subset (only after Phase 0 GO)

- **[declined: ws58 2026-11-03 content-review: conditional on a Phase-0 GO that has not happened; refile then]** **1.1** Run SLIDERS+Coder-30B on a 10-question FinanceBench subset (FinanceBench corpus is referenced by SLIDERS as one of its three existing-benchmark baselines). Record same metrics as Phase 0.3.
- **[declined: ws58 2026-11-03 content-review: conditional on Phase-0 GO]** **1.2** Run our internal-kb-rag K7 evaluation pipeline on the *same* 10 questions but with a chunk-RAG over the FinanceBench corpus. Compare answer accuracy and recall on the same questions, with the ~1pp Flywheel variance band as the noise floor.
- **[declined: ws58 2026-11-03 content-review: conditional on Phase-0 GO]** **1.3** Decision: does SLIDERS-on-Coder-30B beat ColBERT-on-Coder-30B on this benchmark by enough to justify maintaining a parallel architecture? If delta < 5 pp, close as `phase_1_inconclusive_no_advantage`. If delta ≥ 5 pp, escalate to Phase 2 scoping.

#### Phase 2 — Conditional & Speculative: Alternative-Architecture Scoping (only after Phase 1 escalates)

- **[declined: ws58 2026-11-03 content-review: scoping conditional on Phase 1, two gates away]** **2.1** SCOPING ONLY. Produce a written scope for "SLIDERS as alternative architecture for K3/K4 of KB-RAG". Consider: parallel paths (maintain both ColBERT and SLIDERS, route per-query) vs replacement (drop ColBERT) vs hybrid (use SLIDERS for high-aggregation queries, ColBERT otherwise). Include explicit cost estimate (LLM call count per query × specialist cost). **Hard rule**: do NOT merge SLIDERS into the KB-RAG handoff. Maintain two paths or close — never blur the distinction.

#### Closure Section (TO BE FILLED ON CLOSE)

When this handoff closes (either via Phase 0 `not_viable_local` or Phase 1 `phase_1_inconclusive_no_advantage` or Phase 2 deciding not to escalate), append a closure block here with:
- Final verdict
- Which gate(s) tripped, with measured numbers
- Closure-inflation discipline statement: which specific claim is being closed, and which broader claims are NOT being closed (e.g., "SLIDERS-as-released on Coder-30B at FinQ5 scale fails gate X" does NOT close "structured-DB QA architectures are not viable on EPYC")
- Move handoff to `handoffs/completed/` with the closure block as the closing artefact

#### Out of Scope

- Wholesale adoption of SLIDERS into production KB retrieval. That is what Phase 2 scoping deliberately defers.
- Modifying SLIDERS prompts to "fix" Coder-30B failures during Phase 0. Phase 0 measures unmodified-prompt baseline; prompt engineering for small models is a separate (and probably unbounded) work item.
- Re-implementing SLIDERS in our codebase. Phase 0 runs against upstream MIT code in a scratch directory.
- Validation against datasets that SLIDERS does not ship code to regenerate (e.g., Loong, Oolong if not reproducible). FinQ100 / WikiCeleb100 / FinanceBench subset are the in-scope corpora.

#### Cross-References

- **Source intake**: intake-494 in `research/intake_index.yaml` (full Tier 2b critique + GPT-4.1-only adoption blocker documented).
- **Sibling KB architecture**: `internal-kb-rag.md` K1–K7 (ColBERT-based RAG, the sized-appropriate alternative for our corpus scale).
- **Cross-cutting in research-evaluation-index**: registered as a monitoring/experimental row (this handoff's Phase 0 gate is the exit criterion).
- **Master-handoff-index**: dispatched via `research-evaluation-index.md` entry.

#### Effort Estimate

- Phase 0: ~2–3 sessions, single-shot gated. Bounded.
- Phase 1 (conditional on Phase 0 GO): ~2 sessions.
- Phase 2 (conditional on Phase 1 escalate): ~1 session, scoping only.
- Total even in best case: ≤ 6 sessions. Most likely outcome: Phase 0 closes the handoff as `not_viable_local` after ~2 sessions.

### D-LSA research intake — approved 2026-11-03

- [x] **LSA-INTAKE-XREF-1 — Repair intake validation of historical handoff references after the approved backlog folds: resolve old filenames only through an unambiguous committed fold mapping to an existing owner and Track heading; reject unknown, ambiguous and dangling targets. Apply the same resolution to index and cross-reference-map checks, add focused moved/missing/ambiguous tests, and require the full intake validator to exit zero before closing this campaign.** ✅ 2026-11-03 [no-belief: software verification]

Validation evidence: 53 regression tests and 16 subtests passed; the exact approved-plan/checkpoint validator passed all 2,623 entries. The resolver follows committed fold and MEQ lineage and rejects missing, ambiguous, cyclic and dangling references. No model performance or quality result is implied.

##### 2026-11-05 operator-adhoc follow-ups (operator-adhoc-ops-20261105 wrap-up)

- **[declined: operator 2026-11-07 — superseded: the keeper already treats rc 0/75 as a clean stop (`rowflow.py:3088-3095`), rowflow2 auto-ends rc=75 and re-queues (`4b78e3716`), and the disk floor now PAUSES instead of stopping (`d2b1be6d1`, operator 'Pause with hysteresis'); the residual per-packet paddle launcher logic belonged to the unrecoverable r35 packet (19 reaped pins) and is replaced by the reviewed R36]** **PADDLE-RC75-RESUME — the paddle wrapper must treat rc75 (tempfail/disk-floor) as resumable, not failure** (~19 rows affected; codex3).

## Track: integrated-aggregation
<!-- gate: none -->

Design: [`docs/design/integrated-document-aggregation-plan-20261110.md`](../../docs/design/integrated-document-aggregation-plan-20261110.md) (rev 2, operator-approved 2026-11-10). One pipeline over the current document flow with a cost-based planner; replaces the SLIDERS Phase 0 gate (superseded; reuses only SLIDERS' row shape and taxonomy). Closure scope: "integrated planner + lazy fact layer on Qwen3.6-35B-A3B / Qwen3.8-27B at 10-doc scale"; nothing is concluded about SLIDERS' viability.

- [x] **AGG-0.1 — Freeze corpus, questions and verified golds (no compute).** 10 FinanceBench 10-Ks pinned by
  sha256 (FB5 + 5); 20 constructed cross-document aggregation questions with gold derived by script from the
  metrics-generated gold answers **and hand-verified against the filings by a named reviewer, with the
  verification record committed**; 10 original single-fact questions for P-large and 10 for P-small; M1-M5 and
  the kill gate predeclared as in the design doc §(c). Done when the frozen set, verification record
  and rules file have sha256s recorded here; an unverified question is excluded, not assumed.
  - Progress 2026-11-10 (not ticked): build landed in epyc-inference-research `7651a8c2c` (question set, gold review sheet, predeclared gate, runner skeleton); all 10 PDFs now present and sha256-pinned in `corpus.json`. DRAFT golds (facts_sheet 76/80 cells filled, `verified: false`, 20 aggregation golds derived, 5/5 FinanceBench anchors agree) are on research branch `agg0/gold-draft-20261110` (`005950d9d`, NOT main); awaiting operator hand-verification, then merge. [no-belief: draft awaiting verification, no measurement]
  - Done 2026-11-10: golds hand-verified by two independent readers (78/80 cells exact match; PayPal dividends NA, 4 medium cells accepted and agg18 restated without JPMorgan by operator decision) and merged to epyc-inference-research main `aed5730f9` (verification commits `c45e784db`, `832d1f146`). All 20 aggregation questions `verified: true` in `verification_record.json`; the 10 single-fact questions stay unverified and are excluded, not assumed. sha256 (first 16) in `benchmarks/agg_phase0/`: corpus.json `86aab1bb509368c0`, aggregation_questions.json `f43c5aaca8047d15`, golds.jsonl `fd88b13f0027002d`, verification_record.json `cec684c8a897e061`, PREDECLARED.md `0e2b09e77f92596d`. Diffs and medium cells: `GOLD_DIFFS.md`. [no-belief: gold set curated, no measurement]
- [ ] **AGG-0.2 — Corpus store + deterministic layers over the existing parse (no compute).** Persist
  `DocumentPreprocessResult` under content hash; L1 BM25 and L2 index registry keyed (corpus, hash, builder,
  model); L3 `facts` from `DocumentPreprocessResult.tables` + regex spans; catalog→GBNF SQL grammar; tests with a
  fake backend. Done when the 10 parsed docs load once and every layer reads the same store, L3-only M1 is
  reported (informational), and out-of-catalog SQL is rejected by the grammar.
  - Progress 2026-11-10 (not ticked): code landed in epyc-orchestrator `e4e727ae` (store, registry, L3 facts, SQL grammar; flag-off, 11 unit tests pass). Still open: the 10 parsed docs loading once into the store and the L3-only M1 report (needs verified golds). [no-belief: code landed, no measurement]
  - Progress 2026-11-10 (not ticked): r2 load ran, but every parse was flat (`tables: []`, `total_pages: 1`). l3_load was calling the production path correctly; the defect was in production (ODL-PARSE-SCHEMA in the opendataloader-pipeline-integration track), fixed in orchestrator `5354fc0b`. Re-run prepared, unpublished: `/mnt/raid0/llm/tmp/agg0-l3-load-20261110-r3/spec.json` (supersedes r2; orchestrator rebuilt 2026-11-10 from `08d1f0af4236` = parse fix + L3 text-row extractor, research `95915e7c9`, SOURCE.sha256 669 files, fresh `out/`, no r2 cache). Expect pages/headings; tables may stay 0 (ODL-LOCAL-NO-BORDERLESS-TABLES). [no-belief: fix + prepared job, no measurement]
- [ ] **AGG-0.3 — Planner and lazy L4 (no compute beyond a smoke).** Typed planner (Choice over paths + Score,
  deterministic size rules outside the ambiguous band, `decision_receipt.v1`), L4a-d with cached prefix,
  `pin_slot`, `n_predict` cap, quote check, native-catalogue reconcile, 27B audit sample, per-stage
  `cache_n`/prefill receipts; planner skipped (no LLM) when C ≤ 60k and Q = 1. Done when a fake-backend run
  produces facts end to end, the small-corpus path builds no L2-L4 index, and the job writes numeric per-stage
  records early.
  - Progress 2026-11-10 (not ticked): planner + lazy L4 landed in epyc-orchestrator `e4e727ae` (fake-backend end to end and small-corpus-no-index tests pass). Still open: the job writing numeric per-stage records early (receipts are in-memory only). [no-belief: code landed, no measurement]
- [ ] **AGG-0.4 — Phase-0 run (one CPU quarter + one MI210 window, normal grants).** P-large ingest on
  worker_general with M1 and the M5 manifest check computed before the GPU window is requested; then audit, the
  30 P-large questions, B1 on 30, B2 on 5, P-small and B-today on 10. Done when M1-M5 and all arms are filed with
  the frozen rules' sha256 and a belief-kernel row. [inference] est 21600 s (CPU arms ran about 6 h).
  - 2026-11-10: CPU arms row agg0-arms-cpu-20261110 filed PASS (M1 after L4d = 0.92 ≥ 0.70, no futility stop); GPU arms row agg0-arms-gpu-20261110 published, awaiting a GPU gap; the box ticks when the combined verdict lands. [no-belief: row verdict filed by agent]
  - Progress 2026-11-10 (not ticked, autopilot-backlog-session): the arms are wired and the jobs are sealed, but nothing has run.
    - Orchestrator `2a422b7c` adds `src/aggregation/llm_backend.py`, a private llama-server backend on `/v1/chat/completions` with GBNF grammar, cache_prompt, id_slot and an n_predict cap. Its L4a gate reads the yes/no logprobs via `typed_decisions.confidence`, and a context overflow is recorded as `out_of_window`, never truncated.
    - Research `6877ac57c` + `5ec8e1966` add `phase0_arms.py`, which `run_phase0.py --phase cpu|gpu-audit|gpu-answers|score` drives. Coverage: M5 manifest first, lazy L4 with resumable fsynced units, M1 and futility 2, the 27B audit, P-small / B-today / P-large (size-rule planner, typed call stubbed) / B1 / B2, and the mechanical verdict via `agg_phase0.score`.
    - The deterministic scorer replaces CJ-8. PREDECLARED.md was amended pre-data on 2026-11-10; its new sha256 is `0cb303a4d81598329a0f02466f4b18ecc973fe1609992d2e9e7950a63c7a1230`. It supersedes the AGG-0.1 `0e2b09e77f92596d` value for runs.
    - Keeper jobs (unpublished):
      - `/mnt/raid0/llm/tmp/agg0-arms-cpu-20261110/` runs on a CPU quarter, port 9481. It needs a COMPLETE L3 load with n_tables > 0 and pages > 1, from `AGG0_L3_DIR` (default `-r3`; `-r2` is INVALID).
      - `/mnt/raid0/llm/tmp/agg0-arms-gpu-20261110/` runs in an MI210 gpu-quiet exclusive window on 184-191, ports 9482 and 9483. It needs the CPU job COMPLETE with M1 >= 0.70. It runs the np4 recipe for the audit, then the np1 196k recipe for every answer arm.
    - Registry discrepancy, not edited: worker_general/ingest_long_context `draft_max 7` with KV q8_0, against the codified recipe files' `draft_n_max 8` with f16. The recipes are used.
    - Tests: orchestrator 17 passed; research `test_agg_phase0*.py` 17 OK.
    [no-belief: code landed, no measurement]
- [ ] **AGG-0.5 — Verdict.** `go_phase_1` or `superseded_v2_not_viable` with the tripped gate named; closure
  scoped to "integrated planner + lazy fact layer on Qwen3.6-35B-A3B / Qwen3.8-27B at 10-doc scale". On GO,
  file AGG-1.x (25-30 docs, Oolong-real check, incremental re-ingest, one backfill field, mid-size parity) and
  the Phase-2 integration decision package.


- **AGG-0.2/0.3 non-compute finish (autopilot-backlog-session, 2026-11-10).** No box ticked: AGG-0.2 needs the granted
  load run to complete, and AGG-0.3's L4 per-stage records are the AGG-0.4 `stage_ingest` wiring, which needs inference.
  Done now: (a) research `6c70550e7` `benchmarks/agg_phase0/l3_load.py` writes fsynced numeric per-stage records per
  document (`probe|parse|store|l3_doc|doc_done|doc_fail|stop|corpus|m1_l3|done`), is resumable per document (doc_done
  skip, parse cache, idempotent ingest), honours FILLER_DEADLINE/STOPFILE/SMOKE, rc 75 partial; (b)
  `m1_l3_report.py` (stdlib, informational: M1 is `null` with `no_gold_cells_filled` while facts_sheet.csv has 0 of 80
  cells filled, never 0.0; plus candidate coverage); (c) keeper job `/mnt/raid0/llm/tmp/agg0-l3-load-20261110/`
  (spec.json, launch.sh, job.sh, precond.sh, smoke_check.py, check_complete.py, SOURCE.sha256 over orchestrator
  `e4e727ae` + research `6c70550e7` byte copies). No model: local-ODL parse (JVM + Python), deterministic store/L1/L3;
  every record carries llm_calls 0. Tests: research `unittest discover -s tests -p "test_agg_*.py"` 17 OK (orch venv
  python, `AGG_ORCH_ROOT`); orchestrator `test_aggregation_phase0.py` 11 passed. Not run: the parse (CPU grant).
  Gap named: the interpreter + ODL overlay + JRE import is proven only by precond at grant time. Unpublished; the main
  session publishes the row.
