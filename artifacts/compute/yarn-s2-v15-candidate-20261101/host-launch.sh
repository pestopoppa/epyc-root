#!/bin/bash
set -euo pipefail
# Deliberate hard stop until integration and native STOP/drain review.
printf "%s\n" "REFUSED: private host candidate is disabled" >&2
exit 78
[[ ${1:-} == --job && $# == 1 ]] || exit 64
vars=("PATH=/usr/bin:/bin" "OMP_NUM_THREADS=1" "PYTHONDONTWRITEBYTECODE=1")
for name in WS58_REGIONS ${!FILLER_@}; do
  if [[ -v "$name" ]]; then vars+=("$name=${!name}"); fi
done
exec /usr/bin/sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --clear-groups /usr/bin/env "${vars[@]}" /bin/bash -c '
set -euo pipefail
D=/mnt/raid0/llm/tmp/yarn-s2-v15-candidate-20261101/host-src
OLD=/mnt/raid0/llm/tmp/yarn-oolong-s2-host-v32-20261031/scheduler-state
ID=yarn-oolong-s2-host256-eligible26-v32-20261031
# Refuse if prior owner or prior job still has either original custody lock.
[[ -f "$OLD/$ID.launcher.lock" && ! -L "$OLD/$ID.launcher.lock" && -f "$OLD/$ID.runner.lock" && ! -L "$OLD/$ID.runner.lock" ]]
exec 6<"$OLD/$ID.launcher.lock" 7<"$OLD/$ID.runner.lock"
flock -n -x 6
flock -n -x 7
printf "%s  %s\n" 30bece771abc91a4eeebce670eb3cb81d00c4d3fd15aa092020c30f3baaf4289 "$D/SOURCE-MANIFEST-v15.json" | sha256sum --check --status
export YARN_BUNDLE_SHA=30bece771abc91a4eeebce670eb3cb81d00c4d3fd15aa092020c30f3baaf4289
exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B -I "$D/boot.py"
' yarn-host
