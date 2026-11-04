#!/bin/bash
# Preparation guard only. Never pass this to rowflow as a compute launcher.
set -euo pipefail
cd -- "$(dirname -- "$0")"
sha256sum --check --status SHA256SUMS || { echo 'REFUSED: preparation seal mismatch' >&2; exit 65; }
echo 'REFUSED: P1c packet is NOT_READY; see replay-plan.json remaining_before_publish' >&2
exit 78
