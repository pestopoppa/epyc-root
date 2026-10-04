#!/bin/bash
# Store builds of the champion FOLD CANDIDATE fold/champion-kvu19-20261004 (NOT production, NOT yet the champion).
#   source : /mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/src (git worktree of /mnt/raid0/llm/llama.cpp,
#            branch fold/champion-kvu19-20261004, clean)
#   recipes: identical to the champion builds gpu-20260929-90c12df42 (gfx90a-house-v1) and
#            cpu-20260925-90c12df42 (native-openmp-gcc15-cpu-v1), plus the same relocatability flags.
#            Copied verbatim from /mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/build_store.sh (KVU-19b store builds).
# Contention: run ONLY under `region-lock run --cpu-list 0-95 --role build --tag champion-fold`;
#             nice 19, ionice idle, taskset 0-95 (the locked region), -j24.
# usage: build_store.sh gpu|cpu
set -euo pipefail

SRC=/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/src
SHA=$(git -C "$SRC" rev-parse --short=9 HEAD)
[ -z "$(git -C "$SRC" status --porcelain)" ] || { echo "FAIL: $SRC dirty"; exit 1; }
RUN="nice -n 19 ionice -c3 taskset -c 0-95"

case "${1:-}" in
    gpu)
        B=/mnt/raid0/llm/kernels/builds/gpu-20261004-$SHA
        [ ! -e "$B" ] || { echo "FAIL: $B exists"; exit 1; }
        $RUN cmake -S "$SRC" -B "$B" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a \
            -DGGML_HIP_ROCWMMA_FATTN=ON -DGGML_NATIVE=ON \
            -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN;/opt/rocm/lib' \
            > "$B.configure.log" 2>&1
        ;;
    cpu)
        B=/mnt/raid0/llm/kernels/builds/cpu-20261004-$SHA
        [ ! -e "$B" ] || { echo "FAIL: $B exists"; exit 1; }
        $RUN cmake -S "$SRC" -B "$B" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=OFF -DGGML_NATIVE=ON -DGGML_OPENMP=ON \
            -DCMAKE_C_COMPILER=/usr/bin/gcc-15 -DCMAKE_CXX_COMPILER=/usr/bin/g++-15 -DLLAMA_CURL=OFF \
            -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN' \
            > "$B.configure.log" 2>&1
        ;;
    *) echo "usage: $0 gpu|cpu"; exit 2 ;;
esac
mv "$B.configure.log" "$B/CONFIGURE.log"
echo "build start $(date -u +%FT%TZ) src=$(git -C "$SRC" rev-parse HEAD)" > "$B/BUILD.log"
$RUN cmake --build "$B" -j24 >> "$B/BUILD.log" 2>&1
echo "build end $(date -u +%FT%TZ) rc=0" >> "$B/BUILD.log"
(cd "$B/bin" && sha256sum $(find . -maxdepth 1 -type f | sort) > ../SHA256SUMS)
echo "OK $B"
