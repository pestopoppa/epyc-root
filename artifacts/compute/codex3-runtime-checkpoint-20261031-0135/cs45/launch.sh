#!/bin/bash
set -euo pipefail
P=/mnt/raid0/llm/tmp/codex3-next-cpu-prep-20261031-0110
D="$P/cs45"
printf '%s  %s\n' 6f3cca041f4e0a0e36e18eb3517f29ab8b914426501b371587d49de2657002cb "$D/SOURCES.sha256" | sha256sum --status -c
host=(sudo -n --preserve-env=FILLER_CPUS,OMP_NUM_THREADS,OPENBLAS_NUM_THREADS,PYTHONDONTWRITEBYTECODE /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992)
"${host[@]}" /bin/bash -c 'sha256sum --strict --quiet -c "$1"' _ "$D/SOURCES.sha256"
export RUS3_DIAGNOSTIC=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
case ${1:-} in
 --smoke|--cutoff) export FILLER_CPUS=126,127; exec flock -n /mnt/raid0/llm/tmp/compute-flags/prep-locks/30-31.lock taskset -c "$FILLER_CPUS" "${host[@]}" /usr/bin/python3 -B "$P/smoke-supervisor.py" 265 -- "$P/venv312/bin/python" "$D/job.py" smoke;;
 --job) exec "${host[@]}" "$P/venv312/bin/python" "$D/job.py" full;;
 '') export FILLER_STATE_DIR="$D/state"; exec /bin/bash "$P/engine/filler_run13.sh" --id codex3-cs45-tail-rescore-20261031 --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 900 --stop "$D/STOP" --workdir "$D" --cmd "taskset -c \$FILLER_CPUS /bin/bash $D/launch.sh --job" --complete-cmd "test -s $D/results/COMPLETE.json || test -s $D/results/TERMINAL-INCOMPLETE.json";;
 *) exit 64;;
esac
