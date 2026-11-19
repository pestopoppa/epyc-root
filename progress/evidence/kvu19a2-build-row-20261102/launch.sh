#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu19a2-build-row-20261102
case ${1:-} in
 --job)
  [ "$(sha256sum "$D/source_guard.py" | cut -d' ' -f1)" = "5895f1e2fcc71a1a142d7e3e77d4c03012c9186e3043e3c6694d76752d68c823" ] || exit 65
  [ "$(sha256sum "$D/sealed-source-receipt.json" | cut -d' ' -f1)" = "8700981959dc11332792c064647e3227f20de12b65603f0fed35446426afc141" ] || exit 65
  [ "$(sha256sum "$D/job.py" | cut -d' ' -f1)" = "c41826f3bed3482b416532886bc723bb7b9f31a5ed161901f86a997c376bb8ec" ] || exit 65
  [ "$(sha256sum "$D/toolchain.sha256" | cut -d' ' -f1)" = "829aac96abac22b47a2cc29da14d5fc6351121d8cb665bb637d92d9a98a0dbc6" ] || exit 65
  [ "$(sha256sum "$D/source-pair.json" | cut -d' ' -f1)" = "b7a97f0f8f61f8a3fbda3d319f084b044a1d8c955003a4da497b34dfbdaa548c" ] || exit 65
  exec /usr/bin/python3 -B "$D/job.py" ;;
 --engine)
  [ "$(sha256sum "$D/region-lock" | cut -d' ' -f1)" = "c8ee8991be3eb6d4ed0e16ced319f7cb98d4bfcefcb44937e9d91b790c742bbc" ] || exit 65
  [ "$(sha256sum "$D/REGION-LOCK-INPUTS.sha256" | cut -d' ' -f1)" = "fac2f7b1fc26de2e0941f7081beb99b171a91148a49b9e290be943d388613e3f" ] || exit 65
  [ "$(sha256sum "$D/REGION-LOCK-PYTHON-ALLOW.txt" | cut -d' ' -f1)" = "f169fc8f65912c4995fa1a011fe9a4e596f664575e2c76fcf65d635d51cdd043" ] || exit 65
  if [ "${FILLER_DRYRUN:-0}" = 1 ]; then result="${FILLER_DRYRUN_RESULT_PATH:?}"; else result="$D/output/RESULT.json"; fi
  export FILLER_RL="$D/region-lock"
  exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id handoff-kvu-kvu19a2-build-20261102 --class cpu --role build --min-window 3600 --stop "$D/output/STOP" --workdir "$D/output" --complete-cmd "/usr/bin/test -s $result" --cmd "/bin/bash $D/launch.sh --job" ;;
 '') exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env "FILLER_DRYRUN=${FILLER_DRYRUN:-0}" "FILLER_DRYRUN_DIR=${FILLER_DRYRUN_DIR:-}" "FILLER_DRYRUN_RESULT_PATH=${FILLER_DRYRUN_RESULT_PATH:-}" "FILLER_STATE_DIR=${FILLER_STATE_DIR:-}" "FILLER_FLAGS_DIR=${FILLER_FLAGS_DIR:-}" "FILLER_GRANTS_DIR=${FILLER_GRANTS_DIR:-}" "WS58_REGIONS=${WS58_REGIONS:-}" /bin/bash "$D/launch.sh" --engine ;;
 *) exit 64;;
esac
