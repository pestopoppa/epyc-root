#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-backlog-20261031-0255/r2
cd "$D"
[[ $(sha256sum SOURCES.sha256 | cut -d' ' -f1) == f8cb5ecc599f9af8970b9cec7396aa9efeff8e9fdae0fe028083fc2573f4526e ]]
sha256sum --strict --quiet -c SOURCES.sha256
host=(sudo -n --preserve-env=FILLER_CPUS,FILLER_DEADLINE,FILLER_STOPFILE,FILLER_ID,FILLER_END /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992)
case ${1:-} in
 --smoke) tag=${2:?}; [[ $tag =~ ^[a-z0-9-]+$ ]]; mkdir -p "$D/$tag"; export FILLER_CPUS=122,123 FILLER_DEADLINE=$(( $(date +%s)+250 )) FILLER_STOPFILE="$D/$tag/STOP"; exec flock -n /mnt/raid0/llm/tmp/compute-flags/prep-locks/26-27.lock taskset -c "$FILLER_CPUS" "${host[@]}" /usr/bin/python3 -B /mnt/raid0/llm/tmp/codex3-kpf183-chat-impl-20261031/r11_supervisor.py 255 -- /bin/bash "$D/job_entry.sh" smoke "$tag";;
 --job) exec "${host[@]}" /bin/bash "$D/job_entry.sh" full full;;
 '') export RUS3_DIAGNOSTIC=1 FILLER_STATE_DIR="$D/state"; exec /bin/bash /mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/engine/filler_run13.sh --id codex3-lb49-fu03-cli-r1-20261031 --class cpu --claim-cpus "${WS58_REGIONS:?}" --role build --min-window 1800 --stop "$D/STOP" --port 19633 --workdir "$D" --complete-cmd "/usr/bin/python3 -B $D/check_complete.py full" --cmd "taskset -c \${FILLER_CPUS} /bin/bash $D/launch.sh --job";;
 *) exit 64;;
esac
