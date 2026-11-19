#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor/packet
ID=handoff-vidya-kvu19a2-wire-20261117-r2
RESULT=$D/run-output/result.json
case ${1:-} in
 --job)
  /usr/bin/python3 "$D/preflight.py"
  export KVU19A2_ROW_ID=${FILLER_ID:?}
  export KVU19A2_GRANT_RECEIPT=${FILLER_GRANTS_DIR:?}/$KVU19A2_ROW_ID.grant
  export KVU19A2_GRANT_SHA256=$(sha256sum "$KVU19A2_GRANT_RECEIPT" | cut -d' ' -f1)
  export KVU19A2_REPEAT_OUT=$D/run-output
  export EPYC_VIDYA_ROOT=/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-root-code/scripts/vidya
  export KVU19A2_EXE=/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor/build/harness/fa_harness
  export KVU19A2_SOURCE_ARCHIVE=/mnt/raid0/llm/tmp/kvu/kvu19a2-source-pair-20261102/source.tar
  export KVU19A2_BUILD_RECEIPT_SHA256 KVU19A2_EXE_SHA256 KVU19A2_HARNESS_RECEIPT_SHA256
  eval "$(/usr/bin/python3 "$D/pins_env.py")"
  if [ "${FILLER_DRYRUN:-0}" = 1 ]; then
    cpus=$(/usr/bin/python3 -c 'import os; a=sorted(os.sched_getaffinity(0)); assert len(a)>=4; print(",".join(map(str,a[:4])))')
    exec /usr/bin/taskset -c "$cpus" /usr/bin/python3 "$D/kvu19a2_repeat_rootbuild.py"
  fi
  exec /usr/bin/python3 "$D/kvu19a2_repeat_rootbuild.py" ;;
 '')
  cpus=184-191
  if [ "${FILLER_DRYRUN:-0}" = 1 ]; then
    printf -v RESULT '%q' "${FILLER_DRYRUN_RESULT_PATH:?}"
    cpus=${WS58_REGIONS:?}
  fi
  exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class gpu --role bench --gpu-quiet exclusive --claim-cpus "$cpus" --gpu-threads "$cpus" --min-window 2100 --stop "$D/STOP" --workdir "$D" --complete-cmd "/usr/bin/test -s $RESULT" --cmd "/bin/bash $D/row-launch.sh --job" ;;
 *) exit 64;;
esac
