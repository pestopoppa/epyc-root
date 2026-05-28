# Web Research Pipeline — SearXNG + Crawl4AI

**Status**: SX-1–4 done; CA-1–5 ready to start; SX-5/6 + CA-6/7 gated on AR-3 / Camofox
**Created**: 2026-04-14 (via research intake, deep-dive enriched)
**Updated**: 2026-05-05 (merged Crawl4AI steps 2+3; renamed from "SearXNG Search Backend")
**Categories**: search_retrieval, tool_implementation
**Tracked in**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P12

## Four-Step Chain

```
Step 1: SearXNG  (port 8090) — search, returns candidate URLs           SX-1–4 done, SX-5/6 gated on AR-3
Step 2: Crawl4AI (port 8086) — single-page markdown extraction          CA-1–5 ready now
Step 3: Crawl4AI (port 8086) — limited multi-page crawl (docs/logs)    CA-7 (deferred)
Step 4: Camofox  (port 9377) — full browser, last resort only           CA-6 (deferred, intake-524)
```

Policy: **Camofox last.** Only open a real browser when the page forces it. Each step must be exhausted before escalating.

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

## Crawl4AI Work Items (Steps 2+3)

Chosen over Firecrawl after deep-dive (2026-05-05): single container, Apache-2.0, ~1–2 GB idle, undetected Chrome mode self-hosted, BM25 `fit_markdown`, no external SDK. Full detail: [`research/deep-dives/firecrawl-vs-crawl4ai-web-pipeline-steps-2-3.md`](../../research/deep-dives/firecrawl-vs-crawl4ai-web-pipeline-steps-2-3.md)

- [ ] **CA-1**: Add `--shm-size` support to `start_docker_container()` in `orchestrator_stack.py` — one-liner: `if service.get("shm_size"): cmd.extend(["--shm-size", service["shm_size"]])` [30min]
- [ ] **CA-2**: Add Crawl4AI to `DOCKER_SERVICES` — `{"name": "crawl4ai", "port": 8086, "image": "unclecode/crawl4ai:latest", "shm_size": "1g", "env": {"MAX_CONCURRENT_TASKS": "5"}, "health_path": "/health"}` [30min]
- [ ] **CA-3**: Implement `_fetch_page_crawl4ai()`, `_is_blocked_page()`, `_poll_crawl4ai_task()` in `research.py` [2h]
- [ ] **CA-4**: Replace `_fetch_page()` calls with Crawl4AI backend; keep `html.parser` path as fallback if container unreachable [1h]
- [ ] **CA-5**: Smoke test — 5 URLs covering static, JS-heavy, and Cloudflare-protected pages [1h]
- [ ] **CA-6** *(deferred — needs Camofox, intake-524)*: Wire `escalate_to_camofox` signal from `_is_blocked_page()` into step 4 call [2h]
- [ ] **CA-7** *(deferred — post CA-5)*: `_fetch_docs_crawl_crawl4ai()` for step 3 limited BFS crawl, `limit=5`, `maxDiscoveryDepth=2` [2h]

CA-1 through CA-5 are **independent** — no AR-3 gate, no Camofox dependency. Can start now.

## Dependencies

- **Blocks**: None (CA-1–5 independent; CA-6 blocked on intake-524 Camofox)
- **Composes with**: `colbert-reranker-web-research.md` S5 (SearXNG snippets → ColBERT reranking → Crawl4AI fetch)
- **Replaces**: `_search_duckduckgo()` in `search.py` (SX) and `html.parser` fetch in `research.py` (CA)

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

## Research Intake Update — 2026-04-30

### New Related Research

- **[intake-519] "Granite-Embedding-97M-Multilingual-R2"** (HF `ibm-granite/granite-embedding-97m-multilingual-r2`, Apache 2.0, IBM, released 2026-04-29)
  - Relevance to SearXNG backend: **MEDIUM**, primarily as the candidate dense first-stage retriever for a SearXNG → dense-rerank → ColBERT-rerank pipeline. SearXNG returns mixed-language web snippets; a 200+-language 97M ModernBERT encoder with 32K context (vs e5-small's 512) handles longer snippets without chunking and runs CPU-fast (~2.9k docs/s claimed).
  - Delta to current SearXNG work: no change to SX-5/6 items, but if the team chooses a dense first stage to bound the candidate set fed to ColBERT, Granite-97M-r2 is the new size-class baseline to beat — replaces or supersedes any implicit multilingual-e5-small assumption.
  - Tracked primarily in `colbert-reranker-web-research.md` and `internal-kb-rag.md` 2026-04-30 updates. Flagged here so SX-5 analysis factors in dense-stage latency/quality trade.

#### Deep-dive refinement (2026-04-30) — bench owned by granite-97m-r2-bench-plan

Bench handoff at [`granite-97m-r2-bench-plan.md`](granite-97m-r2-bench-plan.md). For SearXNG SX-5/6 specifically: the dense first-stage choice (granite-97m-r2 vs BGE-M3 vs multilingual-e5-base) will come out of that bench. Defer SX-5 dense-stage decisions until Phase B completes. Note that the bench's eval corpus is currently planned as code-snippets-plus-handoffs, NOT mixed-language web snippets — if SearXNG-specific quality matters, add a SearXNG-output slice to the bench's eval-corpus engineering (Phase A-4).

## Research Intake Update — 2026-05-04

### New Related Research
- **[intake-524] "camofox-browser — Stealth headless browser REST API for AI agents"** (github.com/jo-inc/camofox-browser)
  - Relevance: Camofox is the **browser interaction** layer in the SearXNG→Firecrawl→Camofox three-tool stack — the same architecture this handoff's SearXNG component anchors. When SearXNG returns URLs and Firecrawl/direct-fetch returns 429/403/CAPTCHA, Camofox is the fallback that opens a real browser.
  - Key technique: REST API (port 9377) wrapping Camoufox (Firefox fork with C++ fingerprint spoofing). Tools: `browser_open`, `snapshot`, `click`, `navigate`, `screenshot`. Accessibility snapshots are ~90% smaller than raw HTML with stable element refs for LLM interaction.
  - Reported results: ~40MB idle memory, confirmed bypass of Cloudflare and Google bot detection, ~90% token reduction vs raw HTML.
  - Delta from current approach: the canonical four-step fallback chain is **Search (SearXNG) → Scrape (Firecrawl single-page) → Crawl (Firecrawl limited) → Browse (Camofox)**. Camofox is the last resort — "expensive, stateful fallback" per the source doc — only opened when the page forces interaction. Firecrawl covers two steps (scrape + crawl-limited) before Camofox is invoked. This is different from a simple "Firecrawl fails → Camofox" trigger; the crawl-limited step (small page cap for docs/changelogs) should also be attempted first.
  - Action item: after AR-3 data is available (SX-5/6 gate), check fetch-failure rate in web_research logs. If >15% of fetches fail with 403/429/CAPTCHA **after both Firecrawl scrape and crawl-limited attempts**, add camofox-browser to `orchestrator_stack.py` DOCKER_SERVICES at port 9377 and wire `_fetch_camofox()` as the terminal fallback in `web/research.py`. Do not short-circuit to Camofox before Firecrawl crawl-limited is tried.

## Research Intake Update — 2026-05-05

### New Related Research — Crawl4AI (Steps 2+3 resolved)
- **[intake-372] "Crawl4AI — Open-Source LLM-Friendly Web Crawler"** (github.com/unclecode/crawl4ai)
  - Relevance: **HIGH** — deep-dive (2026-05-05) resolved the step 2+3 question in the four-step chain. Crawl4AI is the chosen scraper; Firecrawl (intake-364/365) was evaluated and ruled out (verdict updated to `not_applicable`).
  - Key finding from deep-dive: Firecrawl self-hosted lacks fire-engine (cloud-only anti-bot), requires 5-service docker-compose (incompatible with `start_docker_container()`), and uses 4–8 GB idle RAM. Crawl4AI is a single container, Apache-2.0, ~1–2 GB idle, with undetected Chrome mode self-hosted.
  - Integration: the [Crawl4AI Work Items](#crawl4ai-work-items-steps-23) section above has the full implementation plan (CA-1 through CA-7, port 8086).
  - Deep-dive: [`research/deep-dives/firecrawl-vs-crawl4ai-web-pipeline-steps-2-3.md`](../../research/deep-dives/firecrawl-vs-crawl4ai-web-pipeline-steps-2-3.md)
  - **Sequencing**: CA-1–5 (Crawl4AI step 2) are independent of SX-5/6 (ColBERT gate) and can proceed now. CA-6 (Camofox escalation wiring) waits for intake-524 Camofox integration.
