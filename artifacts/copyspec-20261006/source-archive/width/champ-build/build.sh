#!/bin/bash
set -uo pipefail
W=/mnt/raid0/llm/worktrees/llama-champ-specwidth-20261006
B=/mnt/raid0/llm/tmp/copy-spec-eval-20261006/width/champ-build
cd "$W"
taskset -c 24-47 cmake -S "$W" -B "$B/cpu" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=OFF -DGGML_NATIVE=ON -DGGML_OPENMP=ON -DLLAMA_CURL=OFF -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN' -DCMAKE_C_COMPILER=/usr/bin/gcc-15 -DCMAKE_CXX_COMPILER=/usr/bin/g++-15 > "$B/cpu-configure.log" 2>&1 \
 && taskset -c 24-47 nice -n 10 cmake --build "$B/cpu" -j 24 --target llama-server llama-bench > "$B/cpu-build.log" 2>&1
echo $? > "$B/cpu.rc"
taskset -c 24-47 cmake -S "$W" -B "$B/gpu" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a -DGPU_TARGETS=gfx90a -DGGML_HIP_GRAPHS=ON -DGGML_HIP_NO_VMM=ON -DGGML_HIP_MMQ_MFMA=ON -DGGML_HIP_ROCWMMA_FATTN=ON -DGGML_NATIVE=ON -DGGML_OPENMP=ON -DLLAMA_CURL=OFF -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN;/opt/rocm/lib' -DCMAKE_HIP_COMPILER=/opt/rocm/lib/llvm/bin/clang++ -DCMAKE_C_COMPILER=/usr/bin/gcc-15 -DCMAKE_CXX_COMPILER=/usr/bin/g++-15 > "$B/gpu-configure.log" 2>&1 \
 && taskset -c 24-47 nice -n 10 cmake --build "$B/gpu" -j 24 --target llama-server llama-bench > "$B/gpu-build.log" 2>&1
echo $? > "$B/gpu.rc"
