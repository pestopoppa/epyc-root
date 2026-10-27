#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep
cd "$B"
exec /usr/bin/python3 -B "$B/deps/dryrun_check.py" run --id codex-ni-meta-fix-build-20261027 --row-file "$B/ROW-BACKLOG.md" --min-window-s 3300 --launcher "$B/build-poller.sh" --job "$B/build-body.sh" --engine "$B/deps/filler_run12.sh" --source-manifest "$B/SOURCE.SHA256SUMS" --scoped-pf --entry-json '["/bin/bash","/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep/build-poller.sh"]' --effect source-build --regions 72,73 --required-cpus 72,73 --allowed-cpus 72,73 --cwd "$B" --region-lock-shim "$B/pf-region-claimed.sh" --timeout-s 90
