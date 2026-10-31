#!/bin/bash
set -euo pipefail
export RUS3_DIAGNOSTIC=1
D=/mnt/raid0/llm/tmp/codex3-next-wholehost-prep-20261031/packet
cd "$D"
[[ $(sha256sum SOURCES.sha256 | cut -d' ' -f1) == 16ffd3b28bf8f0f6480c59daaf6c2dbd5b97684bad1867b09758a2489e7cf44d ]]
sha256sum --quiet --strict -c SOURCES.sha256
[[ $(sha256sum /mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/jobs/cpu/ELF.sha256 | cut -d' ' -f1) == 5d984815217de93ed31c998554f0c62d7790f9f0a76600a5a102effeeca63d80 ]]
sha256sum --quiet --strict -c /mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/jobs/cpu/ELF.sha256
host=(sudo -n --preserve-env=FILLER_ID,FILLER_CPUS,FILLER_DEADLINE,FILLER_STOPFILE,RTG57_CONTROL,RTG57_STOP_CONTROL,RUS3_DIAGNOSTIC /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992)
case ${1:-} in
 --smoke|--stop-smoke)
  export RTG57_CONTROL=1 FILLER_CPUS=124,125 FILLER_DEADLINE=$(( $(date +%s) + 255 )) FILLER_STOPFILE="$D/STOP"
  if [[ $1 == --stop-smoke ]]; then export RTG57_STOP_CONTROL=1; else unset RTG57_STOP_CONTROL || :; fi
  exec taskset -c "$FILLER_CPUS" "${host[@]}" /usr/bin/python3 -B "$D/r11_supervisor.py" 260 -- /usr/bin/python3 -B "$D/job.py";;
 --job) unset RTG57_CONTROL RTG57_STOP_CONTROL || :; exec "${host[@]}" /usr/bin/python3 -B "$D/job.py";;
 '') CPU_REGIONS=$(printf '%s' "${WS58_REGIONS:?}" | tr ',' '\n' | awk '$0 != "mi210_0"' | paste -sd, -); [[ $CPU_REGIONS == 0-95 ]] || exit 64; export FILLER_STATE_DIR="$D/state"; exec /bin/bash "$D/engine/filler_run13.sh" --id codex3-kvu-lb1d-t96-quiet-r1-20261031 --class cpu+gpu --claim-cpus "$CPU_REGIONS" --role bench --gpu-quiet exclusive --min-window 5100 --stop "$D/STOP" --workdir "$D" --cmd "taskset -c \${FILLER_CPUS} /bin/bash $D/launch.sh --job" --complete-cmd "test -s $D/COMPLETE";;
 *) exit 64;;
esac
