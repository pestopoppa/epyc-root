#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/p5-astropy-scorer-r1-20261118
ID=vb-p5-astropy-image-rebuild-20261118
LAUNCHER=$D/launch.sh
cd "$D"
printf '%s  %s\n' '52a4537b140e0f440690d68a23750205e17dfe9afaceb2d93c6a13c8b1cc491a' SOURCE.sha256 | sha256sum --check --status
sha256sum --check --status SOURCE.sha256
if (( $# )); then
    unset PYTHONPATH PYTHONHOME
    exec /usr/bin/python3 -B "$D/build-image.py" "$@"
fi
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
    --id "$ID" --class cpu --role build --min-window 300 --stop "$D/STOP" --workdir "$D" \
    --precond-cmd "$LAUNCHER --preflight" --cmd "$LAUNCHER --job" \
    --complete-cmd "$LAUNCHER --complete"
