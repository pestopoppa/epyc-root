#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/ch18-current/packet
/usr/bin/sha256sum --check --status <<'SEAL'
410e23d065212cb882e1cc94b852a095973c0de9e74732d8d3ce588bd8cec920  /mnt/raid0/llm/tmp/vidya-belief-substrate/ch18-current/packet/job.py
0f04f9bb15f0740ddd4de848c964964f5dca539fd1153db0ae8b76ba70de2128  /mnt/raid0/llm/tmp/vidya-belief-substrate/ch18-current/packet/source-pins.json
SEAL
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-mi210-q38-planner-control-20261118 --class cpu --role build --gpu-quiet none   --min-window 120 --stop "$D/STOP" --workdir "$D/engine-work"   --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete --pins-sha256 0f04f9bb15f0740ddd4de848c964964f5dca539fd1153db0ae8b76ba70de2128"   --cmd "/usr/bin/python3 -I -B $D/job.py run --pins-sha256 0f04f9bb15f0740ddd4de848c964964f5dca539fd1153db0ae8b76ba70de2128"
