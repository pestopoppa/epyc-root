#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kvu11c-gpu-mechanics-smoke-r2-20261105
PY="/usr/bin/env -u PYTHONOPTIMIZE /usr/bin/python3 -I"
printf '%s  %s\n' df1edf33ebd95897311f2cb28653f0bc379184371f2575e388f437158ca90279 "$D/job.py" | sha256sum -c
printf '%s  %s\n' e4def906c359e3d2533da02f70ac30da7fc49f28bf2f9fa4e72723e2c283359f "$D/pins.json" | sha256sum -c
printf '%s  %s\n' 74cf44448eac10724eb71427707d8194824080e2997e28e2ed44ac33ae0b9d4d "$D/model-preverify.json" | sha256sum -c
printf '%s  %s\n' 84e1801ec61153c2b40d1bb05f01492f8d5873d46ae33435cf968cc6cb552bca "$D/reference.wav" | sha256sum -c
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id kvu11c-gpu-mechanics-smoke-r2-20261105 --class gpu --role inference \
  --gpu-quiet exclusive --claim-cpus 184-187 --min-window 900 --stop "$D/STOP" --port 18197 --workdir "$D" \
  --precond-cmd "printf '%s  %s\\n' 2bc9caebc666e399d6740e8184cf69d862e4898430c3d587026c6325484b3ee7 '$D/packet.sha256' | sha256sum -c && sha256sum -c '$D/packet.sha256' && printf '%s  %s\\n' 21987e52ee02c609cd5a80f7b493b2d69fbaf367b4dd44bd9ff9fa3ec20c51b2 /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh | sha256sum -c && $PY '$D/job.py' --preflight" \
  --complete-cmd "$PY '$D/job.py' --complete" \
  --cmd "$PY '$D/job.py'"
