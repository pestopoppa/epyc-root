#!/bin/bash
set -euo pipefail
export RUS3_DIAGNOSTIC=1
D=/mnt/raid0/llm/tmp/codex3-kpf183-chat-full-20261031
cd "$D"
[[ $(sha256sum SOURCES.sha256 | cut -d' ' -f1) == 15d55f7e71d17a705a7a20dfda174034e83e9f10bfd3570ff797daee494c3e0f ]]
sha256sum --strict --quiet -c SOURCES.sha256
host=(sudo -n --preserve-env=FILLER_ID,FILLER_CPUS,FILLER_DEADLINE,FILLER_STOPFILE /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992)
case ${1:-} in
 --smoke) export FILLER_CPUS=126,127 FILLER_DEADLINE=$(( $(date +%s) + 255 )) FILLER_STOPFILE="$D/STOP"; exec flock -n /mnt/raid0/llm/tmp/compute-flags/prep-locks/30-31.lock taskset -c "$FILLER_CPUS" "${host[@]}" /usr/bin/python3 -B /mnt/raid0/llm/tmp/codex3-kpf183-chat-impl-20261031/r11_supervisor.py 260 -- /usr/bin/python3 -B "$D/job.py" smoke;;
 --job) exec "${host[@]}" /usr/bin/python3 -B "$D/job.py" full;;
 '') export FILLER_STATE_DIR="$D/state"; exec /bin/bash /mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/engine/filler_run13.sh --id codex3-kpf183-chat-attribution-full-r1-20261031 --class cpu --claim-cpus "${WS58_REGIONS:?}" --role build --min-window 1800 --stop "$D/STOP" --port 19584 --workdir "$D" --cmd "taskset -c \${FILLER_CPUS} /bin/bash $D/launch.sh --job" --complete-cmd "test -s $D/run/RESULT.json";;
 *) exit 64;;
esac
