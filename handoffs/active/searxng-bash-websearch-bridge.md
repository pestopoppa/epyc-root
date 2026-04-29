# SearxNG as a Bash-Issued Web Search Channel for Claude Code Sessions

**Status**: stub
**Created**: 2026-04-29 (during research-intake of arxiv:2604.24432)
**Categories**: search_retrieval, tool_implementation, agent_architecture
**Owner**: deferred — user will handle in a future session

## Objective

Route Claude Code's high-volume / multilingual / engine-diversity web search calls through the already-deployed self-hosted **SearxNG** instance (`localhost:8090`, JSON API) instead of the built-in Anthropic-hosted `WebSearch` tool, in cases where SearxNG is the better fit.

## Why This Matters

Today inside a Claude Code session there are two available web-search paths:

1. **Built-in `WebSearch` tool** — Anthropic-hosted, opaque engine selection, US-only, returns short title/snippet/URL trios. Token cost is implicit in tool-call overhead. Good for one-shot lookups.
2. **Bash + curl against `localhost:8090/search?format=json`** — local SearxNG container (set up by `handoffs/active/searxng-search-backend.md`, SX-1–4 done 2026-04-14). Returns structured JSON with `engines[]`, `score`, `positions[]`, `unresponsive_engines[]`, `suggestions[]`. Token cost is whatever curl/jq/Python prints.

The case for using #2 from inside Claude Code sessions:

- **Engine diversity / consensus**: a result that appears in DDG ∩ Brave ∩ Wikipedia ∩ Qwant has higher prior than one engine alone. SearxNG exposes this directly via the `engines[]` and `score` fields per result.
- **Multilingual**: built-in WebSearch is US-only. SearxNG aggregates engines that index Chinese / European / Japanese content natively — relevant when researching e.g. Chinese-lab papers (Kuaishou, Kimi, Qwen, DeepSeek) where the primary writeup may live on WeChat or a Chinese tech blog.
- **Bulk / surveys / cluster expansion**: research-intake Phase 3 (literature expansion) often wants 5–15 queries in quick succession. Going through WebSearch each time adds tool-call overhead per query. A single `bash -c` running a 10-query loop against SearxNG returns aggregated JSON in one step.
- **Token efficiency**: the model can `grep`/`jq` the JSON down to the URLs it cares about before any of it lands in context, instead of re-reading WebSearch's prose-formatted summary each time.
- **Replicability**: SearxNG has telemetry (`unresponsive_engines[]` logging, `scripts/analysis/searxng_health_report.py`); WebSearch is a black box.

The case for staying with built-in WebSearch:

- It works immediately, no port to bind, no container to run. The auto-summarization step from the small model on the other end of WebSearch is genuinely useful for one-shot "what is X" queries.
- For everything where a single result is enough, the structured JSON is overkill.

## Constraints

- I cannot redirect the built-in `WebSearch` tool itself through SearxNG — that's an Anthropic-hosted tool whose backend isn't user-configurable. The bridge has to be implemented as a **separate path** invoked via Bash.
- SearxNG must be running on `localhost:8090` for the path to work. Activation requires bringing up the container (currently down on this host — `docker` not reachable from sandbox shells; user-initiated launch needed).
- The session model (me) needs to know when to *prefer* SearxNG over WebSearch. Without a written rule, default behavior will be to keep using WebSearch.

## Proposed Approaches (rank-ordered, user to pick)

1. **CLAUDE.md rule + helper script (lightest touch)**
   Add a short section to `/workspace/CLAUDE.md` that says: "When you need ≥3 web search queries in a single phase (literature expansion, cluster surveys, multilingual lookups), prefer `bash scripts/search/searx.sh '<query>'` over `WebSearch`, provided `curl -s -m 2 http://localhost:8090/health` returns 200." Ship a tiny `scripts/search/searx.sh` wrapper that does the curl + jq formatting.
   Pros: zero infra change, trivially reversible. Cons: relies on the model honoring the rule.

2. **Project-level slash command (`/searx <query>`)**
   Add a Claude Code slash command at `.claude/commands/searx.md` that wraps the SearxNG query and pretty-prints results. Same effect as #1 but discoverable via `/`.
   Pros: explicit invocation, less chance of forgetting the path exists. Cons: still relies on the model choosing to invoke it.

3. **MCP bridge (heaviest, most general)**
   The intake already has `intake-361` (`mcp-searxng`) — a MCP server bridging SearxNG into any MCP-aware client including Claude Code. Wiring this means `searxng_search()` becomes a first-class tool alongside WebSearch. The model gets to pick per-query.
   Pros: cleanest integration, no script wrapper needed. Cons: another MCP server in `.mcp.json`, another moving piece on this host's startup.

## Recommendation

Start with **#1** as a one-evening change. If the rule works in practice (i.e. the model actually reaches for SearxNG during literature expansion phases), graduate to **#3** later. **#2** is a middle ground if `/searx` ergonomics matter more than MCP integration.

## Open Questions

- Do we want SearxNG-for-Bash to also be wired into the orchestrator's `web_research` pipeline, or is that already handled by the existing SX-2 `_search_searxng()` → `web_search()` wrapper at `epyc-orchestrator/src/tools/web/search.py`? (A: yes already wired for the orchestrator REPL; this stub is *only* about the Claude Code session-level path.)
- Should the rule cover *all* Bash-issued curl calls to search APIs, or only when SearxNG is the destination?
- Is there a meaningful per-query token-cost differential that warrants prioritizing #3 sooner? (Would need to measure WebSearch tool-call overhead vs `bash curl | jq` overhead in actual session transcripts.)
- Multilingual triggering: does the model need an explicit "use SearxNG when querying in non-English" rule, or does engine diversity (DDG/Qwant/Brave) suffice without language hinting?

## Cross-References

- `handoffs/active/searxng-search-backend.md` — parent SearxNG deployment handoff (SX-1–4 done, SX-5/6 gated on AR-3). All container/config decisions live there.
- `intake-359, intake-360, intake-361` — original SearxNG intake entries; intake-361 is the MCP bridge that approach #3 above would use.
- `feedback_opensource_only.md` (memory) — confirms SearxNG (AGPL-3.0, self-hosted) is on-policy; rules out paid alternatives like Exa, Tavily, Perplexity API.
- `progress/2026-04/2026-04-29.md` — same-day session that spawned this stub (KSA paper extraction triggered the question of whether bulk web search should be routed differently).

## Notes

This is **specifically about Claude Code session web searches**, not about the orchestrator's `web_research` pipeline (which is already SearxNG-aware via SX-2). The two paths are separate because the orchestrator runs as its own process with its own tool registry; Claude Code sessions are a different consumer of the same SearxNG instance.

User flagged this during a 2026-04-29 session where research-intake Phase 3 (literature expansion) needed multilingual searches against Kuaishou/Chinese-lab content and the built-in WebSearch returned only the most popular English-language summaries.
