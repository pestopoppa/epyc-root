#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/fm4-native-current/projection-row
echo '38da35a7c3d92f0b935b12057f39c1c63c1febb8f3cd8edee06392106c9dc167  /mnt/raid0/llm/tmp/vidya-belief-substrate/fm4-native-current/projection-row/job.py' | /usr/bin/sha256sum --check --status
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-fm4-codex-projection-20261118 --class cpu --role build --gpu-quiet none --min-window 120 --stop "$D/STOP" --workdir "$D/engine-work" --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete --pins-sha256 1ba82267185a3bc98e151d6612e1a30a39b57d13e7ecf4f6347a333c8db272f6 --threads 4" --cmd "/usr/bin/python3 -I -B $D/job.py run --pins-sha256 1ba82267185a3bc98e151d6612e1a30a39b57d13e7ecf4f6347a333c8db272f6 --threads 4"
