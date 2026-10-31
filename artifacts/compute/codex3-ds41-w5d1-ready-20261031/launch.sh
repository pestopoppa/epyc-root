#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-wholehost-20261031-0310
cd "$D"
[[ $(sha256sum SOURCES.sha256 | cut -d' ' -f1) == 819c5137cbe096ad46dbf31a4b235849c70c564928c500e665a3173d87555fcf ]]
sha256sum --quiet --strict -c SOURCES.sha256
host=(sudo -n --preserve-env=FILLER_CPUS,FILLER_DEADLINE,FILLER_STOPFILE,FILLER_END,FILLER_ID /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992)
case "${1:-}" in
 --smoke)
  tag=${2:?}; [[ $tag =~ ^[a-z0-9-]+$ ]]; mkdir -p "$D/control-$tag"
  export FILLER_CPUS=122,123 FILLER_DEADLINE=$(( $(date +%s) + 240 )) FILLER_STOPFILE="$D/control-$tag/STOP"
  exec flock -n /mnt/raid0/llm/tmp/compute-flags/prep-locks/26-27.lock taskset -c "$FILLER_CPUS" "${host[@]}" /usr/bin/python3 -B /mnt/raid0/llm/tmp/codex3-kpf183-chat-impl-20261031/r11_supervisor.py 250 -- /usr/bin/python3 -B "$D/job.py" control "$tag";;
 --job)
  exec "${host[@]}" /usr/bin/python3 -B "$D/job.py" full;;
 '')
  export FILLER_STATE_DIR="$D/state"
  exec env -i PATH=/usr/bin:/bin HOME=/home/node RUS3_DIAGNOSTIC=1 FILLER_STATE_DIR="$FILLER_STATE_DIR" /bin/bash /mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/engine/filler_run13.sh --id codex3-ds41-w5d1-r1-20261031 --class cpu --gpu-quiet exclusive --claim-cpus 0-95 --role build --min-window 13500 --stop "$D/STOP" --complete-cmd "/usr/bin/python3 -B $D/check_complete.py" --workdir "$D" --cmd "taskset -c \${FILLER_CPUS} /bin/bash $D/launch.sh --job";;
 *) exit 64;;
esac
