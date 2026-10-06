#!/bin/bash
set -euo pipefail
# Git pre-commit hook: PII / secret hygiene.
# Scans staged blobs (NOT working tree — partial stages via `git add -p` are caught correctly).
# Two label categories: `secret` and `account_number`.
# Exits 1 on match (blocks commit). Exits 0 on clean staged set.
#
# Per handoffs/completed/privacy-hygiene-precommit-hooks.md (PII-1).
# Allow-pattern: research/fixtures/pii_* (the PII-2 fixture itself contains realistic-shape fake secrets).
# Skip: files >1MB, .gitignore'd files (defense in depth — Git already excludes these from index).
#
# Invoke: install at .git/hooks/pre-commit (one-line wrapper: exec /workspace/scripts/hooks/pii_precommit.sh).
# Bypass: `git commit --no-verify` is intentionally available, but document the reason if used.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HOOK_NAME="pii_precommit"
EXIT_CODE=0
MAX_FILE_BYTES=1048576  # 1 MB

# ─── Allow-list patterns (skip these files entirely) ──────────────────────────
ALLOW_PATTERNS=(
  '^research/fixtures/pii_'      # PII-2 evaluation fixture
  '^\.gitignore$'                # gitignore patterns reference secret-shape strings legitimately
  '^scripts/hooks/pii_precommit\.sh$'   # this hook itself contains regex patterns
)

# ─── Vendor-published documentation placeholders (NOT credentials) ────────────
# Exact literals that vendors publish specifically so docs and tests can show the
# shape of a credential without being one. They are matched EXACTLY — a prefix
# rule would let a real key hide behind a known-example stem.
#
# WHY THIS EXISTS. A redaction test has to contain a credential-SHAPED string to
# prove the redactor fires on it; that is the whole point of the test. Blocking it
# creates pressure to weaken the test instead — splitting the literal, or moving
# the fixture — which passes the scanner by hiding what it inspects rather than by
# being safe. That is strictly worse than a narrow, documented exception.
#
# Adding to this list is a security decision: only add strings the vendor
# publishes as a non-credential example, with the source noted.
KNOWN_PLACEHOLDERS=(
  'AKIAIOSFODNN7EXAMPLE'                      # AWS docs canonical example access key ID
  'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'  # AWS docs canonical example secret key
  'ASIAIOSFODNN7EXAMPLE'                      # AWS docs canonical example temporary key ID
)

is_known_placeholder() {
  local candidate="$1" known
  for known in "${KNOWN_PLACEHOLDERS[@]}"; do
    [[ "$candidate" == "$known" ]] && return 0
  done
  return 1
}

# True only when EVERY credential-shaped match on the line is a known placeholder.
# The scan greps whole LINES (no -o), so the credential must be re-extracted here.
# A line carrying both a placeholder and a real key must still block, which is why
# this is an all-must-pass test and not "contains a placeholder".
line_is_only_known_placeholders() {
  local line="$1" regex="$2" hit any=0
  while IFS= read -r hit; do
    [[ -z "$hit" ]] && continue
    any=1
    is_known_placeholder "$hit" || return 1
  done < <(printf '%s\n' "$line" | command grep -oE -e "$regex" 2>/dev/null || true)
  [[ $any -eq 1 ]]
}

# ─── Secret regexes (high-precision, low-false-positive) ─────────────────────
# Each entry: regex<TAB>label<TAB>description.
# Tab separator (not pipe) because alternation `(A|B|C)` inside regexes contains pipes.
SECRET_PATTERNS=(
  $'AKIA[0-9A-Z]{16}\tsecret\tAWS access key ID'
  $'ASIA[0-9A-Z]{16}\tsecret\tAWS temporary access key ID'
  $'aws_secret_access_key[[:space:]]*=[[:space:]]*[A-Za-z0-9/+=]{40}\tsecret\tAWS secret access key'
  $'ghp_[A-Za-z0-9]{36}\tsecret\tGitHub personal access token (classic)'
  $'ghs_[A-Za-z0-9]{36}\tsecret\tGitHub server-to-server token'
  $'gho_[A-Za-z0-9]{36}\tsecret\tGitHub OAuth user-to-server token'
  $'ghu_[A-Za-z0-9]{36}\tsecret\tGitHub user-to-server token'
  $'github_pat_[A-Za-z0-9_]{70,100}\tsecret\tGitHub fine-grained PAT'
  $'xox[baprs]-[A-Za-z0-9-]{10,72}\tsecret\tSlack token'
  $'-----BEGIN[[:space:]]+(RSA|DSA|EC|OPENSSH|ED25519|PGP|ENCRYPTED)?[[:space:]]?PRIVATE[[:space:]]+KEY-----\tsecret\tprivate key (PEM block)'
  $'sk-[A-Za-z0-9]{20,}\tsecret\tgeneric API key prefixed sk-'
  $'sk-ant-api03-[A-Za-z0-9_-]{80,}\tsecret\tAnthropic API key'
  $'AIza[0-9A-Za-z_-]{35}\tsecret\tGoogle API key'
  $'glpat-[A-Za-z0-9_-]{20,}\tsecret\tGitLab personal access token'
  $'eyJ[A-Za-z0-9_-]{10,}\\.eyJ[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}\tsecret\tJWT (header.payload.signature)'
)

# Account-number patterns: long digit runs in non-numeric contexts.
# Pattern intentionally wide; 12-19 digit runs.
# Phone-number / timestamp / log-line disambiguation in scan_blob().
ACCOUNT_PATTERNS=(
  $'\\b[0-9]{12,19}\\b\taccount_number\tlong digit run (12-19 digits) — possible account number'
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

is_allowed() {
  local path="$1"
  for pat in "${ALLOW_PATTERNS[@]}"; do
    if [[ "$path" =~ $pat ]]; then
      PII_ALLOWED_PATTERN="$pat"
      return 0
    fi
  done
  return 1
}

is_phone_number_line() {
  # Skip lines that look like phone numbers (E.164, US dashed, etc.)
  # Returns 0 (true) if the line looks phone-shaped.
  local line="$1"
  # E.164: +DD..., or US: (XXX) XXX-XXXX, XXX-XXX-XXXX, XXX.XXX.XXXX
  echo "$line" | grep -qE '(\+[0-9]{1,3}[[:space:]-]?[0-9]{3,4}[[:space:]-]?[0-9]{3,4}|\([0-9]{3}\)[[:space:]-]?[0-9]{3}[-.][0-9]{4}|\b[0-9]{3}[-.][0-9]{3}[-.][0-9]{4}\b)' && return 0
  return 1
}

is_timestamp_or_log_line() {
  # Skip lines that look like log/timestamp lines.
  # Heuristics:
  #   - line starts with `[` followed by digits (log format)
  #   - line contains a Unix timestamp shape (10/13/16 digits starting with 1[5-9])
  #   - line contains common log severity words near the digit run
  local line="$1"
  # Bracket-prefixed timestamp: [1234567890] or [1234567890.123]
  echo "$line" | grep -qE '^\[[0-9]{10,16}([.][0-9]+)?\]' && return 0
  # ISO date suffix or Unix epoch in line context (10/13/16 digit shapes starting with 1[5-9])
  echo "$line" | grep -qE '\b1[5-9][0-9]{8}([0-9]{3}([0-9]{3})?)?\b' && return 0
  # Log severity keywords
  echo "$line" | grep -qiE '\b(info|warn|error|debug|trace)[: ]' && return 0
  # llama-server log lines. ADDED 2026-08-02 — narrowly, after this rule produced
  # ~170 false positives while committing benchmark evidence.
  #
  # Two independent misses, both real gaps rather than bad luck:
  #   * llama-server prints a SINGLE-LETTER severity ("... I slot ..."), so the
  #     keyword rule above never fires on it.
  #   * its `t_last` slot counters are monotonic values starting 13..., not
  #     wall-clock epochs, so the 1[5-9] epoch shape above never matches either.
  # Net effect: every `t_last = 1304678976466` read as a candidate account number.
  #
  # Deliberately keyed on llama-server's whole line PREFIX shape
  # (`<s>.<ms>.<us>.<ns> <LEVEL> `), not on a looser digit rule: a broad "long
  # digit runs in logs are fine" exemption would be a real weakening, since logs
  # are exactly where a leaked token tends to land.
  echo "$line" | grep -qE '^[0-9]+\.[0-9]{2}\.[0-9]{3}\.[0-9]{3} [IWEDT] ' && return 0
  # Self-describing numeric JSON fields. ADDED 2026-08-02.
  # A digit run whose own KEY says it is a byte count, size or duration is not an
  # account number: `"total_shard_bytes": 238577580768` is a 238 GB model shard.
  # Byte-count keys may carry a semantic suffix (`storage_floor_bytes_free`), and
  # human-readable evidence may render the unit directly (`269009571840 bytes
  # free at campaign open`). Both forms remain keyed to an explicit byte unit.
  # Keyed on the field NAME rather than the value's shape, so it cannot be widened
  # into "long numbers in JSON are fine" — the key has to assert the semantics.
  # `tokens` ADDED 2026-09-07, same rule and same rationale as the byte keys above: a key
  # named `total_tokens` asserts its own semantics exactly as `total_shard_bytes` does. Added
  # after a real over-block -- fan-out token sums (`"total_tokens": 1098574444625`) blocked a
  # commit of measurement evidence. Fixture coverage for this and the four sibling branches
  # landed in the same change; before it, the account_number rule's ONLY must-not-block row
  # was 10 digits and could not reach this regex at all.
  echo "$line" | grep -qE '"[a-z0-9_]*(bytes(_[a-z0-9_]+)?|tokens|size|_ns|_us|_ms|elapsed|duration)"[[:space:]]*:[[:space:]]*[0-9]{12,19}\b' \
    && ! echo "$line" | grep -qiE '(^|[^a-z])(account|card|customer|iban|routing|ssn)([^a-z]|$)' && return 0
  echo "$line" | grep -qE '\b[0-9]{12,19}[[:space:]]+bytes([[:space:]]+(free|used|total))?\b' && return 0
  return 1
}

is_decimal_float_line() {
  # Skip lines where the digit run is part of a decimal float (preceded by `.`).
  # Common cases: temperature: 0.0736042256959058, threshold: 4.09045566671701.
  # Pattern: any `.` followed directly by 12+ digits.
  local line="$1"
  echo "$line" | grep -qE '\.[0-9]{12,}' && return 0
  # YAML-style numeric tuning keys typical in registry / config files.
  # If the line has `key: <number>` shape AND the number context is purely numeric
  # (no surrounding text), it's a config value, not an account number.
  # Do not exempt explicit account/card/customer identifiers.
  # BOUNDARY FIX 2026-09-07. This guard used `\b(account|card|...)\b`, and `\b` does not
  # separate on `_` -- so `\baccount\b` did NOT match `account_number`, the single most
  # obvious field name for an account number, and the config exemption below swallowed it.
  # Found by adding a negative-control fixture row for the exemption itself.
  # `[^a-z]` treats `_` as a separator while still refusing mid-word hits: `discard`,
  # `wildcard` and `shard` do not match `card`, because there the letter before is [a-z].
  echo "$line" | grep -qE '^\s*[A-Za-z_][A-Za-z0-9_]*\s*:' \
    && echo "$line" | grep -qiE '(^|[^a-z])(account|card|customer|iban|routing|ssn)([^a-z]|$)' \
    && return 1
  echo "$line" | grep -qE '^\s*[a-z_][a-z0-9_]*\s*:\s*-?[0-9]+(\.[0-9]+)?(\s*#.*)?\s*$' && return 0
  return 1
}

is_version_or_hash_line() {
  # Skip UUIDs / hashes. The account_number regex can otherwise catch the
  # all-digit tail group in UUIDs such as 550e8400-e29b-41d4-a716-446655440000.
  local line="$1"
  echo "$line" | grep -qiE '\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b' && return 0
  return 1
}

is_benchmark_prompt_hash_line() {
  # Generated benchmark artifacts carry prompt-free numeric prompt_hash fields.
  # Keep this scoped to benchmark result files and the exact JSON key so arbitrary
  # long digit runs in result payloads still trip the account-number guard.
  local path="$1"
  local line="$2"
  [[ "$path" =~ ^benchmarks/results/(eval|orchestrator)/.+[.](jsonl|json)$ ]] || return 1
  echo "$line" | grep -qE '"prompt_hash"[[:space:]]*:[[:space:]]*"[0-9]{12,19}"' && return 0
  return 1
}

is_autokernel_record_id_line() {
  # AutoKernel record identifiers are `<prefix>-<digits>[-<hex>]` with a closed
  # set of prefixes enforced by scripts/kernel_rnd/autokernel/schemas.py
  # (campaign ak-, proposal akp-, candidate akc-, evaluation ake-, journal akj-,
  # device-claim akd-, release akr-, seed aks-). Test fixtures pad the numeric
  # part, producing tokens like `akd-0000000000000000` that trip the bare
  # 12-19-digit account-number heuristic.
  #
  # Scoped to that closed prefix vocabulary ON PURPOSE rather than to a path or
  # to "any identifier-looking token": a genuine account number written as
  # `acct-123456789012` or `iban-...` must still block, and it does — only the
  # eight AutoKernel prefixes are disambiguated. Every match must be part of
  # such a token; a line mixing one AutoKernel id with a bare long digit run
  # still trips on the bare run.
  local line="$1"
  local stripped
  # Remove every well-formed AutoKernel id, then re-test what is left.
  stripped="$(echo "$line" | command sed -E 's/\bak[pcejdrs]?-[0-9]{6,}(-[0-9a-f]+)?//g')"
  if echo "$stripped" | command grep -qE '\b[0-9]{12,19}\b'; then
    return 1   # something else on the line is still a long digit run
  fi
  return 0
}
is_benchmark_per_question_line() {
  # Per-question eval records embed the benchmark's own problem text verbatim.
  # Coding suites (LiveCodeBench, SWE-bench) routinely carry 12-19 digit integer
  # literals in that text — graph edge weights in "Sample Input" blocks, and the
  # 10^18 constraint bound written out as 1000000000000000000 — plus digit runs
  # that fall inside a sha256 response fingerprint.
  #
  # Scoped to per-question artifacts AND the exact row shape those files emit, so
  # an arbitrary long digit run elsewhere in an evidence bundle still trips the
  # guard. Note the `secret` patterns above are NOT disambiguated by this or any
  # other helper: a real key in one of these files still blocks the commit.
  local path="$1"
  local line="$2"
  [[ "$path" =~ (^|/)(artifacts|data)/.+/per_question[.]jsonl$ ]] || return 1
  echo "$line" | grep -qE '"(arm|suite|question_id|qid)"[[:space:]]*:' && return 0
  return 1
}
is_benchmark_timing_line() {
  # llama-bench JSON artifacts legitimately contain 12+ digit nanosecond timing
  # counters and model parameter counts. Keep this exemption limited to generated
  # characterization output and exact benchmark metadata/timing keys; arbitrary
  # long digit runs still fail the hook.
  local path="$1"
  local line="$2"
  [[ "$path" =~ ^data/(cpu-model-characterization|gpu-mi210)/.+/(llama_bench_stdout[.]json|stdout[.]log|summary[.](json|md))$ ]] || return 1
  echo "$line" | grep -qE '"(avg_ns|stddev_ns)"[[:space:]]*:[[:space:]]*[0-9]{12,19}[,]?' && return 0
  echo "$line" | grep -qE '"samples_ns"[[:space:]]*:[[:space:]]*\[[[:space:]]*[0-9]{12,19}([[:space:]]*,[[:space:]]*[0-9]{12,19})*[[:space:]]*\]' && return 0
  if [[ "$path" =~ ^data/(cpu-model-characterization|gpu-mi210)/.+/summary[.]json$ ]]; then
    echo "$line" | grep -qE '^[[:space:]]*[0-9]{12,19},?[[:space:]]*$' && return 0
  fi
  echo "$line" | grep -qE '"model_n_params"[[:space:]]*:[[:space:]]*[0-9]{12,19}[,]?' && return 0
  return 1
}

is_perf_report_counter_line() {
  # Generated perf reports include large event counters. Exempt only perf report
  # headers under measurement artifact directories.
  local path="$1"
  local line="$2"
  [[ "$path" =~ ^data/op2_canonical_window/.+/perf_report(_.*)?[.]txt$ ]] || return 1
  echo "$line" | grep -qE '^# Event count [(]approx[.][)]:[[:space:]]*[0-9]{12,19}$' && return 0
  return 1
}

is_only_linux_vmalloc_total_counter_line() {
  # The exact NI05-61 VmallocTotal counter is a public Linux meminfo value.
  # Accept a raw line, or that exact line inside a serialized JSON raw_text
  # string. Remove only that raw_text occurrence in a scratch copy; any other
  # 12-19 digit candidate on the physical JSON line keeps the normal block path.
  local line="$1" sanitized
  if echo "$line" | grep -qE '^VmallocTotal:[[:space:]]+13743895347199[[:space:]]kB$'; then
    return 0
  fi
  sanitized="$(printf '%s\n' "$line" | command sed -E 's/((^[[:blank:]]*|[,{}][[:blank:]]*)"raw_text"[[:space:]]*:[[:space:]]*"[^"]*\\n)VmallocTotal:[[:space:]]+13743895347199[[:space:]]kB(\\n|")/\1\3/')"
  [[ "$sanitized" != "$line" ]] || return 1
  if printf '%s\n' "$sanitized" | command grep -qE '\b[0-9]{12,19}\b'; then
    return 1
  fi
  return 0
}

is_social_status_url_line() {
  # Skip lines containing X / Twitter status URLs — status IDs are 18-19 digit snowflake IDs.
  # Common shapes:
  #   x.com/<handle>/status/2054906931664585027
  #   x.com/i/status/2052103646712828119
  #   twitter.com/<handle>/status/1234567890123456789
  # Added 2026-05-19 after wiki batch surfaced jun_song / @neural_avb X-post intakes.
  local line="$1"
  echo "$line" | grep -qE '(x\.com|twitter\.com)/[^[:space:]]*status/[0-9]{15,19}' && return 0
  return 1
}

is_benchmark_answer_line() {
  # Generated benchmark result artifacts can legitimately contain long integer
  # factual answers. Keep this narrow: only suppress account-number hits for
  # answer-tagged numeric model responses in benchmark/package result files.
  local path="$1"
  local line="$2"
  [[ "$path" =~ ^benchmarks/results/runs/.+[.]json$ || "$path" =~ ^data/package_g/.+[.](jsonl|json)$ ]] || return 1
  echo "$line" | grep -qE '"response"[[:space:]]*:[[:space:]]*"?<answer>[0-9]{12,19}</answer>"?' && return 0
  return 1
}

is_perf_period_table_cell() {
  # Exempt one 12-13 digit value only in the exact public DS41/OAB
  # `observed periods` column. This is a cell exception: no path, file, or
  # whole-line bypass.
  local blob_content="$1"
  local lineno="$2"
  awk -v target="$lineno" '
    function trim(s) { sub(/^[[:space:]]+/, "", s); sub(/[[:space:]]+$/, "", s); return s }
    function cells(s, a, n) {
      if (s !~ /^\|.*\|$/) return 0
      sub(/^\|/, "", s); sub(/\|$/, "", s)
      n = split(s, a, "|")
      for (i = 1; i <= n; i++) {
        a[i] = trim(a[i])
        sub(/^`+/, "", a[i]); sub(/`+$/, "", a[i])
      }
      return n
    }
    { lines[NR] = $0 }
    END {
      if (target < 3 || target > NR) exit 1

      # Find the nearest separator in this contiguous pipe-table block. This
      # supports every body row and makes a newer/unrelated table supersede an
      # earlier matching header rather than inheriting its exception.
      block_start = target - 1
      while (block_start >= 1) {
        if (!cells(lines[block_start], scratch)) break
        block_start--
      }
      separator_line = 0
      for (j = target - 1; j > block_start; j--) {
        sn = cells(lines[j], sep_candidate)
        if (sn == 0) break
        is_separator = 1
        for (k = 1; k <= sn; k++) {
          part = sep_candidate[k]
          sub(/^:/, "", part); sub(/:$/, "", part)
          if (part !~ /^---+$/) is_separator = 0
        }
        if (is_separator) { separator_line = j; break }
      }
      if (!separator_line || separator_line - 1 <= block_start) exit 1

      hn = cells(lines[separator_line - 1], h)
      sn = cells(lines[separator_line], sep)
      rn = cells(lines[target], row)
      if (hn != 4 || hn != sn || hn != rn) exit 1
      if (tolower(h[1]) != "sampled-period fraction" || tolower(h[2]) != "observed periods" ||
          tolower(h[3]) != "dso" || tolower(h[4]) != "symbol") exit 1

      # Every intervening body row must remain inside this same four-column
      # table. A malformed row invalidates context for later rows.
      for (j = separator_line + 1; j <= target; j++) {
        if (cells(lines[j], body) != 4) exit 1
      }

      header = tolower(lines[separator_line - 1])
      rowtext = tolower(lines[target])
      sensitive = tolower(header " " rowtext)
      gsub(/_/, " ", sensitive)
      if (sensitive ~ /(^|[^[:alnum:]])(account|card|customer|iban|routing|ssn)([^[:alnum:]]|$)/) exit 1

      target_col = 2

      # Require exactly one 12+ digit run in the row, as the complete value
      # of a recognized period/sample cell. Other cells retain normal scanning.
      long_re = "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"
      for (i = 1; i <= rn; i++) {
        copy = row[i]
        count = gsub(long_re, "", copy)
        if (count) {
          total += count
          if (i != target_col || (length(row[i]) != 12 && length(row[i]) != 13) || row[i] !~ /^[0-9]+$/) exit 1
        }
      }
      exit (total == 1 ? 0 : 1)
    }
  ' <<< "$blob_content"
}

scan_blob() {
  local path="$1"
  local blob_content="$2"
  local found=0

  # Secret patterns. Use tab as field separator (regexes contain `|`).
  # Use `command grep` to bypass any shell function aliases (some envs alias grep -> ugrep).
  local entry regex label desc
  for entry in "${SECRET_PATTERNS[@]}"; do
    IFS=$'\t' read -r regex label desc <<<"$entry"
    while IFS=: read -r lineno match; do
      [[ -z "$lineno" ]] && continue
      # A vendor's published non-credential example is not a leak. Exact match only,
      # and only when every match on the line is one.
      if line_is_only_known_placeholders "$match" "$regex"; then
        continue
      fi
      printf 'BLOCKED: %s:%s: [%s] %s — matched: %s\n' "$path" "$lineno" "$label" "$desc" "$(echo "$match" | head -c 80)" >&2
      found=1
      EXIT_CODE=1
    done < <(echo "$blob_content" | command grep -nE -e "$regex" 2>/dev/null || true)
  done

  # Account-number patterns (with phone + timestamp + log-line disambiguation)
  for entry in "${ACCOUNT_PATTERNS[@]}"; do
    IFS=$'\t' read -r regex label desc <<<"$entry"
    while IFS=: read -r lineno match; do
      [[ -z "$lineno" ]] && continue
      local fullline
      fullline="$(echo "$blob_content" | sed -n "${lineno}p")"
      if is_only_linux_vmalloc_total_counter_line "$fullline"; then
        continue
      fi
      if is_phone_number_line "$fullline"; then
        continue
      fi
      if is_timestamp_or_log_line "$fullline"; then
        continue
      fi
      if is_decimal_float_line "$fullline"; then
        continue
      fi
      if is_version_or_hash_line "$fullline"; then
        continue
      fi
      if is_benchmark_prompt_hash_line "$path" "$fullline"; then
        continue
      fi
      if is_benchmark_timing_line "$path" "$fullline"; then
        continue
      fi
      if is_benchmark_per_question_line "$path" "$fullline"; then
        continue
      fi
      if is_autokernel_record_id_line "$fullline"; then
        continue
      fi
      if is_perf_report_counter_line "$path" "$fullline"; then
        continue
      fi
      if is_social_status_url_line "$fullline"; then
        continue
      fi
      if is_benchmark_answer_line "$path" "$fullline"; then
        continue
      fi
      if is_perf_period_table_cell "$blob_content" "$lineno"; then
        continue
      fi
      printf 'BLOCKED: %s:%s: [%s] %s — matched: %s\n' "$path" "$lineno" "$label" "$desc" "$(echo "$match" | head -c 80)" >&2
      found=1
      EXIT_CODE=1
    done < <(echo "$blob_content" | command grep -nE -e "$regex" 2>/dev/null || true)
  done

  return $found
}

# ─── Main ─────────────────────────────────────────────────────────────────────

# Original findings remain PRIVATE. Freeze the selected worktree index and its
# explicit HEAD comparison; recorder failure preserves the existing PII exit.
HOOK_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PII_CAPTURE_DIR=""
PII_CAPTURE_SUPPORTED=0
capture_control=""
if command -v python3 tee mktemp >/dev/null 2>&1 &&
   tee --output-error=warn </dev/null >/dev/null 2>&1 && capture_control=$(mktemp); then
  if python3 "$HOOK_DIR/pii_staged_capture.py" begin "$REPO_ROOT" >"$capture_control"; then
    {
      IFS= read -r -d '' PII_CAPTURE_DIR
      IFS= read -r -d '' PII_CAPTURE_COMPARISON
      IFS= read -r -d '' PII_CAPTURE_SUPPORTED
    } <"$capture_control" || PII_CAPTURE_DIR=""
  fi
  rm -f -- "$capture_control"
fi

pii_record_event() {
  [[ -z "$PII_CAPTURE_DIR" ]] && return 0
  printf '%s\0' "$@" >&"$PII_EVENTS_FD" || true
}

pii_finish_capture() {
  local original_status=$?
  trap - EXIT
  exec {PII_EVENTS_FD}>&-
  exec 1>&3 2>&4
  local logs_complete=1
  wait "$pii_stdout_pid" || logs_complete=0
  wait "$pii_stderr_pid" || logs_complete=0
  python3 "$HOOK_DIR/pii_staged_capture.py" finish "$PII_CAPTURE_DIR" "$original_status" "$logs_complete" || true
  exit "$original_status"
}

if [[ -n "$PII_CAPTURE_DIR" ]] && ! exec {PII_EVENTS_FD}>>"$PII_CAPTURE_DIR/events.nul"; then
  PII_CAPTURE_DIR=""
fi
if [[ -n "$PII_CAPTURE_DIR" ]]; then
  exec 3>&1 4>&2
  exec > >(tee --output-error=warn "$PII_CAPTURE_DIR/stdout.log" >&3)
  pii_stdout_pid=$!
  exec 2> >(tee --output-error=warn "$PII_CAPTURE_DIR/stderr.log" >&4)
  pii_stderr_pid=$!
  trap pii_finish_capture EXIT
  if [[ "$PII_CAPTURE_SUPPORTED" == 1 ]]; then
    export GIT_INDEX_FILE="$PII_CAPTURE_DIR/original-index"
    export GIT_OPTIONAL_LOCKS=0
  fi
fi

# Use -z + readarray to handle filenames safely (spaces, newlines).
comparison_args=()
[[ "$PII_CAPTURE_SUPPORTED" == 1 ]] && comparison_args+=("$PII_CAPTURE_COMPARISON")
mapfile -d '' -t STAGED_FILES < <(git diff --cached "${comparison_args[@]}" --name-only -z --diff-filter=ACM 2>/dev/null || true)

if [[ ${#STAGED_FILES[@]} -eq 0 ]]; then
  exit 0
fi

# Exact reviewed public fixture copies require complete original native custody
# from the INDEX. This does not waive any other file or change scanner patterns.
# One helper invocation batches Git reads and caches each verified phase.
PROVENANCE_FIXTURES=()
provenance_file=$(mktemp)
if python3 "$HOOK_DIR/fixture_snapshot_provenance.py" "$REPO_ROOT" "${comparison_args[@]}" >"$provenance_file"; then
  while IFS= read -r -d '' verified_path; do
    PROVENANCE_FIXTURES+=("$verified_path")
  done <"$provenance_file"
fi
rm -f -- "$provenance_file"

for path in "${STAGED_FILES[@]}"; do
  [[ -z "$path" ]] && continue
  if is_allowed "$path"; then
    pii_record_event "$path" path-exemption "$PII_ALLOWED_PATTERN"
    continue
  fi
  provenance_verified=0
  for verified_path in "${PROVENANCE_FIXTURES[@]}"; do
    if [[ "$path" == "$verified_path" ]]; then
      provenance_verified=1
      break
    fi
  done
  if [[ "$provenance_verified" -eq 1 ]]; then
    pii_record_event "$path" native-exemption original-source-custody
    continue
  fi

  # Skip files >MAX_FILE_BYTES (binary / large data).
  size_status=0
  size=$(git cat-file -s ":${path}" 2>/dev/null) || { size_status=$?; size=0; }
  if [[ "$size" -gt $MAX_FILE_BYTES ]]; then
    if [[ "$size_status" == 0 ]]; then
      pii_record_event "$path" oversized "$MAX_FILE_BYTES"
    else
      pii_record_event "$path" read-error "$size_status:unread:unscanned"
    fi
    continue
  fi

  # Read staged blob (NOT working tree — catches partial stages).
  read_status=0
  blob_content=$(git show ":${path}" 2>/dev/null) || read_status=$?
  if [[ -z "$blob_content" ]]; then
    if [[ "$size_status" == 0 && "$read_status" == 0 ]]; then
      pii_record_event "$path" empty existing-text-conversion
    else
      pii_record_event "$path" read-error "$size_status:$read_status:unscanned"
    fi
    continue
  fi

  scan_status=0
  scan_blob "$path" "$blob_content" || scan_status=$?
  if [[ "$size_status" == 0 && "$read_status" == 0 ]]; then
    pii_record_event "$path" scanned "$scan_status"
  else
    pii_record_event "$path" read-error "$size_status:$read_status:$scan_status"
  fi
done

if [[ $EXIT_CODE -ne 0 ]]; then
  echo "" >&2
  echo "[$HOOK_NAME] One or more staged files contain potential secrets / account numbers." >&2
  echo "[$HOOK_NAME] If false positive: tighten regex in scripts/hooks/pii_precommit.sh, do not bypass with --no-verify." >&2
  echo "[$HOOK_NAME] If real: remove the secret, rotate the credential, then re-stage." >&2
  echo "[$HOOK_NAME] Allow-list (legitimate fixtures): research/fixtures/pii_*" >&2
fi

if [[ -x "$REPO_ROOT/scripts/validate/check_imperative_injection.py" ]]; then
  "$REPO_ROOT/scripts/validate/check_imperative_injection.py" --cached --warn-only >&2 || true
fi

exit $EXIT_CODE
