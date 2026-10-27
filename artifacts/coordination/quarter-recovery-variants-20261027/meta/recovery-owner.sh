#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/codex-ni-20261027-quarter-recovery-variants/meta
B=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep
T=/mnt/raid0/llm/worktrees/meta-fix-c5
ID=codex-ni-meta-recovery-q0-20261027
/bin/bash "$R/retirement-guard.sh"
[[ ${FILLER_PREFLIGHT:-0} != 1 && ${FILLER_ID:-} == "$ID" && ${FILLER_CPUS:-} == 0-23 && ${FILLER_THREADS:-} == 24 && ${FILLER_STOPFILE:-} == "$R/STOP" ]]
[[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == 0-23 ]]
[[ ! -e $R/STOP && ! -L $R/STOP && -z ${LD_PRELOAD:-} && -z ${LD_AUDIT:-} ]]
[[ ${FILLER_END:-} =~ ^[0-9]+$ && ${FILLER_DEADLINE:-} =~ ^[0-9]+$ && $EPOCHSECONDS -lt $FILLER_DEADLINE && $FILLER_DEADLINE -lt $FILLER_END ]]
G=/mnt/raid0/llm/tmp/compute-flags/grants/$ID.grant
[[ -f $G && ! -L $G ]]
read -r line < "$G"
[[ $line =~ ^regions=0-23\ start=([^[:space:]]+)\ end=([^[:space:]]+)$ ]]
start=$(date -u -d "${BASH_REMATCH[1]}" +%s); end=$(date -u -d "${BASH_REMATCH[2]}" +%s)
((start<=EPOCHSECONDS && EPOCHSECONDS<end && end==FILLER_END))
[[ ! -e /mnt/raid0/llm/tmp/compute-flags/grants/$ID.ended && ! -e /mnt/raid0/llm/tmp/compute-flags/grants/$ID.complete ]]
sha256sum --quiet -c "$R/EVIDENCE.SHA256SUMS"
sha256sum --quiet -c "$B/SOURCE.SHA256SUMS"
sha256sum --quiet -c "$B/TRACKED-SOURCE.sha256"
sha256sum --quiet -c "$B/TOOLCHAIN.sha256"
[[ $(git -C "$T" rev-parse HEAD) == c72ec82f5417bb2937310326120f149b665e8400 ]]
cmp <(git -C "$T" diff --binary) "$B/candidate.patch"
for kind in cpu hip; do
 (cd "$B/build$kind/bin" && sha256sum --quiet -c "$B/$kind-build.sha256")
 cmp <(stat -c '%y %n' "$B/build$kind/bin/test-llama-archs" "$B/build$kind/bin/libggml-base.so") "$B/$kind-mtimes.txt"
 [[ ! -s $B/$kind-cache.diff ]]
 grep -Fq 'PASS mixed Meta/host trailing view and two-device partial reduction' "$B/$kind-mixed.log"
 grep -Fq 'FIXTURE_READY partial=1 host_mean=2,3 tail=host-view' "$B/$kind-baseline.log"
 grep -Fq 'FIXTURE_READY partial=1 host_mean=2,3 tail=foreign-compute' "$B/$kind-reject.log"
 grep -Fq 'GGML_ASSERT(ggml_backend_buffer_is_meta(tensor->buffer)) failed' "$B/$kind-baseline.log"
 grep -Fq 'GGML_ASSERT(ggml_backend_buffer_is_meta(tensor->buffer)) failed' "$B/$kind-reject.log"
done
grep -Eq '^RSS_SAMPLED_PEAK_KIB=[0-9]+ LIMIT_KIB=25165824 drained=True$' "$B/ws58-launcher.out"
grep -Fxq 'rc=70 time=2026-10-27T19:24:30Z reason=job-rc-70:exited' /mnt/raid0/llm/tmp/compute-flags/grants/codex-ni-meta-fix-build-20261027.ended
printf 'candidate=c72ec82f5417bb2937310326120f149b665e8400\nevidence_manifest_sha256=%s\noriginal_status=rc70\noriginal_outer_drain=unproven\nmodel_runs=none\n' "$(sha256sum "$R/EVIDENCE.SHA256SUMS" | cut -d' ' -f1)" > "$R/RECOVERY-WORK-DONE"
