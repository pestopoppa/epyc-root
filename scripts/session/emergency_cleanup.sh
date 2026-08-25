#!/bin/bash
# emergency_cleanup.sh - Clean up /tmp/claude and free root FS space
# Usage: sudo bash scripts/session/emergency_cleanup.sh
#
# Does NOT kill processes. It used to `sudo pkill -f claude`; on this shared host
# that is a wildcard over every session's argv (INC-20260731-broad-process-pattern-kills
# — kill only PIDs you captured and verified yourself). This script captures no
# PID, so it refuses to guess and prints the operator steps instead.

set -euo pipefail

echo "=============================================="
echo "Emergency Root FS Cleanup"
echo "=============================================="
echo ""

# Check current usage
ROOT_BEFORE=$(df / | awk 'NR==2 {print $5}')
echo "Root FS usage before cleanup: $ROOT_BEFORE"
echo ""

# ============================================
# 1. STOP RUNNING CLAUDE PROCESSES — REFUSES TO GUESS
# ============================================
#
# OBS-7 (2026-08-12). This section used to be `pgrep -f claude` + `sudo pkill -f
# claude`. A 'claude' substring matches EVERY argv on the host — including the
# caller of this very script and every other operator's session — so the pattern
# kill could terminate other sessions' processes, exactly what
# INC-20260731-broad-process-pattern-kills and AGENTS.md ("Process Management")
# forbid. The kill is gone; the operator stops only pids they verified themselves.

echo "Refusing to stop Claude processes by pattern:"
echo "  a 'claude' substring matches every session's argv on this shared host, and"
echo "  pattern-killing them would terminate other operators' sessions"
echo "  (INC-20260731-broad-process-pattern-kills)."
echo ""
echo "To stop sessions yourself, with pids you verified:"
echo "    ps -eo pid,etime,cmd | grep -i '[c]laude'"
echo "    kill <each-verified-pid>     # SIGTERM first; escalate to SIGKILL if needed"
echo ""

# ============================================
# 2. UNMOUNT /tmp/claude IF MOUNTED
# ============================================

if mountpoint -q /tmp/claude 2>/dev/null; then
  echo "Unmounting /tmp/claude bind mount..."
  if sudo umount /tmp/claude 2>&1; then
    echo "✓ Unmounted"
  else
    echo "⚠️  Unmount FAILED — /tmp/claude is held by a live process (usually a Claude"
    echo "   session). Continuing; a busy mount is not a reason to abort the cleanup."
    echo "   To free it later: stop the holder from within that session, or detach"
    echo "   lazily with:  sudo umount -l /tmp/claude"
  fi
fi

# ============================================
# 3. REMOVE /tmp/claude ENTIRELY
# ============================================

if [ -d /tmp/claude ]; then
  echo ""
  echo "Analyzing /tmp/claude contents..."
  du -sh /tmp/claude 2>/dev/null || echo "  (cannot access)"
  du -sh /tmp/claude/* 2>/dev/null | head -10 || true
  echo ""

  echo "⚠️  This will DELETE /tmp/claude and ALL contents."
  if mountpoint -q /tmp/claude 2>/dev/null; then
    echo "   NOTE: /tmp/claude is still bind-mounted — deletion goes THROUGH the mount"
    echo "   to /mnt/raid0/llm/tmp/claude, removing what a live session may be writing."
  fi
  echo "Continue? (y/n)"
  read -r response
  if [[ "$response" == "y" ]]; then
    echo "Removing /tmp/claude..."
    sudo rm -rf /tmp/claude
    echo "✓ Removed"
  else
    echo "Aborted. /tmp/claude preserved."
    exit 0
  fi
fi

# ============================================
# 4. CLEAN OTHER /tmp CRUFT
# ============================================

echo ""
echo "Cleaning other temporary files..."

# Remove old Python bytecode
sudo find /tmp -name "*.pyc" -type f -delete 2>/dev/null || true
sudo find /tmp -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove old pip builds
sudo rm -rf /tmp/pip-* 2>/dev/null || true

# Remove npm cache if present
sudo rm -rf /tmp/npm-* 2>/dev/null || true

echo "✓ Cleaned temporary files"

# ============================================
# 5. VERIFY RESULTS
# ============================================

echo ""
ROOT_AFTER=$(df / | awk 'NR==2 {print $5}')
echo "Root FS usage after cleanup: $ROOT_AFTER (was $ROOT_BEFORE)"
echo ""

# Verify /tmp/claude is gone
if [ -d /tmp/claude ]; then
  echo "⚠️  WARNING: /tmp/claude still exists!"
else
  echo "✓ /tmp/claude successfully removed"
fi

echo ""
echo "=============================================="
echo "Cleanup complete."
echo "Next steps:"
echo "  1. Use claude_safe_start.sh to start Claude Code"
echo "  2. Monitor root FS: watch -n 5 'df -h /'"
echo "=============================================="
