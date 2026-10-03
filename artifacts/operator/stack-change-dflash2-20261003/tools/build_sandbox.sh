#!/bin/bash
# build_sandbox.sh — full-tree sandbox for preflight/compile/tests.
# Read-only on the real repos: `git archive` + `git show`, nothing else.
# The scratch (scratch.sh) holds the 7 hand-edited sources; the pipeline and the
# test suite need the whole orchestrator tree, so this mirrors HEAD beside it.
set -euo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-dflash2-20261003
ORCH=/mnt/raid0/llm/epyc-orchestrator
RES=/mnt/raid0/llm/epyc-inference-research
NAME="${1:?usage: build_sandbox.sh <name>}"
S="$PKG/sandbox-$NAME"
[ -e "$S" ] && { echo "REFUSING: $S exists" >&2; exit 2; }
mkdir -p "$S/orchestrator" "$S/research/orchestration" "$S/research/artifacts/serving-recipes"
git -C "$ORCH" archive HEAD | tar -x -C "$S/orchestrator"
git -C "$RES" show HEAD:orchestration/model_registry.yaml > "$S/research/orchestration/model_registry.yaml"
cmp "$S/research/orchestration/model_registry.yaml" "$RES/orchestration/model_registry.yaml"
git -C "$RES" show origin/main:orchestration/model_registry.yaml | cmp - "$RES/orchestration/model_registry.yaml"
# The lean symlink points at the REAL master by absolute path; re-point it.
rm "$S/orchestrator/orchestration/model_registry_full.yaml"
ln -s "$S/research/orchestration/model_registry.yaml" "$S/orchestrator/orchestration/model_registry_full.yaml"
echo "sandbox: $S"
echo "orch HEAD $(git -C "$ORCH" rev-parse HEAD)  research HEAD $(git -C "$RES" rev-parse HEAD 2>/dev/null)  origin/main $(git -C "$RES" rev-parse origin/main 2>/dev/null)"
