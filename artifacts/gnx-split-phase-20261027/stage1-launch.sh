#!/bin/bash
set -euo pipefail
root=/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase
[[ -f "$root/MAIN-APPROVAL.txt" && ! -L "$root/MAIN-APPROVAL.txt" ]] || exit 6
grep -Fxq approved-stage=prepare19 "$root/MAIN-APPROVAL.txt" || exit 6
exec /bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-c5-graph-call-edge-repair/deps/filler_run12.sh --id codex-ni-gnx-split-parse-20261027 --class cpu --no-fold-siblings --role build --gpu-quiet none --min-window 3300 --stop "$root/STOP" --workdir "$root" --cmd 'exec taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase/body.sh' --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase/stage1-state/identity.json && jq -e '\'' .kind == "parse-prepared-only" '\'' /mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase/stage1-state/prepared.json >/dev/null && jq -e '\'' .[0].rc == 0 and .[0].failure == null '\'' /mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase/stage1-results/phases.json >/dev/null'
