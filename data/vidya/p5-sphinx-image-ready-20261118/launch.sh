#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/p5-sphinx-image-build-sealed-20261118
ID=vb-p5-sphinx-image-rebuild-20261118
LAUNCHER=/mnt/raid0/llm/tmp/vidya-belief-substrate/p5-sphinx-image-build-sealed-20261118/launch.sh
cd "$D"
printf '%s  %s\n' '34b98a0025f822ec0950d56c32c3cf1ee1ca45e3741eb0dad904c8d74a6a8ca2' SOURCE.sha256 | sha256sum --check --status
sha256sum --check --status SOURCE.sha256
export P5_BUILD_LAUNCHER="$LAUNCHER"
if (( $# )); then
    exec "$D/build-image.sh" "$@"
fi
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
    --id "$ID" --class cpu --role build --min-window 300 --stop "$D/STOP" --workdir "$D" \
    --precond-cmd "$LAUNCHER --preflight" --cmd "$LAUNCHER --job" \
    --complete-cmd "$LAUNCHER --complete"
