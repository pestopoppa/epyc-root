#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-fixed-build
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
 [[ ${FILLER_ID:-} == kpf62-native-g1-fixed-build-20261027 && ${FILLER_CPUS:-} == 72,73 ]]
 [[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == 72-73 ]]
 (cd "$B" && sha256sum --quiet -c SOURCE.SHA256SUMS && sha256sum --quiet -c NATIVE-SOURCES.sha256)
 for f in "$B"/{launch,guard,build-body,build-poller,owned-bootstrap}.sh; do bash -n "$f"; done
 /usr/bin/python3 -B "$B/deps/dryrun_check.py" boundary --job "$B/build-body.sh" --effect source-build
 exit 0
fi
source "$B/owned-bootstrap.sh"
active=''; bootstrap_start=''
cleanup() { local rc=$?; trap - EXIT TERM INT HUP; if [[ -n $active ]] && ! bootstrap_drain; then rc=70; fi; exit "$rc"; }
trap cleanup EXIT
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
[[ ! -e $B/BUILD-ATTEMPT && ! -e $B/BUILD-COMPLETE && ! -e $B/build-receipt.json && ! -e $B/candidate && ! -e $B/build && ! -e $B/build-hip ]]
[[ ${FILLER_DEADLINE:-} =~ ^[0-9]+$ && $EPOCHSECONDS -lt $FILLER_DEADLINE ]]
attempt="${FILLER_ID}:${FILLER_END}:${BASHPID}:${EPOCHSECONDS}"
(set -C; printf '%s\n' "$attempt" > "$B/BUILD-ATTEMPT")
remaining=$((FILLER_DEADLINE-EPOCHSECONDS))
setsid timeout --signal=TERM --kill-after=10 "${remaining}s" /bin/bash "$B/owner-build.sh" &
active=$!
for _ in {1..20}; do bootstrap_capture && break; sleep 0.01; done
[[ -n $bootstrap_start ]]
rc=0; wait "$active" || rc=$?
if ! bootstrap_drain; then rc=70; fi
active=''
if (( rc != 0 )); then exit "$rc"; fi
[[ -s $B/build-receipt.json && $(cat "$B/BUILD-ATTEMPT") == "$attempt" ]]
receipt_sha=$(sha256sum "$B/build-receipt.json"); receipt_sha=${receipt_sha%% *}
(set -C; printf 'attempt=%s\nreceipt_sha256=%s\nrc=0\ndrain=verified\n' "$attempt" "$receipt_sha" > "$B/BUILD-COMPLETE")
