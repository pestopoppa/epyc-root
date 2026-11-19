#!/bin/bash
set -euo pipefail
umask 077
D=/mnt/raid0/llm/tmp/kvu/kvu19a2-gpu-repeat-20261104
E="$D"
ID=handoff-kvu-kvu19a2-repeatability-20261104
case ${1:-} in
 --job)
  [ "$(sha256sum "$E/assets.json" | cut -d' ' -f1)" = "$(cat "$E/assets.sha256")" ] || exit 65
  [ "$(sha256sum "$E/producer.py" | cut -d' ' -f1)" = "$(cat "$E/producer.sha256")" ] || exit 65
  [ "$(sha256sum "$E/device_identity.py" | cut -d' ' -f1)" = "$(cat "$E/device_identity.sha256")" ] || exit 65
  cd "$D"
  [ "$(sha256sum source.sha256 | cut -d' ' -f1)" = d5986318ec79e2b1e5b47bb7ef59d2f2cbd353f237b5b1b3ac5d55cfc2aea222 ] || exit 65
  sha256sum -c --quiet source.sha256
  sha256sum -c --quiet runtime.sha256
  exec /usr/bin/python3 -B "$E/producer.py" ;;
 --engine)
  if [ "${FILLER_DRYRUN:-0}" = 1 ]; then result="${FILLER_DRYRUN_RESULT_PATH:?}"; elif [ "${KVU_GPU_QUALIFICATION:-0}" = 1 ]; then result="$D/QUALIFICATION.json"; else result="$D/RESULT.json"; fi
  completion_mode=full
  if [ "${FILLER_DRYRUN:-0}" = 1 ] || [ "${KVU_GPU_QUALIFICATION:-0}" = 1 ]; then completion_mode=qualification; fi
  host_cpus=184-191
  if [ "${FILLER_DRYRUN:-0}" = 1 ] || [ "${KVU_GPU_QUALIFICATION:-0}" = 1 ]; then host_cpus="${WS58_REGIONS:?GPU smoke requires actual grant CPUs}"; fi
  export FILLER_RL="$D/region-lock"
  exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
    --id "$ID" --class gpu --role bench --gpu-quiet exclusive \
    --claim-cpus "$host_cpus" --gpu-threads "$host_cpus" --min-window 600 \
    --stop "$D/STOP" --workdir "$D" \
    --complete-cmd "/usr/bin/python3 -I -B $D/complete.py $result $completion_mode" \
    --cmd "env -i PATH=/usr/bin:/bin LANG=C.UTF-8 FILLER_DRYRUN=\"\$FILLER_DRYRUN\" FILLER_DRYRUN_RESULT_PATH=\"\${FILLER_DRYRUN_RESULT_PATH:-}\" FILLER_NEEDGPU=\"\$FILLER_NEEDGPU\" FILLER_PIDFILE=\"\$FILLER_PIDFILE\" FILLER_CPUS=\"\$FILLER_CPUS\" KVU_OFFLINE_CONTROL=\"\${KVU_OFFLINE_CONTROL:-0}\" FILLER_ID=\"\$FILLER_ID\" FILLER_STOPFILE=\"\$FILLER_STOPFILE\" FILLER_DEADLINE=\"\$FILLER_DEADLINE\" KVU_GPU_QUALIFICATION=\"\${KVU_GPU_QUALIFICATION:-0}\" /bin/bash $D/launch.sh --job" ;;
 '')
  exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env \
    "FILLER_DRYRUN=${FILLER_DRYRUN:-0}" \
    "FILLER_DRYRUN_DIR=${FILLER_DRYRUN_DIR:-}" \
    "FILLER_DRYRUN_RESULT_PATH=${FILLER_DRYRUN_RESULT_PATH:-}" \
    "FILLER_STATE_DIR=${FILLER_STATE_DIR:-}" \
    "FILLER_FLAGS_DIR=${FILLER_FLAGS_DIR:-}" \
    "FILLER_GRANTS_DIR=${FILLER_GRANTS_DIR:-/mnt/raid0/llm/tmp/compute-flags/grants}" \
    "KVU_OFFLINE_CONTROL=${KVU_OFFLINE_CONTROL:-0}" \
    "FILLER_SMOKE=${FILLER_SMOKE:-0}" \
    "KVU_GPU_QUALIFICATION=${KVU_GPU_QUALIFICATION:-0}" \
    "WS58_REGIONS=${WS58_REGIONS:-}" /bin/bash "$D/launch.sh" --engine ;;
 *) exit 64 ;;
esac
