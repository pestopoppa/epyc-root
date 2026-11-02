#!/bin/bash
# Invoked only inside filler_run15's granted CPU region lock.
set -euo pipefail
readonly commit=7cdd7c97bed538a85c3b75331b6cdb369e5b2adc
readonly source_repo=/mnt/raid0/llm/tmp/inf70/retest1wt
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
run=$(mktemp -d "$scratch/runs/build-XXXXXXXX")
mkdir "$run/src" "$run/build"
git -C "$source_repo" cat-file -e "$commit^{commit}"
git -C "$source_repo" archive --format=tar "$commit" > "$run/source.tar"
sha256sum "$run/source.tar" > "$run/source.tar.sha256"
tar -xf "$run/source.tar" -C "$run/src"
cc=$(realpath -e "$(command -v gcc)")
cxx=$(realpath -e "$(command -v g++)")
[[ $($cc -dumpfullversion) == 15.2.0 && $($cxx -dumpfullversion) == 15.2.0 ]] || { echo 'historical GCC 15.2.0 required' >&2; exit 65; }
sha256sum "$cc" "$cxx" > "$run/compiler.sha256"
"$cc" --version > "$run/gcc-version.txt"
"$cxx" --version > "$run/gxx-version.txt"
cmake --version > "$run/cmake-version.txt"
check_window
cmake -S "$run/src" -B "$run/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER="$cc" -DCMAKE_CXX_COMPILER="$cxx" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DBUILD_SHARED_LIBS=ON -DGGML_HIP=OFF -DGGML_BLAS=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TOOLS=ON > "$run/configure.log" 2>&1
check_window
cmake --build "$run/build" --target llama-quantize --parallel "$FILLER_THREADS" > "$run/build.log" 2>&1
check_window
bin="$run/build/bin/llama-quantize"
[[ -x $bin ]] || exit 65
export LD_LIBRARY_PATH="$run/build/bin"
/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$bin" "$run/build" > "$run/linkage.log" 2>&1
check_window
# Refuse a receipt if either compiler changed while this run was building.
sha256sum --check "$run/compiler.sha256" > /dev/null
python3 - "$result" "$run" "$commit" "$cc" "$cxx" <<'PY'
import hashlib,json,os,pathlib,sys,tempfile
out=pathlib.Path(sys.argv[1]); run=pathlib.Path(sys.argv[2]); commit,cc,cxx=sys.argv[3:]
files=[run/'source.tar',run/'compiler.sha256',run/'gcc-version.txt',run/'gxx-version.txt',run/'cmake-version.txt',run/'configure.log',run/'build.log',run/'linkage.log',run/'build/CMakeCache.txt',run/'build/compile_commands.json',run/'build/bin/llama-quantize']
files += sorted(p for p in (run/'build/bin').glob('*.so*') if p.is_file() and not p.is_symlink())
def digest(p):
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
