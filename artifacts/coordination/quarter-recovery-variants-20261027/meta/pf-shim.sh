#!/bin/bash
set -euo pipefail
[[ ${FILLER_PREFLIGHT:-0} == 1 && ${DRYRUN_NONCE:-} =~ ^[a-f0-9]{48}$ ]]
[[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == 0-1 ]]
p=$PPID; found=0
while ((p>1)); do
 [[ -r /proc/$p/status ]] || exit 70
 cmd=$(tr '\0' ' ' < "/proc/$p/cmdline")
 if [[ $cmd == *'region_lock_cli run --cpu-list 0,1 --role build'* ]]; then
  global=0; build=0
  for fd in /proc/$p/fd/*; do
   target=$(readlink "$fd") || continue
   case "$target" in
    /mnt/raid0/llm/tmp/cpu_region.GLOBAL.q0.lock) grep -Eq '^lock:.*FLOCK.*WRITE' "/proc/$p/fdinfo/${fd##*/}" && global=1;;
    /mnt/raid0/llm/tmp/cpu_region.build.q0.lock) grep -Eq '^lock:.*FLOCK.*WRITE' "/proc/$p/fdinfo/${fd##*/}" && build=1;;
   esac
  done
  ((global && build)) && found=1
 fi
 p=$(awk '/^PPid:/ {print $2}' "/proc/$p/status")
done
((found)) || exit 70
while (($#)) && [[ $1 != -- ]]; do shift; done
[[ ${1:-} == -- ]] || exit 70
shift
exec "$@"
