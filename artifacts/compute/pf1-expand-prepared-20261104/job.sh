#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/brf-exp04-r7-placement-20261104
phase=${1:?phase}; case "$phase" in initial|holdout) ;; *) exit 64;; esac
expected="brf-exp04-pf1-full-${phase}-20261104-r7"
[[ ${FILLER_ID:?} == "$expected" ]] || { echo "REFUSED: wrong row identity" >&2; exit 2; }
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
  [[ -n ${FILLER_CPUS:-} && ${FILLER_NEEDGPU:-0} == 1 ]] || { echo "REFUSED: native smoke needs its allocated CPU+GPU grant" >&2; exit 2; }
else
  [[ ${FILLER_CPUS:-} == 0-95 ]] || { echo "REFUSED: full 0-95 CPU claim required" >&2; exit 2; }
fi
[[ ${FILLER_STOPFILE:?} == "$D/STOP-$phase" && ! -e "$FILLER_STOPFILE" ]] || { echo "REFUSED: invalid STOP" >&2; exit 2; }
sha256sum --check "$D/source-files.sha256" >/dev/null
[[ $(df -Pk "$D" | awk 'NR==2 {print $4}') -ge $(((150+5)*1024*1024)) ]] || { echo "REFUSED: require 150 GiB free after 5 GiB output allowance" >&2; exit 2; }
export PYTHONDONTWRITEBYTECODE=1 TMPDIR="$D/tmp"
mkdir -p "$TMPDIR"
exec /usr/bin/python3 -B "$D/driver.py" "$phase"
