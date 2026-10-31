#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-paw-compact-b-20261030
cd "$D"
sha256sum --strict --quiet -c BRIDGE-SOURCES.sha256
exec docker run --rm --pid=host --network=host --user 1000:1000 -e WS58_REGIONS -e FILLER_CPUS -v /mnt/micron:/mnt/micron -v /mnt/raid0:/mnt/raid0 -v /home/node:/home/node vsc-epyc-root-4946b483b8e7237eab13d43325d143d82bfb2ba2674062b4d2a18450da3b0dcd-uid /bin/bash "$D/host-entry.sh" "$@"
