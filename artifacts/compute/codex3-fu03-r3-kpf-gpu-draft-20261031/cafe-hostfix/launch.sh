#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/cafe1-hostfix
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1
export CAFE_SMALL_SHA=c159d1518f16bc42533d9a09f034eb598b670341adc2b08b9a9751614aea71eb CAFE_FULL_SHA=c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131
cd "$D"
printf '%s  %s\n' 71f4f300ce7286cef7719c7001c314e49dbeca069d6678d3466a4c9ae91c0426 "$D/SOURCE-SHA256SUMS" | sha256sum -c --quiet
printf '%s  %s\n' 18b533c2ca2513fcb47ac84060731882ed9a2bf8a6f5a7e9f9cf297a8c63162d "$D/EARLY.sha256" | sha256sum -c --quiet
sha256sum -c --quiet "$D/EARLY.sha256"
case ${1:-} in
 --job) sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"; sha256sum -c --quiet "$D/RUNTIME-INPUTS.sha256"; sha256sum -c --quiet "$D/FULL-MODEL.sha256"; export CAFE_MODE=full; taskset -c 0-95 /usr/bin/python3 -B "$D/worker.py"; if /usr/bin/python3 -c 'import json,sys; sys.exit(json.load(open(sys.argv[1])).get("state")!="complete_raw")' "$D/run/TERMINAL.json"; then /usr/bin/python3 -B "$D/analyze.py"; fi;;
 --smoke) sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"; sha256sum -c --quiet "$D/RUNTIME-INPUTS.sha256"; export CAFE_MODE=smoke FILLER_DEADLINE=$(( $(date +%s) + 250 )); exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/smoke-supervisor.py" 265 -- /usr/bin/python3 -B "$D/worker.py";;
 --engine) export FILLER_RL="$D/region-lock"; exec /bin/bash "$D/engine/filler_run13.sh" --id codex3-cafe1-pmin-hostfix-20261031 --class cpu --role bench --claim-cpus 0-95 --gpu-quiet exclusive --min-window 12000 --stop "$D/STOP" --workdir "$D" --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/cafe1-hostfix/run/TERMINAL.json' --cmd 'env -i PATH=/usr/bin:/bin LANG=C.UTF-8 RUS3_DIAGNOSTIC=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 FILLER_ID="$FILLER_ID" FILLER_CPUS="$FILLER_CPUS" FILLER_NEEDGPU="$FILLER_NEEDGPU" FILLER_STOPFILE="$FILLER_STOPFILE" FILLER_END="$FILLER_END" FILLER_DEADLINE="$FILLER_DEADLINE" WS58_REGIONS="$WS58_REGIONS" CAFE_SMALL_SHA=c159d1518f16bc42533d9a09f034eb598b670341adc2b08b9a9751614aea71eb CAFE_FULL_SHA=c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131 /bin/bash /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/cafe1-hostfix/launch.sh --job';;
 '') exec > >(tee -a "$D/ws58-launcher.out") 2>&1; exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/launch.sh" --engine;;
 *) exit 64;;
esac
