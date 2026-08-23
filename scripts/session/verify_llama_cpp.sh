#!/bin/bash
# verify_llama_cpp.sh — Verify the exact frozen production llama.cpp identity
#
# Run this at session start to prevent accidentally using the wrong source tip
# or stale CPU/HIP binaries. Returns non-zero on any identity mismatch.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/env.sh"

# Configuration (derived from env.sh)
LLAMA_CPP_DIR="${LLM_ROOT}/llama.cpp"
EXPECTED_BRANCH="production-consolidated-v9"  # 2026-08 v9 cutover: DSpark/DFlash plus request-local speculative n_max.
EXPECTED_COMMIT="0db32c06e3e550065b78311a6031ef3dd2c4f27c"
EXPECTED_VERSION_LINE="version: 10125 (0db32c06e)"
EXPECTED_CPU_SERVER_SHA256="8ebb1355593121a231735d7b58ad076f4539d2c5e3847fa09d2922fa8a980499"
EXPECTED_HIP_SERVER_SHA256="21cfb750dc0ba4b3add0674fcb9dd061d77b3604ebf8e1d063ba0e2c51902feb"
EXPERIMENTAL_DIR="${LLM_ROOT}/llama.cpp-experimental"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

verify_branch() {
  local dir="$1"
  local expected="$2"
  local label="$3"

  if [[ ! -d "$dir/.git" ]]; then
    echo -e "${YELLOW}⚠ $label not found at $dir${NC}"
    return 1
  fi

  local current_branch
  current_branch=$(cd "$dir" && git branch --show-current 2>/dev/null || echo "DETACHED")

  if [[ "$current_branch" == "$expected" ]]; then
    echo -e "${GREEN}✓ $label: $current_branch${NC}"
    return 0
  else
    echo -e "${RED}✗ $label: expected '$expected', got '$current_branch'${NC}"
    echo -e "${YELLOW}  Fix with: cd $dir && git checkout $expected${NC}"
    return 1
  fi
}

verify_commit() {
  local dir="$1"
  local expected="$2"
  local label="$3"
  local current

  if ! current=$(git -C "$dir" rev-parse HEAD 2>/dev/null); then
    echo -e "${RED}✗ $label commit cannot be resolved${NC}"
    return 1
  fi
  if [[ "$current" == "$expected" ]]; then
    echo -e "${GREEN}✓ $label commit: $current${NC}"
    return 0
  fi
  echo -e "${RED}✗ $label commit: expected '$expected', got '$current'${NC}"
  return 1
}

verify_tracked_state() {
  local dir="$1"
  local label="$2"

  if git -C "$dir" diff --quiet &&
      git -C "$dir" diff --cached --quiet; then
    echo -e "${GREEN}✓ $label tracked/index state is clean${NC}"
    return 0
  fi
  echo -e "${RED}✗ $label has tracked or staged changes${NC}"
  return 1
}

check_server_identity() {
  local server="$1"
  local expected_sha256="$2"
  local expected_version_line="$3"
  local label="$4"
  local actual_sha256
  local version_output
  local version_line

  if [[ ! -x "$server" ]]; then
    echo -e "${RED}✗ $label binary missing: $server${NC}"
    return 1
  fi
  actual_sha256=$(sha256sum -- "$server" | awk '{print $1}')
  if [[ "$actual_sha256" != "$expected_sha256" ]]; then
    echo -e "${RED}✗ $label SHA256: expected '$expected_sha256', got '$actual_sha256'${NC}"
    return 1
  fi
  if ! version_output=$(
    env LD_LIBRARY_PATH="$(dirname "$server")" LANG=C LC_ALL=C \
      "$server" --version 2>&1
  ); then
    echo -e "${RED}✗ $label --version failed${NC}"
    return 1
  fi
  version_line="${version_output%%$'\n'*}"
  if [[ "$version_line" != "$expected_version_line" ]]; then
    echo -e "${RED}✗ $label version: expected '$expected_version_line', got '$version_line'${NC}"
    return 1
  fi
  echo -e "${GREEN}✓ $label: $version_line ($actual_sha256)${NC}"
}

# The sanctioned ggml linkage verifier. Same absolute spelling as
# verify_speech_kernels.sh and orchestrator_stack.py's
# _VERIFY_GGML_LINKAGE_SCRIPT so all three enforce the same file rather than
# three drifting copies.
LINKAGE="/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh"

# ggml linkage (NIB2-58a): branch + sha256 prove WHICH binary is on disk; they
# say nothing about WHICH LIBRARIES it loads. Those are different failures, and
# only the second one is silent — on 2026-07-31 a HIP-built whisper-cli loaded
# the production CPU-only ggml, printed `use gpu = 1`, and produced well-formed
# output at CPU speed. This section completes the launcher-level wiring for the
# frozen llama.cpp tree, mirroring verify_speech_kernels.sh's linkage().
#
# Two environments are checked per server:
#   1. LAUNCH RECIPE — own lib dir prepended. Asserts the frozen build is
#      self-sufficient.
#   2. AMBIENT — this shell's LD_LIBRARY_PATH untouched. Asserts the ENVIRONMENT
#      is not poisoned; the condition that produced the incident, invisible to
#      check 1. A poisoned ambient path means anything launched from this shell
#      without prepending runs another tree's ggml.
check_linkage() {
  local label="$1" server="$2" lib_dir
  if [ ! -r "$LINKAGE" ]; then
    echo -e "${RED}✗ $label: ggml linkage verifier unavailable: $LINKAGE${NC}"
    return 1
  fi
  if [ ! -x "$server" ]; then
    echo -e "${RED}✗ $label: binary missing, nothing to link-check: $server${NC}"
    return 1
  fi
  lib_dir="$(cd "$(dirname "$server")" && pwd)"

  local out st inspected core
  # --- 1. launch recipe: own lib dir first
  out=$(LD_LIBRARY_PATH="$lib_dir:${LD_LIBRARY_PATH:-}" bash "$LINKAGE" "$server" "$lib_dir" 2>&1)
  st=$?
  inspected=$(printf '%s\n' "$out" | grep -cE '^[[:space:]]+(OK|BAD)[[:space:]]+lib(ggml|whisper|llama|mtmd)' || true)
  core=$(printf '%s\n' "$out" | grep -cE '^[[:space:]]+(OK|BAD)[[:space:]]+libggml-base\.so' || true)
  if [ "$st" -ne 0 ] || [ "$inspected" -eq 0 ] || [ "$core" -eq 0 ]; then
    echo -e "${RED}✗ $label: launch-recipe linkage FAILED (rc=$st, inspected=$inspected, libggml-base=$core)${NC}"
    printf '%s\n' "$out" | grep -E '^[[:space:]]+BAD ' | sed 's/^/       /'
    return 1
  fi
  echo -e "${GREEN}✓ $label: $inspected ggml libs resolve inside $lib_dir (launch recipe)${NC}"

  # --- 2. ambient environment, untouched
  out=$(bash "$LINKAGE" "$server" "$lib_dir" 2>&1)
  st=$?
  if [ "$st" -ne 0 ]; then
    echo -e "${RED}✗ $label: AMBIENT LD_LIBRARY_PATH mis-resolves this kernel's ggml${NC}"
    printf '%s\n' "$out" | grep -E '^[[:space:]]+BAD ' | sed 's/^/       /'
    echo -e "${YELLOW}  Fix:  export LD_LIBRARY_PATH=\"$lib_dir:\$LD_LIBRARY_PATH\"${NC}"
    return 1
  fi
  echo -e "${GREEN}✓ $label: ambient LD_LIBRARY_PATH also resolves in-tree${NC}"
  return 0
}

check_binary_exists() {
  local cpu_server="$LLAMA_CPP_DIR/build/bin/llama-server"
  local hip_server="$LLAMA_CPP_DIR/build-hip/bin/llama-server"
  local cli="$LLAMA_CPP_DIR/build/bin/llama-cli"
  local rc=0

  if ! check_server_identity \
      "$cpu_server" "$EXPECTED_CPU_SERVER_SHA256" "$EXPECTED_VERSION_LINE" \
      "Production CPU server"; then
    rc=1
  fi
  if ! check_server_identity \
      "$hip_server" "$EXPECTED_HIP_SERVER_SHA256" "$EXPECTED_VERSION_LINE" \
      "Production HIP server"; then
    rc=1
  fi
  # llama-cli is a smoke/bench helper, not a production-serving requirement.
  if [[ -x "$cli" ]]; then
    echo -e "${GREEN}✓ Smoke binary exists: $cli${NC}"
  else
    echo -e "${YELLOW}⚠ Smoke binary optional: $cli not built (only needed for llama-cli benches / smoke tests)${NC}"
  fi
  return $rc
}

main() {
  echo "=== llama.cpp Branch Verification ==="
  echo ""

  local errors=0

  # Check production branch
  if ! verify_branch "$LLAMA_CPP_DIR" "$EXPECTED_BRANCH" "Production"; then
    errors=$((errors + 1))
  fi
  if ! verify_commit "$LLAMA_CPP_DIR" "$EXPECTED_COMMIT" "Production"; then
    errors=$((errors + 1))
  fi
  if ! verify_tracked_state "$LLAMA_CPP_DIR" "Production"; then
    errors=$((errors + 1))
  fi

  # Check experimental is NOT production (should be on feature branch)
  if [[ -d "$EXPERIMENTAL_DIR/.git" ]]; then
    local exp_branch
    exp_branch=$(cd "$EXPERIMENTAL_DIR" && git branch --show-current 2>/dev/null || echo "DETACHED")
    if [[ "$exp_branch" == "$EXPECTED_BRANCH" ]]; then
      echo -e "${YELLOW}⚠ Experimental is also on $EXPECTED_BRANCH (expected feature branch)${NC}"
    else
      echo -e "${GREEN}✓ Experimental: $exp_branch (feature branch)${NC}"
    fi
  fi

  # Check binary exists
  if ! check_binary_exists; then
    errors=$((errors + 1))
  fi

  # ggml linkage — the frozen llama.cpp launch flow must be proven the same way
  # verify_speech_kernels.sh proves the speech trees'. A session that passes
  # branch/commit/sha256 can still silently run another tree's ggml.
  echo ""
  echo "=== ggml linkage ==="
  if ! check_linkage "Production CPU server" "$LLAMA_CPP_DIR/build/bin/llama-server"; then
    errors=$((errors + 1))
  fi
  if ! check_linkage "Production HIP server" "$LLAMA_CPP_DIR/build-hip/bin/llama-server"; then
    errors=$((errors + 1))
  fi

  echo ""

  if [[ $errors -gt 0 ]]; then
    echo -e "${RED}=== VERIFICATION FAILED ===${NC}"
    echo "Production llama.cpp is not correctly configured."
    echo "Fix the issues above before running inference."
    return 1
  else
    echo -e "${GREEN}=== VERIFICATION PASSED ===${NC}"
    return 0
  fi
}

# Run if executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
