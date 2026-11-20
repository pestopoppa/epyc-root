# When Your Agent Opens the Chat App: Agent-Controlled Search over Raw Chat Logs Rivals Structured Memory

- **Intake**: intake-2737 (`intake-2737#record`)
- **Source**: https://arxiv.org/html/2608.12888v2
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: context-and-token-economy.md, memory-program.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Cite the control ablation: the controls, not BM25 alone, carry the result. Do not transfer magnitudes to local models or code/trace corpora without our own probe.

## Key claims (anchored)

0. A prompt-only BM25 agent over raw chat logs (ReFind) reaches the highest mean accuracy (58.2) of the compared systems on MemoryAgentBench-derived tasks, above structured memory systems.
   - Abstract / Sec 4: "ReFind attains the highest mean accuracy (58.2) of any system compared"
1. A matched generic agentic BM25 control without the chat-native controls trails the full interface; context-window removal and session dedup are the largest drops.
   - Sec 5: "This matched Generic Agentic BM25 control reaches"
   - Sec 5: "Context window removal is the largest S drop"
   - Sec 5: "Session deduplication matters more on M"
2. The multi-round search loop is worth 8.5 (S) and 20.4 (M) points over a single forced search.
   - Sec 5: "trails the full method by 8.5 (S) and 20.4 (M) points"
3. Swapping BM25 for dense or hybrid retrieval with the agent and controls fixed does not help.
   - Sec 5: "BM25 has the highest mean on both subsets; even Hybrid does not beat BM25"
4. Indexing needs no model call; queries cost about 5.0 LLM calls each; baselines were reused rather than rerun under a matched budget.
   - Sec 5: "5.0 LLM calls per query"
   - Sec 3: "Indexing requires no model call and no summarization pass"
   - Appendix 9: "the systems were not all rerun with a matched controller or tool-call budget"

## Dive record

2026-11-20 Stage-2b dive (sonnet; full read; surfaced by intake-2729). Independent prompt-only evidence on chat-log QA with GPT-4o-mini / GPT-5-mini only (no open-weight or sub-10B model); LongMemEval S/M subsets are 50/15 questions. The gain over bare iterative BM25 (7-15 points) comes from the controls: +-2 turn context, seen-session dedup, session RRF, time filter. Count mode, pagination and line clipping: NOT-FOUND-IN-SOURCE. Orchestrator @94cd4320: ms.search takes text/session_id/scope only (no time range, no dedup, no neighbour window); ms.expand takes exact event ids (src/trace/mcp_tools.py:L72-L82); FTS5 bm25 backend already matches the paper's sufficient backend (src/trace/query.py:L8-L9,L170-L171). Supports keeping the REPL-EMB freeze (harness-program.md:L2475-L2500 @b5c5fe7) but chat prose may not transfer to code/trace corpora. Surfaced arXiv 2607.26497 (wave-2 candidate); STITCH 2601.10702 and GAM 2511.18423 declined (comparators only). lane_head b5c5fe7b4e63
