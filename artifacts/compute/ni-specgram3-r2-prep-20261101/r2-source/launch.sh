#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-specgram3-repair-20261101/cpu-r2-20261101
ID=codex-ni-specgram3-llg101-cpu-r2-20261101
RUN_ID=$ID
CANONICAL_ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/filler_run14.sh
CANONICAL_ENGINE_SHA=6fe168333738d15e5988d5af42e2b4c348194d722bac11c32368183ae89cd3ef
CANONICAL_CHECKER_SHA=102b6d297d78f2fc60a841d6349f1005e9e78ba4704552bf10bb84cb80bb2f7f
TEST_ENGINE=$D/../engine-exact-fixture/filler_run14.sh
TEST_ENGINE_SHA=$CANONICAL_ENGINE_SHA

sha() { sha256sum "$1" | awk '{print $1}'; }
fail() { echo "REFUSED: $*" >&2; exit 70; }

if [[ ${1:-} == --job ]]; then
  shift
  [[ $# == 0 ]] || fail "--job takes no extra arguments"
  exec /bin/bash "$D/job_entry.sh"
fi
if [[ ${1:-} == --check-complete ]]; then
  shift
  [[ $# == 0 ]] || fail "--check-complete takes no extra arguments"
  exec /bin/bash "$D/complete.sh"
fi
[[ $# == 0 ]] || fail "unsupported launcher arguments"
[[ -d $D && -f $D/job.py && -f $D/job_entry.sh && -f $D/complete.sh ]] || fail "r2 source bundle incomplete"

# Fingerprinting and qualification both bind the engine path from the manifest.
# Production manifests are restricted to the reviewed, ws58-installed canonical v14
# bundle. A model-free fixture may use an exact-byte source snapshot only.
ENGINE=$CANONICAL_ENGINE
if [[ ${WS58_QUAL:-0} == 1 || ${WS58_FINGERPRINT_ONLY:-0} == 1 ]]; then
  [[ -n ${WS58_MANIFEST_PATH:-} && -f $WS58_MANIFEST_PATH ]] || fail "qualification manifest absent"
  read -r manifest_id production engine_path engine_sha < <(/usr/bin/python3 -I - "$WS58_MANIFEST_PATH" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
print(m.get('id',''),int(bool(m.get('production'))),m.get('engine',{}).get('path',''),m.get('engine',{}).get('sha256',''))
PY
)
  [[ -n $manifest_id && $engine_sha == "$CANONICAL_ENGINE_SHA" ]] || fail "manifest engine pin differs from published v14"
  RUN_ID=$manifest_id
  if [[ $production == 1 ]]; then
    [[ $engine_path == "$CANONICAL_ENGINE" ]] || fail "production engine path is not ws58 qual-v1"
    ENGINE=$CANONICAL_ENGINE
  else
    [[ $engine_path == "$TEST_ENGINE" ]] || fail "fixture engine path is not the exact-source fixture snapshot"
    ENGINE=$TEST_ENGINE
  fi
  [[ ${WS58_QUALIFIER_PATH:-} == /mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/qualify_launcher.py ]] || {
    [[ $production == 0 && ${WS58_QUALIFIER_PATH:-} == "$D/../engine-exact-fixture/qualify_launcher.py" ]] || fail "qualifier path differs from pinned canonical v14 bundle"
  }
fi
[[ -f $ENGINE ]] || fail "canonical v14 engine is not installed at $ENGINE"
[[ $(sha "$ENGINE") == "$CANONICAL_ENGINE_SHA" ]] || fail "canonical v14 engine SHA mismatch"
engine_dir=$(dirname "$ENGINE")
[[ $(sha "$engine_dir/dryrun_check.py") == "$CANONICAL_CHECKER_SHA" ]] || fail "canonical v14 checker SHA mismatch"
[[ -n ${WS58_MANIFEST_PATH:-} && -n ${WS58_QUALIFIER_PATH:-} ]] || fail "canonical manifest/qualifier environment missing"

engine_args=(--id "$RUN_ID" --class cpu --role build --claim-cpus "${WS58_REGIONS:-}" \
  --min-window 1200 --stop "$D/STOP" --workdir "$D" \
  --cmd "/bin/bash $D/launch.sh --job" --complete-cmd "/bin/bash $D/complete.sh")
while IFS= read -r tool; do [[ -n $tool ]] && engine_args+=(--requires-tool "$tool"); done < <(/usr/bin/python3 -I - "$WS58_MANIFEST_PATH" <<'PYTOOLS'
import json,sys
for tool in json.load(open(sys.argv[1])).get('requires_tools',[]):print(tool)
PYTOOLS
)
qual_interpreter=$(/usr/bin/python3 -I - "$WS58_MANIFEST_PATH" <<'PYINT'
import json,sys
print(json.load(open(sys.argv[1])).get('qual_interpreter') or '/usr/bin/python3.13')
PYINT
)
engine_args+=(--qual-interpreter "$qual_interpreter")
if [[ ${WS58_FINGERPRINT_ONLY:-0} == 1 ]]; then
  exec /bin/bash "$ENGINE" "${engine_args[@]}"
fi

[[ -n ${WS58_REGIONS:-} ]] || fail "ws58 must provide the actual relocatable grant in WS58_REGIONS"
export OMP_NUM_THREADS=1 RUS3_DIAGNOSTIC=1
mkdir -p "$D/state"
exec /bin/bash "$ENGINE" "${engine_args[@]}"
