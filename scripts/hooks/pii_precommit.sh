#!/bin/bash
set -euo pipefail
# Git pre-commit hook: PII / secret hygiene.
# Scans staged blobs (NOT working tree — partial stages via `git add -p` are caught correctly).
# Two label categories: `secret` and `account_number`.
# Exits 1 on match (blocks commit). Exits 0 on clean staged set.
#
# Per handoffs/active/privacy-hygiene-precommit-hooks.md (PII-1).
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
  $'github_pat_[A-Za-z0-9_]{82}\tsecret\tGitHub fine-grained PAT'
  $'xox[baprs]-[A-Za-z0-9-]{10,72}\tsecret\tSlack token'
  $'-----BEGIN[[:space:]]+(RSA|DSA|EC|OPENSSH|PGP|ENCRYPTED)?[[:space:]]?PRIVATE[[:space:]]+KEY-----\tsecret\tprivate key (PEM block)'
  $'sk-[A-Za-z0-9]{20,}\tsecret\tgeneric API key prefixed sk-'
  $'sk-ant-api03-[A-Za-z0-9_-]{93,}\tsecret\tAnthropic API key'
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
  echo "$line" | grep -qiE '^\s*[a-z_][a-z0-9_]*\s*:\s*-?[0-9]+(\.[0-9]+)?(\s*#.*)?\s*$' && return 0
  return 1
}

is_version_or_hash_line() {
  # Skip lines containing git SHAs / version hashes — long hex runs, not digit runs.
  # The account_number regex only matches `[0-9]{12,19}`, so pure hex SHAs already won't match.
  # This is a placeholder for future extensibility.
  return 1
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
      if is_phone_number_line "$fullline"; then
        continue
      fi
      if is_timestamp_or_log_line "$fullline"; then
        continue
      fi
      if is_decimal_float_line "$fullline"; then
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

# Use -z + readarray to handle filenames safely (spaces, newlines).
mapfile -d '' -t STAGED_FILES < <(git diff --cached --name-only -z --diff-filter=ACM 2>/dev/null || true)

if [[ ${#STAGED_FILES[@]} -eq 0 ]]; then
  exit 0
fi

for path in "${STAGED_FILES[@]}"; do
  [[ -z "$path" ]] && continue
  if is_allowed "$path"; then
    continue
  fi

  # Skip files >MAX_FILE_BYTES (binary / large data).
  size=$(git cat-file -s ":${path}" 2>/dev/null || echo 0)
  if [[ "$size" -gt $MAX_FILE_BYTES ]]; then
    continue
  fi

  # Read staged blob (NOT working tree — catches partial stages).
  blob_content=$(git show ":${path}" 2>/dev/null || true)
  if [[ -z "$blob_content" ]]; then
    continue
  fi

  scan_blob "$path" "$blob_content" || true
done

if [[ $EXIT_CODE -ne 0 ]]; then
  echo "" >&2
  echo "[$HOOK_NAME] One or more staged files contain potential secrets / account numbers." >&2
  echo "[$HOOK_NAME] If false positive: tighten regex in scripts/hooks/pii_precommit.sh, do not bypass with --no-verify." >&2
  echo "[$HOOK_NAME] If real: remove the secret, rotate the credential, then re-stage." >&2
  echo "[$HOOK_NAME] Allow-list (legitimate fixtures): research/fixtures/pii_*" >&2
fi

exit $EXIT_CODE
