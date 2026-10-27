#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep
T=/mnt/raid0/llm/worktrees/meta-fix-c5
ID=codex-ni-meta-fix-build-20261027
guard() {
 [[ ${FILLER_PREFLIGHT:-0} != 1 && ${FILLER_ID:-} == "$ID" && ${FILLER_CPUS:-} == 48-71 && ${FILLER_THREADS:-} == 24 && ${FILLER_STOPFILE:-} == "$B/STOP" ]]
 [[ ! -e $B/STOP && ! -L $B/STOP && -z ${LD_PRELOAD:-} && -z ${LD_AUDIT:-} ]]
 [[ ${FILLER_END:-} =~ ^[0-9]+$ && ${FILLER_DEADLINE:-} =~ ^[0-9]+$ && $EPOCHSECONDS -lt $FILLER_DEADLINE && $FILLER_DEADLINE -lt $FILLER_END ]]
 [[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == 48-71 ]]
 local line start end
 [[ -f /mnt/raid0/llm/tmp/compute-flags/grants/$ID.grant && ! -L /mnt/raid0/llm/tmp/compute-flags/grants/$ID.grant ]]
 read -r line < "/mnt/raid0/llm/tmp/compute-flags/grants/$ID.grant"
 [[ $line =~ ^regions=48-71\ start=([^[:space:]]+)\ end=([^[:space:]]+)$ ]]
 start=$(date -u -d "${BASH_REMATCH[1]}" +%s); end=$(date -u -d "${BASH_REMATCH[2]}" +%s)
 ((start<=EPOCHSECONDS && EPOCHSECONDS<end && end==FILLER_END && end-start==3600))
 [[ ! -e /mnt/raid0/llm/tmp/compute-flags/grants/$ID.ended && ! -e /mnt/raid0/llm/tmp/compute-flags/grants/$ID.complete ]]
 ! compgen -G '/mnt/raid0/llm/tmp/compute-flags/HOLD_*' >/dev/null
 [[ ! -e /mnt/raid0/llm/tmp/HOLD_GPU_FOR_QUIET_20261024 ]]
}
guard
sha256sum --quiet -c "$B/SOURCE.SHA256SUMS"
sha256sum --quiet -c "$B/TRACKED-SOURCE.sha256"
sha256sum --quiet -c "$B/TOOLCHAIN.sha256"
[[ $(git -C "$T" rev-parse HEAD) == c72ec82f5417bb2937310326120f149b665e8400 ]]
cmp <(git -C "$T" diff --binary) "$B/candidate.patch"
[[ ! -e "$B/buildcpu" && ! -e "$B/buildhip" && ! -e "$B/sourcehip" && ! -e "$T/tools/ui/dist" ]]
sha256sum --quiet -c "$B/UI-SOURCE.sha256"
cp -a "$T" "$B/sourcehip"
sed "s@$T/@$B/sourcehip/@g" "$B/TRACKED-SOURCE.sha256" | sha256sum --quiet -c -
cp -a /mnt/raid0/llm/kernels/builds/cpu-20261023-141e4bcf5-lbh/tools/ui/dist "$T/tools/ui/dist"
cp -a /mnt/raid0/llm/kernels/builds/gpu-20261023-141e4bcf5-lbh/tools/ui/dist "$B/sourcehip/tools/ui/dist"
export OMP_NUM_THREADS=1
ulimit -c 0
for kind in cpu hip; do
 guard
 if [[ $kind == cpu ]]; then S=$T; D=$B/buildcpu; BASE=/mnt/raid0/llm/kernels/builds/cpu-20261024-c72ec82f5-c5; export LD_LIBRARY_PATH="$D/bin"; else S=$B/sourcehip; D=$B/buildhip; BASE=/mnt/raid0/llm/kernels/builds/gpu-20261024-c72ec82f5-c5; export LD_LIBRARY_PATH="$D/bin:/opt/rocm/lib"; fi
 PMAP="-ffile-prefix-map=$S=. -fmacro-prefix-map=$S=. -ffile-prefix-map=$D=.build -fmacro-prefix-map=$D=.build"
 common=(-DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON "-DCMAKE_C_FLAGS=$PMAP" "-DCMAKE_CXX_FLAGS=$PMAP" -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON)
 if [[ $kind == cpu ]]; then
  cmake -S "$S" -B "$D" "${common[@]}" -DGGML_HIP=OFF -DGGML_OPENMP=ON -DCMAKE_C_COMPILER=/usr/bin/gcc-15 -DCMAKE_CXX_COMPILER=/usr/bin/g++-15 -DLLAMA_CURL=OFF '-DCMAKE_INSTALL_RPATH=$ORIGIN' > "$B/cpu-configure.log" 2>&1
 else
  cmake -S "$S" -B "$D" "${common[@]}" -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a -DGGML_HIP_ROCWMMA_FATTN=ON "-DCMAKE_HIP_FLAGS=$PMAP" '-DCMAKE_INSTALL_RPATH=$ORIGIN;/opt/rocm/lib' > "$B/hip-configure.log" 2>&1
 fi
 diff -u <(grep -E '^(GGML|LLAMA)_' "$BASE/CMakeCache.txt" | grep -v -E 'CCACHE|_DIR|PATH' | sort) <(grep -E '^(GGML|LLAMA)_' "$D/CMakeCache.txt" | grep -v -E 'CCACHE|_DIR|PATH' | sort) > "$B/$kind-cache.diff"
 guard
 cmake --build "$D" -j "$FILLER_THREADS" > "$B/$kind-build.log" 2>&1
 guard
 /workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$D/bin/test-llama-archs" > "$B/$kind-linkage.log" 2>&1
 readelf -d "$D/bin/libggml-base.so" > "$B/$kind-elf.txt"
 (cd "$D/bin" && sha256sum test-llama-archs libggml*.so* libllama.so*) > "$B/$kind-build.sha256"
 stat -c '%y %n' "$D/bin/test-llama-archs" "$D/bin/libggml-base.so" > "$B/$kind-mtimes.txt"
 for fixture in host-view-fixture meta-mixed-graph-fixture; do
  /usr/bin/g++-15 -std=c++17 -O2 -I"$T/ggml/include" -I"$T/ggml/src" "$B/$fixture.cpp" -L"$D/bin" -Wl,-rpath,"$D/bin" -lggml-cpu -lggml-base -lggml -pthread -o "$B/$kind-$fixture"
 done
 /usr/bin/g++-15 -std=c++17 -O2 -I"$T/ggml/include" -I"$T/ggml/src" '-DMETA_SOURCE="/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep/baseline-meta.cpp"' "$B/meta-mixed-graph-fixture.cpp" -L"$D/bin" -Wl,-rpath,"$D/bin" -lggml-cpu -lggml-base -lggml -pthread -o "$B/$kind-baseline-fixture"
 "$B/$kind-host-view-fixture" > "$B/$kind-host-view.log" 2>&1
 "$B/$kind-meta-mixed-graph-fixture" > "$B/$kind-mixed.log" 2>&1
 /usr/bin/python3 -B "$B/verify-aborts.py" "$B/$kind-baseline-fixture" "$B/$kind-meta-mixed-graph-fixture" "$B/$kind"
done
guard
sha256sum --quiet -c "$B/TRACKED-SOURCE.sha256"
printf 'private_candidate=c72ec82f5417bb2937310326120f149b665e8400\npatch_sha256=%s\nmodel_runs=none\n' "$(sha256sum "$B/candidate.patch" | cut -d' ' -f1)" > "$B/BUILD-WORK-DONE"
