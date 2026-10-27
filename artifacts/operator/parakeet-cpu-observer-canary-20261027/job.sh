#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-parakeet-cpu-v2
C=/mnt/raid0/llm/tmp/refactor-01a16fc3/compute-coordination-20261026/launch-contract-85c442b3d
mode=${1:?}; case "$mode" in canary|full) ;; *) exit 2;; esac
ID=codex-ni-parakeet-observed-$mode-20261027
refuse() { printf 'REFUSED %s\n' "$*" >&2; exit 2; }
[ "${FILLER_ID:?}" = "$ID" ] || refuse id
if [ "${FILLER_PREFLIGHT:-0}" = 1 ]; then
 : "${DRYRUN_NONCE:?}"; [ "${#DRYRUN_NONCE}" -ge 32 ] || refuse nonce
 [ "${FILLER_GRANTS_DIR:?}" = "$D/dryrun/$DRYRUN_NONCE/grants" ] || refuse grantdir
 grant=$FILLER_GRANTS_DIR/$ID.grant; affinity=48-49
else grant=/mnt/raid0/llm/tmp/compute-flags/grants/$ID.grant; [ "${OFFICIAL_FILLER_GRANT:-$grant}" = "$grant" ] || refuse grantpath; affinity=24-25; fi
[ -r "$grant" ] || refuse grant
read -r -a fields < "$grant"; [ "${#fields[@]}" = 3 ] || refuse grantfields
region= start= end=
for field in "${fields[@]}"; do case "$field" in regions=*) [ -z "$region" ] || refuse duplicate; region=${field#regions=};; start=*) [ -z "$start" ] || refuse duplicate; start=${field#start=};; end=*) [ -z "$end" ] || refuse duplicate; end=${field#end=};; *) refuse field;; esac; done
[ "$region" = "$affinity" ] || refuse region
[[ "$start" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}Z$ && "$end" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}Z$ ]] || refuse granttime
s=$(date -u -d "$start" +%s); e=$(date -u -d "$end" +%s); now=$(date -u +%s)
min=600; [ "$mode" = canary ] || min=3600
[ "$s" -le "$now" ] && [ "$e" -gt "$s" ] && [ "$((e-now))" -ge "$min" ] || refuse window
[ "${FILLER_END:?}" -eq "$e" ] && [ "${FILLER_DEADLINE:?}" -eq "$((e-90))" ] || refuse deadline
[ "${FILLER_STOPFILE:?}" = "$D/STOP-$mode" ] && [ ! -e "$D/STOP-$mode" ] || refuse stop
if compgen -G '/mnt/raid0/llm/tmp/compute-flags/HOLD_*' >/dev/null; then refuse hold; fi
[ "${FILLER_NEEDGPU:-0}" = 0 ] || refuse gpu
[ "${FILLER_CPUS:?}" = "$affinity" ] && [ "$(awk '/Cpus_allowed_list/ {print $2}' /proc/self/status)" = "$affinity" ] || refuse affinity
free=$(df -Pk "$D" | awk 'NR==2 {print $4}'); [ "$free" -ge "$((152*1024*1024))" ] || refuse disk
sha256sum -c "$D/source-files.sha256" || refuse source
if [ "${FILLER_PREFLIGHT:-0}" = 1 ]; then python3 -B "$C/dryrun_check.py" boundary --effect validated-parakeet-observed-before-inference --job "$D/job.sh"; exit 0; fi
[ "${DRY_RUN:-0}" != 1 ] || refuse dryrun
exec 6>"$D/single-writer.lock"; flock -n 6 || refuse running
[ ! -e "$D/evidence/$mode/COMPLETE.json" ] || refuse already-complete
if [ "$mode" = full ]; then python3 -B "$D/verify_canary.py" "$D/evidence/canary" || refuse canary; fi
export REFERENCE_GRANT="$grant" REFERENCE_SOURCE_MANIFEST="$D/source-files.sha256"
mkdir -p "$D/evidence/attempts"; attempt="$D/evidence/attempts/$mode-$(date -u +%Y%m%dT%H%M%S)-$$"
python3 -B "$D/cpu_runner.py" "$attempt" "$mode"
ln -s "$attempt" "$D/evidence/$mode"
