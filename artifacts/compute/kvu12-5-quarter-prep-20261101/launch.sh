#!/bin/bash
# DRAFT: refuses execution until producer/integration is implemented and reviewed.
set -euo pipefail
D=/mnt/raid0/llm/tmp/handoff-kvu12-5-quarter-20261101
ID=handoff-kvu12-5-quarter-20261101
case "${1:-}" in
  --job) exec /usr/bin/python3 -B "$D/job.py" ;;
  --engine) exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --role bench --claim-cpus 72-95,168-191 --gpu-quiet exclusive --min-window 39600 --stop "$D/STOP" --port 18970 --workdir "$D" --complete-cmd "test -s $D/COMPLETE.json" --cmd "/bin/bash $D/launch.sh --job" ;;
  '') echo 'DRAFT NOT READY: no keeper dispatch until producer and safety controls are complete' >&2; exit 64 ;;
  *) exit 64 ;;
esac
