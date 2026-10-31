#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
SOURCE=/mnt/raid0/llm/tmp/lb49-codex-deterministic-20261028
BUILD=/mnt/raid0/llm/tmp/lb49-codex-evidence-20261028/build-deterministic-feature/bin
for name in fixture_qkv replay_qkv capture_qkv; do
 g++ -std=c++17 -O1 -Wall -Wextra -I"$SOURCE/include" -I"$SOURCE/ggml/include" "$name.cpp" -L"$BUILD" -Wl,-rpath,"$BUILD" -lllama -lggml -lggml-cpu -lggml-base -pthread -o "$name"
done
