#!/bin/bash
set -euo pipefail
# Fail closed until native token proof, calibrated rate, source closure, engine allowlist and manifest exist.
exec /usr/bin/python3 /mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/df2_launcher.py --role gpu --manifest /mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/finalization-ready-draft/gpu/FINAL-MANIFEST.json
