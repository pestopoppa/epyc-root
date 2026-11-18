#!/bin/bash
set -euo pipefail
D="$(cd "$(dirname "$0")/.." && pwd)"
cd "$D"
/usr/bin/sha256sum --check --status SOURCE.sha256
source code/model.env
export LD_LIBRARY_PATH="$(dirname "$FM2_SERVER_BIN")"
[ "$(stat -Lc '%d:%i:%s:%Y:%Z' "$FM2_MODEL_GGUF")" = "$FM2_MODEL_STAT" ]
/usr/bin/sha256sum --check --status KERNEL.sha256
ver="$("$FM2_SERVER_BIN" --version 2>&1)"
[[ "$ver" == *'10303 (ffc1bac82)'* ]]
/bin/bash "$D/code/verify_ggml_linkage.sh" "$FM2_SERVER_BIN" "$LD_LIBRARY_PATH" >/dev/null 2>&1
