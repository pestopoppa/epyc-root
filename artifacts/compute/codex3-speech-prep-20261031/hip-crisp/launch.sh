#!/bin/bash
set -euo pipefail
export RUS3_DIAGNOSTIC=1
D=/mnt/raid0/llm/tmp/codex3-cs8-stt4-crisp-20261031
cd "$D"
printf '%s  %s\n' bb9e0e91b3e0aef759622f3d6f4d4ba567cde10390c070c5c75759e02a7e45ea SOURCES.sha256 | sha256sum --strict --quiet -c -
host=(sudo -n --preserve-env=FILLER_ID,FILLER_CPUS,FILLER_DEADLINE,BUILD_MODE /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992)
"${host[@]}" /usr/bin/sha256sum --strict --quiet -c "$D/SOURCES.sha256"
case ${1:-} in
 --smoke)
  export FILLER_CPUS=122,123 BUILD_MODE=smoke FILLER_DEADLINE=$(( $(date +%s) + 260 ))
  exec flock -n /mnt/raid0/llm/tmp/compute-flags/prep-locks/26-27.lock flock -n /mnt/raid0/llm/tmp/compute-flags/prep-locks/122-123.lock taskset -c "$FILLER_CPUS" "${host[@]}" /usr/bin/python3 -B "$D/prep_supervisor.py" 265 -- /bin/bash "$D/job.sh";;
 --job) export BUILD_MODE=full; exec "${host[@]}" /bin/bash "$D/job.sh";;
 '')
  export FILLER_STATE_DIR="$D/state"
  exec /bin/bash /mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/engine/filler_run13.sh --id codex3-cs8-stt4-crisp-hip-build-20261031 --class cpu --claim-cpus "${WS58_REGIONS:?}" --role build --min-window 3600 --stop "$D/STOP" --workdir "$D" --cmd "taskset -c \${FILLER_CPUS} /bin/bash $D/launch.sh --job" --complete-cmd "test -s $D/BUILD-SUCCESS";;
 *) exit 64;;
esac
