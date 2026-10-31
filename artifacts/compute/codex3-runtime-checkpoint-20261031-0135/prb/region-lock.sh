#!/bin/bash
set -euo pipefail
cd /mnt/micron/codex3-lanes/orchestrator
exec /usr/bin/python3 -B -m src.runtime.region_lock_cli "$@"
