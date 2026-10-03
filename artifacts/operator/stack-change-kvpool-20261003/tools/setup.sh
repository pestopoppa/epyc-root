#!/bin/bash
# setup.sh — phase 1 for STACKCHG-KVPOOL-20261003: tools from the DFLASH2 precedent
# (path-rewritten), the skill's scratch copy, and two git-archive sandboxes (base, new).
# Read-only on the real repos (git archive / git show / cp of sources).
set -euo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-kvpool-20261003
OLD=/mnt/raid0/llm/tmp/stack-change-dflash2-20261003
mkdir -p "$PKG/evidence" "$PKG/patches/orchestrator" "$PKG/patches/research" "$PKG/receipts"
for f in build_sandbox.sh verify.sh run_tests.sh make_patches.sh capacity_report.py render_argv.py; do
  sed "s#$OLD#$PKG#g" "$OLD/tools/$f" > "$PKG/tools/$f"
done
chmod +x "$PKG"/tools/*
bash /workspace/.claude/skills/stack-change/scripts/scratch.sh "$PKG/scratch"
bash "$PKG/tools/build_sandbox.sh" base
bash "$PKG/tools/build_sandbox.sh" new
du -sh "$PKG"
