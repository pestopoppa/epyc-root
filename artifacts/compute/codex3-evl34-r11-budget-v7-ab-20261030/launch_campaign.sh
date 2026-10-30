#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-evl34-r11-budget-v7-ab-20261030
# The literal catalog digest pins every member before any host entry executes.
EXPECTED_CATALOG_SHA256=fc909212d2fbddcc7c43cf383ddc2da144f6a9803c88a0009ac40d968d3a9607
[[ $(sha256sum "$D/CAMPAIGN-SOURCES.sha256" | cut -d' ' -f1) == "$EXPECTED_CATALOG_SHA256" ]] || { echo 'source catalog digest mismatch' >&2; exit 78; }
sha256sum --quiet -c "$D/CAMPAIGN-SOURCES.sha256" || { echo 'source catalog member mismatch' >&2; exit 78; }
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 RUS3_DIAGNOSTIC=1
cd "$D"
: "${EVL34_EXTRA_HEADROOM_BYTES:=0}"
export EVL34_EXTRA_HEADROOM_BYTES
host=(sudo -n --preserve-env=HOME,FILLER_ID,FILLER_CPUS,FILLER_THREADS,FILLER_NEEDGPU,FILLER_END,FILLER_DEADLINE,FILLER_PIDFILE,EVL34_EXTRA_HEADROOM_BYTES,EVL34_PREFLIGHT_LOG /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/host-entry.sh")
if [[ ${1:-} == --calibration-smoke48 && $# == 1 ]]; then
 preflight_ok=0
 for spec in '26-27:26,27' '26-27:50,51' '26-27:74,75' '26-27:2,3' '26-27:122,123'; do
  pair=${spec%%:*}; cpus=${spec#*:}; exec {prep_fd}<>"/mnt/raid0/llm/tmp/compute-flags/prep-locks/${pair}.lock"
  if flock -n "$prep_fd"; then
   preflight_output=$(sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/taskset -c "$cpus" /usr/bin/env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 /mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/prep/prep_supervisor.py 120 -- /bin/bash "$D/host-entry.sh" --preflight) || { flock -u "$prep_fd"; exec {prep_fd}>&-; continue; }
   IFS= read -r EVL34_PREFLIGHT_LOG <<< "$preflight_output"; export EVL34_PREFLIGHT_LOG
   flock -u "$prep_fd";exec {prep_fd}>&-;preflight_ok=1;break
  fi
  exec {prep_fd}>&-
 done
 [[ $preflight_ok == 1 ]] || exit 75
 exec /workspace/repos/epyc-orchestrator/scripts/region-lock run --gpu-quiet exclusive --timeout-s 300 -- taskset -c 184-185 "${host[@]}" --smoke
fi
if [[ ${1:-} == --job && $# == 1 ]]; then exec "${host[@]}" --job;fi
[[ $# == 0 ]] || exit 64
exec bash /mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/engine/filler_run13.sh --id codex3-evl34-r11-budget-v7-ab-20261030 --class gpu --gpu-quiet exclusive --no-fold-siblings --gpu-threads 184-191 --min-window 19740 --port 19987 --stop "$D/STOP" --workdir "$D" --cmd "taskset -c \"\$FILLER_CPUS\" /bin/bash $D/launch_campaign.sh --job" --complete-cmd "test -f $D/PILOT-DONE.json" >> "$D/ws58-launcher.out" 2>&1
