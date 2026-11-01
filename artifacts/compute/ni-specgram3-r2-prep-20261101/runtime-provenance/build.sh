#!/bin/bash
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd)
SRC=/mnt/raid0/llm/llama.cpp
LIB=/mnt/raid0/llm/kernels/production/cpu
c++ -O3 -DNDEBUG -std=c++17 -DLLAMA_USE_LLGUIDANCE -I"$SRC/include" -I"$SRC/ggml/include" -I"$SRC/common" -I"$SRC/vendor" -I"$S/llguidance-src/parser" "$S/bench-grammar-sampler.cpp" "$S/llguidance.cpp" "$S/wheel/llguidance/_lib.abi3.so" /usr/lib/x86_64-linux-gnu/libpython3.13.so.1 -L"$LIB" -lllama-common -lllama -lggml -lggml-base -Wl,-rpath,"$LIB" -Wl,-rpath,"$S/wheel/llguidance" -o "$S/bench-specgram3"
