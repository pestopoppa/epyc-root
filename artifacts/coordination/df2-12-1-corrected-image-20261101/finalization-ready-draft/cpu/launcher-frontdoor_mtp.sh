#!/bin/bash
set -euo pipefail
# Fail closed until native token proof, calibrated rate, source closure, engine allowlist and manifest exist.
exec /usr/bin/python3 /mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/df2_launcher.py --role cpu --manifest /mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/finalization-ready-draft/cpu/FINAL-MANIFEST.json
