#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/hsf3-census-r3-20261104
CENSUS=/mnt/raid0/llm/tmp/kvu/hsf3-census-r3-20261104/census.py
CENSUS_SHA256=41cba0cbcaa7c7342d3d936a3fc39fecc700e4821ebed1371238410a5dda1f7d
RUN='timeout 10m nice -n 19 ionice -c 3 python3 -B'
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id kvu-hsf3-source-coverage-r3-20261104 --class cpu --role build \
  --gpu-quiet none --min-window 120 --stop "$D/STOP" --workdir "$D" \
  --precond-cmd "test -f '$CENSUS' && test \"\$(sha256sum '$CENSUS' | cut -d' ' -f1)\" = '$CENSUS_SHA256'" \
  --complete-cmd "python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x.get(\"schema\")==\"hsf3_source_coverage_census.v1\" and x.get(\"mode\")==\"read_only_aggregate_only\"' '$D/RESULT.json'" \
  --cmd "if [[ \"\${FILLER_SMOKE:-0}\" == 1 ]]; then : \"\${FILLER_DRYRUN_RESULT_PATH:?publisher must supply isolated smoke result path}\"; exec $RUN '$CENSUS' --out-file \"\$FILLER_DRYRUN_RESULT_PATH\"; else if [[ -n \"\${FILLER_DRYRUN_RESULT_PATH:-}\" ]]; then echo 'unexpected smoke output path outside publisher smoke' >&2; exit 2; fi; exec $RUN '$CENSUS' --out-file '$D/RESULT.json'; fi"
