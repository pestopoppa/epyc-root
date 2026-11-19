#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/yarn-e1-mem-chain-20261104
OUT=${1:-$D/out/chain-E1-A1}
[ -d "$OUT" ] || { echo "missing capture directory: $OUT" >&2; exit 2; }
find "$OUT" -type f ! -name RAW-CUSTODY.sha256 -print0 | sort -z | xargs -0 -r sha256sum > "$OUT/RAW-CUSTODY.sha256"
