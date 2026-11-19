#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/fm4-native-current
echo '10a979f050a887f54c5ccad3ed30d753cac76616f13c918a0ebb51cbc5ef9194  /mnt/raid0/llm/tmp/vidya-belief-substrate/fm4-native-current/job.py' | /usr/bin/sha256sum --check --status
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-fm4-codex-native-20261118 --class cpu --role build --gpu-quiet none --min-window 120 --stop "$D/STOP" --workdir "$D/engine-work" --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete --pins-sha256 a6af6dfa952245b69efb40214b57998993eb7517c8a984966f911f75e6c5fe8d --threads 4" --cmd "/usr/bin/python3 -I -B $D/job.py run --pins-sha256 a6af6dfa952245b69efb40214b57998993eb7517c8a984966f911f75e6c5fe8d --threads 4"
