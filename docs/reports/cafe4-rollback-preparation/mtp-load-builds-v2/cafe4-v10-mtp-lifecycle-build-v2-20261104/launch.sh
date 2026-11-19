#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/speculative-decoding-mtp/cafe4-mtp-build-v2
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id cafe4-v10-mtp-lifecycle-build-v2-20261104 --class cpu --role build --min-window 1800 --stop "$D/STOP" --workdir "$D" --precond-cmd "sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/proof.py check"
