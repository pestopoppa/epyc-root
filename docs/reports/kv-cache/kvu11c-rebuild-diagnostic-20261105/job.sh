#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kvu11c-rebuild-diagnostic-20261105
S=/mnt/raid0/llm/tmp/kvfork/kvu11c-source-20261104
B=$D/build
O=$D/out
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
 B=${FILLER_DRYRUN_DIR:?}/kvu11c-build
 O=${FILLER_DRYRUN_DIR:?}/kvu11c-out
fi
: "${FILLER_THREADS:?}" "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
mkdir -p "$O"
python3 "$D/check.py"
export PATH=/opt/rocm/bin:$PATH CMAKE_PREFIX_PATH=/opt/rocm HIPCXX=/opt/rocm/llvm/bin/clang++
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake -G 'Unix Makefiles' -S "$S" -B "$B" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a > "$O/configure.log" 2>&1
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$B" --target ggml-base --parallel "$FILLER_THREADS" > "$O/base.log" 2>&1
python3 "$D/check.py"
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 - "$B/libggml-base.so" "${FILLER_DRYRUN_RESULT_PATH:?}" <<'PY'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]).resolve(); assert p.is_file() and p.stat().st_size>0
pathlib.Path(sys.argv[2]).write_text(json.dumps({'status':'built-ggml-base-only','bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'four-CPU build smoke only'})+'\n')
PY
 exit 0
fi
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$B" --target tts-server --parallel "$FILLER_THREADS" > "$O/build.log" 2>&1
export LD_LIBRARY_PATH="$B:/opt/rocm/lib"
bash "$D/verify_ggml_linkage.sh" "$B/tts-server" "$B" > "$O/linkage.log" 2>&1
"$B/tts-server" --help > "$O/help.log" 2>&1
grep -F -- '--threads <n>' "$O/help.log" >/dev/null
python3 "$D/check.py"
python3 "$D/proof.py"
