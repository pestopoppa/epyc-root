#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-gpu-arch-ready/packet
B=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep
cd "$D"
exec /usr/bin/python3 -B "$D/dryrun_check.py" run --id codex-ni-meta-gpu-arch-20261027 --row-file "$D/ROW-BACKLOG.md" --min-window-s 3300 --launcher "$D/poller.sh" --job "$D/job.sh" --engine "$D/filler_run12.sh" --source-manifest "$D/SOURCES.sha256" --scoped-pf --entry-json '["/bin/bash","/mnt/raid0/llm/tmp/codex-ni-20261027-meta-gpu-arch-ready/packet/poller.sh"]' --effect model-inference --regions mi210_0,72,73 --required-cpus 72,73 --allowed-cpus 72,73 --cwd "$D" --region-lock-shim "$D/pf-shim.sh" --timeout-s 90
