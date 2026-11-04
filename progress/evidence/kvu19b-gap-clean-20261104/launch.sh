#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kvu19b-gap-clean-20261104
ID=handoff-kvu19b-gap-clean-20261104
smoke_cpus() {
 /usr/bin/python3 -c 'import os,re
text=os.environ.get("FILLER_CPUS",os.environ.get("WS58_REGIONS",""))
allowed=set()
for token in text.split(","):
 if token=="mi210_0":continue
 if not re.fullmatch(r"[0-9]+(?:-[0-9]+)?",token):raise SystemExit(64)
 lo,_,hi=token.partition("-");lo=int(lo);hi=int(hi or lo)
 if hi<lo or hi>191:raise SystemExit(64)
 allowed.update(range(lo,hi+1))
cpus=sorted(allowed & os.sched_getaffinity(0))[:4]
if len(cpus)!=4:raise SystemExit(64)
print(",".join(map(str,cpus)))'
}
case ${1:-} in
 --smoke-cpus) smoke_cpus ;;
 --job)
 if [ "${FILLER_DRYRUN:-0}" = 1 ]; then
  cpus=$(smoke_cpus)
  exec /usr/bin/taskset -c "$cpus" /bin/bash "$D/launch.sh" --job-pinned
 fi
 exec /bin/bash "$D/launch.sh" --job-pinned ;;
 --job-pinned)
 cd "$D"
 [ "$(sha256sum runtime.sha256 | cut -d' ' -f1)" = 936e6b36e2d1c4162d457b5ed390c0b7e48f3d04d8c268dd98a3390f20a09dd4 ] || exit 65
 sha256sum -c --quiet runtime.sha256
 exec /usr/bin/python3 -B "$D/producer.py" ;;
 --engine)
 export FILLER_RL="$D/region-lock"
 mode=full
 result="$D/RESULT.json"
 host_cpus=0-191
 if [ "${FILLER_DRYRUN:-0}" = 1 ]; then
  mode=qualification
  result="${FILLER_DRYRUN_RESULT_PATH:?}"
  host_cpus="$(printf '%s' "${WS58_REGIONS:?}" | tr ',' '\n' | sed -n '/^[0-9][0-9,-]*$/p' | paste -sd, -)"
  [ -n "$host_cpus" ] || exit 64
 fi
 exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class gpu --role bench --gpu-quiet exclusive --claim-cpus "$host_cpus" --gpu-threads "$host_cpus" --min-window 1200 --stop "$D/STOP" --workdir "$D" --cmd "bash $D/launch.sh --job" --complete-cmd "python3 -B $D/complete.py $result $mode" ;;
 '')
 exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env \
 "FILLER_DRYRUN=${FILLER_DRYRUN:-0}" "FILLER_DRYRUN_DIR=${FILLER_DRYRUN_DIR:-}" "FILLER_DRYRUN_RESULT_PATH=${FILLER_DRYRUN_RESULT_PATH:-}" "FILLER_STATE_DIR=${FILLER_STATE_DIR:-}" "FILLER_FLAGS_DIR=${FILLER_FLAGS_DIR:-}" "FILLER_GRANTS_DIR=${FILLER_GRANTS_DIR:-/mnt/raid0/llm/tmp/compute-flags/grants}" "FILLER_SMOKE=${FILLER_SMOKE:-0}" "WS58_REGIONS=${WS58_REGIONS:-}" /bin/bash "$D/launch.sh" --engine ;;
 *) exit 64 ;;
esac
