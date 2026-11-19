#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/autokernel-all-devices-all-dimensions/hip-build-prereq-repair-20261104
PIN=32349a5fd7a814985fe3c711196cce9232f4c7cea475307ca0811e5e28c73596
python3 "$D/verify_seal.py" --pin "$PIN"
export AKX_PACKET_PIN="$PIN"
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id codex-ni-akxall31-gdn-hip-build-repair-20261104 \
  --class cpu --role build --gpu-quiet none --claim-cpus 0-3 \
  --min-window 4200 --stop "$D/STOP" --workdir "$D" \
  --cmd "bash $D/job.sh" --complete-cmd "python3 $D/complete.py"
