#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor
S=/mnt/raid0/llm/tmp/kvu/kvu19a2-source-pair-20261102/source.tar
P=/mnt/raid0/llm/tmp/kvu/kvu19a2-source-pair-20261102/candidate.patch
H=/mnt/raid0/llm/tmp/stack-change-apply-20261117T193233Z/epyc-inference-research/scripts/benchmark/native/kvu19a2_fa_harness.cpp
cd "$D"
printf '%s  %s\n' 87e3cdc13b1859a31dfd3ced43c596e6b9653e2194b1ebd0d5eb6772593c04c2 "$S" 4147d2b65bbb416fdee1bf004d5447238933524bf3c087a69dcf6bbeca73b235 "$P" b9f352a91ea975c682cbe78c2f4dbf9035c6a40e309b84035bfbdaf49b420091 "$H" | sha256sum -c -
mkdir -p build
for arm in base candidate; do test "$(git -C "source/$arm" rev-parse HEAD)" = a0d0ae238e714aaab04e973ef4b5a4b7c9917744; done
test -z "$(git -C source/base status --porcelain)"
test "$(git -C source/candidate status --porcelain)" = ' M ggml/src/ggml-cuda/fattn-tile.cuh' 
printf '%s  %s\n' 878a3640f685e68c6c3d3102c331c43054bfb0bce81f68c3224ad271b8d9d844 source/base/ggml/src/ggml-cuda/fattn-tile.cuh 3f79373e68603691630c7dc38703411456cdf5fa12348d07812323568cdb1e82 source/candidate/ggml/src/ggml-cuda/fattn-tile.cuh | sha256sum -c -
for arm in base candidate; do
 cmake -S "$D/source/$arm" -B "$D/build/$arm" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TOOLS=OFF > "$D/$arm-configure.log" 2>&1
 cmake --build "$D/build/$arm" --target test-backend-ops --parallel 4 > "$D/$arm-build.log" 2>&1
done
mkdir -p "$D/build/harness"
g++ -std=c++17 -O2 "$H" -I"$D/source/base/ggml/include" -L"$D/build/base/bin" -lggml -lggml-base -lggml-cpu -o "$D/build/harness/fa_harness" > "$D/harness-build.log" 2>&1
python3 - <<'PY'
from pathlib import Path
import hashlib,json,subprocess,datetime,os
D=Path('/mnt/raid0/llm/tmp/vidya-belief-substrate/kvu19-successor')
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[D/'build/harness/fa_harness']+[p for a in ('base','candidate') for p in sorted((D/'build'/a/'bin').glob('libggml*.so.0.16.0'))]
assert len(paths)==9,paths
r={'schema':'kvu19a2.successor-build.v1','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'new prospective build; no equivalence to original build or GPU measurement','source_commit':'a0d0ae238e714aaab04e973ef4b5a4b7c9917744','source_archive_content_equals_git_tree':True,'source_sha256':'87e3cdc13b1859a31dfd3ced43c596e6b9653e2194b1ebd0d5eb6772593c04c2','patch_sha256':'4147d2b65bbb416fdee1bf004d5447238933524bf3c087a69dcf6bbeca73b235','harness_source_sha256':'b9f352a91ea975c682cbe78c2f4dbf9035c6a40e309b84035bfbdaf49b420091','actual_affinity':sorted(os.sched_getaffinity(0)),'claim_role':'build','cmake_version':subprocess.check_output(['cmake','--version'],text=True).splitlines()[0],'compiler_version':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],'artifacts':{str(p):digest(p) for p in paths},'logs':{str(p):digest(p) for p in D.glob('*-build.log')}}
(D/'build-receipt.json').write_text(json.dumps(r,indent=2)+'\n')
PY
