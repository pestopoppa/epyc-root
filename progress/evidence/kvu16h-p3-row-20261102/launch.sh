#!/bin/bash
set -euo pipefail
umask 077
D=/mnt/raid0/llm/tmp/kvu/p3-row-20261102
ID=handoff-kvu16h-p3-lifecycle-20261102
case ${1:-} in
 --job)
  read -r runtime_pin _ < <(sha256sum "$D/runtime.sha256")
  read -r source_pin _ < <(sha256sum "$D/source.sha256")
  [ "$runtime_pin" = 3cb7242f993ab0347503f28e9bb28465bc3ea84019fd74f6d01c036f3ea28811 ] || exit 65
  [ "$source_pin" = 9f4e62f0870ad911f4e89f36e7b331c1d291b185c1aec9917133e301c3f88848 ] || exit 65
  sha256sum -c --quiet "$D/runtime.sha256"
  sha256sum -c --quiet "$D/source.sha256"
  /usr/bin/python3 -B "$D/identity.py" "$D/model-receipt.json" 42d05e6400e73d4618a84ec739bee0d00d62f3d4509f01b7534e38efbc74b078
  export LD_LIBRARY_PATH=/mnt/raid0/llm/kernels/production/gpu:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib
  /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh /mnt/raid0/llm/kernels/production/gpu/llama-server /mnt/raid0/llm/kernels/production/gpu > "$D/linkage-${FILLER_DRYRUN}.txt"
  exec /usr/bin/python3 -B "$D/job.py" ;;
 --engine)
  if [ "${FILLER_DRYRUN:-0}" = 1 ]; then complete="${FILLER_DRYRUN_RESULT_PATH:?}"; else complete="$D/result.json"; fi
  export FILLER_RL=$D/region-lock
  exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id handoff-kvu16h-p3-lifecycle-20261102 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 184-191 --gpu-threads 184-191 --min-window 600 --stop "$D/STOP" --port 18198 --workdir "$D" --complete-cmd "/usr/bin/test -s $complete" --cmd "env PATH=/usr/bin:/bin LANG=C.UTF-8 FILLER_DRYRUN=\"\$FILLER_DRYRUN\" FILLER_DRYRUN_RESULT_PATH=\"\${FILLER_DRYRUN_RESULT_PATH:-}\" FILLER_NEEDGPU=\"\$FILLER_NEEDGPU\" FILLER_STOPFILE=\"\$FILLER_STOPFILE\" FILLER_DEADLINE=\"\$FILLER_DEADLINE\" FILLER_PIDFILE=\"\$FILLER_PIDFILE\" FILLER_CPUS=\"\$FILLER_CPUS\" /bin/bash $D/launch.sh --job" ;;
 '')
  exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env "FILLER_DRYRUN=${FILLER_DRYRUN:-0}" "FILLER_DRYRUN_DIR=${FILLER_DRYRUN_DIR:-}" "FILLER_DRYRUN_RESULT_PATH=${FILLER_DRYRUN_RESULT_PATH:-}" "FILLER_STATE_DIR=${FILLER_STATE_DIR:-}" "FILLER_FLAGS_DIR=${FILLER_FLAGS_DIR:-}" "FILLER_GRANTS_DIR=${FILLER_GRANTS_DIR:-/mnt/raid0/llm/tmp/compute-flags/grants}" "WS58_REGIONS=${WS58_REGIONS:-}" /bin/bash "$D/launch.sh" --engine ;;
 *) exit 64;;
esac
