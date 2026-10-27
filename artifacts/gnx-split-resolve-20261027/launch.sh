#!/bin/bash
set -euo pipefail
root=/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase
packet="$root/stage2-packet-r2"
if [[ ${FILLER_PREFLIGHT:-0} != 1 ]]; then
 [[ -f "$packet/MAIN-APPROVAL.txt" && ! -L "$packet/MAIN-APPROVAL.txt" ]] || exit 6
 grep -Fxq approved-stage=resolve "$packet/MAIN-APPROVAL.txt" || exit 6
fi
exec /bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-c5-graph-call-edge-repair/deps/filler_run12.sh --id codex-ni-gnx-split-resolve-r2-20261027 --class cpu --no-fold-siblings --role build --gpu-quiet none --min-window 2700 --stop "$root/STOP" --workdir "$packet" --cmd 'exec taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase/stage2-packet-r2/body.sh' --complete-cmd 'jq -e '\''.status == "SCOPED_C72_SENTINELS_PASS_REVIEW_ONLY" and .fold_authority == false'\'' /mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase/stage2-results-r2/RESULT.json >/dev/null'
