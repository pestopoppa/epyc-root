#!/bin/bash
set -euo pipefail
# SearxNG bash bridge for Claude Code sessions.
# Routes high-volume / multilingual / engine-diversity queries through the
# self-hosted SearxNG instance at localhost:8090 instead of the built-in WebSearch.
#
# Per handoffs/active/searxng-bash-websearch-bridge.md (Approach #1).
#
# Usage: bash scripts/search/searx.sh '<query>' [--top N] [--engines e1,e2,...]
# Exit codes:
#   0 — query succeeded, JSON results emitted
#   1 — usage error (missing query)
#   2 — SearxNG not reachable, fall back to built-in WebSearch
#   3 — query failed (curl error, malformed response)

SEARX_URL="${SEARX_URL:-http://localhost:8090}"
TOP="${SEARX_TOP:-10}"
ENGINES=""

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
if ! curl -s -m 2 -o /dev/null -w '%{http_code}' "${SEARX_URL}/healthz" 2>/dev/null | grep -qE '^(200|204)$'; then
  # /healthz is the standard SearxNG health endpoint; some configs use /. Try /.
  if ! curl -s -m 2 -o /dev/null -w '%{http_code}' "${SEARX_URL}/" 2>/dev/null | grep -qE '^(200|302)$'; then
    echo "SearxNG not reachable at ${SEARX_URL} — fall back to built-in WebSearch tool." >&2
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

# Flatten top-N results: title | url | score | engines | content snippet.
echo "$RESPONSE" | jq --argjson top "$TOP" '
  {
    query: .query,
    number_of_results: .number_of_results,
    unresponsive_engines: .unresponsive_engines,
    results: [.results[:$top] | .[] | {
      title,
      url,
      score,
      engines,
      content: (.content // "" | .[0:240])
    }]
  }
'
