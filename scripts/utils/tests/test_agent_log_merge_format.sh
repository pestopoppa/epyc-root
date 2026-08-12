#!/bin/bash
# Regression test for scripts/utils/agent_log_read.sh's agent_log_merged().
#
# WHY THIS EXISTS (2026-08-12, coordinator review of 1c6839c5). The original
# claim was "all entries share ts-first JSON key order, so lexical sort is a
# correct chronological merge." That held on a synthetic fixture built from
# only JSON entries and was never checked against the real corpus. Measured
# against the real logs/agent_audit.log (4,402 lines): 1,167 lines are a
# pre-2026 bracketed format (`[2025-12-15T17:12:49+01:00] TASK_END: ...`), not
# JSON at all, plus a handful of older `{"timestamp":...}`-keyed lines. Lexical
# sort does not parse any of these — it happens to put every bracketed line
# before every JSON line only because `[` (0x5B) sorts before `{` (0x7B), and
# that accidentally matches chronology only because the bracketed format
# stopped being written before the JSON format started (Dec 2025 changeover).
#
# THE PROPERTY ACTUALLY UNDER TEST: agent_log_merged() produces two blocks —
# ALL legacy-format lines (in their original, already-chronological append
# order) followed by ALL "ts"-first JSON lines (sorted chronologically among
# themselves) — NOT one fully interleaved chronology. A fixture with only one
# format (as the original ad hoc verification used) cannot distinguish "sorts
# by real timestamp" from "sorts by leading byte, which happens to agree
# here" — this fixture mixes both formats specifically to tell them apart.
#
# Decision recorded here, not just in agent_log_read.sh: two-block ordering is
# ACCEPTED, not fixed with a timestamp-extracting parser — nothing has written
# the legacy formats since Dec 2025 (frozen corpus), so a multi-format parser
# on the hot read path would guard against writes that will never happen.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.." || exit 1
# shellcheck source=../agent_log_read.sh
source scripts/utils/agent_log_read.sh

pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got '$2' want '$3')"; fail=$((fail+1)); fi; }

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/logs"

# Legacy monolith: mixed-format, exactly as the real agent_audit.log is — old
# bracketed lines from before the Dec 2025 changeover, then JSON lines after
# it, all appended to the one file in real chronological order.
cat >"$TMP/logs/agent_audit.log" <<'EOF'
[2025-12-15T21:30:00+01:00] SESSION_START: legacy entry 1 | session=ses_legacy
[2025-12-15T21:35:00+01:00] TASK_START: legacy entry 2 | session=ses_legacy
{"ts":"2026-01-05T10:00:00+00:00","session":"ses_legacy","level":"INFO","cat":"TASK_END","msg":"first JSON entry after the changeover","details":""}
EOF

# Per-agent shard: JSON-only (shards did not exist before the format was
# already JSON), with one entry chronologically EARLIER than the monolith's
# JSON tail and one entry LATER — this is what actually exercises "sorts by
# real ts among JSON entries", independent of the legacy-block question.
cat >"$TMP/logs/agent_audit-mainA.log" <<'EOF'
{"ts":"2026-01-05T09:00:00+00:00","session":"ses_mainA","level":"INFO","cat":"TASK_START","msg":"shard entry earlier than monolith tail","details":""}
{"ts":"2026-01-05T11:00:00+00:00","session":"ses_mainA","level":"INFO","cat":"TASK_END","msg":"shard entry later than monolith tail","details":""}
EOF

merged="$(agent_log_merged "$TMP/logs")"
merged_lines="$(printf '%s\n' "$merged" | wc -l | tr -d ' ')"

# 1. No silent narrowing: merged output covers every line from every file,
#    not just one (the failure mode this whole shard/merge design exists to
#    prevent — see 1c6839c5's mainC-sees-0-vs-4 reproduction).
chk "total lines = sum of all fixture files (no narrowing)" "$merged_lines" "5"

# 2. DOCUMENTED (not aspirational) behavior: the two legacy-bracket lines
#    form a contiguous block, first in the output, in their original order.
first_two="$(printf '%s\n' "$merged" | head -2)"
expected_first_two='[2025-12-15T21:30:00+01:00] SESSION_START: legacy entry 1 | session=ses_legacy
[2025-12-15T21:35:00+01:00] TASK_START: legacy entry 2 | session=ses_legacy'
chk "legacy-bracket block is first, in original order" "$first_two" "$expected_first_two"

# 3. Every legacy-bracket line ('[' = 0x5B) sorts before every JSON line
#    ('{' = 0x7B) — the actual mechanism, stated as an assertion so a future
#    change to the merge (e.g. adding a real parser) has something to break.
bracket_after_json="$(printf '%s\n' "$merged" | awk '
  /^\{/ { seen_json=1 }
  /^\[/ && seen_json { found=1 }
  END { print (found ? "yes" : "no") }
')"
chk "no bracket line appears after a JSON line (two-block property)" "$bracket_after_json" "no"

# 4. Among the JSON entries, ts DOES drive order (this part is real, not
#    accidental): mainA's earlier shard entry sorts before the monolith's
#    JSON tail, which sorts before mainA's later shard entry.
json_only="$(printf '%s\n' "$merged" | grep '^{')"
json_ts_order="$(printf '%s\n' "$json_only" | grep -o '"ts":"[^"]*"')"
expected_ts_order='"ts":"2026-01-05T09:00:00+00:00"
"ts":"2026-01-05T10:00:00+00:00"
"ts":"2026-01-05T11:00:00+00:00"'
chk "JSON entries interleave correctly across files by real ts" "$json_ts_order" "$expected_ts_order"

# 5. The failure this test exists to catch: if agent_log_merged regressed to
#    reading only the legacy file (dropping shards), (1) would already fail
#    (3 lines, not 5) — restated explicitly here so it has its own name.
legacy_only_lines="$(wc -l <"$TMP/logs/agent_audit.log" | tr -d ' ')"
chk "legacy-only line count is NOT what the merge returns (sanity on the fixture itself)" \
  "$([ "$legacy_only_lines" != "$merged_lines" ] && echo differ || echo same)" "differ"

echo
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
