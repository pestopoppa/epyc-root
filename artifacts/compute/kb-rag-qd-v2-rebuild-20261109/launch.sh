#!/bin/bash
# kb-rag-qd-v2-rebuild-20261109: build a FRESH qd-v2 KB-RAG index (never index/ or index-qd-v1/) with
# parallel_reembed at 24 workers on one quarter, then validate rows + stamp + a query. CPU only, no GPU.
set -euo pipefail
cd /mnt/raid0/llm/tmp/kb-rag-qd-v2-rebuild-20261109
/usr/bin/sha256sum --check --status SOURCE.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kb-rag-qd-v2-rebuild-20261109 \
  --class cpu --gpu-quiet none --role build --min-window 1800 \
  --precond-cmd "/usr/bin/python3 -I /mnt/raid0/llm/tmp/kb-rag-qd-v2-rebuild-20261109/job.py --precond" \
  --cmd "/usr/bin/python3 -I /mnt/raid0/llm/tmp/kb-rag-qd-v2-rebuild-20261109/job.py --workers 24" \
  --complete-cmd "/usr/bin/python3 -I /mnt/raid0/llm/tmp/kb-rag-qd-v2-rebuild-20261109/check_complete.py" \
  --stop "/mnt/raid0/llm/tmp/kb-rag-qd-v2-rebuild-20261109/STOP" --workdir "/mnt/raid0/llm/tmp/kb-rag-qd-v2-rebuild-20261109"
