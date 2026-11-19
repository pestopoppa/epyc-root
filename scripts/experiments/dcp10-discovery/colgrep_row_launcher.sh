#!/bin/bash
set -euo pipefail
R=__SCRATCH_ROOT__
D="$R/packet"
/usr/bin/sha256sum --check --status --strict <<< "__SOURCE_SHA__  $D/SOURCE.sha256"
(cd "$D" && /usr/bin/sha256sum --check --status --strict SOURCE.sha256)
runner="/usr/bin/python3 -I -B $D/colgrep_row.py --receipt-sha __RECEIPT_SHA__"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id __ROW_ID__ --class cpu --role bench --gpu-quiet none --no-fold-siblings \
  --claim-cpus "$WS58_REGIONS" --min-window 1500 --stop "$R/STOP" --workdir "$D" \
  --cmd "$runner run" --complete-cmd "$runner complete" --precond-cmd "$runner precondition"
