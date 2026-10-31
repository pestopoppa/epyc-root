#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/hil15-s3-t1-repair-20261030/s2-r13-pid-20261031
M=/mnt/micron/refactor-hil15-s2-r13-pid-20261031
E=$D/engine
ID=codex-hil15-s2-r13-pid-20261031
PORT=19433
SOURCE_SHA=fb651765ff14ecf02607775467b31e779156d8d33c78fbbdd3fcd50771ffc396
export RUS3_DIAGNOSTIC=1

bounded_log() {
  /usr/bin/sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --clear-groups \
    /usr/bin/env PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -I "$M/bounded_logger.py"
}

enter_host() {
  local vars=("PATH=/usr/bin:/bin" "OMP_NUM_THREADS=1" "OPENBLAS_NUM_THREADS=1" "MKL_NUM_THREADS=1" "PYTHONDONTWRITEBYTECODE=1" "RUS3_DIAGNOSTIC=1" "HIL15_MANIFEST_SHA=$SOURCE_SHA" "HIL15_SOURCE_MANIFEST=$M/SOURCE.sha256" "HIL15_CAPSULE_ROOT=$M")
  for name in WS58_REGIONS ${!FILLER_@}; do
    if [[ -v "$name" ]]; then vars+=("$name=${!name}"); fi
  done
  /usr/bin/sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --clear-groups /usr/bin/env "${vars[@]}" /bin/bash -c '
set -euo pipefail
[[ $(id -u) == 1000 ]]
printf "host RUS3_DIAGNOSTIC=%s\n" "${RUS3_DIAGNOSTIC:-unset}" >&2
[[ ${RUS3_DIAGNOSTIC:-} == 1 ]]
/usr/bin/sha256sum --check --status <<"PINS"
fb651765ff14ecf02607775467b31e779156d8d33c78fbbdd3fcd50771ffc396  /mnt/micron/refactor-hil15-s2-r13-pid-20261031/SOURCE.sha256
PINS
if [[ "${1-}" == --smoke ]]; then
  [[ $# == 2 && ( $2 == normal || $2 == cutoff ) ]]
  smoke_root=$(/usr/bin/mktemp -d "$HIL15_CAPSULE_ROOT/real-unit-smoke-$2-XXXXXXXX")
  export HIL15_SMOKE_ROOT="$smoke_root" TMPDIR="$smoke_root"
  printf "smoke_root=%s\n" "$smoke_root" >&2
  exec /usr/bin/taskset -c 154,155 /usr/bin/python3 -B -I /mnt/micron/refactor-hil15-s2-r13-pid-20261031/boot.py "$@"
fi
exec /usr/bin/python3 -B -I /mnt/micron/refactor-hil15-s2-r13-pid-20261031/boot.py "$@"
' hil15-r11-host "$@"
}

case "${1-}" in
  --smoke)
    [[ $# == 2 && ( $2 == normal || $2 == cutoff ) ]] || exit 64
    enter_host --smoke "$2"
    exit $?
    ;;
  --preflight|--job|--check-complete)
    [[ $# == 1 ]] || exit 64
    enter_host "$1"
    exit $?
    ;;
  '') ;;
  *) exit 64 ;;
esac

case "${WS58_REGIONS:?keeper must bind selected quarter}" in
  0-23|24-47|48-71|72-95) ;;
  *) exit 64 ;;
esac
if [[ -n "${HIL15_PRIVATE_FLAGS_DIR:-}" ]]; then
  [[ "$HIL15_PRIVATE_FLAGS_DIR" == "$D"/fixture-* && ! -L "$HIL15_PRIVATE_FLAGS_DIR" ]] || exit 64
fi
mkdir -p "$D/scheduler-state"
printf '%s [%s] launcher up pid=%s class=cpu poll=45s grants=/mnt/raid0/llm/tmp/compute-flags/grants stop=%s minwin=1800s ports=%s\n' \
  "$(date -u +%FT%TZ)" "$ID" "$$" "$D/STOP" "$PORT"
exec > >(bounded_log) 2>&1
printf 'launcher RUS3_DIAGNOSTIC=%s\n' "$RUS3_DIAGNOSTIC"
sha256sum --check --status "$E/engine.sha256"
enter_host --preflight
exec env -u FILLER_GRANTS_DIR -u FILLERS_MD -u FILLER_STUB_CMD -u FILLER_PREFLIGHT -u FILLER_RL \
  FILLER_FLAGS_DIR="${HIL15_PRIVATE_FLAGS_DIR:-/mnt/raid0/llm/tmp/compute-flags}" FILLER_STATE_DIR="$D/scheduler-state" RUS3_DIAGNOSTIC=1 /bin/bash "$E/filler_run13.sh" \
  --id "$ID" --class cpu --claim-cpus "$WS58_REGIONS" --role build --min-window 1800 \
  --cmd "/bin/bash $D/launch.sh --job" --stop "$D/STOP" --port "$PORT" \
  --complete-cmd "taskset -c $WS58_REGIONS /bin/bash $D/launch.sh --check-complete" --workdir "$D"
