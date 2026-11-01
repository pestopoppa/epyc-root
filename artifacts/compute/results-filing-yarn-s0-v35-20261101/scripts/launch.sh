#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/refactor-01a16fc3/yarn-s0-v35-window-20261031
ID=yarn-oolong-s0-host256-eligible28-v35-20261031
enter_host() {
 local vars=("PATH=/usr/bin:/bin" "OMP_NUM_THREADS=1" "OPENBLAS_NUM_THREADS=1" "MKL_NUM_THREADS=1" "PYTHONDONTWRITEBYTECODE=1")
 for name in WS58_REGIONS ${!FILLER_@}; do if [[ -v "$name" ]]; then vars+=("$name=${!name}"); fi; done
 /usr/bin/sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --clear-groups /usr/bin/env -i "${vars[@]}" /bin/bash -c '
set -euo pipefail
[[ $(id -u) == 1000 ]]
/usr/bin/sha256sum --check --status <<"PINS"
3014e1f6451d35079f31a6324265d07d2c8073b5bf97f307c365ac4c62e4e320  /mnt/micron/refactor-yarn-s0-v35-window-20261031/SOURCE-MANIFEST-v35.json
ab6305eae6b87b939f721c7fc4f6c5d9d8979bebefe361291440f69bf40d1cb1  /mnt/micron/refactor-yarn-s0-v35-window-20261031/launch.sh
PINS
exec /bin/bash /mnt/micron/refactor-yarn-s0-v35-window-20261031/launch.sh "$@"
' yarn-host "$@"
}
case "${1-}" in
 --smoke) [[ $# == 2 && ( $2 == normal || $2 == cutoff ) ]] || exit 64; enter_host "$@"; exit $?;;
 --job|--preflight) [[ $# == 1 ]] || exit 64; enter_host "$@"; exit $?;;
 '') ;;
 *) exit 64;;
esac
case "${WS58_REGIONS:?}" in 0-23|24-47|48-71) ;; *) exit 64;; esac
printf '%s [%s] launcher up pid=%s class=cpu regions=%s minwin=42000s\n' "$(date -u +%FT%TZ)" "$ID" "$$" "$WS58_REGIONS"
exec env -u PYTHONHOME -u PYTHONPATH -u FILLER_FLAGS_DIR -u FILLER_GRANTS_DIR -u FILLERS_MD -u FILLER_STUB_CMD -u FILLER_PREFLIGHT -u FILLER_RL PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 RUS3_DIAGNOSTIC=1 FILLER_STATE_DIR="$D/scheduler-state" /usr/bin/python3 -B -I "$D/outer_log.py" /bin/bash "$D/engine/filler_run13.sh" --id "$ID" --class cpu --claim-cpus "$WS58_REGIONS" --role build --min-window 42000 --stop "$D/STOP" --port 19434 --workdir "$D" --cmd "/bin/bash $D/launch.sh --job" --complete-cmd false
