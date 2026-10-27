#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-rtg57-f32-completion/oracle
B=/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/buildcpu/bin
sha256sum "$D/source/test-fa-rowexact.cpp" > "$D/source.sha256"
g++ -std=c++17 -O2 -I "$D/source/ggml/include" "$D/source/test-fa-rowexact.cpp" -L "$B" -Wl,-rpath,"$B" -lggml -lggml-base -lggml-cpu -o "$D/test-fa-rowexact-c5"
sha256sum "$D/test-fa-rowexact-c5" > "$D/binary.sha256"
