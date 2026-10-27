#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-shipped-parity/successor
exec /bin/bash "$D/deps/filler_run12.sh" --id codex-ni-ufh12-gp1-r2-20261027 --class cpu --claim-cpus 72-95 --role build --min-window 1200 --port 18994 --stop "$D/STOP" --workdir "$D" --cmd "exec /bin/bash $D/job.sh" --complete-cmd "test -e $D/COMPLETE.json"
