#!/bin/bash
# INF-70 HARNESS-1: co-residency sampler. ONE implementation, shared by the cold and hot arm
# scripts, so the two cannot drift the way champion1 -> champion3 did.
#
# Every foreign process burning CPU is classified by tools/cpuoverlap.py against the bench
# region using the REAL /sys SMT topology. The predicate it replaces ("any cpu id <= 95")
# labelled cpus 184-191 "disjoint-from-0-95" when they are the SMT siblings of bench cores
# 88-95 -- a lane CHAMPION-3 measured a real ~7% effect from.
#
#   usage: cores_sampler.sh <self_pid> <outfile> [bench_cpu_list=0-95] [interval=20]
set -u
ME=$1; OUTF=$2; BENCH=${3:-0-95}; IVAL=${4:-20}
H=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
while :; do
  { echo "=== $(date -u +%T) load=$(cut -d' ' -f1-3 /proc/loadavg)"
    ps -eo pid,pcpu,comm --sort=-pcpu --no-headers | head -12 | while read -r p c cm; do
        [ "$p" = "$ME" ] && { echo "  SELF pid=$p cpu=$c $cm"; continue; }
        awk "BEGIN{exit !($c>5)}" || continue
        ex=$(readlink /proc/$p/exe 2>/dev/null || echo "?")
        cal=$(awk '/Cpus_allowed_list/{print $2}' /proc/$p/status 2>/dev/null || echo "?")
        [ "$cal" = "?" ] && { echo "  FOREIGN pid=$p cpu=$c comm=$cm exe=$ex cpus_allowed=? GONE"; continue; }
        ov=$(python3 "$H/tools/cpuoverlap.py" "$cal" "$BENCH" 2>/dev/null || echo "CLASSIFY-ERROR")
        echo "  FOREIGN pid=$p cpu=$c comm=$cm exe=$ex cpus_allowed=$cal $ov"
      done
  } >> "$OUTF"
  sleep "$IVAL"
done
