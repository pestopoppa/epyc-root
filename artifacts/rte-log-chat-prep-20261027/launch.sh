#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-next-ranked-launcher/chat
exec bash "$D/deps/filler_run12.sh" --id rte-log-chat-live --class cpu --self-claim --claim-cpus 0-95 --role build --min-window 900 --stop "$D/STOP" --workdir "$D" --cmd "bash $D/job.sh"
