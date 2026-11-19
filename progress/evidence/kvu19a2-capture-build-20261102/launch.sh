#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kvu19a2-capture-build-20261102
ID=handoff-kvu-kvu19a2-capture-build-20261102
case ${1:-} in
 --job)
  [ "$(sha256sum "$D/job.py" | cut -d' ' -f1)" = "4764aef2ddb78e617007e0adb11a70436874738bef1d8757b34a67fb7f4e31ae" ] || exit 65
  [ "$(sha256sum "$D/inputs.json" | cut -d' ' -f1)" = "3d4fb5dd755c70ad6805731188d64cc8356600e774954f8e4de850ac3d61cfc9" ] || exit 65
  exec /usr/bin/python3 -B "$D/job.py" ;;
 --engine)
  if [ "${FILLER_DRYRUN:-0}" = 1 ]; then result="${FILLER_DRYRUN_RESULT_PATH:?}"; else result="$D/RESULT.json"; fi
  export FILLER_RL="$D/region-lock"
  exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --role build --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "/usr/bin/test -s $result" --cmd "/bin/bash $D/launch.sh --job" ;;
 '') exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env "FILLER_DRYRUN=${FILLER_DRYRUN:-0}" "FILLER_DRYRUN_DIR=${FILLER_DRYRUN_DIR:-}" "FILLER_DRYRUN_RESULT_PATH=${FILLER_DRYRUN_RESULT_PATH:-}" "FILLER_STATE_DIR=${FILLER_STATE_DIR:-}" "FILLER_FLAGS_DIR=${FILLER_FLAGS_DIR:-}" "FILLER_GRANTS_DIR=${FILLER_GRANTS_DIR:-}" "FILLER_SMOKE=${FILLER_SMOKE:-0}" "WS58_REGIONS=${WS58_REGIONS:-}" /bin/bash "$D/launch.sh" --engine ;;
 *) exit 64;;
esac
