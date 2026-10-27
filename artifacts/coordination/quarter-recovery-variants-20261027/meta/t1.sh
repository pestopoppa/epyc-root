#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/codex-ni-20261027-quarter-recovery-variants/meta
B=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep
cd "$R"
exec /usr/bin/python3 -B "$B/deps/dryrun_check.py" run --id codex-ni-meta-recovery-q0-20261027 --row-file "$R/ROW-BACKLOG.md" --min-window-s 300 --launcher "$R/recovery-poller.sh" --job "$R/recovery-body.sh" --engine "$B/deps/filler_run12.sh" --source-manifest "$R/RECOVERY.SHA256SUMS" --scoped-pf --entry-json '["/bin/bash","/mnt/raid0/llm/tmp/codex-ni-20261027-quarter-recovery-variants/meta/recovery-poller.sh"]' --effect source-build --regions 0,1 --required-cpus 0,1 --allowed-cpus 0,1 --cwd "$R" --region-lock-shim "$R/pf-shim.sh" --timeout-s 90
