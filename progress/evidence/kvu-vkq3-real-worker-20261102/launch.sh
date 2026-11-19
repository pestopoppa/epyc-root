#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/vkq3-row/launcher
ID=handoff-kvu-vkq3-mtp-bound-20261102
cd "$D"
case ${1:-} in
 --job)
  [ "$(sha256sum SOURCE-SHA256SUMS | cut -d' ' -f1)" = "2ed990e1f624decc76d99573e759107d016c5e5ee60abe34d06a4d26a9b69f87" ] || exit 64
  sha256sum -c --quiet SOURCE-SHA256SUMS
  sha256sum -c --quiet RUNTIME-CODE.sha256
  [ "$(sha256sum /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh | cut -d' ' -f1)" = "57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33" ] || exit 64
  LD_LIBRARY_PATH=/mnt/raid0/llm/kernels/builds/cpu-20261004-9a3f1392a/bin /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh /mnt/raid0/llm/kernels/builds/cpu-20261004-9a3f1392a/bin/llama-server /mnt/raid0/llm/kernels/builds/cpu-20261004-9a3f1392a/bin > "$D/linkage-${FILLER_DRYRUN:-unknown}.txt"
  export VKQ3_INPUT_RECEIPT=/mnt/raid0/llm/tmp/kvu/vkq3-row/preflight-receipt.json
  export VKQ3_INPUT_RECEIPT_SHA256=e1c8fcf716b09dfdc45fe0cbb9457f11800e48937c49a830ad5daffd1356cabf
  export VKQ3_PREBUILT_PROMPT=/mnt/raid0/llm/tmp/kvu/vkq3-row/preflight-prompt.txt
  exec /usr/bin/python3 -B "$D/worker.py";;
 --engine)
  export FILLER_RL="$D/region-lock"
  case ${FILLER_DRYRUN:-missing} in
   1) complete="${FILLER_DRYRUN_RESULT_PATH:?}"; completion_mode=qualification ;;
   0) complete="$D/run/TERMINAL.json"; completion_mode=full ;;
   *) exit 64 ;;
  esac
  exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --role bench --min-window 9000 --stop "$D/STOP" --workdir "$D" --complete-cmd "/usr/bin/python3 -B $D/completion.py $completion_mode $complete" --cmd "/bin/bash $D/launch.sh --job";;
 '')
  exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env "FILLER_DRYRUN=${FILLER_DRYRUN:-0}" "FILLER_DRYRUN_DIR=${FILLER_DRYRUN_DIR:-}" "FILLER_DRYRUN_RESULT_PATH=${FILLER_DRYRUN_RESULT_PATH:-}" "FILLER_STATE_DIR=${FILLER_STATE_DIR:-}" "FILLER_FLAGS_DIR=${FILLER_FLAGS_DIR:-}" "FILLER_GRANTS_DIR=${FILLER_GRANTS_DIR:-}" "FILLER_POLL=${FILLER_POLL:-5}" "WS58_REGIONS=${WS58_REGIONS:-}" "FILLER_OWNER=${FILLER_OWNER:-handoff-kvu}" /bin/bash "$D/launch.sh" --engine;;
 *) exit 64;;
esac
