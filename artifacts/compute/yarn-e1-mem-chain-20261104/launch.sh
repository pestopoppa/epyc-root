#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/yarn-e1-mem-chain-20261104
ID=codex-ni-yarn-e1-mem-chain-r1-20261104
cd "$D"
sha256sum -c SOURCE.sha256 >/dev/null
sha256sum -c image.sha256 >/dev/null
export FILLER_FLAGS_DIR=${FILLER_FLAGS_DIR:-/mnt/raid0/llm/tmp/compute-flags}
export FILLER_GRANTS_DIR=${FILLER_GRANTS_DIR:-/mnt/raid0/llm/tmp/compute-flags/grants}
export FILLER_STATE_DIR=${FILLER_STATE_DIR:-$D/state}
exec > >(/usr/bin/tee -a "$D/launcher.log") 2>&1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class gpu --gpu-threads 184-191 --no-fold-siblings --role bench --gpu-quiet exclusive --min-window 3000 --stop "$D/STOP" --workdir "$D" --port 18438 --cmd "/bin/bash $D/job.sh" --complete-cmd "python3 -c 'import json, pathlib; assert json.load(open(\"$D/out/RESULT.json\"))[\"status\"] == \"COMPLETE\"; assert pathlib.Path(\"$D/out/chain-E1-A1/RAW-CUSTODY.sha256\").is_file()'"
