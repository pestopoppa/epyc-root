#!/bin/bash
set -uo pipefail
arm=$1
S=/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030
P=/mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/prep
if [[ "$arm" == paddle ]]; then W="$S/paddle-watch"; else W="$S/watch"; fi
exec 9>"$W/watcher.lock"
flock -n 9 || exit 1
while :; do
 while read -r n epoch; do
  [[ "$n" =~ ^[0-9]+$ && "$epoch" =~ ^[0-9a-f]{64}$ ]] || continue
  for pair in 122,123 26,27 50,51 74,75 2,3; do
   if /usr/bin/python3 -c 'import sys;sys.path.insert(0,sys.argv[1]);import prep_admission;prep_admission.live(tuple(map(int,sys.argv[2].split(","))))' "$P" "$pair" 2>/dev/null; then
    flock -n -E 99 /mnt/raid0/llm/tmp/compute-flags/prep-locks/26-27.lock /bin/bash "$S/epoch_run.sh" "$arm" "$n" "$epoch" "$pair"
    rc=$?
    if [[ $rc -ne 99 ]]; then printf '%s arm=%s shard=%s epoch=%s rc=%s\n' "$(date -u +%FT%TZ)" "$arm" "$n" "$epoch" "$rc"; break; fi
   fi
  done
 done < <(/usr/bin/python3 "$S/epoch_watch.py" list "$arm")
 sleep 30
done
