#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/v11-promotion-checklist/llg-gpu-gate/build
cd "$D"
/usr/bin/sha256sum --check --status SOURCE.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id v11-122-llg-gpu-c13-nollg-build-20261118 --class cpu --role build --gpu-quiet none \
  --min-window 900 --workdir "$D" --stop "$D/STOP" \
  --precond-cmd "/usr/bin/python3 -I -B $D/build.py --precondition" \
  --cmd "/usr/bin/python3 -I -B $D/build.py" \
  --complete-cmd "/usr/bin/test -s $D/out/BUILD-OK.json"
