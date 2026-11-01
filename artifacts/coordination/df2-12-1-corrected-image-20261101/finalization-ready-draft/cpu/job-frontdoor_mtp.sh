#!/bin/bash
set -euo pipefail
# The canonical v14 engine supplies the same environment and same job in normal/cutoff.
if [[ "${WS58_QUAL:-0}" == 1 ]]; then OUT=/mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/qualification-work/frontdoor_mtp; else OUT=/mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/science/frontdoor_mtp; fi
exec /usr/bin/python3 /mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/run_role.py --shape frontdoor_mtp --binary /mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/frontend-instrument-corrected/cpu/bin/llama-server --port 19070 --manifest /mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/PROMPTS.json --manifest-sha de3096605c354c6346418267ad09efc5cbf6eb7599816301a940e3b93cb8e0e1 --proof-dir /mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/corrected-proof --out "$OUT"
