#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kvu11c-asan-build-20261105/packet-r2; S=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kvu11c-asan-build-20261105/source; B=$D/build; O=$D/out
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then B=${FILLER_DRYRUN_DIR:?}/build; O=${FILLER_DRYRUN_DIR:?}/out; fi
: "${FILLER_THREADS:?}" "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
mkdir -p "$O"
python3 "$D/check.py"
export PATH=/opt/rocm/bin:/usr/bin:/bin CMAKE_PREFIX_PATH=/opt/rocm HIPCXX=/opt/rocm/llvm/bin/clang++
export LD_LIBRARY_PATH="$B:/opt/rocm/lib"
run() { python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" "$@"; }
run /usr/bin/cmake -G 'Unix Makefiles' -S "$S" -B "$B" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a '-DCMAKE_C_FLAGS=-fsanitize=address -fno-omit-frame-pointer' '-DCMAKE_CXX_FLAGS=-fsanitize=address -fno-omit-frame-pointer' '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address' '-DCMAKE_SHARED_LINKER_FLAGS=-fsanitize=address' > "$O/configure.log" 2>&1
run /usr/bin/cmake --build "$B" --target ggml-base --parallel "$FILLER_THREADS" > "$O/base.log" 2>&1
python3 "$D/check.py"
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 "$D/proof.py" "$B" "${FILLER_DRYRUN_RESULT_PATH:?}" smoke
 exit 0
fi
run /usr/bin/cmake --build "$B" --target tts-server --parallel "$FILLER_THREADS" > "$O/build.log" 2>&1
run /bin/bash "$D/verify_ggml_linkage.sh" "$B/tts-server" "$B" > "$O/linkage.log" 2>&1
python3 "$D/check.py"
python3 "$D/proof.py" "$B" "$O/RESULT.json" full
