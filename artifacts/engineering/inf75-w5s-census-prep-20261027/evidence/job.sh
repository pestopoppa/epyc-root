#!/bin/bash
set -euo pipefail
KIND=cpu
BASE=/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate
JOB=$BASE/jobs/$KIND
SRC=/mnt/raid0/llm/worktrees/prep-01a16fc3-c5-candidate
EXPECT=c72ec82f5417bb2937310326120f149b665e8400
ID_EXPECT=refactor-01a16fc3-c5-$KIND-build-20261027
CHECKER=/mnt/raid0/llm/tmp/refactor-01a16fc3/compute-coordination-20261026/launch-contract-85c442b3d/dryrun_check.py
REGION=72-95
EST=8
MINWIN=900
mode=official
[ "${FILLER_PREFLIGHT:-0}" != 1 ] || mode=preflight
refuse() { printf 'REFUSED kind=%s mode=%s: %s\n' "$KIND" "$mode" "$*" >&2; exit 2; }
trap 'rc=$?; printf "ENTRY_ERROR rc=%s line=%s kind=%s mode=%s\n" "$rc" "$LINENO" "$KIND" "$mode" >&2; exit "$rc"' ERR
[ "${FILLER_ID:?}" = "$ID_EXPECT" ] || refuse 'wrong ID'
if [ "$mode" = preflight ]; then
  : "${DRYRUN_NONCE:?}"
  [ "${#DRYRUN_NONCE}" -ge 32 ] || refuse 'missing source-bound checker nonce'
  [ "${FILLER_GRANTS_DIR:?}" = "$JOB/dryrun/$DRYRUN_NONCE/grants" ] || refuse 'wrong isolated grant directory'
  GRANT=$FILLER_GRANTS_DIR/$FILLER_ID.grant
else
  GRANT=/mnt/raid0/llm/tmp/compute-flags/grants/$FILLER_ID.grant
  [ "${OFFICIAL_FILLER_GRANT:-$GRANT}" = "$GRANT" ] || refuse 'noncanonical grant'
fi
[ -r "$GRANT" ] || refuse 'grant missing'
read -r -a fields < "$GRANT"
[ "${#fields[@]}" = 3 ] || refuse 'exactly three writer fields required'
region= start= end=
for field in "${fields[@]}"; do
  case "$field" in regions=*) [ -z "$region" ] || refuse duplicate-region; region=${field#regions=};; start=*) [ -z "$start" ] || refuse duplicate-start; start=${field#start=};; end=*) [ -z "$end" ] || refuse duplicate-end; end=${field#end=};; *) refuse unknown-field;; esac
done
if [ "$mode" = preflight ]; then [ "$region" = 24-25 ] || refuse 'PF region'; else [ "$region" = "$REGION" ] || refuse 'wrong owner quarter'; fi
[[ "$start" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}Z$ ]] || refuse 'start not writer minute ISO'
[[ "$end" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}Z$ ]] || refuse 'end not writer minute ISO'
s=$(date -u -d "$start" +%s); e=$(date -u -d "$end" +%s); now=$(date -u +%s)
[ "$s" -le "$now" ] && [ "$e" -gt "$s" ] && [ "$((e-now))" -ge "$MINWIN" ] || refuse 'invalid/start/remaining window'
[ "${FILLER_END:?}" -eq "$e" ] && [ "${FILLER_DEADLINE:?}" -eq "$((e-90))" ] || refuse 'exported deadline mismatch'
[ "$now" -lt "$FILLER_DEADLINE" ] || refuse 'expired deadline'
[ "${FILLER_STOPFILE:?}" = "$JOB/STOP" ] || refuse 'STOP path mismatch'
[ ! -e "$JOB/STOP" ] || refuse STOP
if compgen -G '/mnt/raid0/llm/tmp/compute-flags/HOLD_*' >/dev/null; then refuse HOLD; fi
[ "${FILLER_NEEDGPU:-0}" = 0 ] || refuse 'builds require no GPU device/model'
affinity=$(awk '/Cpus_allowed_list/ {print $2}' /proc/self/status)
if [ "$mode" = preflight ]; then
  [ "${DRYRUN_REQUIRED_CPUS:?}" = 24,25 ] && [ "$affinity" = 24-25 ] && [ "${FILLER_CPUS:?}" = 24-25 ] || refuse 'PF inherited affinity'
else
  [ "${FILLER_CPUS:?}" = "$REGION" ] && [ "$affinity" = "$REGION" ] || refuse 'inherited quarter affinity'
  [ "${FILLER_THREADS:?}" = 24 ] || refuse 'unexpected grant thread count'
fi
free_kib=$(df -Pk "$BASE" | awk 'NR==2 {print $4}')
cutover=$(date -u -d 2026-10-28T08:10:00Z +%s)
floor=150; [ "$now" -ge "$cutover" ] || floor=50
[ "$free_kib" -ge "$(((floor+EST)*1024*1024))" ] || refuse 'insufficient free-after-est disk'
[ "$(git -C "$SRC" rev-parse HEAD)" = "$EXPECT" ] || refuse 'source HEAD changed'
[ -z "$(git -C "$SRC" status --porcelain --untracked-files=no)" ] || refuse 'tracked source dirty'
[ "$(git -C "$SRC" symbolic-ref -q HEAD || :)" = '' ] || refuse 'source must stay detached'
sha256sum -c "$JOB/source-files.sha256" || refuse 'source manifest mismatch'
[ -x /usr/bin/gcc-15 ] && [ -x /usr/bin/g++-15 ] || refuse 'CPU compilers absent'
if [ "$KIND" = hip ]; then [ -x /opt/rocm/lib/llvm/bin/clang++ ] && [ -d /opt/rocm/lib/cmake/hip ] || refuse 'ROCm toolchain absent'; fi
printf 'VALIDATED mode=%s id=%s region=%s affinity=%s source=%s estimated_output_GiB=%s floor_GiB=%s scratch_root=%s\n' "$mode" "$FILLER_ID" "$region" "$affinity" "$EXPECT" "$EST" "$floor" "$BASE"
printf 'RLIMITS before first side effect:\n'; ulimit -a
if [ "$mode" = preflight ]; then
  python3 -B "$CHECKER" boundary --effect validated-c5-build-before-mkdir --job "$JOB/job.sh"
  exit 0
fi
[ "${DRY_RUN:-0}" != 1 ] || refuse 'DRY_RUN outside official checker context'
# First side effect below. All previous operations are validation/read-only.
B=$BASE/build$KIND
mkdir -p "$B"
if [ "$KIND" = hip ]; then export LD_LIBRARY_PATH="$B/bin:/opt/rocm/lib"; else export LD_LIBRARY_PATH="$B/bin"; fi
export OMP_NUM_THREADS=$FILLER_THREADS
unset GGML_FA_VKQ_F32 GGML_FA_VKQ_F16
config=(cmake -S "$SRC" -B "$B" -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON)
if [ "$KIND" = cpu ]; then
 config+=(-DGGML_HIP=OFF -DGGML_OPENMP=ON -DCMAKE_C_COMPILER=/usr/bin/gcc-15 -DCMAKE_CXX_COMPILER=/usr/bin/g++-15 -DLLAMA_CURL=OFF '-DCMAKE_INSTALL_RPATH=$ORIGIN')
else
 config+=(-DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a -DCMAKE_HIP_COMPILER=/opt/rocm/lib/llvm/bin/clang++ -DGGML_HIP_ROCWMMA_FATTN=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN;/opt/rocm/lib')
fi
printf '%q ' "${config[@]}" > "$JOB/CONFIGURE.command"; printf '\n' >> "$JOB/CONFIGURE.command"
check_continue() { [ ! -e "$JOB/STOP" ] || refuse STOP; [ "$(date -u +%s)" -lt "$FILLER_DEADLINE" ] || refuse deadline; if compgen -G '/mnt/raid0/llm/tmp/compute-flags/HOLD_*' >/dev/null; then refuse HOLD; fi; }
check_continue
"${config[@]}" > "$JOB/CONFIGURE.log" 2>&1
check_continue
printf 'source=%s cpus=%s jobs=%s start=%s\n' "$EXPECT" "$FILLER_CPUS" "$FILLER_THREADS" "$(date -u +%FT%TZ)" > "$JOB/BUILD.log"
cmake --build "$B" --parallel "$FILLER_THREADS" >> "$JOB/BUILD.log" 2>&1
check_continue
cp "$B/CMakeCache.txt" "$JOB/CMakeCache.full.txt"
find "$B/CMakeFiles" -name '*Compiler.cmake' -type f -exec cat {} + > "$JOB/COMPILER-ID.txt"
find "$B/bin" -maxdepth 1 -type f -print0 | sort -z | xargs -0 sha256sum > "$JOB/ELF.sha256"
commit_epoch=$(git -C "$SRC" show -s --format=%ct HEAD)
find "$B/bin" -maxdepth 1 -type f -printf '%T@ %p\n' > "$JOB/BINARY-MTIMES.txt"
[ "$(stat -c %Y "$B/bin/llama-server")" -gt "$commit_epoch" ] || refuse 'binary predates source commit'
CPU_LIB=$B/bin/libggml-cpu.so
strings "$CPU_LIB" | sed -n '/GGML_FA_VKQ_F32/p' > "$JOB/strings-GGML_FA_VKQ_F32.txt"
[ -s "$JOB/strings-GGML_FA_VKQ_F32.txt" ] || refuse 'FA F32 runtime knob missing from CPU ELF'
if [ "$KIND" = hip ]; then
  strings "$B/bin/libggml-hip.so" | sed -n '/rocwmma\|ROCWMMA\|GGML_HIP_ROCWMMA\|flash_attn_ext_wmma_f16/p' > "$JOB/strings-rocWMMA.txt"
  [ -s "$JOB/strings-rocWMMA.txt" ] || refuse 'rocWMMA symbols absent'
  rg -n 'GGML_HIP_ROCWMMA_FATTN' "$B/compile_commands.json" > "$JOB/rocWMMA-compile-definition.txt"
fi
/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/controlproofs/verify_ggml_linkage.sh "$B/bin/llama-server" > "$JOB/LINKAGE.txt" 2>&1
printf 'BUILD_COMPLETE source=%s kind=%s end=%s no-model-runs=true\n' "$EXPECT" "$KIND" "$(date -u +%FT%TZ)" > "$JOB/BUILD_COMPLETE"
