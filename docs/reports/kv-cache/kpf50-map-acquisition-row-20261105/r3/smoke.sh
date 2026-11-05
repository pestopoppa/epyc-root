#!/bin/bash
set -euo pipefail
: "${FILLER_DRYRUN_RESULT_PATH:?isolated smoke receipt required}"
: "${WS58_REGIONS:?exactly four granted smoke CPUs required}"
export FILLER_SMOKE=1
exec /bin/bash /mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf50-own-child-map-acquisition-r3-20261105/launch.sh
