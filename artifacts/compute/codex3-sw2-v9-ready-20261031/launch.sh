#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/sw2
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1
cd "$D"
printf '%s  %s\n' 870f555b87ee4c217b01559c9896423a609d8d0add1cada5df19c3bb6e4a41f3 "$D/SOURCE-SHA256SUMS" | sha256sum -c - >/dev/null
sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"
printf '%s  %s\n' 824f2ad5bd66fae498f35d3f2cb559b5a6f382035300b7056da05b30f67f5cf6 "$D/ORIGINAL-INPUT-SHA256SUMS" | sha256sum -c - >/dev/null
sha256sum -c --quiet "$D/ORIGINAL-INPUT-SHA256SUMS"
case ${1:-} in
 --job) export SW2_MODE=full; exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/worker.py";;
 --smoke) export SW2_MODE=smoke FILLER_DEADLINE=$(( $(date +%s) + 250 )); exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/smoke-supervisor.py" 265 -- /usr/bin/python3 -B "$D/worker.py";;
 --engine) export FILLER_RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock; exec /bin/bash "$D/engine/filler_run13.sh" --id codex3-sw2-v9-clamp-20261031 --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 900 --stop "$D/STOP" --workdir "$D" --complete-cmd "test -s $D/run/TERMINAL.json" --cmd 'env RUS3_DIAGNOSTIC=1 taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/sw2/launch.sh --job';;
 '') exec sudo -n --preserve-env=WS58_REGIONS,FILLER_CPUS /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/launch.sh" --engine;;
 *) exit 64;;
esac
