#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-cpu-prep-20261031-0110
printf '%s  %s\n' ee8cb5be891118879c3a7d3e6e18f35d334b0374bfbe7422ab646ea30000415e "$D/SOURCES.sha256" | sha256sum --status -c
host=(sudo -n --preserve-env=FILLER_CPUS,G1_WORKERS,OMP_NUM_THREADS,OPENBLAS_NUM_THREADS /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992)
"${host[@]}" /bin/bash -c 'cd "$1"; sha256sum --strict --quiet -c SOURCES.sha256' _ "$D"
export RUS3_DIAGNOSTIC=1
case ${1:-} in
 --smoke|--cutoff) export FILLER_CPUS=126,127; mode=${1#--}; exec flock -n /mnt/raid0/llm/tmp/compute-flags/prep-locks/30-31.lock taskset -c "$FILLER_CPUS" "${host[@]}" /usr/bin/python3 -B "$D/smoke-supervisor.py" 265 -- /bin/bash "$D/job.sh" "$mode";;
 --job) exec "${host[@]}" /bin/bash "$D/job.sh" full;;
 '') export FILLER_STATE_DIR="$D/state"; exec /bin/bash "$D/engine/filler_run13.sh" --id codex3-cs8-g1b-cascade-20261031 --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 900 --stop "$D/STOP" --workdir "$D" --cmd "taskset -c \$FILLER_CPUS /bin/bash $D/launch.sh --job" --complete-cmd "test -s $D/results/COMPLETE.json || test -s $D/results/TERMINAL-INCOMPLETE.json";;
 *) exit 64;;
esac
