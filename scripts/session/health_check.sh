#!/bin/bash
# health_check.sh - Pre-session system health check
# Usage: bash scripts/session/health_check.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/env.sh"

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

echo "--- Process Status ---"

if pgrep -f "claude" >/dev/null; then
  echo "⚠️  WARN: Claude process already running"
  ps aux | grep -i claude | grep -v grep
  ((WARN+=1))
else
  echo "✅ PASS: No Claude processes running"
  ((PASS+=1))
fi

if pgrep -f "monitor_storage" >/dev/null; then
  echo "✅ PASS: Storage monitor is running"
  ((PASS+=1))
else
  echo "⚠️  WARN: Storage monitor not running - consider starting it"
  ((WARN+=1))
fi

echo ""

# ============================================
# 5. SYSTEM RESOURCES
# ============================================

echo "--- System Resources ---"

MEM_AVAIL=$(free -g | awk 'NR==2 {print $7}')
check "Available RAM >100GB" "[ $MEM_AVAIL -gt 100 ]"

CPU_GOVERNOR=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "unknown")
check "CPU governor is 'performance'" "[ \"$CPU_GOVERNOR\" == \"performance\" ]" "Currently: $CPU_GOVERNOR"

# Canonical inference host prereqs — see docs/infrastructure/01-hardware-system.md
# and handoffs/active/cpu-kernel-env-flags-inventory.md
NUMA_BAL=$(cat /proc/sys/kernel/numa_balancing 2>/dev/null || echo "unknown")
check "kernel.numa_balancing is 0" "[ \"$NUMA_BAL\" == \"0\" ]" "Currently: $NUMA_BAL — fix: sudo sysctl -w kernel.numa_balancing=0 (self-resets per session per feedback_numa_balancing_self_reset)"

THP_ENABLED=$(awk -F'[][]' '{print $2}' /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || echo "unknown")
check "THP enabled is 'always'" "[ \"$THP_ENABLED\" == \"always\" ]" "Currently: $THP_ENABLED — fix: echo always | sudo tee /sys/kernel/mm/transparent_hugepage/enabled"

THP_DEFRAG=$(awk -F'[][]' '{print $2}' /sys/kernel/mm/transparent_hugepage/defrag 2>/dev/null || echo "unknown")
check "THP defrag is 'always'" "[ \"$THP_DEFRAG\" == \"always\" ]" "Currently: $THP_DEFRAG — fix: echo always | sudo tee /sys/kernel/mm/transparent_hugepage/defrag"

PERF_PARANOID=$(cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo "unknown")
check "kernel.perf_event_paranoid <= 1" "[ \"$PERF_PARANOID\" -le 1 ] 2>/dev/null" "Currently: $PERF_PARANOID — fix: sudo sysctl -w kernel.perf_event_paranoid=1"

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
  check "Episodic store integrity (index/id_map, round-trip, diversity)" \
    "[ $EPISODIC_RC -eq 0 ]" \
    "$(echo "$EPISODIC_OUT" | grep -E '^\s+\[FAIL\]' | sed 's/^ *//' | tr '\n' ';') — do NOT trust memory-derived results; see handoffs/active/episodic-memory-integrity.md"
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
  if [ "$CPU_GOVERNOR" != "performance" ]; then
    echo "  3. Set CPU governor: echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
  fi
  echo ""
  exit 1
elif [ $WARN -gt 0 ]; then
  echo "⚠️  WARNINGS PRESENT - Review above"
  echo ""
  echo "Recommended actions:"
  if ! pgrep -f "monitor_storage" >/dev/null; then
    echo "  • Start monitor: bash ${PROJECT_ROOT}/scripts/session/monitor_storage.sh &"
  fi
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
