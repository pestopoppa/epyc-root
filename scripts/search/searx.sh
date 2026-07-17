#!/bin/bash
set -euo pipefail
# SearxNG bash bridge for Claude Code sessions.
# Routes high-volume / multilingual / engine-diversity queries through the
# self-hosted SearxNG instance at localhost:8888 instead of the built-in WebSearch.
#
# Per handoffs/active/searxng-bash-websearch-bridge.md (Approach #1).
#
# Usage: bash scripts/search/searx.sh '<query>' [--top N] [--engines e1,e2,...]
# Exit codes:
#   0 — query succeeded, JSON results emitted
#   1 — usage error (missing query)
#   2 — SearxNG not reachable/invalid, fall back to built-in WebSearch
#   3 — query failed (curl error, malformed response)

SEARX_URL="${SEARX_URL:-http://localhost:8888}"
TOP="${SEARX_TOP:-10}"
# WS1 default engine set: only engines that are responsive from our egress IP.
# duckduckgo (CAPTCHA), qwant (access denied) and startpage (Suspended: CAPTCHA)
# block our IP and are excluded. bing is the reliable workhorse; wikipedia is
# clean; brave/mojeek are best-effort (intermittently rate-limited) but harmless
# extras since bing carries results. Override with --engines or SEARX_ENGINES.
DEFAULT_ENGINES="brave,bing,mojeek,wikipedia"
ENGINES="${SEARX_ENGINES:-$DEFAULT_ENGINES}"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 '<query>' [--top N] [--engines e1,e2,...]" >&2
  exit 1
fi

QUERY="$1"
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --top) TOP="$2"; shift 2 ;;
    --engines) ENGINES="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

# Health check — exit 2 if unreachable so caller can fall back to WebSearch.
# To launch SearxNG: `bash scripts/search/searxng_up.sh` (delegates to
# orchestrator_stack.py's DOCKER_SERVICES entry — single source of truth).
if ! curl -s -m 2 -o /dev/null -w '%{http_code}' "${SEARX_URL}/healthz" 2>/dev/null | grep -qE '^(200|204)$'; then
  # /healthz is the standard SearxNG health endpoint; some configs use /. Try /.
  if ! curl -s -m 2 -o /dev/null -w '%{http_code}' "${SEARX_URL}/" 2>/dev/null | grep -qE '^(200|302)$'; then
    echo "SearxNG not reachable at ${SEARX_URL} — fall back to built-in WebSearch tool." >&2
    echo "To start: bash $(dirname "$0")/searxng_up.sh (or run orchestrator_stack.py start)" >&2
    exit 2
  fi
fi

# Build query URL.
ENGINE_PARAM=""
if [[ -n "$ENGINES" ]]; then
  ENGINE_PARAM="&engines=${ENGINES}"
fi

RESPONSE=$(curl -s -m 10 -G \
  --data-urlencode "q=${QUERY}" \
  "${SEARX_URL}/search?format=json&safesearch=0${ENGINE_PARAM}" 2>&1) || {
    echo "curl failed: ${RESPONSE}" >&2
    exit 3
  }

if ! echo "$RESPONSE" | jq empty 2>/dev/null; then
  echo "malformed JSON from SearxNG" >&2
  echo "$RESPONSE" | head -5 >&2
  exit 3
fi

if ! echo "$RESPONSE" | jq -e '(.results | type) == "array"' >/dev/null 2>&1; then
  echo "SearxNG search endpoint invalid at ${SEARX_URL} — fall back to built-in WebSearch tool." >&2
  echo "Expected /search?format=json to return a JSON object with a results array." >&2
  exit 2
fi

# WS1: base success on the actual results array, NOT on .number_of_results.
# SearxNG frequently reports number_of_results: 0 while .results is populated;
# a naive caller keying on that field wrongly concludes failure.
RESULT_COUNT=$(echo "$RESPONSE" | jq '(.results | length)')

# WS1b: degradation guard. When a majority of the REQUESTED engines are
# unresponsive, the responsive remainder (often just bing) tends to return
# low-relevance filler (fonts/dictionaries/homepages) rather than empty — a
# valid-JSON-but-junk failure that a naive caller trusts. Warn loudly so the
# caller prefers built-in WebSearch. Non-heuristic: keyed on the response's own
# unresponsive_engines list, not on score thresholds. Observed 2026-07-14:
# brave "too many requests" + mojeek "access denied" left bing-only junk.
REQ_ENGINE_COUNT=$(echo "$ENGINES" | tr ',' '\n' | grep -c . || true)
UNRESP_COUNT=$(echo "$RESPONSE" | jq '(.unresponsive_engines // [] | length)')
if [[ "${REQ_ENGINE_COUNT:-0}" -gt 0 && "${UNRESP_COUNT:-0}" -ge $(( (REQ_ENGINE_COUNT + 1) / 2 )) ]]; then
  echo "searx.sh: ⚠ DEGRADED — ${UNRESP_COUNT}/${REQ_ENGINE_COUNT} requested engines unresponsive; remaining results may be low-relevance filler. Prefer built-in WebSearch for this query." >&2
fi

# Flatten top-N results: title | url | score | engines | content snippet.
echo "$RESPONSE" | jq --argjson top "$TOP" '
  {
    query: .query,
    reported_number_of_results: .number_of_results,
    unresponsive_engines: .unresponsive_engines,
    results: [.results[:$top] | .[] | {
      title,
      url,
      score,
      engines,
      content: (.content // "" | .[0:240])
    }]
  } | . + {number_of_results: (.results | length)}
'

# A valid JSON response with an empty results array is a soft "no results"
# (exit 0), NOT a malformed/unreachable failure. Note it on stderr so the
# caller can decide whether to retry with --engines or fall back to WebSearch.
if [[ "$RESULT_COUNT" -eq 0 ]]; then
  echo "searx.sh: 0 results for query (engines=${ENGINES:-default}). Valid response, no hits — try --engines or WebSearch." >&2
fi
exit 0
