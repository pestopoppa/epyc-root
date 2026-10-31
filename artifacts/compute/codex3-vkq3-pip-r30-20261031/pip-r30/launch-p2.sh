#!/bin/bash
set -euo pipefail
D=$(dirname "$(readlink -f "$0")")
M=/mnt/micron/codex3-pip-pool2-r30-v2-20261031
export R25_LAUNCHER="$D/launch-p2.sh"
host_run() {
 vars=("PATH=/usr/bin:/bin" "OMP_NUM_THREADS=1" "OPENBLAS_NUM_THREADS=1" "PYTHONDONTWRITEBYTECODE=1" "HF_HUB_OFFLINE=1" "TRANSFORMERS_OFFLINE=1" "HF_DATASETS_OFFLINE=1" "R25_LAUNCHER=$R25_LAUNCHER" "R30_STOP_CONTROL=${R30_STOP_CONTROL:-0}" "R25_NORMAL_THREADS_SMOKE=${R25_NORMAL_THREADS_SMOKE:-0}")
 for var in WS58_REGIONS ${!FILLER_@}; do if [[ -v "$var" ]]; then vars+=("$var=${!var}"); fi; done
 /usr/bin/sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env "${vars[@]}" /bin/bash -c '
set -euo pipefail
M=/mnt/micron/codex3-pip-pool2-r30-v2-20261031
printf "%s  %s\n" 506ac72c24355d36a0e098ec19f52917698eb0a76cf4b50bbdd4bcfadc2dd70b "$M/source.sha256" | /usr/bin/sha256sum --check --status
/usr/bin/sha256sum --quiet -c "$M/source.sha256"
if [[ "${1:-}" == --supervised ]]; then
 shift
 if [[ "${R30_STOP_CONTROL:-0}" == 1 ]]; then C="$M/control-stop"; else C="$M/control-normal"; fi
 exec /usr/bin/python3.12 -B -S "$M/cpu_r11_split_supervisor.py" 260 -- /usr/bin/python3.12 -B -S "$C/pool.py" "$@"
fi
exec /usr/bin/python3.12 -B -S "$M/pool.py" "$@"
' pip30 "$@"
}
case "${1:-}" in
 --host-smoke) host_run --supervised --pool 2 --regions 24-47 --port 25690 --smoke; exit $?;;
 --check-complete) exec /usr/bin/sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/test -e "$M/DONE-2";;
 --job) : "${WS58_REGIONS:?}"; host_run --pool 2 --regions "$WS58_REGIONS" --port 25602; exit $?;;
 --smoke)
  stamp=$(date -u +%M%S); seconds=$((10#${stamp:0:2}*60+10#${stamp:2:2})); ((seconds<720 || seconds>=1110)) || exit 75
  export R25_NORMAL_THREADS_SMOKE=1 FILLER_ID=codex3-pip02-paddle-relocatable-r30-smoke FILLER_STOPFILE="$D/STOP-smoke-${R30_STOP_CONTROL:-0}" FILLER_THREADS=2 FILLER_CPUS=122,123
  mkdir "$D/control-once-${R30_STOP_CONTROL:-0}" || exit 78
  exec taskset -c "$FILLER_CPUS" /bin/bash "$D/launch-p2.sh" --host-smoke;;
 '') ;;
 *) exit 64;;
esac
case "${WS58_REGIONS:?}" in 0-23|24-47|48-71|72-95) ;; *) exit 64;; esac
mkdir -p "$D/scheduler-state"
exec env -i PATH=/usr/bin:/bin WS58_REGIONS="$WS58_REGIONS" RUS3_DIAGNOSTIC=1 FILLER_STATE_DIR="$D/scheduler-state" /bin/bash /mnt/raid0/llm/tmp/codex3-pip02-paddle-relocatable-r13-20261030/engine/filler_run13.sh --id codex3-pip02-paddle-relocatable-r30-pool2-20261031 --class cpu --role bench --claim-cpus "$WS58_REGIONS" --min-window 1320 --port 25602 --stop "$D/STOP-2" --workdir "$D" --cmd "taskset -c \${FILLER_CPUS} bash $D/launch-p2.sh --job" --complete-cmd "bash $D/launch-p2.sh --check-complete"
