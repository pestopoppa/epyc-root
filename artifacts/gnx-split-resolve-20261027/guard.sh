#!/bin/bash
set -euo pipefail
root=/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase
packet="$root/stage2-packet-r2"
flags=/mnt/raid0/llm/tmp/compute-flags
fail() { printf 'SPLIT2_ADMISSION_REFUSED:%s\n' "$1" >&2; exit 6; }
[[ ${FILLER_ID:-} == codex-ni-gnx-split-resolve-r2-20261027 ]] || fail id
[[ ${FILLER_STOPFILE:-} == "$root/STOP" && ! -e $root/STOP && ! -L $root/STOP ]] || fail stop
sha256sum -c "$packet/PACKET.sha256" >/dev/null || fail packet
[[ ${FILLER_END:-} =~ ^[0-9]+$ && ${FILLER_DEADLINE:-} =~ ^[0-9]+$ ]] || fail deadline
(( FILLER_DEADLINE > EPOCHSECONDS && FILLER_DEADLINE < FILLER_END && FILLER_END - EPOCHSECONDS > 300 )) || fail window
if [[ ${SPLIT_RUNNING:-0} != 1 ]]; then (( FILLER_END - EPOCHSECONDS >= 2700 )) || fail initial_window; fi
grant="${FILLER_GRANTS_DIR:-$flags/grants}/$FILLER_ID.grant"
[[ -f $grant && ! -L $grant && ! -e ${grant%.grant}.ended && ! -e ${grant%.grant}.complete ]] || fail grant
read -r line < "$grant"
[[ $line =~ ^regions=([^[:space:]]+)\ start=([^[:space:]]+)\ end=([^[:space:]]+)$ ]] || fail format
region=${BASH_REMATCH[1]}; start=$(date -u -d "${BASH_REMATCH[2]}" +%s) || fail start
end=$(date -u -d "${BASH_REMATCH[3]}" +%s) || fail end
(( start <= EPOCHSECONDS && end == FILLER_END && end - start == 3000 )) || fail grant_window
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
  [[ ${FILLER_THREADS:-} == 2 ]] || fail pf_region
  case $region in
    0,1|0-1) [[ ${FILLER_CPUS:-} == 0,1 || ${FILLER_CPUS:-} == 0-1 ]] || fail pf_region; expected=0-1;;
    72,73|72-73) [[ ${FILLER_CPUS:-} == 72,73 || ${FILLER_CPUS:-} == 72-73 ]] || fail pf_region; expected=72-73;;
    *) fail pf_region;;
  esac
else
  [[ ( $region == 72,73 || $region == 72-73 ) && ( ${FILLER_CPUS:-} == 72,73 || ${FILLER_CPUS:-} == 72-73 ) && ${FILLER_THREADS:-} == 2 ]] || fail real_region
  expected=72-73
  [[ -f $packet/MAIN-APPROVAL.txt && ! -L $packet/MAIN-APPROVAL.txt ]] || fail main_review
  grep -Fxq approved-stage=resolve "$packet/MAIN-APPROVAL.txt" || fail stage_review
  seal=$(sha256sum "$packet/PACKET.sha256"); seal=${seal%% *}
  grep -Fxq "packet-sha256=$seal" "$packet/MAIN-APPROVAL.txt" || fail packet_review
fi
[[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == "$expected" ]] || fail affinity
for h in "$flags"/HOLD_* /mnt/raid0/llm/tmp/HOLD_GPU_FOR_QUIET_20261024; do [[ ! -e $h && ! -L $h ]] || fail hold; done
printf 'SPLIT2_ADMISSION_PASS region=%s deadline=%s\n' "$region" "$FILLER_DEADLINE"
