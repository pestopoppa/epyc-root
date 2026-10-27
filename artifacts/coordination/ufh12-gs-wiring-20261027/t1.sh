#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-gs-rehearsal/wiring
exec /usr/bin/python3 -B "$B/deps/dryrun_check.py" run --id ufh12-gs-scores-20261027 --row-file "$B/ROW-DRAFT.md" --min-window-s 900 --launcher "$B/poller.sh" --job "$B/job.sh" --engine "$B/deps/filler_run12.sh" --source-manifest "$B/SOURCE.sha256" --scoped-pf --entry-json "[\"/bin/bash\",\"$B/poller.sh\",\"scores\"]" --effect owned-eg2-bge-server-start --regions 48,49 --required-cpus 48,49 --allowed-cpus 48,49 --cwd "$B" --region-lock-shim "$B/pf-region-claimed.sh" --timeout-s 90
