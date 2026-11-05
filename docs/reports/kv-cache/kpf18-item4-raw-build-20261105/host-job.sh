#!/bin/bash
set -euo pipefail
S=/mnt/raid0/llm/tmp/kvu/kpf18-raw-build-20261105
I=$S/input
SRC=/mnt/raid0/llm/tmp/kvu/kpf18-raw-logits-source-20261105
: "${FILLER_DEADLINE:?}" "${FILLER_STOPFILE:?}" "${FILLER_THREADS:?}"
check() { [[ ! -e "$FILLER_STOPFILE" && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75; }
check
python3 "$S/v3/integrity.py"
mkdir -p "$S/runs"
R=$(mktemp -d "$S/runs/build-XXXXXXXX")
python3 /mnt/raid0/llm/tmp/kvu/kpf18-raw-build-20261105/v3/supervise.py "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake -G Ninja -S "$SRC" -B "$R/build" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a -DGGML_HIP_ROCWMMA_FATTN=ON -DGGML_NATIVE=ON -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN;/opt/rocm/lib' >"$R/configure.log" 2>&1
python3 "$S/v3/integrity.py" "$R/build/CMakeCache.txt"
check
python3 /mnt/raid0/llm/tmp/kvu/kpf18-raw-build-20261105/v3/supervise.py "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$R/build" --target tools/server/CMakeFiles/server-context.dir/server-context.cpp.o --parallel "$FILLER_THREADS" >"$R/first-unit.log" 2>&1
check
python3 "$S/v3/integrity.py" "$R/build/CMakeCache.txt"
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 /mnt/raid0/llm/tmp/kvu/kpf18-raw-build-20261105/v3/proof.py smoke "$R" "${FILLER_DRYRUN_RESULT_PATH:?}"
 exit 0
fi
python3 /mnt/raid0/llm/tmp/kvu/kpf18-raw-build-20261105/v3/supervise.py "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$R/build" --parallel "$FILLER_THREADS" >"$R/build.log" 2>&1
check
python3 "$S/v3/integrity.py" "$R/build/CMakeCache.txt"
export LD_LIBRARY_PATH="$R/build/bin"
sha256sum -c "$S/v3/linkage.sha256"
/bin/bash "$S/v3/verify_ggml_linkage.sh" "$R/build/bin/llama-server" "$R/build" >"$R/linkage.log" 2>&1
sha256sum -c "$S/v3/linkage.sha256"
for pair in 'libllama.so LLAMA_KPF_LAYOUT_TRACE' 'libllama-server-impl.so LLAMA_KPF_ITEM4_TRACE' 'libllama-server-impl.so KPF18_RAW_LOGITS_PATH' 'libllama-common.so --slot-fork-min-tokens'; do
 read -r lib knob <<<"$pair"
 strings "$R/build/bin/$lib" | grep -F -- "$knob" >/dev/null
done
check
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then O=${FILLER_DRYRUN_RESULT_PATH:?}; else O=$S/RESULT.json; fi
python3 /mnt/raid0/llm/tmp/kvu/kpf18-raw-build-20261105/v3/proof.py write "$R" "$O"

python3 "$S/v3/custody.py" seal --build-dir "$R/build/bin" --build-receipt "$O" --output "$S/CUSTODY.json"
