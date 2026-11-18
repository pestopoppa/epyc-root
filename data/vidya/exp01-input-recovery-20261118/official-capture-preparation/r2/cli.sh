#!/bin/bash
set -euo pipefail
exec /usr/bin/python3 -B "${EXP01_CAPTURE_DIR:?}/launch_capture.py" cli "$@"
