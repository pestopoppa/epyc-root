#!/bin/bash
set -euo pipefail
packet=${EXP01_CAPTURE_DIR:?A sealed prospective EXP01 source packet is required}
: "${OUT:?An isolated prospective EXP01 attempt directory is required}"
export OUT MODELSET="$packet/models.env" LAUNCHES=3 CAP_S=5400
exec /bin/bash "$packet/job_r3.sh" --capture-official
