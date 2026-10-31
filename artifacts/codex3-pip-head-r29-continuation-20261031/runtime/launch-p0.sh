#!/bin/bash
set -euo pipefail
D=$(dirname "$(readlink -f "$0")"); ROOT=/mnt/raid0/llm/tmp/codex3-pip-head-r26-20261030; M=/mnt/micron/codex3-pip-head-r26-20261030
name=$(basename "$0"); [[ "$name" =~ ^launch-p([0-3])\.sh$ ]] || exit 64
n=${BASH_REMATCH[1]}; port=$((25400+n)); export R25_LAUNCHER="$D/$name"
host_run() {
 vars=("PATH=/usr/bin:/bin" "OMP_NUM_THREADS=1" "OPENBLAS_NUM_THREADS=1" "PYTHONDONTWRITEBYTECODE=1" "HF_HUB_OFFLINE=1" "TRANSFORMERS_OFFLINE=1" "HF_DATASETS_OFFLINE=1" "R25_LAUNCHER=$R25_LAUNCHER" "R29_STOP_CONTROL=${R29_STOP_CONTROL:-0}" "R25_NORMAL_THREADS_SMOKE=${R25_NORMAL_THREADS_SMOKE:-0}")
 for var in WS58_REGIONS ${!FILLER_@}; do if [[ -v "$var" ]]; then vars+=("$var=${!var}"); fi; done
 /usr/bin/sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env "${vars[@]}" /bin/bash -c '
set -euo pipefail
printf "%s  %s\n" 1b71bee9b7cd01a7a01ddf9a3b5f8a6bce2091ce1d1327a5d189c5597c8cd465 /mnt/micron/codex3-pip-head-r26-20261030/source.sha256 | /usr/bin/sha256sum --check --status
/usr/bin/sha256sum --quiet -c /mnt/micron/codex3-pip-head-r26-20261030/source.sha256
printf "%s  %s\n" 63f15f638c88e3de96c584f621a71fb3ac778855b58cd06bef27bb64eaf2cec3 /mnt/raid0/llm/tmp/codex3-pip-head-r29-repair-20261031/source-pins.json | /usr/bin/sha256sum --check --status
printf "%s  %s\n" 27adcfd36240e692a30392ba0d613fff7ccacb7a0256ed8913dc31f3c323c00f /mnt/raid0/llm/tmp/codex3-pip-head-r29-repair-20261031/source.sha256 | /usr/bin/sha256sum --check --status
/usr/bin/sha256sum --quiet -c /mnt/raid0/llm/tmp/codex3-pip-head-r29-repair-20261031/source.sha256
if [[ "${1:-}" == --supervised ]]; then
 shift
 if [[ "${R29_STOP_CONTROL:-0}" == 1 ]]; then
  exec /usr/bin/python3.12 -B -S /mnt/micron/codex3-pip-head-r26-20261030/cpu_r11_split_supervisor.py 260 -- /usr/bin/python3.12 -B -S /mnt/raid0/llm/tmp/codex3-pip-head-r29-repair-20261031/control-stop/pool.py "$@"
 fi
 exec /usr/bin/python3.12 -B -S /mnt/micron/codex3-pip-head-r26-20261030/cpu_r11_split_supervisor.py 260 -- /usr/bin/python3.12 -B -S /mnt/raid0/llm/tmp/codex3-pip-head-r29-repair-20261031/control/pool.py "$@"
fi
exec /usr/bin/python3.12 -B -S /mnt/raid0/llm/tmp/codex3-pip-head-r29-repair-20261031/pool.py "$@"
' pip21 "$@"
}
case "${1:-}" in
 --host-smoke) host_run --supervised --pool "$n" --regions 72-95 --port 25490 --smoke; exit $?;;
 --check-complete) exec /usr/bin/sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/test -e "$M/HEAD-DONE";;
 --job) : "${WS58_REGIONS:?}"; host_run --pool "$n" --regions "$WS58_REGIONS" --port "$port"; exit $?;;
 --smoke)
  stamp=$(date -u +%M%S); seconds=$((10#${stamp:0:2}*60+10#${stamp:2:2})); ((seconds<720 || seconds>=1110)) || exit 75
  export R25_NORMAL_THREADS_SMOKE=1 FILLER_ID=codex3-pip02-paddle-relocatable-r26-smoke FILLER_STOPFILE="$D/STOP-smoke-${R29_STOP_CONTROL:-0}" FILLER_THREADS=2 FILLER_CPUS=168,169
  mkdir "$D/control-once-r29-${R29_STOP_CONTROL:-0}" || exit 78
  exec taskset -c "$FILLER_CPUS" /bin/bash "$D/$name" --host-smoke;;
 '') ;;
 *) exit 64;;
esac
case "${WS58_REGIONS:?}" in 0-23|24-47|48-71|72-95) ;; *) exit 64;; esac
mkdir -p "$D/scheduler-state"
export RUS3_DIAGNOSTIC=1
exec env -i PATH=/usr/bin:/bin WS58_REGIONS="$WS58_REGIONS" RUS3_DIAGNOSTIC=1 FILLER_STATE_DIR="$D/scheduler-state" /bin/bash /mnt/raid0/llm/tmp/codex3-pip02-paddle-relocatable-r13-20261030/engine/filler_run13.sh --id "codex3-pip02-paddle-relocatable-r29-head-20261031" --class cpu --role bench --claim-cpus "$WS58_REGIONS" --min-window 1320 --port "$port" --stop "$D/STOP-$n" --workdir "$D" --cmd "taskset -c \${FILLER_CPUS} bash $D/$name --job" --complete-cmd "bash $D/$name --check-complete"
