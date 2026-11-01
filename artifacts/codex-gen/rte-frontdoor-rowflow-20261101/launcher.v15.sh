#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-rte-frontdoor-quarter-v15-candidate-20261101
EXPECTED_SOURCE_REVIEW=af538ed1ce8f4c3d9faa40a0e30055955f6a2f211a9b765a03247eb8a690979c
ACTUAL_SOURCE_REVIEW=$(sha256sum "$D/SOURCE-REVIEW.sha256" | awk '{print $1}')
[[ "$ACTUAL_SOURCE_REVIEW" == "$EXPECTED_SOURCE_REVIEW" ]] || { echo 'REFUSED: source-review manifest digest mismatch' >&2; exit 65; }
(cd "$D" && sha256sum -c SOURCE-REVIEW.sha256)
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id codex-ni-rte-frontdoor-quarter-20261031 \
  --class cpu --role build --gpu-quiet none \
  --min-window 1800 --port 8070 \
  --stop "$D/STOP" --workdir "$D" \
  --cmd "bash $D/run_job.sh" \
  --complete-cmd "if [ \"\${FILLER_DRYRUN:-0}\" = 1 ]; then exit 1; else python3 -B $D/completion_unit.py --check $D; fi"
