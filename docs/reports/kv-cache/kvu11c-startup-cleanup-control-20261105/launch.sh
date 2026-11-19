#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kvu11c-startup-cleanup-control-prep-20261105
printf '%s  %s\n' 1f0ced5150718943f181d7929d81a130451a181c3620daa4eac1ed049eafa25c "$D/job.py" | sha256sum -c
printf '%s  %s\n' e4def906c359e3d2533da02f70ac30da7fc49f28bf2f9fa4e72723e2c283359f "$D/pins.json" | sha256sum -c
printf '%s  %s\n' 74cf44448eac10724eb71427707d8194824080e2997e28e2ed44ac33ae0b9d4d "$D/model-preverify.json" | sha256sum -c
printf '%s  %s\n' 6a20b41abb07e3efeb9c882420a5246940db90f6e6b44acf388e81e84396d999 "$D/build-receipt.json" | sha256sum -c
printf '%s  %s\n' 57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33 "$D/verify_ggml_linkage.sh" | sha256sum -c
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
  export FILLER_STOPFILE="${FILLER_DRYRUN_DIR:?}/stop"
else
  export FILLER_STOPFILE="$D/STOP"
fi
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
printf '%s  %s\n' 21987e52ee02c609cd5a80f7b493b2d69fbaf367b4dd44bd9ff9fa3ec20c51b2 /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh | sha256sum -c
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id kvu11c-startup-cleanup-control-r1-20261105 --class gpu --role inference --gpu-quiet exclusive --claim-cpus 184-187 \
  --min-window 900 --stop "$D/STOP" --port 18209 --workdir "$D" \
  --precond-cmd "/usr/bin/env -u PYTHONOPTIMIZE /usr/bin/python3 -I '$D/job.py' --preflight" \
  --complete-cmd "/usr/bin/env -u PYTHONOPTIMIZE /usr/bin/python3 -I '$D/job.py' --complete" \
  --cmd "/usr/bin/env -u PYTHONOPTIMIZE /usr/bin/python3 -I '$D/job.py'"
