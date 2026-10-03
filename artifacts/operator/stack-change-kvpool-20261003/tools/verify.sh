#!/bin/bash
# Phase-3/5 verification on sandbox-pristine = CURRENT HEADs (git archive) + this package's
# patches, applied with `git apply` exactly as phase 7 will. Also proves each patch still
# `git apply --check`s on the REAL working trees (read-only). Writes only under $PKG.
set -uo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-kvpool-20261003
S="$PKG/sandbox-pristine"
E="$PKG/evidence"
ORCH=/mnt/raid0/llm/epyc-orchestrator
RES=/mnt/raid0/llm/epyc-inference-research
OP="$PKG/patches/orchestrator/stackchg-kvpool-20261003.orchestrator.patch"
RP="$PKG/patches/research/stackchg-kvpool-20261003.research.patch"
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
rm -rf "$S"
bash "$PKG/tools/build_sandbox.sh" pristine 2>&1 | grep -v safe.directory
{
  echo "applied at $(date -u +%FT%TZ)"
  echo "orchestrator HEAD $(git -C "$ORCH" rev-parse HEAD)"
  echo "research     HEAD $(git -C "$RES" rev-parse HEAD 2>/dev/null)"
  echo "== git apply --check on the REAL working trees (read-only)"
  git -C "$ORCH" apply --check "$OP" && echo "ok  orchestrator patch applies to $(git -C "$ORCH" rev-parse --short HEAD)"
  git -C "$RES" apply --check "$RP" 2>/dev/null && echo "ok  research patch applies to $(git -C "$RES" rev-parse --short HEAD 2>/dev/null)"
  echo "== git apply into sandbox-pristine"
  (cd "$S/orchestrator" && git apply --verbose "$OP" 2>&1)
  (cd "$S/research" && git apply --verbose "$RP" 2>&1)
} > "$E/apply-proof.txt" 2>&1
# Byte-identity of the applied tree with the sandbox the patch was cut from.
for f in scripts/registry/stack_change_pipeline.py src/backends/context_limits.py stack_templates/default.yaml \
         tests/unit/test_context_limits_model_cap.py tests/unit/test_stack_change_pipeline.py tests/unit/test_stack_templates_v2.py tests/unit/test_kv_pool_long_prefill.py; do
  cmp -s "$S/orchestrator/$f" "$PKG/sandbox-new/orchestrator/$f" && echo "identical $f" || echo "DIFFERS $f"
done >> "$E/apply-proof.txt"
if cmp -s "$S/research/orchestration/model_registry.yaml" "$PKG/sandbox-new/research/orchestration/model_registry.yaml"; then
  echo "identical research master" >> "$E/apply-proof.txt"
else
  echo "DIFFERS research master" >> "$E/apply-proof.txt"
fi
cat "$E/apply-proof.txt"
bash "$PKG/tools/compile.sh" pristine
# Review-only delta of what phase 7's `update` will write (derived files, base vs pristine).
for f in orchestration/model_registry.yaml orchestration/derived/stack_priors.yaml \
         orchestration/model_descriptors.yaml docs/generated/current_stack_summary.md; do
  diff -u --label "HEAD+update/$f" --label "candidate+update/$f" \
    "$PKG/sandbox-base/orchestrator/$f" "$S/orchestrator/$f"
done > "$E/derived-delta.GENERATED.diff"
echo "derived delta lines: $(grep -c '^[-+][^-+]' "$E/derived-delta.GENERATED.diff")"
# The skill's preflight, repointed at the pristine sandbox.
sed -e "s|^ORCH=/mnt/raid0/llm/epyc-orchestrator\$|ORCH=$S/orchestrator|" \
    -e "s|^PY=\"\$ORCH/.venv/bin/python\"\$|PY=$PY|" \
    -e "s|check --numa-mode \"\$NUMA\"|check --numa-mode \"\$NUMA\" --research-registry $S/research/orchestration/model_registry.yaml|" \
    /workspace/.claude/skills/stack-change/scripts/preflight.sh > "$PKG/tools/preflight_scratch.sh"
bash "$PKG/tools/preflight_scratch.sh" "$E/preflight-classified.txt" > /dev/null 2>&1
echo "preflight rc=$?" >> "$E/preflight-classified.txt"
cat "$E/preflight-classified.txt"
# Skill sub-checks on the pristine tree (read-only; topology_check takes --orchestrator).
"$PY" /workspace/.claude/skills/change-topology/scripts/topology_check.py --orchestrator "$S/orchestrator" \
   --intent "$PKG/intent.yaml" > "$E/topology_check.txt" 2>&1
echo "rc=$?" >> "$E/topology_check.txt"
tail -4 "$E/topology_check.txt"
(cd "$S/orchestrator" && ORCH="$S/orchestrator" bash "$PKG/tools/capacity_sh_local.sh") > "$E/capacity_sh.txt" 2>&1
echo "rc=$?" >> "$E/capacity_sh.txt"
tail -12 "$E/capacity_sh.txt"
