#!/bin/bash
set -euo pipefail
D=$(dirname "$(readlink -f "$0")"); ROOT=/mnt/raid0/llm/tmp/codex3-pip-head-r26-20261030; M=/mnt/micron/codex3-pip-head-r26-20261030
name=$(basename "$0"); [[ "$name" =~ ^launch-p([0-3])\.sh$ ]] || exit 64
n=${BASH_REMATCH[1]}; port=$((25400+n)); export R25_LAUNCHER="$D/$name"
host_run() {
 vars=("PATH=/usr/bin:/bin" "OMP_NUM_THREADS=1" "OPENBLAS_NUM_THREADS=1" "PYTHONDONTWRITEBYTECODE=1" "HF_HUB_OFFLINE=1" "TRANSFORMERS_OFFLINE=1" "HF_DATASETS_OFFLINE=1" "R25_LAUNCHER=$R25_LAUNCHER" "R25_NORMAL_THREADS_SMOKE=${R25_NORMAL_THREADS_SMOKE:-0}")
 for var in WS58_REGIONS ${!FILLER_@}; do if [[ -v "$var" ]]; then vars+=("$var=${!var}"); fi; done
 /usr/bin/sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env "${vars[@]}" /bin/bash -c '
set -euo pipefail
printf "%s  %s\n" 1b71bee9b7cd01a7a01ddf9a3b5f8a6bce2091ce1d1327a5d189c5597c8cd465 /mnt/micron/codex3-pip-head-r26-20261030/source.sha256 | /usr/bin/sha256sum --check --status
/usr/bin/sha256sum --quiet -c /mnt/micron/codex3-pip-head-r26-20261030/source.sha256
printf "%s  %s\n" 71eee5884d5c5bc92f195ebfad7291eb3deb5adb462d0f98bd6b1604e4161828 /mnt/raid0/llm/tmp/codex3-filing-pip-dtap-c6-20261031-0230/repair/head/pool.py | /usr/bin/sha256sum --check --status
if [[ "${1:-}" == --supervised ]]; then
 printf "%s  %s\n" 9a4a8bb3512a231bdba08647df00eb56ab2b00eac14e2fdb7c63a7f30d75498c /mnt/raid0/llm/tmp/codex3-filing-pip-dtap-c6-20261031-0230/repair/head/control-source-q3/pool-control.py | /usr/bin/sha256sum --check --status
 shift
 exec /usr/bin/python3.12 -B -S /mnt/micron/codex3-pip-head-r26-20261030/cpu_r11_split_supervisor.py 260 -- /usr/bin/python3.12 -B -S /mnt/raid0/llm/tmp/codex3-filing-pip-dtap-c6-20261031-0230/repair/head/control-source-q3/pool-control.py "$@"
fi
exec /usr/bin/python3.12 -B -S /mnt/raid0/llm/tmp/codex3-filing-pip-dtap-c6-20261031-0230/repair/head/pool.py "$@"
' pip21 "$@"
}
case "${1:-}" in
 --host-smoke) host_run --supervised --pool "$n" --regions 72-95 --port 25490 --smoke; exit $?;;
 --check-complete) exec /usr/bin/sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/test -e "$M/HEAD-DONE";;
 --job) : "${WS58_REGIONS:?}"; host_run --pool "$n" --regions "$WS58_REGIONS" --port "$port"; exit $?;;
 --smoke)
  stamp=$(date -u +%M%S); seconds=$((10#${stamp:0:2}*60+10#${stamp:2:2})); ((seconds<720 || seconds>=1110)) || exit 75
  export R25_NORMAL_THREADS_SMOKE=1 FILLER_ID=codex3-pip02-paddle-relocatable-r26-smoke FILLER_STOPFILE="$D/STOP-smoke" FILLER_THREADS=2 FILLER_CPUS=168,169
  mkdir "$D/control-once-r28cc" || exit 78
  exec taskset -c "$FILLER_CPUS" /bin/bash "$D/$name" --host-smoke;;
 '') ;;
 *) exit 64;;
esac
case "${WS58_REGIONS:?}" in 0-23|24-47|48-71|72-95) ;; *) exit 64;; esac
mkdir -p "$D/scheduler-state"
export RUS3_DIAGNOSTIC=1
exec env -u FILLER_FLAGS_DIR -u FILLER_GRANTS_DIR -u FILLERS_MD -u FILLER_STUB_CMD -u FILLER_PREFLIGHT -u FILLER_RL FILLER_STATE_DIR="$D/scheduler-state" /bin/bash /mnt/raid0/llm/tmp/codex3-pip02-paddle-relocatable-r13-20261030/engine/filler_run13.sh --id "codex3-pip02-paddle-relocatable-r28-head-20261031" --class cpu --role bench --claim-cpus "$WS58_REGIONS" --min-window 1320 --port "$port" --stop "$D/STOP-$n" --workdir "$D" --cmd "taskset -c \${FILLER_CPUS} bash $D/$name --job" --complete-cmd "bash $D/$name --check-complete"
