#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/task8
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id hsf3-source-coverage-task8-20261104 --class cpu --role build \
  --gpu-quiet none --min-window 120 --stop "$D/STOP" --workdir "$D" \
  --precond-cmd "test -x '$D/run_cpu.sh' && test -f '$D/PUBLISH_SPEC.md'" \
  --complete-cmd "python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x.get(\"schema\")==\"hsf3_source_coverage_census.v1\" and x.get(\"mode\")==\"read_only_aggregate_only\"' '$D/RESULT.json'" \
  --cmd "bash '$D/job.sh'"
