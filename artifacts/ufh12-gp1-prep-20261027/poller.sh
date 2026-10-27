#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-shipped-parity
exec /bin/bash "$D/deps/filler_run12.sh" --id codex-ni-ufh12-gp1-20261027 --class cpu --claim-cpus 72-95 --role build --min-window 1200 --port 18993 --stop "$D/STOP" --workdir "$D" --cmd "exec /bin/bash $D/job.sh" --complete-cmd "test -e $D/COMPLETE.json"
