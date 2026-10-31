#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-next-gpu-prep-20261031
ID=codex-ni-yarn-e1-mem-phase-r1-20261031
cd "$D"
sha256sum -c SOURCE.sha256 >/dev/null
case ${1:-} in
  --smoke)
    export FILLER_CPUS=184-185
    exec taskset -c "$FILLER_CPUS" /usr/bin/python3 -B "$D/run.py" smoke --deadline "$(( $(date +%s) + 270 ))"
    ;;
  --job)
    exec taskset -c "${FILLER_CPUS:?missing native CPUs}" /usr/bin/python3 -B "$D/run.py" full --deadline "${FILLER_DEADLINE:?missing native deadline}"
    ;;
  '') ;;
  *) exit 64;;
esac
cd "$D"
exec > >(/usr/bin/tee -a "$D/ws58-launcher.out") 2>&1
exec /usr/bin/env -i PATH=/usr/bin:/bin HOME=/home/node FILLER_FLAGS_DIR=/mnt/raid0/llm/tmp/compute-flags FILLER_GRANTS_DIR=/mnt/raid0/llm/tmp/compute-flags/grants FILLERS_MD=/mnt/raid0/llm/tmp/compute-flags/FILLERS.md FILLER_STATE_DIR="$D/state" /bin/bash "$D/helper/filler_run13.sh" --id "$ID" --class gpu --gpu-threads 184-191 --no-fold-siblings --role bench --gpu-quiet exclusive --min-window 5700 --stop "$D/STOP" --workdir "$D" --port 18437 --cmd "/bin/bash $D/launch.sh --job" --complete-cmd "python3 -c 'import json; assert json.load(open(\"$D/out/RESULT.json\"))[\"status\"] == \"COMPLETE\"'"
