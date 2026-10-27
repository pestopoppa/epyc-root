#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-build-recovery
B=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep
cd "$R"
exec /usr/bin/python3 -B "$B/deps/dryrun_check.py" run --id codex-ni-meta-recovery-20261027 --row-file "$R/ROW-BACKLOG.md" --min-window-s 300 --launcher "$R/recovery-poller.sh" --job "$R/recovery-body.sh" --engine "$B/deps/filler_run12.sh" --source-manifest "$R/RECOVERY.SHA256SUMS" --scoped-pf --entry-json '["/bin/bash","/mnt/raid0/llm/tmp/codex-ni-20261027-meta-build-recovery/recovery-poller.sh"]' --effect source-build --regions 72,73 --required-cpus 72,73 --allowed-cpus 72,73 --cwd "$R" --region-lock-shim "$B/pf-region-claimed.sh" --timeout-s 90
