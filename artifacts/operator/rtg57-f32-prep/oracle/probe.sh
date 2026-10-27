#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-rtg57-f32-completion/oracle
B=/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/buildcpu/bin
O="$D/out"
[ ! -e "$O" ] || { echo existing-output >&2; exit 70; }
mkdir "$O"
sha256sum -c "$D/source.sha256" "$D/binary.sha256" > "$O/instrument-check.txt"
sha256sum -c /mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/jobs/cpu/ELF.sha256 > "$O/c5-elf-check.txt"
strings "$B/libggml-cpu.so.0.16.0" | grep -Fx GGML_FA_VKQ_F32 > "$O/compiled-knob.txt"
stat -c '%y %n' "$D/test-fa-rowexact-c5" "$B/libggml-cpu.so.0.16.0" > "$O/mtimes.txt"
export LD_LIBRARY_PATH="$B" GGML_FA_VKQ_F32=1 GGML_FA_SPLIT_KV=0 FA_ROWEXACT_THREADS=1 FA_ROWEXACT_TYPES=f16
unset GGML_FA_VKQ_F16 GGML_IQK
bash /mnt/raid0/llm/worktrees/f8-kvu121b-research-95550d294/scripts/utils/verify_ggml_linkage.sh "$D/test-fa-rowexact-c5" "$B" > "$O/linkage.txt"
"$D/test-fa-rowexact-c5" --masks causal 8192 > "$O/positive.log" 2>&1 &
pid=$!
found=0
for i in $(seq 1 200); do
  if [ -r "/proc/$pid/maps" ] && grep -F "$B/libggml-cpu.so.0.16.0" "/proc/$pid/maps" > "$O/loaded-map.txt"; then
    tr '\0' '\n' < "/proc/$pid/environ" | grep -E '^(GGML_FA_VKQ_F32|GGML_FA_SPLIT_KV|FA_ROWEXACT_THREADS|FA_ROWEXACT_TYPES)=' > "$O/environ.txt"
    found=1; break
  fi
  ps -p "$pid" >/dev/null || break
  sleep .02
done
if wait "$pid"; then rc=0; else rc=$?; fi
printf '%s\n' "$rc" > "$O/positive.rc"
[ "$found" = 1 ] && [ "$rc" = 0 ]
grep -Fx 'GGML_FA_VKQ_F32=1' "$O/environ.txt" >/dev/null
grep -Fx 'GGML_FA_SPLIT_KV=0' "$O/environ.txt" >/dev/null
grep -E '^ORACLE_1ROW .*finite=1 mutation=0' "$O/positive.log" >/dev/null
grep -E '^RESULT .*type=f16 .*verdict=PASS' "$O/positive.log" >/dev/null
if "$D/test-fa-rowexact-c5" --mutate-output --masks causal 8192 > "$O/mutation.log" 2>&1; then rc=0; else rc=$?; fi
printf '%s\n' "$rc" > "$O/mutation.rc"
[ "$rc" = 1 ]
grep -E '^ORACLE_1ROW .*finite=1 mutation=1' "$O/mutation.log" >/dev/null
grep -E '^RESULT .*type=f16 .*verdict=FAIL' "$O/mutation.log" >/dev/null
/usr/bin/python3 -B -I "$D/write-receipt.py"
