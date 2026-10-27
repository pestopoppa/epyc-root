#!/bin/bash
set -euo pipefail
# Draft: must be used inside the region-lock/filler wrapper. No standalone launch.
root=/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase
flags=/mnt/raid0/llm/tmp/compute-flags
fail() { printf 'SPLIT_ADMISSION_REFUSED:%s\n' "$1" >&2; exit 6; }
case ${FILLER_ID:-} in
  codex-ni-gnx-split-parse-20261027) real=0-23; threads=24; stage=prepare19 ;;
  codex-ni-gnx-split-resolve-20261027) real=0,1; threads=2; stage=resolve ;;
  *) fail id ;;
esac
[[ ${FILLER_STOPFILE:-} == "$root/STOP" && ! -e $root/STOP && ! -L $root/STOP ]] || fail stop
sha256sum -c "$root/PACKET.sha256" >/dev/null || fail packet_integrity
[[ ${FILLER_END:-} =~ ^[0-9]+$ && ${FILLER_DEADLINE:-} =~ ^[0-9]+$ ]] || fail deadline
(( FILLER_DEADLINE > EPOCHSECONDS && FILLER_DEADLINE < FILLER_END && FILLER_END - EPOCHSECONDS > 300 )) || fail window
if [[ ${SPLIT_RUNNING:-0} != 1 ]]; then
  (( FILLER_END - EPOCHSECONDS >= 3300 )) || fail initial_window
fi
grant="${FILLER_GRANTS_DIR:-$flags/grants}/$FILLER_ID.grant"
[[ -f $grant && ! -L $grant ]] || fail grant
[[ ! -e ${grant%.grant}.ended && ! -e ${grant%.grant}.complete ]] || fail terminal
read -r line < "$grant"
[[ $line =~ ^regions=([^[:space:]]+)\ start=([^[:space:]]+)\ end=([^[:space:]]+)$ ]] || fail format
region=${BASH_REMATCH[1]}; start=$(date -u -d "${BASH_REMATCH[2]}" +%s) || fail start
end=$(date -u -d "${BASH_REMATCH[3]}" +%s) || fail end
(( start <= EPOCHSECONDS && end == FILLER_END && end - start == 3600 )) || fail grant_window
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
  [[ $region == 72,73 && ${FILLER_CPUS:-} == 72,73 && ${FILLER_THREADS:-} == 2 ]] || fail pf_region
  expected=72-73
else
  [[ $region == "$real" && ${FILLER_CPUS:-} == "$real" && ${FILLER_THREADS:-} == "$threads" ]] || fail real_region
  expected=0-23; [[ $stage == resolve ]] && expected=0-1
  [[ -f $root/MAIN-APPROVAL.txt && ! -L $root/MAIN-APPROVAL.txt ]] || fail main_review
  grep -Fxq "approved-stage=$stage" "$root/MAIN-APPROVAL.txt" || fail stage_review
  packet_sha=$(sha256sum "$root/PACKET.sha256"); packet_sha=${packet_sha%% *}
  grep -Fxq "packet-sha256=$packet_sha" "$root/MAIN-APPROVAL.txt" || fail packet_review
fi
[[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == "$expected" ]] || fail affinity
for h in "$flags"/HOLD_* /mnt/raid0/llm/tmp/HOLD_GPU_FOR_QUIET_20261024; do [[ ! -e $h && ! -L $h ]] || fail hold; done
printf 'SPLIT_ADMISSION_PASS stage=%s region=%s deadline=%s\n' "$stage" "$region" "$FILLER_DEADLINE"
