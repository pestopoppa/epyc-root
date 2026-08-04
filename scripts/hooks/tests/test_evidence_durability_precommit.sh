#!/bin/bash
set -uo pipefail
# Asserts that epyc-inference-research's evidence-durability pre-commit extras
# actually blocks a registry commit that cites unverifiable evidence.
#
# WHY THIS EXISTS
# ---------------
# `scripts/validate/check_evidence_durability.py` was written on 2026-08-02, after
# the master registry was found citing 157 artifacts under the scratch root as the
# evidence behind ratified, production-affecting claims. It was then referenced by
# exactly one thing: a COMMENT inside model_registry.yaml. It had therefore never
# run automatically, in any repo, on any commit — a drift guard that only fires
# when somebody remembers it is not a guard, and the drift it catches is precisely
# the kind nobody remembers.
#
# It was wired on 2026-08-03 into `make evidence-check`, `make lint`/`make test`,
# `scripts/session/health_check.sh`, and `.git/hooks/pre-commit.extras`. The first
# three are covered by the research repo's own pytest/ruff suites. This file covers
# the fourth, for the same reason `test_precommit_wrapper.sh` exists: the hook
# COMPOSITION is not covered by the tests of the thing being composed, and the
# composition is where the 2026-08-03 status-propagation defect lived.
#
# WHAT IT ASSERTS
#   1. the installed wrapper still SOURCES pre-commit.extras (delete that line and
#      every per-repo check silently stops running, with a green tree);
#   2. the extras block passes a clean staged registry;
#   3. it FAILS a staged registry citing a scratch path;
#   4. it FAILS a staged registry citing a path that does not exist;
#   5. it fails CLOSED when the staged blob cannot be read.
#
# 2 exists so that 3-5 mean something: a hook that rejects everything blocks a bad
# commit for the wrong reason and gets disabled within the week.
#
# git is STUBBED rather than driven against a throwaway repo. The extras' whole job
# is to read `git diff --cached` and `git show :<path>`, so controlling those two
# answers is what makes the failure modes reachable — including the unreadable-blob
# branch, which a real index cannot easily produce. It also keeps this test from
# writing to any index on a shared host.
#
# Run: bash scripts/hooks/tests/test_evidence_durability_precommit.sh

RESEARCH_REPO="/mnt/raid0/llm/epyc-inference-research"
TRACKED_EXTRAS="${RESEARCH_REPO}/scripts/hooks/pre-commit.extras"
INSTALLED_EXTRAS="${RESEARCH_REPO}/.git/hooks/pre-commit.extras"
WRAPPER="${RESEARCH_REPO}/.git/hooks/pre-commit"
REGISTRY="${RESEARCH_REPO}/orchestration/model_registry.yaml"

FAILURES=0
pass() { printf '  ok   %s\n' "$1"; }
fail() { printf '  FAIL %s — %s\n' "$1" "$2"; FAILURES=$((FAILURES + 1)); }
note() { printf '  note %s\n' "$1"; }

# TEST THE TRACKED SOURCE, not the installed copy.
#
# Until 2026-08-04 this file read `.git/hooks/pre-commit.extras` and exited 0 with a
# "skip" when it was absent — which is every clone but this host, because `.git/` is
# versioned by nothing. The test therefore asserted nothing anywhere it could have
# caught a regression, while reporting success. The extras is now tracked at
# scripts/hooks/pre-commit.extras and installed from there, so a clone has the file to
# test whether or not the installer has ever run.
EXTRAS="$TRACKED_EXTRAS"
if [[ ! -e "$EXTRAS" ]]; then
  EXTRAS="$INSTALLED_EXTRAS"
  [[ -e "$EXTRAS" ]] || {
    echo "  skip epyc-inference-research — no pre-commit.extras, tracked or installed"
    exit 0
  }
  note "no tracked extras; falling back to the installed copy"
fi
if [[ ! -r "$REGISTRY" ]]; then
  echo "  skip epyc-inference-research — registry not present"
  exit 0
fi

# Drift between the tracked source and what this host actually runs. Informational:
# the remedy is `bash scripts/hooks/install_git_hooks.sh`, which rewrites live hooks and
# is the operator's to run, so a stale local copy must not turn this suite red. It must
# not be SILENT either — a host quietly running different bytes from the reviewed ones
# is how the extras became a one-host artifact in the first place.
if [[ -e "$TRACKED_EXTRAS" && -e "$INSTALLED_EXTRAS" ]] \
   && ! cmp -s "$TRACKED_EXTRAS" "$INSTALLED_EXTRAS"; then
  note "installed extras differs from the tracked source — run scripts/hooks/install_git_hooks.sh"
fi

# -- 1. the wrapper must still source the extras ------------------------------
if [[ -e "$WRAPPER" ]] && grep -q 'pre-commit.extras' "$WRAPPER"; then
  pass "wrapper sources pre-commit.extras"
else
  fail "wrapper" "does not source pre-commit.extras — every per-repo check is dead"
fi

# -- scaffolding: a stub git that answers only what the extras asks -----------
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
cat > "$TMP/bin/git" <<'STUB'
#!/bin/bash
case "$1" in
  diff) cat "$FAKE_STAGED_LIST"; exit 0 ;;
  show)
    if [[ -n "${FAKE_SHOW_FAIL:-}" ]]; then
      echo "fatal: path does not exist in the index" >&2
      exit 128
    fi
    cat "$FAKE_STAGED_BLOB"; exit 0 ;;
esac
exit 0
STUB
chmod +x "$TMP/bin/git"

printf 'README.md\n' > "$TMP/list_unrelated"
printf 'orchestration/model_registry.yaml\n' > "$TMP/list_registry"
cp "$REGISTRY" "$TMP/blob_clean.yaml"
cp "$REGISTRY" "$TMP/blob_scratch.yaml"
printf '\n# injected: /mnt/raid0/llm/tmp/synthetic-run-for-test/summary.json\n' \
  >> "$TMP/blob_scratch.yaml"
cp "$REGISTRY" "$TMP/blob_dead.yaml"
printf '\n# injected: data/no_such_campaign_for_test_20260803/summary.json\n' \
  >> "$TMP/blob_dead.yaml"

# Source the REAL extras with $status initialised the way the wrapper does.
drive() {
  PATH="$TMP/bin:$PATH" \
  FAKE_STAGED_LIST="$1" FAKE_STAGED_BLOB="$2" FAKE_SHOW_FAIL="${3:-}" \
  bash -c 'status=0; . "$0" >/dev/null 2>&1; echo "$status"' "$EXTRAS"
}

# -- 2. registry not staged: silent, and passes -------------------------------
rc="$(drive "$TMP/list_unrelated" "$TMP/blob_clean.yaml")"
if [[ "$rc" == "0" ]]; then
  pass "does not fire when the registry is not staged"
else
  fail "scoping" "fired on an unrelated staged file (status $rc) — an over-broad guard pushes people to --no-verify, which also skips the PII hook"
fi

# -- 3. the compliant path: current registry must pass ------------------------
rc="$(drive "$TMP/list_registry" "$TMP/blob_clean.yaml")"
if [[ "$rc" == "0" ]]; then
  pass "passes the current registry"
else
  fail "compliant path" "rejected the registry as it stands (status $rc) — the checks below prove nothing if it fails everything"
fi

# -- 4. a scratch citation must block -----------------------------------------
rc="$(drive "$TMP/list_registry" "$TMP/blob_scratch.yaml")"
if [[ "$rc" == "1" ]]; then
  pass "blocks a staged registry citing a scratch path"
else
  fail "scratch" "staged scratch citation did NOT block (status $rc)"
fi

# -- 5. a citation that resolves nowhere must block ----------------------------
rc="$(drive "$TMP/list_registry" "$TMP/blob_dead.yaml")"
if [[ "$rc" == "1" ]]; then
  pass "blocks a staged registry citing a path that does not resolve"
else
  fail "dead path" "staged dead citation did NOT block (status $rc)"
fi

# -- 6. unreadable staged blob must fail closed --------------------------------
rc="$(drive "$TMP/list_registry" "$TMP/blob_clean.yaml" 1)"
if [[ "$rc" == "1" ]]; then
  pass "fails closed when the staged blob cannot be read"
else
  fail "fail-closed" "unreadable staged blob was treated as a pass (status $rc)"
fi

if [[ "$FAILURES" -gt 0 ]]; then
  printf 'FAILED: %d assertion(s).\n' "$FAILURES" >&2
  exit 1
fi
echo "All assertions passed."
