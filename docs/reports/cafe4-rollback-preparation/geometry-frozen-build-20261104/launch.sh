#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/cafe4-geometry-frozen-build
seal_hash=$(sha256sum "$D/runtime.sha256")
[[ ${seal_hash%% *} == "92d569ec831cde607a730303451437fa8172b3c373bb6626e20afcd6a76d59c9" ]] || { echo "runtime seal mismatch" >&2; exit 1; }
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id cafe4-v10-geometry-holdout-frozen-build-20261104 --class cpu --role build --min-window 1800 --stop "$D/STOP" --workdir "$D" --precond-cmd "sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/proof.py check"
