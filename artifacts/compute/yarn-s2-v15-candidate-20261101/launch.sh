#!/bin/bash
set -euo pipefail
# Deliberate hard stop: source review and native STOP/drain are not complete.
printf "%s\n" "REFUSED: private candidate requires integration review and keeper qualification" >&2
exit 78
D=/mnt/raid0/llm/tmp/yarn-s2-v15-candidate-20261101
ID=yarn-oolong-s2-v15-oneitem-20261101
ENGINE=$D/engine/filler_run15.sh
sha256sum --check --status <<'PINS'
df9c52dedaf93031b3f6d8529ea19ccf8ea9dd6eac41f6cc9274ae2b728dc789  /mnt/raid0/llm/tmp/yarn-s2-v15-candidate-20261101/host-launch.sh
257a64709a409a6cdab48d9b3d1a605b7165f3be5afbf1954e9efd51cf539bbb  /mnt/raid0/llm/tmp/yarn-s2-v15-candidate-20261101/engine/filler_run15.sh
241e522f4a7d7208e7485834c90d77676434a9bc88fd253575e034ad2934237c  /mnt/raid0/llm/tmp/yarn-s2-v15-candidate-20261101/engine/filler_lib.sh
a271e93a7a9ac54386352d254e5ad2ab57a5f39fc40daad99106afa919bfa157  /mnt/raid0/llm/tmp/yarn-s2-v15-candidate-20261101/engine/dryrun_disk_policy.json
PINS
[[ $# == 0 ]] || exit 64
case "${WS58_REGIONS:?}" in 0-23|24-47|48-71|72-95) ;; *) exit 64;; esac
exec /bin/bash "$ENGINE" --id "$ID" --class cpu --claim-cpus "$WS58_REGIONS" --role build --min-window 42000 --stop "$D/STOP" --port 19422 --workdir "$D" --cmd 'taskset -c "$FILLER_CPUS" bash /mnt/raid0/llm/tmp/yarn-s2-v15-candidate-20261101/host-launch.sh --job' --complete-cmd false
