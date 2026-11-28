#!/bin/bash
set -euo pipefail
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
KERNEL_SRC="${1:?pass a clean pinned V10 source checkout}"
STORE="${2:?pass the V10 CPU store bin directory}"
OUT="${3:?pass an experimental output path}"
PIN=ffc1bac82eeca6f9099e1ccd9ba49703c460a115
[[ "$(git -C "$KERNEL_SRC" rev-parse HEAD)" == "$PIN" ]]
[[ -z "$(git -C "$KERNEL_SRC" status --porcelain --untracked-files=no)" ]]
g++ -std=c++20 -O3 -march=znver5 -fopenmp -Werror -Wall -Wextra -Wno-missing-field-initializers \
    -I"$KERNEL_SRC/include" -I"$KERNEL_SRC/ggml/include" "$SRC_DIR/replay.cpp" \
    -L"$STORE" -Wl,-rpath,"$STORE" -lllama -lggml -lggml-cpu -lggml-base -o "$OUT"
objdump -d "$OUT" | rg 'vpdpwssd|vpdpwssds'
