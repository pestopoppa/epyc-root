#!/bin/bash
# check_claims_grammar.sh — warn-mode validator for the MEASUREMENT.md claim grammar.
#
# Scans handoff/index markdown for decision-flavored performance/quality numbers
# that lack a protocol citation ([P-<ID>, ...]) or an explicit observation marker.
# Warn-mode by default (always exit 0); --strict exits 1 when findings exist.
#
# Usage:
#   check_claims_grammar.sh                 # scan uncommitted+staged diff vs HEAD
#   check_claims_grammar.sh --range A..B    # scan added lines in a git range
#   check_claims_grammar.sh --files F1 F2   # scan whole files
#   check_claims_grammar.sh --strict [...]  # nonzero exit on findings
#
# Heuristic, not authoritative: a finding means "this added line looks like a
# claim and cites no protocol" — the reviewer decides. Governed by MEASUREMENT.md §5.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

STRICT=0
MODE="diff"
RANGE=""
FILES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict) STRICT=1; shift ;;
    --range)  MODE="range"; RANGE="$2"; shift 2 ;;
    --files)  MODE="files"; shift; while [[ $# -gt 0 && "$1" != --* ]]; do FILES+=("$1"); shift; done ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Metric-shaped content: number + unit, or delta-language next to a number.
METRIC_RE='[0-9]+([.][0-9]+)? ?(t/s|tok/s|tokens/s|tasks?/(h|hour|eval-wall-h))|[0-9]+([.][0-9]+)? ?(pp|percentage points)\b|(speedup|faster|slower|regression|improvement|degrad)[a-z]* (of |by )?[0-9]|[0-9]+([.][0-9]+)?(x|×) (faster|slower|speedup)|\b(ECE|AUROC) [0-9]'
# Lines carrying any of these are already compliant or explicitly non-claims.
EXEMPT_RE='\[P-[A-Z]|P-SMOKE|[Oo]bservation|demoted|demote-to-prior|claim:unverified|prior only|historical|era-labeled|SUSPENDED|not promotable|\[x\]|https?://'

scan_stream() { # stdin: "file:line:text" triples
  grep -E "$METRIC_RE" | grep -Ev "$EXEMPT_RE" || true
}

findings=""
case "$MODE" in
  files)
    for f in "${FILES[@]}"; do
      findings+="$(grep -nE "$METRIC_RE" "$f" 2>/dev/null | grep -Ev "$EXEMPT_RE" | sed "s|^|$f:|" || true)"$'\n'
    done ;;
  range|diff)
    if [[ "$MODE" == "range" ]]; then diffcmd=(git diff "$RANGE"); else diffcmd=(git diff HEAD); fi
    findings="$("${diffcmd[@]}" --unified=0 -- 'handoffs/**/*.md' '*-index.md' 2>/dev/null \
      | awk '/^\+\+\+ b\//{f=substr($0,7)} /^\+[^+]/{print f": "substr($0,2)}' \
      | scan_stream)" ;;
esac

findings="$(printf '%s' "$findings" | sed '/^[[:space:]]*$/d')"
if [[ -n "$findings" ]]; then
  n=$(printf '%s\n' "$findings" | wc -l)
  echo "check_claims_grammar: $n line(s) look like uncited claims (need [P-<ID>, n, date, attest] or an observation marker):"
  printf '%s\n' "$findings" | head -50
  [[ "$n" -gt 50 ]] && echo "... ($((n-50)) more suppressed)"
  [[ "$STRICT" -eq 1 ]] && exit 1
else
  echo "check_claims_grammar: clean"
fi
exit 0
