#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-build-recovery
B=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep
sha256sum --quiet -c "$R/RECOVERY.SHA256SUMS"
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
 [[ ${FILLER_ID:-} == codex-ni-meta-recovery-20261027 && ${FILLER_CPUS:-} == 72,73 ]]
 [[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == 72-73 ]]
 /usr/bin/python3 -B "$B/deps/dryrun_check.py" boundary --job "$R/recovery-body.sh" --effect source-build
 exit 0
fi
source "$R/owned-bootstrap.sh"
active=''; bootstrap_start=''
cleanup() { local rc=$?; trap - EXIT TERM INT HUP; if [[ -n $active ]] && ! bootstrap_drain; then rc=70; fi; exit "$rc"; }
trap cleanup EXIT
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
[[ ${FILLER_DEADLINE:-} =~ ^[0-9]+$ && $EPOCHSECONDS -lt $FILLER_DEADLINE ]]
remaining=$((FILLER_DEADLINE-EPOCHSECONDS))
setsid timeout --signal=TERM --kill-after=10 "${remaining}s" /usr/bin/python3 -I -B "$B/resource-watch.py" /bin/bash "$R/recovery-owner.sh" &
active=$!
for _ in {1..20}; do bootstrap_capture && break; sleep 0.01; done
[[ -n $bootstrap_start ]]
rc=0; wait "$active" || rc=$?
if bootstrap_drain; then active=''; else exit 70; fi
((rc==0)) || exit "$rc"
[[ -s "$R/RECOVERY-WORK-DONE" ]]
cp "$R/RECOVERY-WORK-DONE" "$R/RECOVERY-ACCEPTED"
