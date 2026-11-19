#!/bin/bash
set -euo pipefail
ROOT=/mnt/raid0/llm/tmp/pf1-loadthreads-build-20261104
cd "$ROOT"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id brf-exp04-c6-loadthreads-build-20261104-r1 \
  --class cpu --claim-cpus 0-3 --role build --min-window 9000 \
  --cmd "/usr/bin/python3 -I $ROOT/loadthreads-build/build.py" \
  --complete-cmd "test -s $ROOT/loadthreads-build/BUILD-RECEIPT.json" \
  --stop "$ROOT/loadthreads-build/STOP" --workdir "$ROOT"
