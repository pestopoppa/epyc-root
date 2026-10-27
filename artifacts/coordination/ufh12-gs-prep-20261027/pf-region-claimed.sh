#!/bin/bash
set -euo pipefail
[[ ${FILLER_PREFLIGHT:-0} == 1 ]] || { printf 'PF_REFUSED:preflight_only\n' >&2; exit 70; }
[[ ${1:-} == run && ${2:-} == --cpu-list && ${3:-} == 48,49 ]] || { printf 'PF_REFUSED:unexpected_inner_region_shape\n' >&2; exit 70; }
seen_separator=0
while (($#)); do
 if [[ $1 == -- ]]; then seen_separator=1; shift; break; fi
 shift
done
((seen_separator)) && (($#)) || { printf 'PF_REFUSED:missing_inner_command\n' >&2; exit 70; }
p=$PPID
found=0
while ((p>1)); do
 [[ -r /proc/$p/status ]] || exit 70
 cmd=$(tr '\0' ' ' < "/proc/$p/cmdline")
 if [[ $cmd == *'region_lock_cli run --regions q2 --role build'* ]]; then
  global=0; build=0
  for fd in /proc/$p/fd/*; do
   target=$(readlink "$fd") || continue
   case "$target" in
    /mnt/raid0/llm/tmp/cpu_region.GLOBAL.q2.lock) grep -Eq '^lock:.*FLOCK.*WRITE' "/proc/$p/fdinfo/${fd##*/}" && global=1;;
    /mnt/raid0/llm/tmp/cpu_region.build.q2.lock) grep -Eq '^lock:.*FLOCK.*WRITE' "/proc/$p/fdinfo/${fd##*/}" && build=1;;
   esac
  done
  ((global && build)) && found=1
 fi
 p=$(awk '/^PPid:/ {print $2}' "/proc/$p/status")
 [[ $p =~ ^[0-9]+$ ]] || exit 70
done
((found)) || { printf 'PF_REFUSED:outer_official_q2_claim_missing\n' >&2; exit 70; }
exec "$@"
