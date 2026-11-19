#!/bin/bash
set -euo pipefail
base=/mnt/raid0/llm/tmp/inf22-m4-q38-recipe-r4-20261104
src=$base/source
plan=$base/plan/PLAN.json
sha=98efaa341a003b0a9fb12f7071a8e14cd7bd80b0f453ab46e975e986e77917a4
python=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
flags=${FILLER_FLAGS_DIR:-/mnt/raid0/llm/tmp/compute-flags}
grants=${FILLER_GRANTS_DIR:-$flags/grants}
birth=$(sed 's/.*) //' /proc/$$/stat | awk '{print $20}')
output=$base/captures/run-r1
args=(--plan "$plan" --plan-sha256 "$sha" --grant "$grants/$FILLER_ID.grant" --stop "$FILLER_STOPFILE" --hold "$flags" --output "$output" --deadline "$FILLER_DEADLINE")
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
  "$python" -B "$src/scripts/benchmark/m4_cpu_recipe_entry.py" "${args[@]}" --owner-pid "$$" --owner-birth "$birth"
else
  mkdir "$output"
  "$python" -B "$src/scripts/benchmark/m4_cpu_ownership/lease_owner.py" --caller-pid "$$" --caller-birth "$birth" --gpu-quiet shared -- "$python" -B "$src/scripts/benchmark/m4_cpu_recipe_entry.py" "${args[@]}" --owner-pid '{owner_pid}' --owner-birth '{owner_birth}'
fi
