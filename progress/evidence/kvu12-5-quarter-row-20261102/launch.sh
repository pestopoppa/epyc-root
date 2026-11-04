#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kvu12-5-quarter-r2-20261102
ID=handoff-kvu12-5-quarter-r2-20261102
case "${1:-}" in
 --job)
  cd "$D"
  printf '%s  %s\n' f939806afda6dc3b247031a8ab7159c8847b9b0497c2bc6e6b73ecfdd79c305f SOURCE-SHA256SUMS | sha256sum -c --quiet
  sha256sum -c --quiet SOURCE-SHA256SUMS
  exec /usr/bin/python3 -B "$D/job.py" ;;
 --engine)
  export FILLER_RL="$D/region-lock"
  export FILLER_GRANTS_DIR="${FILLER_GRANTS_DIR:-/mnt/raid0/llm/tmp/compute-flags/grants}"
  case "${FILLER_DRYRUN:-missing}" in
   1) complete=control ;;
   0) complete=target ;;
   *) echo 'invalid or missing FILLER_DRYRUN' >&2; exit 64 ;;
  esac
  exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --role bench --claim-cpus 72-95,168-191 --gpu-quiet exclusive --min-window 45000 --stop "$D/STOP" --port 18970 --workdir "$D" --complete-cmd "/usr/bin/python3 -B $D/completion.py $complete" --cmd "env -i PATH=/usr/bin:/bin LANG=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 FILLER_DRYRUN=${FILLER_DRYRUN:-0} FILLER_DRYRUN_RESULT_PATH=\"\$FILLER_DRYRUN_RESULT_PATH\" FILLER_GRANTS_DIR=\"\$FILLER_GRANTS_DIR\" FILLER_ID=\"\$FILLER_ID\" FILLER_CPUS=\"\$FILLER_CPUS\" FILLER_THREADS=\"\$FILLER_THREADS\" FILLER_NEEDGPU=\"\$FILLER_NEEDGPU\" FILLER_STOPFILE=\"\$FILLER_STOPFILE\" FILLER_END=\"\$FILLER_END\" FILLER_DEADLINE=\"\$FILLER_DEADLINE\" FILLER_PIDFILE=\"\$FILLER_PIDFILE\" WS58_REGIONS=\"\$WS58_REGIONS\" /bin/bash $D/launch.sh --job" ;;
 '')
  exec > >(tee -a "$D/ws58-launcher.out") 2>&1
  exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env "FILLER_DRYRUN=${FILLER_DRYRUN:-0}" "FILLER_DRYRUN_RESULT_PATH=${FILLER_DRYRUN_RESULT_PATH:-}" "FILLER_SMOKE=${FILLER_SMOKE:-0}" "FILLER_DRYRUN_ONE_QUARTER=${FILLER_DRYRUN_ONE_QUARTER:-0}" "FILLER_DRYRUN_DIR=${FILLER_DRYRUN_DIR:-}" "FILLER_STATE_DIR=${FILLER_STATE_DIR:-}" "FILLER_FLAGS_DIR=${FILLER_FLAGS_DIR:-}" "FILLER_GRANTS_DIR=${FILLER_GRANTS_DIR:-}" "FILLER_POLL=${FILLER_POLL:-5}" "WS58_REGIONS=${WS58_REGIONS:-}" "FILLER_OWNER=${FILLER_OWNER:-handoff-kvu}" /bin/bash "$D/launch.sh" --engine ;;
 *) exit 64 ;;
esac
