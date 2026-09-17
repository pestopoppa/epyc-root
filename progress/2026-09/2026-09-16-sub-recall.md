# 2026-09-16 — sub-recall: dead `recall()` on `/v1` fixed

Follow-up to [`2026-09-16-sub-hermes-memory.md`](2026-09-16-sub-hermes-memory.md) (the latent `/v1` defect and the inert config block).

## Commits (unpushed, need to be merged)

| Repo | Branch | SHA | Worktree |
|---|---|---|---|
| epyc-orchestrator | `sub/recall-fix-20260916` | `3037646cd9f29f6e6f13d3bb208f6b69a0856a1c` | `/mnt/raid0/llm/worktrees/sub-recall` |
| epyc-root | `sub/recall-mempalace-inert-20260916` | `c677980f0abfeb8fea0d6f5bf0d5c811847ded7a` | `/mnt/raid0/llm/worktrees/sub-recall-root` |

## Bug confirmed

- **`/chat` path.** `chat.py:1246`, `chat_pipeline/repl_executor.py:372,391` and `chat_pipeline/stream_adapter.py:168` all pass `retriever=state.hybrid_router.retriever` and `hybrid_router=`.
- **`/v1` path.** `openai_compat.py` (REPL sites, formerly ~:675 and ~:876) passed neither. Every `/v1` `recall()` therefore went to `_recall_legacy`.
- **The fallback called two methods that do not exist.**
  - `EpisodicStore.search_similar` does not exist. The real API is `retrieve_by_similarity(query_embedding, k, action_type, min_q_value)`.
  - `TaskEmbedder.embed` does not exist either. The real methods are `embed_exploration` and `embed_text`.
  - The fallback also read `mem.task_description` and `mem.similarity`. `MemoryEntry` has neither; the correct fields are `context["objective"]` and `similarity_score`.
- **How the failure was hidden.** The AttributeError was folded into `{"results": [], "error": ...}` and nothing was logged. For a caller, that looks the same as "no memories".
- **Stuck-guidance consumer.** `context.py` STUCK() injected any non-"No memories" recall payload, including error JSON, as "Similar past situations".

## Fix

- **`/v1` wiring.** New `_repl_memrl_kwargs(state)` in `openai_compat.py` calls `ensure_memrl_initialized` (idempotent, and a no-op when the flag is off) and passes `retriever` and `hybrid_router` to both `/v1` REPL sites.
- **Legacy fallback.** It now uses `embed_exploration` + `retrieve_by_similarity(action_type="exploration")`, which mirrors `TwoPhaseRetriever.retrieve_for_exploration`. It closes the store and embedder when done and logs a WARNING whenever it is used.
- **Failure contract.** Both paths now log at ERROR with a traceback and return `{"status": "unavailable", "results": [], "error": "<Type>: <msg>"}`. A success carries `"status": "ok"`, so callers can tell an empty result from a broken recall.
- **STUCK().** It now skips empty and `unavailable` payloads.
- **Scope.** The diff does not touch `knowledge_fence` code (AP-54).

## `/v1` recall decision: YES, `/v1` should get recall

- `hermes-outer-shell.md` says that with no override, `/v1` runs the "full frontdoor → MemRL → specialist → escalation graph". It also says MemRL "powers Hermes's reasoning".
- "Hermes never sees our episodic store" (Two-Layer Memory) refers to the *client*. `recall()` is a tool of the orchestrator's own REPL, so the store stays internal and the two memory layers stay separate.
- `unified-trace-memory-service.md` does not argue against this; that document is about provenance queries, not routing memory.
- The decision is parity with `/chat`. When the memrl flag is off, the retriever is None and the fallback applies. Any failure is now explicit.

## Tests (offline, hermetic)

- **New file** `tests/unit/test_repl_recall_v1.py`, 5 tests. All 5 fail on the unfixed code and pass with the fix. They cover:
  - a real `EpisodicStore` fixture under `tmp_path` (asserted to lack `search_similar`);
  - a store double with no search API, which now gives ERROR log + `unavailable`;
  - a retriever exception, which also gives `unavailable`;
  - the kwargs helper;
  - an end-to-end `POST /v1/chat/completions` (REPL mode) test. It captures the REPL the route builds and asserts that the REPL holds the shared retriever and that `recall()` returns the fixture row.
- **Existing tests made hermetic.** `TestRecall` (`test_repl_routing.py`) and `test_graceful_with_no_memories` (`test_stuck_signal.py`) previously opened the **repo-default store path**; in the shared clone that is the production store. A new STUCK test checks that an unavailable payload is not injected.
- **Results.** `pytest tests/unit -k "repl or openai or recall or routing" -n 4`: 1285 passed, 9 skipped. `ruff` is clean.
- **Leftover file.** My first run of the old, non-hermetic test created an ignored empty `orchestration/repl_memory/sessions/episodic.db` inside my worktree only. The permission guard refused to delete it. It is harmless (gitignored) and goes away when the worktree is removed.

## Blast radius (the repo is not gitnexus-indexed, so this is grep-based)

- **`_recall` callers.** The REPL tool table (`environment.py:444`) and STUCK (`context.py:270`).
- **New `status` key.** It is additive: existing keys are unchanged and error payloads keep `error`.
- **`/v1` REPLs now carry `hybrid_router`,** so `route_advice()` also works on `/v1` (it previously returned its "no router" answer). This matches `/chat`.
- **Risk: LOW–MEDIUM.** On `/v1` REPL turns that call `recall`/`route_advice`, behaviour changes from "silently empty" to real retrieval. Retrieval runs one embedding call against the embedding server, as it already does on `/chat`.
- **The live API still serves the old code** until this is merged and the API is reloaded. The reload belongs to the session that owns inference; I did not reload.

## Inert `mempalace:` block (`epyc-root/scripts/hermes/hermes-config.yaml`, formerly lines 115–120)

- Hermes reads MCP servers only from `mcp_servers:`, so the `mempalace:` key was never read.
- On the root branch the block is **commented out** (not deleted, because `mempalace_setup.sh:213` points at "the mempalace section"). An INERT note replaces the false claim that "MemPalace MCP tools are available as `mcp__mempalace__*`".
- A YAML parse confirms the `mempalace` key is gone. The other top-level keys are unchanged.
- If MemPalace is wanted in Hermes, it needs an `mcp_servers:` entry. That is a separate, deliberate decision; this change does not make it.
