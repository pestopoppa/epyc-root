#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep
R=/mnt/raid0/llm/tmp/codex-ni-20261027-quarter-recovery-variants/df2
cd "$R"
sha256sum --quiet -c RECOVERY-SOURCE.sha256
sha256sum --quiet -c ORIGINAL-EVIDENCE.sha256
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
 [[ ${FILLER_ID:-} == codex-ni-df2-build-recovery-q0-20261027 && ${FILLER_CPUS:-} == 0,1 ]]
 [[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == 0-1 ]]
 bash -n "$R/check.sh" "$R/job.sh" "$R/poller.sh" "$R/owned-bootstrap.sh"
 /usr/bin/python3 -B "$B/deps/dryrun_check.py" boundary --job "$R/job.sh" --effect artifact-recovery
 exit 0
fi
[[ ${FILLER_STOPFILE:-} == "$R/STOP" && ${FILLER_DEADLINE:-} =~ ^[0-9]+$ && $EPOCHSECONDS -lt $FILLER_DEADLINE ]]
source "$R/owned-bootstrap.sh"
source "$R/finalize.sh"
recovery_fresh "$R/RECOVERY-WORK-DONE" "/mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep/recovery/RECOVERY-COMPLETE" || exit 70
active=''; bootstrap_start=''
cleanup() { local rc=$?; trap - EXIT TERM INT HUP; if [[ -n $active ]] && ! bootstrap_drain; then rc=70; fi; exit "$rc"; }
trap cleanup EXIT; trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
setsid timeout --signal=TERM --kill-after=10 "$((FILLER_DEADLINE-EPOCHSECONDS))s" /usr/bin/python3 -I -B "$R/resource-watch.py" --limit-kib 4194304 /bin/bash "$R/check.sh" &
active=$!
for _ in {1..20}; do bootstrap_capture && break; sleep 0.01; done
[[ -n $bootstrap_start ]]
rc=0; wait "$active" || rc=$?
drain_rc=0; bootstrap_drain || drain_rc=$?
active=''
((rc==0)) || exit "$rc"
((drain_rc==0)) || exit 70
[[ -s "$R/RECOVERY-WORK-DONE" ]] || exit 70
finalize_recovery "$rc" "$drain_rc" "$R/RECOVERY-WORK-DONE" "$B/BUILD-COMPLETE" "/mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep/recovery/RECOVERY-COMPLETE" || exit 70
