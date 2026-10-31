#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240
cd "$D"
[[ $(sha256sum SOURCES.sha256 | cut -d' ' -f1) == c4eab78384a9ce0511f16502cc08da68250b1e6d4221890c12de78571bba0639 ]]
sha256sum --quiet --strict -c SOURCES.sha256
host=(sudo -n --preserve-env=FILLER_CPUS,FILLER_DEADLINE,FILLER_STOPFILE,FILLER_ID,FILLER_END /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992)
case "${1:-}" in
 --smoke)
   tag=${2:?control tag required}; [[ $tag =~ ^[a-z0-9-]+$ ]]
   mkdir -p "$D/control-$tag"
   export FILLER_CPUS=124,125 FILLER_DEADLINE=$(( $(date +%s)+255 )) FILLER_STOPFILE="$D/control-$tag/STOP"
   exec flock -n /mnt/raid0/llm/tmp/compute-flags/prep-locks/28-29.lock taskset -c "$FILLER_CPUS" "${host[@]}" /usr/bin/python3 -B /mnt/raid0/llm/tmp/codex3-kpf183-chat-impl-20261031/r11_supervisor.py 260 -- /bin/bash "$D/job.sh" smoke "$tag";;
 --job)
   exec "${host[@]}" /bin/bash "$D/job.sh" full;;
 '')
   export RUS3_DIAGNOSTIC=1 FILLER_STATE_DIR="$D/state"
   exec /bin/bash /mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/engine/filler_run13.sh --id codex3-kpf181-cpu-r1-20261031 --class cpu --claim-cpus "${WS58_REGIONS:?}" --role build --min-window 3600 --stop "$D/STOP" --port 19627 --workdir "$D" --cmd "taskset -c \${FILLER_CPUS} /bin/bash $D/launch.sh --job";;
 *) exit 64;;
esac
