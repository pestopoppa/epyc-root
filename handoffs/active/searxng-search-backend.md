# SearXNG Search Backend

**Status**: SX-1–4 implemented and tested, SX-5/6 gated on AR-3
**Created**: 2026-04-14 (via research intake, deep-dive enriched)
**Updated**: 2026-04-14 (findings audit: added checklist, engine tuning, monitoring, work items)
**Categories**: search_retrieval, tool_implementation
**Tracked in**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P12

## Objective

Replace the brittle DDG HTML scraping + Brave fallback in `epyc-orchestrator/src/tools/web/search.py` (lines 31-142) with a self-hosted SearXNG instance providing a structured JSON API that aggregates 250+ search engines without HTML parsing, bot detection workarounds, or per-engine rate limiting code.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-359 | SearXNG (metasearch engine) | high | new_opportunity |
| intake-360 | SearXNG Documentation | high | new_opportunity |
| intake-361 | mcp-searxng (MCP bridge) | medium | worth_investigating |

## Current State (search.py)

```
_search_duckduckgo() — 112 lines of fragile HTML parsing:
  curl → DDG HTML → regex parse result__a/snippet classes → fallback to Brave HTML → regex parse snippet-content
  Rate limiting: 2s hardcoded sleep between requests
  Failure mode: "result__a" class check for bot detection; falls through to Brave if DDG returns empty
```

Problems: (1) Layout changes break regex parsers, (2) Bot detection blocks after repeated queries, (3) Only 2 engines, (4) No structured metadata, (5) subprocess curl dependency.

## Proposed Architecture

```
SearXNG Docker container (port 8090, ~183MB)
  GET /search?q=...&format=json&engines=duckduckgo,brave,wikipedia,qwant
  → JSON: {results: [{url, title, content, engines[], positions[], score}], suggestions[], unresponsive_engines[]}
  → ColBERT reranker (S5): MaxSim on snippet content field, top-3
  → fetch + synthesize (existing research.py pipeline)
```

## Deployment Plan

### Docker (fits orchestrator_stack.py pattern)

Add to `DOCKER_SERVICES` list alongside NextPLAID containers:
```python
{
    "name": "searxng",
    "port": 8090,
    "image": "docker.io/searxng/searxng:latest",
    "description": "Metasearch aggregator (JSON API)",
    "volumes": [
        f"{_PATHS['project_root']}/config/searxng:/etc/searxng:Z",
    ],
    "args": [],  # Config via settings.yml, not CLI args
}
```

### Minimal settings.yml

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

### Engine Tuning

SearXNG supports per-engine configuration (finding #5). Each engine accepts: `timeout` (override global), `weight` (result scoring multiplier), `disabled` (user-toggleable) vs `inactive` (completely removed), `retry_on_http_error` (bool or specific codes like `[403, 429]`), per-engine proxy config, `api_key` for premium engines.

Initial tuning targets:
- Set engine weights favoring DDG and Brave (proven reliable in current `search.py`)
- Per-engine timeout to `3.0s` (matching `outgoing.request_timeout`)
- `retry_on_http_error: [429]` for rate-limited engines
- Disable Google engine explicitly (`inactive: true`) — TLS fingerprint blocking (issue #2515)
- Enable DDG, Brave, Wikipedia, Qwant, Startpage as primary engine set

The `engines=` API parameter also allows per-request engine selection — could route different query types to different engine sets in future.

### _search_searxng() implementation (~15 lines)

```python
def _search_searxng(query: str, max_results: int = 5) -> list[dict[str, str]]:
    params = {"q": query, "format": "json"}
    resp = urllib.request.urlopen(
        urllib.request.Request(f"http://localhost:8090/search?{urllib.parse.urlencode(params)}"),
        timeout=10,
    )
    data = json.loads(resp.read())
    return [
        {"title": r["title"], "url": r["url"], "snippet": r.get("content", ""),
         "score": r.get("score", 0), "engines": r.get("engines", [])}
        for r in data.get("results", [])[:max_results]
    ]
```

## Pre-Deployment Checklist

- [ ] Verify `limiter: false` in settings.yml (finding #1: API_MAX=4/hr blocks all programmatic use when enabled)
- [ ] Verify `json` in `search.formats` list (finding: returns 403 without it — not enabled by default)
- [ ] Confirm Granian ASGI server running, NOT uWSGI (finding #4: Granian replaced uWSGI in recent builds; do NOT configure uWSGI workers)
- [ ] Test with python urllib/requests user-agent succeeds (finding #2: bot detection disabled when limiter is false)
- [ ] DDG/Brave/Wikipedia/Qwant engines return results under load (finding: Google unreliable due to TLS fingerprinting)

## Post-Deployment Monitoring

Wire `unresponsive_engines[]` from JSON response into orchestrator telemetry (finding #6). The JSON API reports `[["engine_name", "error message"], ...]` for every failed engine per query — useful for diagnosing upstream blocking without checking container logs.

- Log `unresponsive_engines` on every `_search_searxng()` call (same telemetry path as DS-1 queue depth in `routing_meta`)
- Alert when >50% of configured engines appear in `unresponsive_engines` for 3+ consecutive queries
- Track engine failure rate over time to detect gradual degradation (DDG CAPTCHA, Brave rate limiting)

### Post-AR-3 Analysis Script (NIB2-31, 2026-04-21)

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

## Critical Caveats (from deep-dive)

1. **Google blocks SearXNG** via TLS/HTTP2 fingerprinting (issue #2515). Expect Google engine to be unreliable. Mitigation: rely on DDG/Brave/Wikipedia/Qwant.
2. **Limiter MUST be disabled** for backend use. API_MAX=4/hr is a hard blocker. Bot detection also blocks python-requests/curl user-agents. `limiter: false` disables both.
3. **JSON format not enabled by default** — must add `json` to `search.formats` or GET /search?format=json returns 403.
4. **No max_results API parameter** — fixed ~20 results/page, client-side truncation needed.
5. **Single-user instances** more easily fingerprinted by upstream engines than multi-user public instances.
6. **Granian ASGI server has replaced uWSGI** — the docs reference architecture still shows uWSGI but the actual container uses Granian. Do not configure uWSGI workers.

## Open Questions

- Does SearXNG reliably return DDG/Brave results under EPYC's query volume (~50-200 searches/session) when Google is excluded?
- Should SearXNG run in the orchestrator_stack.py Docker management (alongside NextPLAID) or as a standalone docker-compose service?
- Is the `engines[]` multi-provenance data useful for the ColBERT reranker's confidence scoring?
- Can the `suggestions[]` response field enhance query reformulation in the web_research pipeline?
- Should the MCP server pattern (intake-361) be deployed for Claude Code sessions as a separate concern?

## Work Items

Mirrors P12 in [`routing-and-optimization-index.md`](routing-and-optimization-index.md). Both locations must stay in sync.

- [x] **SX-1: Docker container deployment** — ✅ 2026-04-14. SearXNG in `DOCKER_SERVICES` (port 8090, ~183MB). Config: `config/searxng/settings.yml`. Health check fix: `health_path: "/"` (SearXNG has no `/health`). **TESTED**: Container starts, health check passes, serves JSON on `/search?format=json`.
- [x] **SX-2: `_search_searxng()` implementation** — ✅ 2026-04-14. Added to `search.py`. Returns `{title, url, snippet, score, engines[]}` from JSON API. `web_search()` wrapper tries SearXNG first when flag enabled, falls back to DDG on failure. **TESTED**: 3/3 query types pass (normal 908ms, domain-filtered 653ms, niche 836ms). Multi-engine consensus confirmed (3-engine score ~9.9, 2-engine ~3.3, 1-engine <1).
- [x] **SX-3: Engine tuning** — ✅ 2026-04-14. `config/searxng/settings.yml`: Google `inactive: true`, DDG weight 1.2, Brave 1.1, Wikipedia 1.0, Qwant 0.9. Per-engine timeout 3.0s, Qwant `retry_on_http_error: true`.
- [x] **SX-4: `unresponsive_engines[]` telemetry** — ✅ 2026-04-14. `_search_searxng()` logs `searxng unresponsive_engines: ...` on every call with failures. Folded into AR-3 Package D Phase 6b for production validation.
- [ ] **SX-5: Load test** — Folded into AR-3 Package D. Web_research sentinel suite (50q) provides realistic load validation. Post-AR-3: analyze engine failure rates + latency via Phase 6b checks.
- [ ] **SX-6: Swap default** — Feature flag `ORCHESTRATOR_SEARXNG_DEFAULT=1` implemented. Gated on AR-3 warmup trial quality data. Post-AR-3: confirm no regression → lock in swap. See bulk-inference-campaign.md Phase 6b.

## Dependencies

- **Blocks**: None (independent workstream, no data gate, no inference dependency)
- **Composes with**: `colbert-reranker-web-research.md` S5 (SearXNG snippets → ColBERT reranking → fetch top-3)
- **Replaces**: `_search_duckduckgo()` in `search.py` lines 31-142

## Notes

AGPL-3.0 license — no issue for self-hosted internal tool use (no distribution). Python 80.5%, 9340+ commits, actively maintained (docs version 2026.4.13). LiteLLM has first-class SearXNG integration as reference pattern. Docker image from DockerHub or GHCR.

## Research Intake Update — 2026-04-14

### New Related Research
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

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-453] "Reason-mxbai-colbert-v0-32m: Edge-Scale Reasoning ColBERT (32M params)"** (`huggingface.co/DataScience-UIBK/Reason-mxbai-colbert-v0-32m`)
  - Relevance: candidate CPU-latency-friendly reranker over SearXNG top-K results. 32M params ≈ 5× smaller than current 150M GTE-ModernColBERT-v1 on :8089; could drop reranker call from ~180 ms → ~40 ms if PyLate→ONNX export path works.
  - Delta: this sharpens the reranker choice behind SearXNG output but does not change the search-engine tuning or SX-5/6 work items. Tracked primarily in `colbert-reranker-web-research.md` — flagged here so SX-5 analysis factors in the latency/quality trade.
