#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/lsa-gpu-dense-bf16-8k-20261104/packet
R=/mnt/raid0/llm/tmp/lsa-gpu-dense-bf16-8k-20261104
ID=lsa-gpu-dense-bf16-8k-20261104
: "${FILLER_STATE_DIR:=$R/state}"
export FILLER_STATE_DIR
if [[ ${1:-} == --job ]]; then
  : "${FILLER_CPUS:?}"
  exec taskset -c "$FILLER_CPUS" /mnt/raid0/llm/epyc-inference-research/.venv/bin/python "$D/job.py"
fi
if [[ ${1:-} == --complete ]]; then
 python3 -c 'import json,os,pathlib,sys;p=pathlib.Path(os.environ["FILLER_STATE_DIR"]).parent/"native/RESULT.json";sys.exit(0 if p.is_file() and json.loads(p.read_text()).get("status") in ("pass","failure") else 1)'
 exit
fi
[[ $# == 0 ]]
: "${WS58_REGIONS:?}"
CLAIM_CPUS=${WS58_REGIONS#mi210_0,}
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class gpu --self-claim --role bench --gpu-quiet exclusive --claim-cpus "$CLAIM_CPUS" --min-window 900 --stop "$R/STOP" --workdir "$D" --cmd "/bin/bash $D/launcher.sh --job" --complete-cmd "/bin/bash $D/launcher.sh --complete"
