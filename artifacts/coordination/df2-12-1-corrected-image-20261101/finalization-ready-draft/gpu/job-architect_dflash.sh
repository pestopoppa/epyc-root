#!/bin/bash
set -euo pipefail
# The canonical v14 engine supplies the same environment and same job in normal/cutoff.
if [[ "${WS58_QUAL:-0}" == 1 ]]; then OUT=/mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/qualification-work/architect_dflash; else OUT=/mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/science/architect_dflash; fi
exec /usr/bin/python3 /mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/run_role.py --shape architect_dflash --binary /mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/frontend-instrument-corrected/gpu/bin/llama-server --port 19083 --manifest /mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/PROMPTS.json --manifest-sha de3096605c354c6346418267ad09efc5cbf6eb7599816301a940e3b93cb8e0e1 --proof-dir /mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/corrected-proof --out "$OUT"
