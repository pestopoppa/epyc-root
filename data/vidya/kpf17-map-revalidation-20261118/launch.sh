#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/kpf17-map-revalidation-20261118
echo '08b4b8d48ec1bd5477ca596345f25a0134333351e1cf487e4bfacd0403fde9de  /mnt/raid0/llm/tmp/vidya-belief-substrate/kpf17-map-revalidation-20261118/run.py' | /usr/bin/sha256sum --check --status
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id vb-kpf17-map-revalidation-20261118 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" \
  --precond-cmd "/usr/bin/python3 -BI $D/run.py verify --threads 4" \
  --complete-cmd "/usr/bin/python3 -BI $D/run.py complete --threads 4" \
  --cmd "/usr/bin/python3 -BI $D/run.py run --threads 4"
