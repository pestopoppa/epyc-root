#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-paw-compact-a-20261030
P=/mnt/micron/codex3-paw-compact-a-20261030/packet
sha256sum --strict --quiet -c "$D/INNER-SOURCES.sha256"
exec /bin/bash "$P/launch.sh" "$@"
