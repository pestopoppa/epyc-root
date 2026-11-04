#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/worktrees/mains/h-triattention-kv-selection/artifacts/compute/lsa-cpu-window-8k-20261104
R=/mnt/raid0/llm/tmp/lsa-screen-1-cpu-window-8k-20261104
ID=lsa-screen-1-cpu-window-8k-20261104
: "${FILLER_STATE_DIR:=$R/state}"
export FILLER_STATE_DIR
if [[ ${1:-} == --job ]]; then
  : "${FILLER_CPUS:?}"
  exec taskset -c "$FILLER_CPUS" python3 -B "$D/job.py"
fi
if [[ ${1:-} == --complete ]]; then
  python3 -c 'import json,os,pathlib,sys; p=pathlib.Path(os.environ["FILLER_STATE_DIR"]).parent/"native/RESULT.json"; sys.exit(0 if p.is_file() and json.loads(p.read_text()).get("status")=="pass" else 1)'
  exit
fi
[[ $# == 0 ]]
: "${WS58_REGIONS:?}"
[[ $WS58_REGIONS =~ ^(0-3|24-27|48-51|72-75)$ ]] || { echo 'requires allocator four-core mask' >&2; exit 70; }
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --self-claim --role bench --gpu-quiet none --claim-cpus "$WS58_REGIONS" --min-window 300 --stop "$R/STOP" --port 18198 --workdir "$D" --cmd "/bin/bash $D/launcher.sh --job" --complete-cmd "/bin/bash $D/launcher.sh --complete"
