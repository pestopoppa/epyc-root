#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu126-gauge-live-v2-20261104
[ "$(sha256sum "$D/INPUTS.sha256" | cut -d" " -f1)" = "2fbf934183dbff3aa0644cf5da85ec9c46a6c0b854130d23ca22d301093b1ac5" ] || { echo "input manifest digest changed" >&2; exit 65; }
sha256sum --check --quiet "$D/INPUTS.sha256"
export PYTHONDONTWRITEBYTECODE=1
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu126-live-gauge-r2-20261104 --class cpu --role build --gpu-quiet none --min-window 600 --stop "$D/STOP" --port 19896 --workdir "$D" --complete-cmd "test -e '$D/out/COMPLETE'" --cmd "python3 '$D/job.py'"
