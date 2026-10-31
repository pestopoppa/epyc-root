#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/refactor-01a16fc3/ufh14-next-source-20261030
# The calendar keeper can invoke this from the container, where the approved
# Micron mount is host-only. Preserve the grant's CPU/deadline contract on entry.
if [ ! -e /mnt/micron/refactor-lanes/llama.cpp-experimental/.git ]; then
  exec sudo -n chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --init-groups /usr/bin/env \
    FILLER_CPUS="${FILLER_CPUS:-}" FILLER_THREADS="${FILLER_THREADS:-}" \
    FILLER_DEADLINE="${FILLER_DEADLINE:-}" FILLER_STOPFILE="${FILLER_STOPFILE:-}" \
    AKX8_SMOKE="${AKX8_SMOKE:-0}" AKX8_BUILD_DIR="${AKX8_BUILD_DIR:-}" \
    GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory \
    GIT_CONFIG_VALUE_0=/mnt/micron/refactor-lanes/llama.cpp-experimental \
    /bin/bash "$D/build-packet-r5/build-job.sh"
fi
S=/mnt/micron/refactor-lanes/llama.cpp-experimental
B=${AKX8_BUILD_DIR:-$S/build-cpu-akx8-r5-20261031}
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0="$S"
case "$B" in "$S"/build-*) ;; *) echo "bad build dir $B"; exit 75;; esac
EXPECTED=c72ec82f5417bb2937310326120f149b665e8400
RESULT=$D/build-packet-r5/build-result.json
[ -n "${FILLER_CPUS:-}" ] || { echo 'FILLER_CPUS missing'; exit 75; }
[ -n "${FILLER_DEADLINE:-}" ] || { echo 'FILLER_DEADLINE missing'; exit 75; }
[ -n "${FILLER_STOPFILE:-}" ] || { echo 'FILLER_STOPFILE missing'; exit 75; }
[ ! -e "$FILLER_STOPFILE" ] || exit 75
[ -d "$S/.git" ] || [ -f "$S/.git" ] || { echo 'Micron source lane absent'; exit 75; }
[ "$(git -C "$S" rev-parse HEAD)" = "$EXPECTED" ] || { echo 'source head changed'; exit 75; }
git -C "$S" merge-base --is-ancestor ffc1bac82eeca6f9099e1ccd9ba49703c460a115 HEAD || { echo 'production ancestry lost'; exit 75; }
[ -z "$(git -C "$S" status --porcelain)" ] || { echo 'source dirty'; exit 75; }
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
mkdir -p "$D/build-packet-r5/logs"
LOG="$D/build-packet-r5/logs/build-$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
exec > >(tee "$LOG") 2>&1
printf 'source=%s\ncompiler=%s\ncpus=%s\n' "$EXPECTED" "$(g++ --version | head -1)" "$FILLER_CPUS"
# Source and output disk admission precede fresh configure/compile.
python3 -B "$D/build-packet-r5/disk_gate.py" --scratch "$D" --output-estimate-gib 0.125
if [ ! -f "$B/CMakeCache.txt" ]; then
  cmake -S "$S" -B "$B" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DGGML_HIP=OFF -DGGML_CUDA=OFF -DGGML_CCACHE=OFF -DGGML_NATIVE=ON -DGGML_OPENMP=ON \
    -DBUILD_SHARED_LIBS=ON -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=ON \
    -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON \
    -DLLAMA_BUILD_MTMD=OFF -DGGML_CPU_PROF=OFF \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN'
fi
[ ! -e "$FILLER_STOPFILE" ] || exit 75
seconds=$((FILLER_DEADLINE - $(date +%s)))
if [ "$seconds" -le 120 ]; then
  printf '{"partial":true,"reason":"insufficient_window","source":"%s"}\n' "$EXPECTED" > "$RESULT"
  exit 75
fi
# Ninja can resume an interrupted build; the hard outer end belongs to filler_run13.
set +e
target=llama-server
[ "${AKX8_SMOKE:-0}" = 1 ] && target=ggml-base
timeout --signal=TERM --kill-after=10s "${seconds}s" cmake --build "$B" --target "$target" -j "$(( FILLER_THREADS > 8 ? 8 : FILLER_THREADS ))" &
timed_pid=$!
python3 -B "$D/build-packet-r5/compile_witness.py" "$timed_pid" "$D/build-packet-r5/compile-witness-${AKX8_SMOKE:-0}.jsonl" &
witness_pid=$!
wait "$timed_pid"
rc=$?
wait "$witness_pid" || true
set -e
if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ] || [ "$rc" -eq 143 ]; then
  printf '{"partial":true,"reason":"window_cutoff","source":"%s"}\n' "$EXPECTED" > "$RESULT"
  exit 75
fi
[ "$rc" -eq 0 ] || exit "$rc"
if [ "$target" = ggml-base ]; then
  test -f "$B/bin/libggml-base.so"
  printf '{"partial":false,"smoke":"same-job-entry-ggml-base-linked","source":"%s"}\n' "$EXPECTED" > "$D/build-packet-r5/smoke-job-result.json"
  exit 0
fi
LIBCPU=$B/bin/libggml-cpu.so
LIBLLAMA=$B/bin/libllama.so
SERVER=$B/bin/llama-server
[ -f "$LIBCPU" ] && [ -f "$LIBLLAMA" ] && [ -x "$SERVER" ]
strings "$LIBCPU" | rg 'GGML_FA_SPLIT_KV' >/dev/null
strings "$LIBLLAMA" | rg 'GGML_FUSED_DECODE_OFF' >/dev/null
strings "$LIBLLAMA" | rg 'GGML_FUSED_DECODE_ON' >/dev/null
LD_LIBRARY_PATH="$B/bin" ldd "$SERVER" | rg 'libggml|libllama'
python3 -B - "$SERVER" "$LIBCPU" "$LIBLLAMA" "$EXPECTED" "$RESULT" <<'PY'
import hashlib,json,os,sys,time
from pathlib import Path
server,cpu,llama,source,out=map(Path,sys.argv[1:])
files={str(p):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mtime_ns':p.stat().st_mtime_ns} for p in (server,cpu,llama)}
Path(out).write_text(json.dumps({'schema':'epyc.akxall8.build.v1','partial':False,'source':str(source),'built_at':time.time(),'build_dir':str(Path(server).parent.parent),'files':files},indent=2,sort_keys=True)+'\n')
PY
python3 -B "$D/build-packet-r5/write_build_identity.py" --source "$S" --build "$B" --head "$EXPECTED"
PYTHONPATH="$D/source-current:$D/source-current/scripts/kernel_rnd" AKX8_BUILD_DIR="$B" python3 -B "$D/build-packet-r5/rebind_after_build.py"
printf 'BUILD COMPLETE result=%s\n' "$RESULT"
