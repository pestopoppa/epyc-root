#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-backlog-20261031-0255/r3
cd "$D"
SOURCE_SHA=cdaa8d5ac04b030f393ee89e8d1de3e7d09a81312e60d2a08e43b73f791312c6
printf '%s  %s\n' "$SOURCE_SHA" "$D/SOURCES.sha256" | sha256sum --status -c
sha256sum --strict --quiet -c "$D/SOURCES.sha256"
host=(sudo -n --preserve-env=FILLER_CPUS,FILLER_DEADLINE,FILLER_STOPFILE,FILLER_ID,FILLER_END /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992)
case ${1:-} in
 --smoke)
  tag=${2:?}; [[ $tag =~ ^[a-z0-9-]+$ ]]; mkdir -p "$D/$tag"
  export FILLER_CPUS=126,127 FILLER_DEADLINE=$(( $(date +%s)+250 )) FILLER_STOPFILE="$D/$tag/STOP"
  exec flock -n /mnt/raid0/llm/tmp/compute-flags/prep-locks/30-31.lock taskset -c "$FILLER_CPUS" "${host[@]}" /usr/bin/python3 -B /mnt/raid0/llm/tmp/codex3-kpf183-chat-impl-20261031/r11_supervisor.py 255 -- /bin/bash "$D/job_entry.sh" smoke "$tag";;
 --job)
  exec /bin/bash "$D/job_entry.sh" full full;;
 --host-run)
  claim=${2:?CPU grant required}
  (cd /mnt/micron/codex3-lanes/orchestrator; sha256sum --strict --quiet -c "$D/LOCK-MODULES.sha256")
  exec /usr/bin/env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/home/daniele LANG=C LC_ALL=C PYTHONDONTWRITEBYTECODE=1 RUS3_DIAGNOSTIC=1 FILLER_RL="$D/region-lock.sh" FILLER_FLAGS_DIR=/mnt/raid0/llm/tmp/compute-flags FILLER_GRANTS_DIR=/mnt/raid0/llm/tmp/compute-flags/grants FILLERS_MD=/mnt/raid0/llm/tmp/compute-flags/FILLERS.md FILLER_STATE_DIR="$D/state" FILLER_POLL=45 /bin/bash /mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/engine/filler_run13.sh --id codex3-lb49-fu03-cli-r3-20261031 --class cpu --claim-cpus "$claim" --role build --min-window 1800 --stop "$D/STOP" --port 19633 --workdir "$D" --complete-cmd "/usr/bin/python3 -B $D/check_complete.py full" --cmd "taskset -c \${FILLER_CPUS} /bin/bash $D/launch.sh --job";;
 '')
  : "${WS58_REGIONS:?}"
  exec "${host[@]}" /bin/bash "$D/launch.sh" --host-run "$WS58_REGIONS";;
 *) exit 64;;
esac
