# SearXNG Search Backend

**Status**: stub (deployment plan + work items SX-1 through SX-6)
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

- [ ] **SX-1: Docker container deployment** — Deploy SearXNG image (~183MB) on port 8090 via `orchestrator_stack.py` DOCKER_SERVICES. Config: `limiter: false`, `search.formats: [html, json]`, Granian ASGI (not uWSGI). Valkey sidecar NOT needed.
- [ ] **SX-2: `_search_searxng()` implementation** — ~15 lines in `search.py` replacing 112-line `_search_duckduckgo()`. Return `{title, url, snippet, score, engines[]}` from JSON API. `web_search()` wrapper unchanged.
- [ ] **SX-3: Engine tuning** — Per-engine weight, timeout (3.0s), `retry_on_http_error: [429]`. Disable Google engine explicitly (TLS fingerprint blocking, issue #2515). Favor DDG/Brave/Wikipedia/Qwant.
- [ ] **SX-4: `unresponsive_engines[]` telemetry** — Wire JSON response `unresponsive_engines[]` into orchestrator monitoring (same telemetry path as DS-1 queue depth). Alert on >50% engine failure rate.
- [ ] **SX-5: Load test** — 50-200 queries/session against DDG/Brave/Wikipedia/Qwant to validate reliability under EPYC's single-user query volume. Measure latency, engine failure rate, result quality.
- [ ] **SX-6: Swap default** — Replace `_search_duckduckgo` with `_search_searxng` as primary backend in `web_search()`. Keep DDG HTML as fallback if SearXNG container is down.

## Dependencies

- **Blocks**: None (independent workstream, no data gate, no inference dependency)
- **Composes with**: `colbert-reranker-web-research.md` S5 (SearXNG snippets → ColBERT reranking → fetch top-3)
- **Replaces**: `_search_duckduckgo()` in `search.py` lines 31-142

## Notes

AGPL-3.0 license — no issue for self-hosted internal tool use (no distribution). Python 80.5%, 9340+ commits, actively maintained (docs version 2026.4.13). LiteLLM has first-class SearXNG integration as reference pattern. Docker image from DockerHub or GHCR.
