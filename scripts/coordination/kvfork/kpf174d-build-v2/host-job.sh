#!/bin/bash
set -euo pipefail
S=/mnt/raid0/llm/tmp/kvfork/kpf174d-build
I=$S/input
: "${FILLER_DEADLINE:?}" "${FILLER_STOPFILE:?}" "${FILLER_THREADS:?}"
check() { [[ ! -e "$FILLER_STOPFILE" && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75; }
check
[[ $(sha256sum "$I/source-files.sha256" | cut -d' ' -f1) == 39089f3d1221e2539f04c24a2244551661c14a8891caf24a8de4f83c1bf8f2b3 ]]
[[ $(sha256sum "$I/reference-cache.txt" | cut -d' ' -f1) == 527dbc99938414bcfecb5b309a2f4001f76e168a84b0cc9a32e18d6e26184f76 ]]
[[ $(sha256sum "$I/source.tar" | cut -d' ' -f1) == eb58f5b820ccfce7a7a97e8260bb14e2476caf861efa7509239fdf749151cb95 ]]
(cd "$I/src" && sha256sum -c "$I/source-files.sha256" >/dev/null)
(cd "$I/src" && find . -type f -print | LC_ALL=C sort | cmp -s - "$I/source-file-list.txt")
[[ -z $(find "$I/src" -type l -print -quit) ]]
mkdir -p "$S/runs"
R=$(mktemp -d "$S/runs/build-XXXXXXXX")
python3 /mnt/raid0/llm/tmp/kvfork/kpf174d-build/v2/supervise.py "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake -G Ninja -S "$I/src" -B "$R/build" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a -DGGML_HIP_ROCWMMA_FATTN=ON -DGGML_NATIVE=ON -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN;/opt/rocm/lib' >"$R/configure.log" 2>&1
python3 /mnt/raid0/llm/tmp/kvfork/kpf174d-build/v2/proof.py compare "$I/reference-cache.txt" "$R/build/CMakeCache.txt"
check
python3 /mnt/raid0/llm/tmp/kvfork/kpf174d-build/v2/supervise.py "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$R/build" --parallel "$FILLER_THREADS" >"$R/build.log" 2>&1
check
export LD_LIBRARY_PATH="$R/build/bin"
/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$R/build/bin/llama-server" "$R/build" >"$R/linkage.log" 2>&1
for pair in 'libllama.so LLAMA_KPF_LAYOUT_TRACE' 'libllama-server-impl.so LLAMA_KPF_ITEM4_TRACE' 'libllama-common.so --slot-fork-min-tokens'; do
 read -r lib knob <<<"$pair"
 strings "$R/build/bin/$lib" | grep -F -- "$knob" >/dev/null
done
check
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then O=${FILLER_DRYRUN_RESULT_PATH:?}; else O=$S/RESULT.json; fi
python3 /mnt/raid0/llm/tmp/kvfork/kpf174d-build/v2/proof.py write "$R" "$O"
