#!/bin/bash
# health_check.sh - Pre-session system health check
# Usage: bash scripts/session/health_check.sh
#
# OBS-6 (2026-09-15): this script used to have exactly two verdicts, PASS/FAIL
# (WARN was a soft FAIL), and several probes forced an unreadable signal into
# that binary by piping it through `|| echo "unknown"` and then COMPARING
# "unknown" against the expected value — which reports FAIL for a node this
# container simply cannot see, identically to a real misconfiguration. Two
# name-pattern process probes had the matching defect for identity instead of
# for readability: `pgrep -f "claude"` is a bare substring over every process's
# argv, including THIS CHECK'S OWN CALLER (CLAUDE.md: "a guard process's argv
# necessarily contains the names it guards"), and `pgrep -f "monitor_storage"`
# reads a renamed/relocated monitor as permanently absent forever. Neither
# process publishes a pid/heartbeat file this script could check instead, so
# per the observation contract (scripts/coordination/observer_guard.sh) the
# honest answer where no reliable channel exists is UNKNOWN, not a guess dressed
# up as PASS/WARN/FAIL. Everything below is restructured so `main` can be
# skipped when this file is SOURCED (by scripts/session/tests/test_health_check.sh),
# leaving only read-only helper functions defined.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/env.sh"

check() {
  local test_name="$1"
  local condition="$2"
  local fail_msg="${3:-}"

  if eval "$condition"; then
    echo "✅ PASS: $test_name"
    ((PASS+=1))
    return 0
  else
    if [[ -n "$fail_msg" ]]; then
      echo "❌ FAIL: $test_name - $fail_msg"
      ((FAIL+=1))
    else
      echo "⚠️  WARN: $test_name"
      ((WARN+=1))
    fi
    return 0  # don't trip outer `set -e` — failures are tracked via $FAIL/$WARN + the summary
  fi
}

# sysfs_value <path> - print the raw content of a /proc or /sys node, or the
# literal sentinel __UNREADABLE__ if it cannot be read.
#
# __UNREADABLE__ is deliberately not a string the kernel could ever publish, so
# it can never be confused with a real (if wrong) setting the way the old
# `cat ... || echo "unknown"` fallback could — "unknown" IS a value a caller
# might legitimately compare against, and comparing an I/O failure to it by
# accident is exactly how an unreadable node got scored FAIL.
sysfs_value() {
  local path="$1"
  [[ -r "$path" ]] || { printf '__UNREADABLE__\n'; return 0; }
  cat "$path" 2>/dev/null || printf '__UNREADABLE__\n'
}

# sysfs_bracketed <path> - like sysfs_value, but for a kernel enum file whose
# active choice is the bracketed token (e.g. "always [madvise] never").
sysfs_bracketed() {
  local path="$1" raw
  raw="$(sysfs_value "$path")"
  [[ "$raw" == "__UNREADABLE__" ]] && { printf '__UNREADABLE__\n'; return 0; }
  printf '%s\n' "$raw" | awk -F'[][]' '{print $2}'
}

# check_sysfs_eq <test_name> <value> <expected> <fail_msg>
#
# THE THREE-VALUED FOLD for a sysfs/procfs equality probe: PASS, FAIL, or
# (new) UNKNOWN when the node could not be read at all — never counted as a
# pass, never counted as a fail. UNKNOWN is tallied separately and never gates
# the exit code, mirroring the SKIP verdict this file already uses for the
# episodic-memory check.
check_sysfs_eq() {
  local test_name="$1" value="$2" expected="$3" fail_msg="$4"
  if [[ "$value" == "__UNREADABLE__" ]]; then
    echo "❓ UNKNOWN: $test_name - node unreadable (container/sandbox?); not scored pass or fail"
    ((UNKNOWN+=1))
    return 0
  fi
  if [[ "$value" == "$expected" ]]; then
    echo "✅ PASS: $test_name"
    ((PASS+=1))
  else
    echo "❌ FAIL: $test_name - $fail_msg"
    ((FAIL+=1))
  fi
}

main() {

# Health-check profile: 'session-init' (default) protects quarter-TB model downloads; 'batch' relaxes
# thresholds for an inference-batch preflight whose artifact footprint is MB-scale, and demotes the
# /tmp/claude bind-mount check to advisory. Select via --profile <p> / --profile=<p> / $HEALTH_CHECK_PROFILE.
PROFILE="${HEALTH_CHECK_PROFILE:-session-init}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --profile=*) PROFILE="${1#*=}"; shift ;;
    *) shift ;;
  esac
done
case "$PROFILE" in
  session-init|batch) ;;
  *) echo "unknown --profile '$PROFILE' (use: session-init | batch)"; exit 64 ;;
esac

echo "=============================================="
echo "Pre-Session Health Check (profile: $PROFILE)"
echo "=============================================="
echo ""

PASS=0
WARN=0
FAIL=0
UNKNOWN=0

# ============================================
# 1. FILESYSTEM CHECKS
# ============================================

echo "--- Filesystem Health ---"

# Mount-aware free-GB check on the raid surface (replaces 2026-05-28 a hard <70% root-percentage
# threshold + a "RAID0 available >100GB" check whose 102400 1K-blocks threshold was actually 100 MB).
# Operator-set thresholds for the 3.7T shared surface: warn <750G, fail <500G.
RAID_MOUNT=/mnt/raid0
RAID_AVAIL_GB=$(df --output=avail -BG "$RAID_MOUNT" | awk 'NR==2 {gsub(/G/,""); print $1+0}')
# Guard an empty/missing df result so `[ "" -lt N ]` cannot trip set -e (audit cleanup item).
[ -z "$RAID_AVAIL_GB" ] && RAID_AVAIL_GB=0
if [ "$PROFILE" = "batch" ]; then
  # A batch/eval preflight writes MB-scale artifacts; guard only against a genuinely-full disk.
  RAID_FREE_WARN_GB=100
  RAID_FREE_FAIL_GB=20
else
  # session-init protects quarter-TB model downloads.
  RAID_FREE_WARN_GB=750
  RAID_FREE_FAIL_GB=500
fi
if [ "$RAID_AVAIL_GB" -lt "$RAID_FREE_FAIL_GB" ]; then
  echo "❌ FAIL: $RAID_MOUNT free ${RAID_AVAIL_GB}G < ${RAID_FREE_FAIL_GB}G fail threshold"
  ((FAIL+=1))
elif [ "$RAID_AVAIL_GB" -lt "$RAID_FREE_WARN_GB" ]; then
  echo "⚠️  WARN: $RAID_MOUNT free ${RAID_AVAIL_GB}G < ${RAID_FREE_WARN_GB}G warn threshold"
  ((WARN+=1))
else
  echo "✅ PASS: $RAID_MOUNT free ${RAID_AVAIL_GB}G (>= ${RAID_FREE_WARN_GB}G warn / ${RAID_FREE_FAIL_GB}G fail)"
  ((PASS+=1))
fi

check "/mnt/raid0/llm exists" "[ -d /mnt/raid0/llm ]" "Create with: mkdir -p /mnt/raid0/llm"

# /tmp/claude bind-mount matters for an interactive session (scratch redirection) but is irrelevant to a
# batch preflight, so it is advisory (WARN, not FAIL) under the batch profile.
if [ "$PROFILE" = "batch" ]; then
  check "/tmp/claude bind-mounted (advisory in batch)" "mountpoint -q /tmp/claude 2>/dev/null"
else
  check "/tmp/claude bind-mounted" "mountpoint -q /tmp/claude 2>/dev/null" "Not mounted - use claude_safe_start.sh"
fi

echo ""

# ============================================
# 2. ENVIRONMENT VARIABLES
# ============================================

echo "--- Environment Variables ---"

check "TMPDIR set" "[ -n \"\${TMPDIR:-}\" ]" "Set via env.sh or export TMPDIR=${TMP_DIR}"

if [ -n "${TMPDIR:-}" ]; then
  check "TMPDIR under LLM_ROOT" "[[ \"$TMPDIR\" == ${LLM_ROOT}/* ]]" "Currently: $TMPDIR"
fi

check "HF_HOME set" "[ -n \"\${HF_HOME:-}\" ]" "Set via env.sh or export HF_HOME=${HF_HOME}"

if [ -n "${HF_HOME:-}" ]; then
  check "HF_HOME under LLM_ROOT" "[[ \"$HF_HOME\" == ${LLM_ROOT}/* ]]" "Currently: $HF_HOME"
fi

echo ""

# ============================================
# 3. REQUIRED DIRECTORIES
# ============================================

echo "--- Required Directories ---"

check "${TMP_DIR} exists" "[ -d ${TMP_DIR} ]"
check "${CACHE_DIR} exists" "[ -d ${CACHE_DIR} ]"
check "${LLM_ROOT}/LOGS exists" "[ -d ${LLM_ROOT}/LOGS ]"
check "${MODELS_DIR} exists" "[ -d ${MODELS_DIR} ]"

echo ""

# ============================================
# 4. PROCESS CHECKS
# ============================================
#
# OBS-6: neither process below publishes a pid file or heartbeat this script
# could check instead of an argv substring, so — per the observation contract —
# the honest verdict is UNKNOWN, not a guessed PASS/WARN from a channel known to
# misfire. Recorded as UNKNOWN, never silently dropped: the limitation is the
# finding.

echo "--- Process Status ---"

echo "❓ UNKNOWN: Other Claude sessions running - no reliable channel: \`pgrep -f \"claude\"\` is a bare"
echo "   substring that matches this very check's own caller (CLAUDE.md: a guard's argv necessarily"
echo "   contains the names it guards), and no per-session pid/lock file exists to check instead. Not scored."
((UNKNOWN+=1))

echo "❓ UNKNOWN: Storage monitor running - \`pgrep -f \"monitor_storage\"\` reads a renamed or relocated"
echo "   monitor as permanently absent, and monitor_storage.sh publishes no pid/lock file to check instead."
echo "   Not scored; verify manually if this matters right now."
((UNKNOWN+=1))

echo ""

# ============================================
# 5. SYSTEM RESOURCES
# ============================================

echo "--- System Resources ---"

MEM_AVAIL=$(free -g | awk 'NR==2 {print $7}')
check "Available RAM >100GB" "[ $MEM_AVAIL -gt 100 ]"

CPU_GOVERNOR="$(sysfs_value "${EPYC_SYS_ROOT:-/sys}/devices/system/cpu/cpu0/cpufreq/scaling_governor")"
check_sysfs_eq "CPU governor is 'performance'" "$CPU_GOVERNOR" "performance" "Currently: $CPU_GOVERNOR"

# Canonical inference host prereqs — see docs/infrastructure/01-hardware-system.md
# and handoffs/active/cpu-kernel-env-flags-inventory.md
NUMA_BAL="$(sysfs_value "${EPYC_PROC_ROOT:-/proc}/sys/kernel/numa_balancing")"
check_sysfs_eq "kernel.numa_balancing is 0" "$NUMA_BAL" "0" "Currently: $NUMA_BAL — fix: sudo sysctl -w kernel.numa_balancing=0 (self-resets per session per feedback_numa_balancing_self_reset)"

THP_ENABLED="$(sysfs_bracketed "${EPYC_SYS_ROOT:-/sys}/kernel/mm/transparent_hugepage/enabled")"
check_sysfs_eq "THP enabled is 'always'" "$THP_ENABLED" "always" "Currently: $THP_ENABLED — fix: echo always | sudo tee /sys/kernel/mm/transparent_hugepage/enabled"

THP_DEFRAG="$(sysfs_bracketed "${EPYC_SYS_ROOT:-/sys}/kernel/mm/transparent_hugepage/defrag")"
check_sysfs_eq "THP defrag is 'always'" "$THP_DEFRAG" "always" "Currently: $THP_DEFRAG — fix: echo always | sudo tee /sys/kernel/mm/transparent_hugepage/defrag"

PERF_PARANOID="$(sysfs_value "${EPYC_PROC_ROOT:-/proc}/sys/kernel/perf_event_paranoid")"
if [[ "$PERF_PARANOID" == "__UNREADABLE__" ]]; then
  echo "❓ UNKNOWN: kernel.perf_event_paranoid <= 1 - node unreadable (container/sandbox?); not scored pass or fail"
  ((UNKNOWN+=1))
elif [[ "$PERF_PARANOID" =~ ^-?[0-9]+$ ]] && [ "$PERF_PARANOID" -le 1 ]; then
  echo "✅ PASS: kernel.perf_event_paranoid <= 1"
  ((PASS+=1))
else
  echo "❌ FAIL: kernel.perf_event_paranoid <= 1 - Currently: $PERF_PARANOID — fix: sudo sysctl -w kernel.perf_event_paranoid=1"
  ((FAIL+=1))
fi

echo ""

# ============================================
# 6. EPISODIC MEMORY INTEGRITY
# ============================================
#
# The episodic store's vector resolution was silently wrong for 22 days
# (2026-07-05 -> 2026-07-27) and nothing noticed, because nothing looked: the
# index loaded, queries returned neighbours, and retrieval produced
# plausible-looking results that were semantically random. An
# internally-consistent store can be completely wrong, so assert the properties
# that were actually violated. Metadata-only (0.2 s, no BGE servers, no
# inference); the decisive re-embed check is --semantic and is left to the
# pre-Autopilot gate.

echo "--- Episodic Memory ---"

EPISODIC_CHECK="${LLM_ROOT}/epyc-orchestrator/scripts/maintenance/check_episodic_integrity.py"
EPISODIC_STORE="${LLM_ROOT}/epyc-orchestrator/orchestration/repl_memory/sessions/embeddings.faiss"

if [[ ! -f "$EPISODIC_STORE" ]]; then
  echo "⏭️  SKIP: episodic store not present (nothing seeded yet)"
elif [[ ! -f "$EPISODIC_CHECK" ]]; then
  echo "⚠️  WARN: $EPISODIC_CHECK missing — store integrity is UNVERIFIED"
  ((WARN+=1))
else
  EPISODIC_OUT=$(cd "${LLM_ROOT}/epyc-orchestrator" && uv run python "$EPISODIC_CHECK" 2>&1) && EPISODIC_RC=0 || EPISODIC_RC=$?
  check "Episodic store integrity (sync, round-trip, diversity, degenerate vectors)" \
    "[ $EPISODIC_RC -eq 0 ]" \
    "$(echo "$EPISODIC_OUT" | grep -E '^\s+\[FAIL\]' | sed 's/^ *//' | tr '\n' ';') — do NOT trust memory-derived results; see handoffs/active/episodic-memory-integrity.md"
fi

echo ""

# ============================================
# 6b. TOOLING INTERPRETERS
# ============================================
# WHY: the orchestrator venv pins a uv-managed CPython. A devcontainer rebuild can
# wipe /home/node/.local/share/uv/python/, leaving .venv/bin/python a dangling
# symlink — every venv-backed gate (intake validation, kb-search, kb_rag hooks)
# then fails at invocation time, session by session, with no single owner.
# Repair: `uv python install 3.11` (version comes from .venv/pyvenv.cfg).

echo "--- Tooling Interpreters ---"

for VENV_PY in \
  "${PROJECT_ROOT}/repos/epyc-orchestrator/.venv/bin/python" \
  "${PROJECT_ROOT}/repos/epyc-inference-research/.venv/bin/python"; do
  VENV_NAME="$(basename "$(dirname "$(dirname "$(dirname "$VENV_PY")")")")"
  if [[ ! -L "$VENV_PY" && ! -f "$VENV_PY" ]]; then
    echo "⏭️  SKIP: $VENV_NAME venv not present"
    continue
  fi
  check "$VENV_NAME venv interpreter resolves" \
    "\"$VENV_PY\" -c 'import sys' >/dev/null 2>&1" \
    "interpreter is a dangling symlink ($(readlink -f "$VENV_PY" 2>/dev/null || echo unresolved)) — venv-backed gates (validate_intake.sh, kb-search) are DISABLED; repair with: uv python install \$(grep '^version_info' \"$(dirname "$(dirname "$VENV_PY")")/pyvenv.cfg\" | cut -d= -f2 | xargs | cut -d. -f1,2)"
done

# The repair path needs its own check: the same rebuild left ~/.cache/uv root-owned,
# so `uv python install` failed with Permission denied before it could fix anything.
UV_CACHE="${UV_CACHE_DIR:-${HOME}/.cache/uv}"
if [[ -d "$UV_CACHE" ]]; then
  UV_UNWRITABLE=$(find "$UV_CACHE" -maxdepth 1 -mindepth 1 -type d ! -writable 2>/dev/null | head -3 | tr '\n' ' ')
  check "uv cache is writable (the venv repair path)" \
    "[ -z \"$UV_UNWRITABLE\" ]" \
    "not writable: ${UV_UNWRITABLE:-?} — 'uv python install' will fail with Permission denied; repair with: sudo chown -R \$(id -un):\$(id -gn) $UV_CACHE"
fi

echo ""

# ============================================
# 7. SUMMARY
# ============================================

echo "=============================================="
echo "Health Check Summary"
echo "=============================================="
echo "  Passed:   $PASS ✅"
echo "  Warnings: $WARN ⚠️"
echo "  Failed:   $FAIL ❌"
echo "  Unknown:  $UNKNOWN ❓ (not scored pass or fail — see notes above)"
echo ""

if [ $FAIL -gt 0 ]; then
  echo "🚨 CRITICAL ISSUES DETECTED"
  echo ""
  echo "Recommended actions:"
  if [ "$RAID_AVAIL_GB" -lt "$RAID_FREE_FAIL_GB" ]; then
    echo "  1. Run emergency_cleanup.sh to free raid space (only ${RAID_AVAIL_GB}G free, < ${RAID_FREE_FAIL_GB}G fail threshold)"
  fi
  if ! mountpoint -q /tmp/claude 2>/dev/null; then
    echo "  2. Start Claude via: bash ${PROJECT_ROOT}/scripts/session/claude_safe_start.sh"
  fi
  if [ "$CPU_GOVERNOR" != "performance" ] && [ "$CPU_GOVERNOR" != "__UNREADABLE__" ]; then
    echo "  3. Set CPU governor: echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
  fi
  echo "  *. Apply ALL host tunables at once (governor, THP, numa_balancing,"
  echo "     perf_event_paranoid, EPP): bash ${PROJECT_ROOT}/scripts/session/host_prep.sh --apply"
  echo "     Boot persistence for the same set: host_prep.sh --verify-boot (install with --install-boot)"
  echo ""
  exit 1
elif [ $WARN -gt 0 ]; then
  echo "⚠️  WARNINGS PRESENT - Review above"
  echo ""
  exit 0
else
  echo "✅ ALL CHECKS PASSED - System ready for Claude session"
  echo ""
  echo "Start Claude Code:"
  echo "  bash ${PROJECT_ROOT}/scripts/session/claude_safe_start.sh"
  echo ""
  exit 0
fi

}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
