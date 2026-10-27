#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-ufh14-lb51-template
S="$B/STOP"
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then S="$B/T1-STOP"; else [[ -s "$B/MAIN-ACCEPTANCE.txt" ]] || exit 70; fi
exec /bin/bash "$B/deps/filler_run12.sh" --id ufh14-lb51-live-template-20261027 --class cpu --no-fold-siblings --role build --gpu-quiet none --min-window 600 --port 18994 --stop "$S" --workdir "$B" --cmd 'exec taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-ufh14-lb51-template/job.sh' --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex-ni-20261027-ufh14-lb51-template/PASS.json'
