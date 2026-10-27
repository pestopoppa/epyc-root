#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep
R=$B/recovery
cd "$R"
exec /usr/bin/python3 -B "$B/deps/dryrun_check.py" run --id codex-ni-df2-build-recovery-20261027 --row-file "$R/ROW-BACKLOG.md" --min-window-s 600 --launcher "$R/poller.sh" --job "$R/job.sh" --engine "$B/deps/filler_run12.sh" --source-manifest "$R/RECOVERY-SOURCE.sha256" --scoped-pf --entry-json '["/bin/bash","/mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep/recovery/poller.sh"]' --effect artifact-recovery --regions 0,1 --required-cpus 0,1 --allowed-cpus 0,1 --cwd "$R" --region-lock-shim "$R/pf-shim.sh" --timeout-s 90
