#!/bin/bash
# build_fix.sh — CPU build of experimental/cpu-fa-fp32-vkq-20261004 with recipe native-openmp-gcc15-cpu-v1.
# Run under: region-lock run --cpu-list 0-23 --role build --tag cpu-fa-f16 -- taskset -c 0-23 nice -n 19 ./build_fix.sh
set -euo pipefail
S=/mnt/raid0/llm/tmp/cpu-fa-f16-20261004/src
B=/mnt/raid0/llm/tmp/cpu-fa-f16-20261004/build-cpu
cmake -S "$S" -B "$B" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=OFF -DGGML_NATIVE=ON -DGGML_OPENMP=ON \
    -DCMAKE_C_COMPILER=/usr/bin/gcc-15 -DCMAKE_CXX_COMPILER=/usr/bin/g++-15 -DLLAMA_CURL=OFF \
    -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN' > "$B.configure.log" 2>&1
cmake --build "$B" -j24 --target ggml llama llama-bench test-backend-ops > "$B.build.log" 2>&1
ls -la "$B/bin/"
strings "$B/bin/libggml-cpu.so" | grep -c GGML_FA_VKQ_F16
