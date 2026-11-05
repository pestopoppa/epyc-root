#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kvu19b-native-custody-r4-20261105
exec python3 "$D/supervise.py" "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}" python3 "$D/job.py"
