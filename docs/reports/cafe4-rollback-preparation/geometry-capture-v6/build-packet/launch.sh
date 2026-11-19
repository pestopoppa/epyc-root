#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/speculative-decoding-mtp/cafe4-geometry-capture-v6-build
seal_hash=$(sha256sum "$D/runtime.sha256")
[[ ${seal_hash%% *} == "17fc367565a1a5c707010aa3c87d14aabbfc33bb46550772372c971e905e18d4" ]] || { echo "runtime seal mismatch" >&2; exit 1; }
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id cafe4-v10-geometry-capture-v6-build-20261104 --class cpu --role build --min-window 1800 --stop "$D/STOP" --workdir "$D" --precond-cmd "sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/proof.py check"
