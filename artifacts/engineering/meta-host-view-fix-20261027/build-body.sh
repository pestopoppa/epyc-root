#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep
T=/mnt/raid0/llm/worktrees/meta-fix-c5
cd "$B"
sha256sum --quiet -c SOURCE.SHA256SUMS
sha256sum --quiet -c TRACKED-SOURCE.sha256
sha256sum --quiet -c TOOLCHAIN.sha256
[[ $(git -C "$T" rev-parse HEAD) == c72ec82f5417bb2937310326120f149b665e8400 ]]
cmp <(git -C "$T" diff --binary) "$B/candidate.patch"
[[ -z ${LD_PRELOAD:-} && -z ${LD_AUDIT:-} ]]
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
 [[ ${FILLER_ID:-} == codex-ni-meta-fix-build-20261027 && ${FILLER_CPUS:-} == 72,73 ]]
 [[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == 72-73 ]]
 for f in "$B"/build-{poller,body,owner}.sh "$B"/t1.sh "$B"/pf-region-claimed.sh; do bash -n "$f"; done
 /usr/bin/python3 -B "$B/deps/dryrun_check.py" boundary --job "$B/build-body.sh" --effect source-build
 exit 0
fi
source "$B/owned-bootstrap.sh"
active=''; bootstrap_start=''
cleanup() {
 local rc=$?
 trap - EXIT TERM INT HUP
 if [[ -n $active ]] && ! bootstrap_drain; then rc=70; fi
 exit "$rc"
}
trap cleanup EXIT
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
[[ ${FILLER_DEADLINE:-} =~ ^[0-9]+$ && $EPOCHSECONDS -lt $FILLER_DEADLINE ]]
remaining=$((FILLER_DEADLINE-EPOCHSECONDS))
setsid timeout --signal=TERM --kill-after=10 "${remaining}s" /usr/bin/python3 -I -B "$B/resource-watch.py" /bin/bash "$B/build-owner.sh" &
active=$!
for _ in {1..20}; do bootstrap_capture && break; sleep 0.01; done
[[ -n $bootstrap_start ]]
rc=0; wait "$active" || rc=$?
bootstrap_drain || rc=70
active=''
((rc==0)) || exit "$rc"
[[ -s "$B/BUILD-WORK-DONE" ]]
cp "$B/BUILD-WORK-DONE" "$B/BUILD-COMPLETE"
