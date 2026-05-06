# Firecrawl Integration Deep-Dive: Steps 2+3 of the Web Research Chain

**Date**: 2026-05-05
**Status**: Pre-integration research — verdict reached
**Context**: EPYC orchestrator web pipeline — SearXNG (step 1) → scrape (step 2) → limited crawl (step 3) → Camofox (step 4)
**Intake entries**: intake-364, intake-365 (Firecrawl); intake-372 (Crawl4AI)
**Related handoffs**: searxng-search-backend.md, crawl4ai-web-scraper.md (new stub)

---

## 1. Architecture Overview

### What Firecrawl Is Under the Hood

Firecrawl is a Node.js/TypeScript API server (`apps/api`) with a multi-engine scraping backend organized around a waterfall/fallback architecture. It dispatches requests through a ranked list of 13 distinct engine types:

```typescript
type Engine =
  | "fire-engine;chrome-cdp"         // Cloud-only: remote Chrome CDP
  | "fire-engine(retry);chrome-cdp"  // Cloud-only: retry variant
  | "fire-engine;chrome-cdp;stealth" // Cloud-only: stealth Chrome CDP
  | "fire-engine;tlsclient"          // Cloud-only: TLS fingerprint spoofing
  | "fire-engine;tlsclient;stealth"  // Cloud-only: stealth TLS
  | "playwright"                     // Self-hosted: Playwright microservice
  | "fetch"                          // Self-hosted: plain HTTP
  | "pdf"                            // Self-hosted: PDF extraction
  | "document"                       // Self-hosted: document formats
  | "index"                          // Caching engine
  | "wikipedia"                      // Wikipedia-specific
  | "x-twitter"                      // Twitter-specific
```

`buildFallbackList()` selects an ordered sequence based on environment variables and request features. A quality score system (0–1500) ranks engines: fire-engine variants score 10–50, Playwright scores 20, fetch scores 5.

**JavaScript rendering**: Handled by the Playwright microservice (`apps/playwright-service-ts`), a separate TypeScript service with browser pooling. Self-hosted deployments get JS rendering through this. Fire-engine variants handle heavy-duty anti-bot bypassing — cloud only.

**The /crawl mechanism**: Queue-based via RabbitMQ. `POST /v1/crawl` returns a job ID; the crawler discovers pages via sitemaps + recursive link traversal, fans them out as individual scrape jobs, and workers process them. Results polled via `GET /v1/crawl/{id}` or delivered via webhook/WebSocket.

### Docker Service Breakdown

Five services from `docker-compose.yaml`:

| Service | Image | CPU | RAM | Purpose |
|---------|-------|-----|-----|---------|
| `api` | Built from `apps/api` | 4.0 cores | 8 GB | Main API server + worker processes |
| `playwright-service` | Built from `apps/playwright-service-ts` | 2.0 cores | 4 GB | Browser automation |
| `redis` | `redis:alpine` | — | — | Caching + rate limiting |
| `rabbitmq` | `rabbitmq:3-management` | — | — | Job queue |
| `nuq-postgres` | Built from `apps/nuq-postgres` | — | — | Persistence |

**Total minimum footprint**: ~12 GB RAM reserved, ~6 CPU cores. Idle usage lower (Playwright pool spins up on demand) but the reservation is substantial.

---

## 2. Self-Hosted vs Cloud Gap

### Feature Matrix

| Feature | Cloud | Self-Hosted | Notes |
|---------|-------|-------------|-------|
| `/v1/scrape` | Yes | **Yes** | Core endpoint, fully available |
| `/v1/crawl` | Yes | **Yes** | Core endpoint, fully available |
| `/v1/map` | Yes | **Yes** | URL discovery, available |
| `/v1/batch/scrape` | Yes | **Yes** | Available |
| `/v1/extract` | Yes | Partial | Requires OpenAI key |
| `/v1/agent` | Yes | **No** | Cloud-only |
| `/v1/browser` | Yes | **No** | Cloud-only |
| `fire-engine;chrome-cdp` | Yes | **No** | Cloud-only anti-bot Chrome |
| `fire-engine;tlsclient` | Yes | **No** | Cloud-only TLS fingerprint spoofing |
| JavaScript rendering | Yes | **Yes** | Via Playwright microservice |
| Browser actions (click, write, scroll) | Yes | Partial | Playwright only, not fire-engine |
| Stealth/anti-bot | **Advanced** | **Basic** | Fire-engine's main value; Playwright minimal stealth |
| Enhanced proxy | Yes | Self-managed | Must supply own `PROXY_SERVER` env var |
| Structured JSON extraction | Yes | Requires key | `OPENAI_API_KEY` or Ollama |
| Screenshots | Yes | **Yes** | Via Playwright |

### The Fire-Engine Problem (Critical)

The official docs state explicitly:

> "Currently, self-hosted instances of Firecrawl do not have access to Fire-engine, which includes advanced features for handling IP blocks, robot detection mechanisms, and more."

Fire-engine is a closed proprietary service run by Firecrawl.dev. It provides:
- Chrome DevTools Protocol with residential proxy rotation
- TLS client fingerprint spoofing (bypasses Akamai, Cloudflare, etc.)
- Stealth headless detection bypass

Without fire-engine, the self-hosted fallback sequence is:
1. Playwright (quality score 20) — Chromium-based, detectable as automated
2. fetch (quality score 5) — plain HTTP, no JS, trivially blocked

PR #2282 ("Add anti-fingerprinting to Playwright service") has been open since Oct 2025 and remains unmerged as of May 2026.

**Practical implication**: Self-hosted Firecrawl handles ordinary websites well. Cloudflare "I'm Under Attack" mode, Akamai Bot Manager, and PerimeterX block it reliably. This maps cleanly to our escalation logic: Firecrawl handles steps 2-3 for cooperating sites; Camofox handles step 4 for blocked sites.

---

## 3. Integration Fit Assessment

### Step 2: Single-Page Scrape (`/v1/scrape`)

**Verdict: Strong fit.** Core use case, works reliably self-hosted.

Key parameters for our pipeline:
- `waitFor`: ms to wait for JS (default 0; set 500–2000 for heavy SPAs)
- `onlyMainContent: true` (default): strips navbars, footers, sidebars
- `timeout`: 60s default, up to 300s
- `maxAge`: 172800000 ms (48h) cache TTL

Markdown output is substantially better than our current `html.parser` in `web/fetch.py`: headings, lists, code blocks, tables, and alt text preserved; boilerplate stripped. Returns `metadata.title`, `metadata.description`, `metadata.statusCode`.

**Bot detection signals** for Camofox escalation:
```python
ESCALATE_PATTERNS = (
    "access denied", "please complete the security check",
    "ray id",              # Cloudflare signature
    "checking your browser", "ddos protection",
    "please enable javascript", "enable cookies",
)
```
If Firecrawl returns these patterns or `statusCode: 403/429`, escalate to Camofox step 4.

### Step 3: Limited Multi-Page Crawl (`/v1/crawl`)

**Verdict: Usable, but async-first requires adaptation.**

`POST /v1/crawl` returns a job ID; results are polled. For docs/changelogs with `limit: 5`, `maxDiscoveryDepth: 2`, completes in 10–30s — fits within `web_research_impl`'s 90s timeout with a polling loop.

```json
{
  "url": "https://docs.example.com/changelog",
  "limit": 5,
  "maxDiscoveryDepth": 2,
  "scrapeOptions": {"formats": ["markdown"], "onlyMainContent": true},
  "includePaths": ["/changelog", "/releases", "/docs"]
}
```

The Python SDK's `async_crawl_url` + `check_crawl_status` pair handles polling natively.

---

## 4. Crawl4AI Comparison

### Side-by-Side

| Dimension | Firecrawl (self-hosted) | Crawl4AI |
|-----------|------------------------|----------|
| **License** | AGPL-3.0 | Apache-2.0 |
| **Stars** | ~38K (repo) | 65K |
| **Language** | TypeScript/Node.js | Python (async) |
| **Browser engine** | Playwright (self-hosted), CDP+TLS (cloud) | Playwright (Chromium/Firefox/WebKit) |
| **Anti-bot (self-hosted)** | Basic Playwright only | Undetected Chrome mode + 3-tier detection |
| **JS rendering** | Yes (Playwright service) | Yes (Playwright, async) |
| **Output formats** | Markdown, HTML, JSON, screenshots, PDF | Markdown (clean + `fit_markdown`), JSON, HTML, screenshots |
| **BM25 filtering** | No | **Yes** — `fit_markdown` filters by query relevance |
| **Docker complexity** | **5 services** (api, playwright, redis, rabbitmq, postgres) | **1 service** (all-in-one) |
| **Port** | 3002 | 11235 (configurable) |
| **Idle RAM** | ~4–8 GB | ~1–2 GB |
| **Python SDK** | `firecrawl-py` (external dep) | Native (`AsyncWebCrawler`) or plain HTTP |
| **Async native** | Partial (crawl async, scrape sync) | Yes — async-first |
| **Self-hosted parity** | Gaps: no /agent, /browser, fire-engine | **None** — identical to cloud |
| **Active development** | Commercial (Mendable/Firecrawl.dev) | Community (unclecode) |

### License: AGPL-3.0 vs Apache-2.0

AGPL-3.0's network use clause applies when you provide the *Firecrawl service itself* to external users. Running Firecrawl as a private internal dependency (orchestrator calls Firecrawl's HTTP API; users interact with the orchestrator, not Firecrawl directly) does **not** constitute "providing access to the modified program through a network." Running stock unmodified Docker images means AGPL is not triggered at all.

However: Apache-2.0 (Crawl4AI) is zero-friction — no legal review needed, no future compliance risk.

### Anti-Bot: The Key Technical Differentiator

Crawl4AI self-hosted has substantially better anti-bot coverage:
- Undetected Chrome mode (bypasses Cloudflare/Akamai at the Playwright level)
- Stealth mode with header/cookie manipulation
- Proxy escalation chain with fallback functions
- 3-tier detection awareness

This means fewer Camofox escalations (step 4) in practice. Firecrawl self-hosted and Crawl4AI both eventually hit sites they can't handle — but Crawl4AI reaches that ceiling later.

### The BM25 `fit_markdown` Advantage

Crawl4AI's `fit_markdown` applies BM25 filtering during extraction, returning only content relevant to the query. This partially replaces the `_synthesize_page()` worker model call in `research.py` — for content-dense pages, `fit_markdown` already does the topic-filtering that the Qwen2.5-7B explore worker currently handles. The worker call is still valuable for query-focused synthesis, but preprocessing quality improves.

### Docker Complexity (Deal-Breaker for Firecrawl)

Crawl4AI is a single Docker container with everything included (supervisord manages internal redis + gunicorn). It fits `start_docker_container()` with a one-line `--shm-size` addition.

Firecrawl's 5-service setup requires `docker compose` — which our `orchestrator_stack.py` does not currently support. Adding `start_compose_service()` is a moderate implementation burden (new function + compose file management), whereas Crawl4AI's single-container model requires adding two lines.

---

## 5. Concrete Integration Path (Crawl4AI)

### Port Assignment

- 8088: nextplaid-code
- 8089: nextplaid-docs
- 8090: SearXNG
- 9377: Camofox

Recommended: **8086** for Crawl4AI (clean gap, clear semantic slot below SearXNG).

### Docker Service Config

Add to `DOCKER_SERVICES` in `orchestrator_stack.py`:

```python
{
    "name": "crawl4ai",
    "port": 8086,
    "image": "unclecode/crawl4ai:latest",
    "description": "Async web scraper with JS rendering (steps 2+3 in research chain)",
    "volumes": [],
    "args": [],
    "env": {"MAX_CONCURRENT_TASKS": "5"},
    "shm_size": "1g",   # NEW field — Playwright requires shared memory
    "health_path": "/health",
},
```

One-line addition to `start_docker_container()`:
```python
if service.get("shm_size"):
    cmd.extend(["--shm-size", service["shm_size"]])
```

### Python Integration in `web/research.py`

```python
_CRAWL4AI_URL = "http://localhost:8086"

def _fetch_page_crawl4ai(url: str, max_length: int = _CONTENT_PER_PAGE) -> dict:
    """Step 2: single-page scrape via Crawl4AI."""
    import json, urllib.request
    payload = json.dumps({
        "urls": [url],
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "only_text": False,
            "word_count_threshold": 10,
        }
    }).encode()
    req = urllib.request.Request(
        f"{_CRAWL4AI_URL}/crawl",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        task_id = data["task_id"]
        result = _poll_crawl4ai_task(task_id, timeout=30)
        if not result or not result.get("success"):
            return {"url": url, "content": "", "success": False,
                    "escalate_to_camofox": _is_blocked_page(result)}
        content = (result.get("fit_markdown")
                   or result.get("markdown", {}).get("fit_markdown", ""))
        return {"url": url, "content": content[:max_length], "success": True,
                "escalate_to_camofox": False}
    except Exception as e:
        return {"url": url, "content": "", "success": False, "error": str(e)}
```

Step 3 (limited crawl) uses Crawl4AI's deep crawl endpoint with `BFS` strategy and `limit: 5`.

### Blocked-Page Detection

```python
_BLOCKED_SIGNALS = frozenset([
    "access denied", "ray id", "checking your browser",
    "ddos protection", "please enable javascript",
    "enable cookies", "verify you are human",
])

def _is_blocked_page(result: dict) -> bool:
    content = (result or {}).get("fit_markdown", "").lower()
    return not content or any(s in content for s in _BLOCKED_SIGNALS)
```

---

## 6. Verdict and Recommendation

### Adopt Crawl4AI for Steps 2+3

Crawl4AI wins on every dimension that matters for our stack:

| Criterion | Winner | Reason |
|-----------|--------|--------|
| Deployment simplicity | **Crawl4AI** | 1 container vs 5-service compose |
| Resource efficiency | **Crawl4AI** | ~1-2 GB idle vs 4-8 GB |
| Anti-bot (self-hosted) | **Crawl4AI** | Undetected Chrome vs basic Playwright |
| License | **Crawl4AI** | Apache-2.0 vs AGPL-3.0 |
| SDK dependency | **Crawl4AI** | Native HTTP vs `firecrawl-py` |
| `fit_markdown` BM25 filtering | **Crawl4AI** | Reduces synthesis worker load |
| Feature parity (our use case) | Tie | Both cover scrape + limited crawl |

**Firecrawl advantages** (structured JSON extraction, richer output formats, commercial support) are all irrelevant to our use case or require the cloud tier.

### Blocking Issues

None. Crawl4AI single-container fits `start_docker_container()` with a two-line change. No external SDK dependency. Apache-2.0.

### Integration Sequencing

1. **Now (independent of Camofox)**: Integrate Crawl4AI as `_fetch_page()` backend in `research.py`. Higher quality markdown than `html.parser`. No dependency on other open work.
2. **With Camofox** (intake-524 adopt_component phase): Wire `escalate_to_camofox` signal — when Crawl4AI returns a blocked-page indicator, call Camofox at step 4.
3. **Step 3**: Add `_fetch_docs_crawl_crawl4ai()` for limited multi-page crawl. Trigger when URL is a docs root or changelog index.

### Target Files

| File | Change |
|------|--------|
| `epyc-orchestrator/scripts/server/orchestrator_stack.py` | Add Crawl4AI to `DOCKER_SERVICES`; add `--shm-size` support to `start_docker_container()` |
| `epyc-orchestrator/src/tools/web/research.py` | Replace `_fetch_page()` with Crawl4AI backend; add `_is_blocked_page()` escalation signal |
| `epyc-orchestrator/src/tools/web/fetch.py` | Parallel change or shared backend abstraction |
| `epyc-root/config/crawl4ai/` | Docker config directory (likely zero-config via env vars) |

---

*Sources: github.com/mendableai/firecrawl, docs.firecrawl.dev, github.com/unclecode/crawl4ai, firecrawl-py PyPI, epyc-orchestrator source*
