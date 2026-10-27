#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep
R=/mnt/raid0/llm/tmp/codex-ni-20261027-quarter-recovery-variants/df2
T=/mnt/raid0/llm/worktrees/df2-row-exact-c5
ID=codex-ni-df2-build-recovery-q0-20261027
/bin/bash "$R/retirement-guard.sh"
[[ ${FILLER_ID:-} == "$ID" && ${FILLER_CPUS:-} == 0-23 && ${FILLER_THREADS:-} == 24 && ${FILLER_STOPFILE:-} == "$R/STOP" && ${FILLER_PREFLIGHT:-0} != 1 ]]
[[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == 0-23 ]]
[[ ${FILLER_DEADLINE:-} =~ ^[0-9]+$ && ${FILLER_END:-} =~ ^[0-9]+$ && $EPOCHSECONDS -lt $FILLER_DEADLINE && $FILLER_DEADLINE -lt $FILLER_END ]]
[[ ! -e $R/STOP && ! -L $R/STOP && ! -e $B/BUILD-COMPLETE && ! -L $B/BUILD-COMPLETE && -z ${LD_PRELOAD:-} && -z ${LD_AUDIT:-} ]]
! compgen -G '/mnt/raid0/llm/tmp/compute-flags/HOLD_*' >/dev/null
G=/mnt/raid0/llm/tmp/compute-flags/grants/$ID.grant
[[ -f $G && ! -L $G ]]
read -r line < "$G"
[[ $line =~ ^regions=0-23\ start=([^[:space:]]+)\ end=([^[:space:]]+)$ ]]
start=$(date -u -d "${BASH_REMATCH[1]}" +%s); end=$(date -u -d "${BASH_REMATCH[2]}" +%s)
((start<=EPOCHSECONDS && EPOCHSECONDS<end && end==FILLER_END && end-start==900))
cd "$R"
sha256sum --quiet -c RECOVERY-SOURCE.sha256
sha256sum --quiet -c ORIGINAL-EVIDENCE.sha256
cd "$B"
sha256sum --quiet -c SOURCE.SHA256SUMS
sha256sum --quiet -c TRACKED-SOURCE.sha256
sha256sum --quiet -c TOOLCHAIN.sha256
sha256sum --quiet -c UI-SOURCE.sha256
[[ $(git -C "$T" rev-parse HEAD) == c72ec82f5417bb2937310326120f149b665e8400 ]]
cmp <(git -C "$T" diff --binary) "$B/candidate.patch"
(cd buildcpu/bin && sha256sum --quiet -c "$B/cpu-build.sha256")
(cd buildhip/bin && sha256sum --quiet -c "$B/hip-build.sha256")
sha256sum --quiet -c fixture-binary.sha256
sha256sum --quiet -c width-probe-binary.sha256
[[ ! -s cpu-cache.diff && ! -s hip-cache.diff && -s BUILD-WORK-DONE ]]
for source in ggml/src/ggml-cuda/mmvq.cu ggml/src/ggml-cuda/mmvq.cuh ggml/src/ggml-cuda/ggml-cuda.cu; do
 [[ "$B/buildhip/bin/libggml-hip.so" -nt "$T/$source" ]] || exit 70
done
stat -Lc '%y %n' "$B/buildhip/bin/libggml-hip.so" "$T/ggml/src/ggml-cuda/mmvq.cu" "$T/ggml/src/ggml-cuda/mmvq.cuh" "$T/ggml/src/ggml-cuda/ggml-cuda.cu" > "$R/source-build-mtimes.log"
LD_LIBRARY_PATH="$B/buildcpu/bin" /workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$B/buildcpu/bin/test-llama-archs" > "$R/cpu-linkage.log"
LD_LIBRARY_PATH="$B/buildhip/bin:/opt/rocm/lib" /workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$B/buildhip/bin/test-llama-archs" > "$R/hip-linkage.log"
strings "$B/buildhip/bin/libggml-hip.so" | grep -F 'GGML_CUDA_DF2_ROW_EXACT active' > "$R/marker.log"
if strings "$B/buildhip/bin/libggml-hip.so" | grep -E 'GGML_CUDA_DF2_(CHECK_BYTES|INJECT_BYTE_MISMATCH)' > "$R/diagnostic-marker.log"; then exit 70; fi
if ps -p 786940 > "$R/original-pid.log"; then exit 70; fi
printf 'artifact_recovery=validated\noriginal_ended_sha256=%s\noriginal_work_done_sha256=%s\nsource_manifest_sha256=%s\n' "$(sha256sum /mnt/raid0/llm/tmp/compute-flags/grants/codex-ni-df2-row-exact-build-20261027.ended | cut -d' ' -f1)" "$(sha256sum "$B/BUILD-WORK-DONE" | cut -d' ' -f1)" "$(sha256sum "$B/SOURCE.SHA256SUMS" | cut -d' ' -f1)" > "$R/RECOVERY-WORK-DONE"
