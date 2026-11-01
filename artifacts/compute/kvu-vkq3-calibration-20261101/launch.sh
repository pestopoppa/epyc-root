#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/handoff-kvu-vkq3-independent-calibration-20261101
ID=handoff-kvu-vkq3-independent-calibration-20261101
cd "$D"
case ${1:-} in
 --job)
  sha256sum -c --quiet SOURCE-SHA256SUMS
  sha256sum -c --quiet SOURCE-INPUTS.sha256
  sha256sum -c --quiet RUNTIME-INPUTS.sha256
  sha256sum -c --quiet FULL-MODELS.sha256
  case ${FILLER_DRYRUN:-missing} in
   1) export VKQ3_MODE=qualification ;;
   0) export VKQ3_MODE=full ;;
   *) echo "invalid or missing FILLER_DRYRUN" >&2; exit 64 ;;
  esac
  exec taskset -c 0-95 /usr/bin/python3 -B "$D/worker.py";;
 --engine)
  export FILLER_RL="$D/region-lock"
  case ${FILLER_DRYRUN:-missing} in
   1) complete="$D/qualification/QUALIFICATION.json"; completion_mode=qualification ;;
   0) complete="$D/run/TERMINAL.json"; completion_mode=full ;;
   *) echo "invalid or missing FILLER_DRYRUN" >&2; exit 64 ;;
  esac
  exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --role bench --claim-cpus 0-95 --min-window 9000 --stop "$D/STOP" --workdir "$D" --complete-cmd "/usr/bin/python3 -B $D/completion.py $completion_mode $complete" --cmd "env -i PATH=/usr/bin:/bin LANG=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 FILLER_DRYRUN=${FILLER_DRYRUN:-0} FILLER_ID=\"\$FILLER_ID\" FILLER_CPUS=\"\$FILLER_CPUS\" FILLER_NEEDGPU=\"\$FILLER_NEEDGPU\" FILLER_STOPFILE=\"\$FILLER_STOPFILE\" FILLER_END=\"\$FILLER_END\" FILLER_DEADLINE=\"\$FILLER_DEADLINE\" WS58_REGIONS=\"\$WS58_REGIONS\" /bin/bash $D/launch.sh --job";;
 '')
  exec > >(tee -a "$D/ws58-launcher.out") 2>&1
  exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env "FILLER_DRYRUN=${FILLER_DRYRUN:-0}" "FILLER_DRYRUN_DIR=${FILLER_DRYRUN_DIR:-}" "FILLER_STATE_DIR=${FILLER_STATE_DIR:-}" "FILLER_FLAGS_DIR=${FILLER_FLAGS_DIR:-}" "FILLER_GRANTS_DIR=${FILLER_GRANTS_DIR:-}" "FILLER_POLL=${FILLER_POLL:-5}" "WS58_REGIONS=${WS58_REGIONS:-}" "FILLER_OWNER=${FILLER_OWNER:-handoff-kvu}" /bin/bash "$D/launch.sh" --engine;;
 *) exit 64;;
esac
