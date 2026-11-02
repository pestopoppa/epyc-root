#!/bin/bash
# Invoked only inside filler_run15's granted CPU region lock.
set -euo pipefail
readonly commit=7cdd7c97bed538a85c3b75331b6cdb369e5b2adc
readonly helper_dir=$(dirname "$(realpath "$0")")
readonly scratch=/mnt/raid0/llm/tmp/inf75-quantizer-7cdd7c97-20261102
: "${FILLER_DEADLINE:?}" "${FILLER_STOPFILE:?}" "${FILLER_THREADS:?}" "${FILLER_ID:?}"
[[ $FILLER_ID == inf75-quantizer-7cdd7c97-20261102 && $FILLER_DEADLINE =~ ^[0-9]+$ && $FILLER_THREADS =~ ^[1-9][0-9]*$ ]] || exit 64
check_window() { [[ ! -e "$FILLER_STOPFILE" && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75; }
check_window
mkdir -p "$scratch/runs"
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
  result=${FILLER_DRYRUN_RESULT_PATH:?dry run requires isolated native result}
  [[ "$result" == "${FILLER_DRYRUN_DIR:?}"/native-attempts/* ]] || exit 64
else
  result=$scratch/RESULT.json
fi
[[ ! -e "$result" ]] || exit 65
# Preparation is deliberately outside the grant. Never regenerate/extract here.
[[ ${FILLER_SMOKE:-0} != 1 || ${FILLER_DRYRUN:-0} == 1 ]] || exit 64
run=$(python3 - "$scratch" "${FILLER_SMOKE:-0}" <<'PYRUN'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1])
p=json.loads((root/('PREPARED-SMOKE.json' if sys.argv[2] == '1' else 'PREPARED.json')).read_text())
run=pathlib.Path(p['run_dir'])
if run.resolve(strict=True) != run or run.parent != (root/'runs').resolve(strict=True):
 raise SystemExit('invalid prepared run')
print(run)
PYRUN
)
[[ ! -e "$run/build/CMakeCache.txt" ]] || exit 65
python3 "$helper_dir/check_source.py" "$run"
cc=$(realpath -e "$(command -v gcc)")
cxx=$(realpath -e "$(command -v g++)")
[[ $($cc -dumpfullversion) == 15.2.0 && $($cxx -dumpfullversion) == 15.2.0 ]] || { echo 'historical GCC 15.2.0 required' >&2; exit 65; }
sha256sum "$cc" "$cxx" > "$run/output/compiler.sha256"
"$cc" --version > "$run/output/gcc-version.txt"
"$cxx" --version > "$run/output/gxx-version.txt"
cmake --version > "$run/output/cmake-version.txt"
check_window
cmake -S "$run/src" -B "$run/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER="$cc" -DCMAKE_CXX_COMPILER="$cxx" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DBUILD_SHARED_LIBS=ON -DGGML_HIP=OFF -DGGML_BLAS=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TOOLS=ON > "$run/output/configure.log" 2>&1
check_window
if [[ ${FILLER_SMOKE:-0} == 1 ]]; then
  python3 "$helper_dir/smoke_unit.py" "$result" "$run" "$commit"
  exit 0
fi
cmake --build "$run/build" --target llama-quantize --parallel "$FILLER_THREADS" > "$run/output/build.log" 2>&1
check_window
bin="$run/build/bin/llama-quantize"
[[ -x $bin ]] || exit 65
export LD_LIBRARY_PATH="$run/build/bin"
/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$bin" "$run/build" > "$run/output/linkage.log" 2>&1
check_window
# Refuse a receipt if either compiler changed while this run was building.
python3 "$helper_dir/check_source.py" "$run"
sha256sum --check "$run/output/compiler.sha256" > /dev/null
python3 - "$result" "$run" "$commit" "$cc" "$cxx" <<'PY'
import hashlib,json,os,pathlib,sys,tempfile
out=pathlib.Path(sys.argv[1]); run=pathlib.Path(sys.argv[2]); commit,cc,cxx=sys.argv[3:]
files=[run/'source.tar',run/'tree-manifest.json',run/'source-provenance.json',run/'output/compiler.sha256',run/'output/gcc-version.txt',run/'output/gxx-version.txt',run/'output/cmake-version.txt',run/'output/configure.log',run/'output/build.log',run/'output/linkage.log',run/'build/CMakeCache.txt',run/'build/compile_commands.json',run/'build/bin/llama-quantize']
files += sorted(p for p in (run/'build/bin').glob('*.so*') if p.is_file() and not p.is_symlink())
provenance=json.loads((run/'source-provenance.json').read_text())
def digest(p):
 if p == run/'source.tar': return provenance['archive_sha256']
 if p == run/'tree-manifest.json': return provenance['manifest_sha256']
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
 return h.hexdigest()
if not any('ggml' in p.name for p in files): raise SystemExit('no ggml shared objects')
record={'schema':'epyc.inf75.quantizer_build.v1','status':'built','source_commit':commit,'run_dir':str(run),'cc':cc,'cxx':cxx,'threads':int(os.environ['FILLER_THREADS']),'files':{str(p):digest(p) for p in files},'linkage_rc':0,'scope':'build only; no model quantization or P1c replay'}
out.parent.mkdir(parents=True,exist_ok=True)
fd,tmp=tempfile.mkstemp(prefix='.result-',dir=out.parent)
try:
 with os.fdopen(fd,'w') as f: json.dump(record,f,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,out)
finally:
 if os.path.exists(tmp): os.unlink(tmp)
PY
