#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/triattention-s8c-float-v2-build-20261104
S=/mnt/raid0/llm/tmp/triattention-s8c-float-v2-20261104
P="$D/packet"
BASE=ffc1bac82eeca6f9099e1ccd9ba49703c460a115
PATCH=7612c84004793847a77237d8881830a8f17041625be28bd409591289f62298dc
[[ $(git -C "$S" rev-parse HEAD) == "$BASE" ]]
[[ $(git -C "$S" diff --binary | sha256sum | cut -d' ' -f1) == "$PATCH" ]]
[[ $(sha256sum "$P/recency-safety.patch" | cut -d' ' -f1) == "$PATCH" ]]
[[ -z $(git -C "$S" ls-files --others --exclude-standard) ]]
[[ ! -e ${FILLER_STOPFILE:?} && $(date +%s) -lt ${FILLER_DEADLINE:?} ]] || exit 75
unset LD_PRELOAD LD_LIBRARY_PATH GGML_BACKEND_PATH
if [[ ! -f "$D/base-unit.json" ]]; then
 cmake -S "$S" -B "$D/out" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DGGML_NATIVE=ON -DGGML_OPENMP=ON -DGGML_BLAS=OFF -DGGML_HIP=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_BUILD_SERVER=ON -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_CURL=OFF -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
 cmake --build "$D/out" --target ggml-base --parallel "${FILLER_THREADS:-4}"
 python3 - "$D" "$BASE" "$PATCH" <<'PY'
import hashlib,json,pathlib,sys
d=pathlib.Path(sys.argv[1]); libs=[x for x in (d/'out').rglob('libggml-base.so.*') if x.is_file() and not x.is_symlink()];assert len(libs)==1
files=[d/'out/CMakeCache.txt',d/'out/compile_commands.json',libs[0]]
(d/'base-unit.json').write_text(json.dumps({'base_commit':sys.argv[2],'patch_sha256':sys.argv[3],'files':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in files}},indent=2)+'\n')
PY
 printf '{"unit":"ggml-base","status":"pass"}\n' >> "$D/results.jsonl"
 exit 75
fi
python3 - "$D/base-unit.json" "$BASE" "$PATCH" <<'PY'
import hashlib,json,pathlib,sys
x=json.loads(pathlib.Path(sys.argv[1]).read_text());assert x['base_commit']==sys.argv[2] and x['patch_sha256']==sys.argv[3]
for p,h in x['files'].items():assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,p
PY
[[ ! -e $FILLER_STOPFILE && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75
cmake --build "$D/out" --target llama-server --parallel "${FILLER_THREADS:-4}"
[[ $(git -C "$S" diff --binary | sha256sum | cut -d' ' -f1) == "$PATCH" ]]
find "$D/out" -type f \( -name 'libggml*.so*' -o -name 'libllama*.so*' -o -name 'llama-server' \) -exec sha256sum {} + > "$D/artifact-sha256.txt"
grep -F '/llama-server' "$D/artifact-sha256.txt" >/dev/null
printf '{"unit":"cpu-server-build","status":"pass"}\n' >> "$D/results.jsonl"
touch "$D/complete"
