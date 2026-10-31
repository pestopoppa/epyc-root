#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/dsc25592-hostfix
O=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/dsc25592
export RUS3_DIAGNOSTIC=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1
cd "$D"
printf '%s  %s\n' 272b9a08e0aaaa640621c4a3e1d6b34495a558de503fd14c8644234c64941542 "$D/SOURCE-SHA256SUMS" | sha256sum -c --quiet
sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"
case ${1:-} in
 --smoke) exec /bin/bash "$O/launch.sh" --smoke;;
 --engine) export FILLER_RL="$D/region-lock"; exec /bin/bash "$O/engine/filler_run13.sh" --id codex3-dsc-25592-replay-hostfix-20261031 --class cpu --role build  --claim-cpus "${WS58_REGIONS:?}" --min-window 5700 --stop "$O/STOP" --workdir "$O" --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/dsc25592/run/TERMINAL.json' --cmd 'env -i PATH=/usr/bin:/bin LANG=C.UTF-8 RUS3_DIAGNOSTIC=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 FILLER_ID="$FILLER_ID" FILLER_CPUS="$FILLER_CPUS" FILLER_NEEDGPU="$FILLER_NEEDGPU" FILLER_STOPFILE="$FILLER_STOPFILE" FILLER_END="$FILLER_END" FILLER_DEADLINE="$FILLER_DEADLINE" FILLER_PORTS="$FILLER_PORTS" WS58_REGIONS="$WS58_REGIONS" /bin/bash /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/dsc25592/launch.sh --job';;
 '') exec > >(tee -a "$D/ws58-launcher.out") 2>&1; exec sudo -n --preserve-env=WS58_REGIONS,FILLER_CPUS /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/launch.sh" --engine;;
 *) exit 64;;
esac
