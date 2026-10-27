#!/bin/bash
set -euo pipefail
[ "${FILLER_PREFLIGHT:-0}" = 1 ] || exit 70
[ "${1:-}" = run ] || exit 70
seen_cpu=0; seen_sep=0
while (($#)); do
  case "$1" in
    --cpu-list) [ "${2:-}" = 72-73 ] || exit 70; seen_cpu=1; shift 2;;
    --gpu-quiet) exit 70;;
    --) seen_sep=1; shift; break;;
    *) shift;;
  esac
done
((seen_cpu && seen_sep && $#)) || exit 70
p=$PPID; found=0
while ((p>1)); do
  [ -r "/proc/$p/status" ] || exit 70
  cmd=$(tr '\0' ' ' < "/proc/$p/cmdline")
  if [[ "$cmd" == *"region_lock_cli run --cpu-list 72,73 --role build"* ]]; then
    global=0; build=0
    for fd in /proc/$p/fd/*; do
      target=$(readlink "$fd") || continue
      case "$target" in
        /mnt/raid0/llm/tmp/cpu_region.GLOBAL.q3.lock)
          grep -Eq '^lock:.*FLOCK.*WRITE' "/proc/$p/fdinfo/${fd##*/}" && global=1;;
        /mnt/raid0/llm/tmp/cpu_region.build.q3.lock)
          grep -Eq '^lock:.*FLOCK.*WRITE' "/proc/$p/fdinfo/${fd##*/}" && build=1;;
      esac
    done
    ((global && build)) && found=1
  fi
  p=$(awk '/^PPid:/{print $2}' "/proc/$p/status")
done
((found)) || exit 70
exec "$@"
