# Research intake — Agent Memory Repo and EmbeddingGemma 2 — 2026-10-07

Stage 1 ingestion and preliminary current-consumer comparison are complete. All five entries remain `stage1-unverified`, `read_depth: DIGEST`, and `awaiting_dive`. Publisher claims have not been independently reproduced. Selected-source deep dives (Stage 2), a reviewed Stage-3 action plan and approved Stage-4 filing remain distinct steps.

## Processed entries

| Record | Source | Novelty | Relevance | Credibility | Provisional verdict |
|---|---|---|---|---|---|
| intake-1963#record | [Cognition Agent Memory Repo](https://cognition.com/agent-memory-repo) | low | high | unscored | adopt_patterns |
| intake-1964#record | [Google EmbeddingGemma 2 model card](https://huggingface.co/google/embeddinggemma-2) | medium | high | 1 | worth_investigating |
| intake-1965#record | [Official AgentMemoryRepo specification and local skill](https://github.com/AgentMemoryRepo/agentmemoryrepo) | low | high | unscored | adopt_patterns |
| intake-1966#record | [EmbeddingGemma 2 developer guide](https://developers.googleblog.com/en/embeddinggemma-2-the-developer-guide/) | medium | high | 1 | worth_investigating |
| intake-1967#record | [Official ggml-org GGUF artifact](https://huggingface.co/ggml-org/embeddinggemma-2-GGUF) | medium | high | unscored | worth_investigating |

Both user inputs and all three companion URLs are new after an unbounded normalized-URL/arXiv identifier sweep of all 1,958 surviving prior entries. Existing ID gaps were preserved. Root allocated new IDs only after fetching/fast-forwarding the isolated lane to `99b3763078abd859026c8051e1c480b89a15ee72`; the prior index bytes were preserved as an exact prefix. Three depth-1 entries came from primary-source links, zero from search; this uses 3 of the 10-entry expansion cap. The Google launch announcement is supporting discovery/custody, not another entry or independent corroboration.

## Preliminary source/current-consumer comparison

**Memory:** the Cognition record describes a compact entry point, linked topic notes, source/date metadata, separate owner repositories and proposed periodic consolidation. Existing project-wiki compilation, source hashes, query tools, per-writer records and episodic recall already cover substantial ground. Root rejected a blanket broken-link audit as redundant with current structural checks and the recently completed 114-source compilation. Potential additions to verify are task-focused knowledge briefs at cold start, reusable diagnostic-artifact links, owner-scoped composition and a proposal-only source-change maintenance pass. No automatic editing, installation, push-after-every-edit policy or scheduled job was adopted.

The article's broader Dreaming/swarm examples are illustrative, not controlled measurements. The linked local trial omits automatic startup and scheduled Dreaming; its commit guidance is narrower than the article's push guidance. Git merge detection does not establish semantic contradiction resolution. Relevant prior records: intake-268#record, intake-269#record, intake-270#record and intake-492#record. Relevant owners inspected include episodic-memory-integrity, internal-kb-rag, repl-session-memory-maturity, session-bus-thin-dispatcher and completed knowledge-base-governance/wiki-compilation handoffs.

**Embedder:** the Google record reports code NDCG@10 78.68 versus its predecessor's 68.76, while multilingual mean moves 61.15 to 61.36. These vendor comparisons do not establish a win over the project's BGE, MiniLM or ColBERT routes. The candidate is 768-dimensional with supported smaller MRL vectors, an 8,192-token context, task-specific asymmetric retrieval prompts, mean pooling and BF16/FP32 guidance. Truncated vectors need normalization; FP16 has explicit model-card caveats. Same-checkpoint multimodal configurations do not establish compatibility with incumbent vector spaces. Phone RAM claims are not EPYC measurements.

Consumer inspection is pinned to orchestrator `2b0a727e490b1e4a01f1d2d720dcc7d0349d630e`:

- `src/repl_environment/context_search.py:121-126,292-297` already supplies BGE query prefixes; raw document chunks appear at 369-373. Model-ID-bound reset/refusal exists at 339-342 and 423-424. Root corrected the preliminary reader's blanket no-prefix assertion.
- `src/embedding_pool/cache.py:17-22` keys model identity and exact text. Existing identity separation should be reused; changing model, revision, prefix, pooling or dimension requires separate candidate vectors/cache identity.
- `orchestration/repl_memory/embedder.py:34-38,141-153,339`, `episodic_store.py:250-260` and `routing_graph.py:63-84,341,382` use default 1,024-dimensional BGE task/episodic/routing vectors. Generic task embeddings are a distinct semantic use; absence of retrieval prefixes there alone is not a bug. Width changes require migration/re-encoding and router review.
- `src/vision/analyzers/clip_embed.py:150-160,176-212` implements MiniLM text-description embeddings; the CLIP image path is separate. `src/vision/search.py:40-45,96-111` consumes description vectors. A text retrieval comparison and any multimodal branch have separate scope.
- KB ColBERT is a separate configured route. Configuration/code inspection does not prove any service is active or accepted in production. Relevant older model record: intake-519#record.

The frozen llama.cpp source at `ffc1bac82eeca6f9099e1ccd9ba49703c460a115` registers `gemma-embedding`, while the official converted artifact advertises `gemma-embedding2`. This source mismatch warrants experimental-runtime compatibility verification; it is not an observed load failure or evidence about a running binary. No kernel, model weight, endpoint, dependency, vector schema or runtime was changed.

## Bounded contradiction search

Primary sources and bounded implementation/adversarial searches were reviewed for memory contradictions, version-2 dtype/runtime problems and BGE comparisons. No independent version-2-vs-EPYC-incumbent controlled result surfaced. This search absence is provisional. Same-publisher model-card/guide/launch restatements are not independent corroboration. Older EmbeddingGemma-300M runtime/pooling reports were not transferred to version 2. The memory trial/specification limits implementation claims about the broader proposed consolidation loop.

## Recommended deep dives — operator selects

| Rank | Record | What a dive would settle |
|---|---|---|
| 1 | intake-1964#record | Exact code-retrieval mechanism, prompts, dtype/dimension contract and relevance to existing consumer workloads |
| 2 | intake-1967#record | Converted architecture, upstream runtime/pooling support and a safe experimental path past the frozen kernel |
| 3 | intake-1963#record | Which source-linked task briefing/artifact/composition patterns add capability beyond current wiki and recall |
| 4 | intake-1965#record | What the shipped skill/spec actually implements versus the proposal's automatic maintenance narrative |
| 5 | intake-1966#record | Exact library/API and task-prefix contract for a separate full-precision reference and candidate |

All five are recommended as two tightly bounded source groups: memory (intake-1963, intake-1965) and embedder (intake-1964, intake-1966, intake-1967). No entries were dismissed as inapplicable. Companion artifacts are related evidence, not extra independent votes.

Preliminary actions remain unverified hypotheses in the retained checkpoint. A later retrieval deciding screen must freeze a native corpus/query manifest and actual baseline, retain per-item outputs and complete failure/invalid/abstention denominators, use held-out or later queries, and predeclare quality/latency promotion or stop conditions. Runtime/source verification should precede this workload screen; broader reproduction needs an observable trigger. Stage 3 will identify exact owners after the selected dives, not create redundant mechanism tasks now.

## Steering and custody

One current operator request is retained verbatim in `.research-session.json`, together with all preliminary actionables and source revisions/digests. Empty `entries_remaining` means ingestion finished, not campaign closure. The displaced checkpoint was already Stage-4 complete; its exact prior bytes remain in scratch and are recoverable through the checkpoint's parent git reference. No prior campaign ledger was erased from history. Scratch and the locked intake worktree remain retained for the next stage.

Cognition HTML, the pinned Google card/API, pinned AgentMemoryRepo README/SPEC, Google launch/developer guide and pinned GGUF card/API are retained under `/mnt/raid0/llm/tmp/intake-memory-embedding-20261007/`; the checkpoint records their SHA-256 and byte sizes. Model revision: `914f7f89142e33e77833254d9c9b90c3cef7303b`; memory repo: `8798cb26c817d451a5ed6cba0ad8d9eca8d5ec3e`; GGUF collection: `bfcd298762cc34d0357ece5ebdd31791a3a374d8`.

## Validation and scoped wrap-up

`bash scripts/validate/validate_intake.sh` exited 0: taxonomy valid, all 1,963 surviving entries validated. Initial wrong handoff path prefixes were corrected to the required basenames before this successful run. `index_state.py --check` exited 0 (zero problems; existing advisory warnings for the missing ignored graph and 145 unrelated handoffs without Scratch fields). README freshness and whitespace checks exited 0. Final publication and remote containment are recorded in retained scratch receipts, outside the provisional evidence claims.

No handoff, domain/master index or wiki edits were made for this Stage-1 task. No task checkboxes are claimed complete beyond this ingestion phase. Main owns persistence/review/wrap-up; the two cheap Stage-1 readers supplied data only. The GitNexus index was stale and did not supply authoritative data-file impact evidence; no executable symbol was edited. Session-bus drain cannot register this isolated API session's audit label as a roster ID; no peer's inbox/outbox was borrowed or modified. README freshness check passed without warnings. Source custody and the checkpoint remain retained until the review/filing stages reconcile.
