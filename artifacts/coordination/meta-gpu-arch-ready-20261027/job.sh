#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-gpu-arch-ready/packet
R=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-build-recovery
B=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-fix-prep
sha256sum --quiet -c "$D/SOURCES.sha256"
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then
 [[ ${FILLER_ID:-} == codex-ni-meta-gpu-arch-20261027 && ${FILLER_CPUS:-} == 72,73 ]]
 /usr/bin/python3 -B "$D/dryrun_check.py" boundary --job "$D/job.sh" --effect model-inference
 exit 0
fi
[[ -s $R/RECOVERY-ACCEPTED && -s $D/MAIN-ACCEPTANCE.txt && ! -L $R/RECOVERY-ACCEPTED && ! -L $D/MAIN-ACCEPTANCE.txt ]]
[[ -s "$D/BK-ENROLLMENT-APPLIED.txt" && ! -L "$D/BK-ENROLLMENT-APPLIED.txt" ]]
grep -Fxq "adapter-sha256=$(sha256sum "$D/adapter-reviewed.py" | cut -d" " -f1)" "$D/BK-ENROLLMENT-APPLIED.txt"
grep -Fxq "planning-canary=passed" "$D/BK-ENROLLMENT-APPLIED.txt"
grep -Fxq "installed-root=/mnt/raid0/llm/views/epyc-root-main" "$D/BK-ENROLLMENT-APPLIED.txt"
grep -Fxq "recovery-accepted-sha256=$(sha256sum "$R/RECOVERY-ACCEPTED" | cut -d' ' -f1)" "$D/MAIN-ACCEPTANCE.txt"
grep -Fxq "gpu-source-seal-sha256=$(sha256sum "$D/SOURCES.sha256" | cut -d' ' -f1)" "$D/MAIN-ACCEPTANCE.txt"
grep -Fxq "evidence-manifest-sha256=$(sha256sum "$R/EVIDENCE.SHA256SUMS" | cut -d' ' -f1)" "$D/MAIN-ACCEPTANCE.txt"
[[ ${FILLER_ID:-} == codex-ni-meta-gpu-arch-20261027 && ${FILLER_NEEDGPU:-0} == 1 && ${FILLER_CPUS:-} == 184-191 && ${FILLER_STOPFILE:-} == "$D/STOP" ]]
[[ $(awk '/^Cpus_allowed_list:/ {print $2}' /proc/self/status) == 184-191 ]]
[[ ${FILLER_DEADLINE:-} =~ ^[0-9]+$ && $EPOCHSECONDS -lt $FILLER_DEADLINE && ! -e $D/STOP && ! -L $D/STOP && -z ${LD_PRELOAD:-} && -z ${LD_AUDIT:-} ]]
[[ -f /mnt/raid0/llm/tmp/compute-flags/grants/$FILLER_ID.grant && ! -L /mnt/raid0/llm/tmp/compute-flags/grants/$FILLER_ID.grant ]]
sha256sum --quiet -c "$R/EVIDENCE.SHA256SUMS"
sha256sum --quiet -c "$D/actual-bindings.sha256"
for kind in cpu hip; do (cd "$B/build$kind/bin" && sha256sum --quiet -c "$B/$kind-build.sha256"); done
export LD_LIBRARY_PATH="$B/buildhip/bin:/opt/rocm/lib" OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$B/buildhip/bin/test-llama-archs" "$B/buildhip/bin" > "$D/linkage.log" 2>&1
grep -Fq PASS "$D/linkage.log"
source "$D/owned-bootstrap.sh"
active=''; bootstrap_start=''
cleanup() { local rc=$?; trap - EXIT TERM INT HUP; if [[ -n $active ]] && ! bootstrap_drain; then rc=70; fi; exit "$rc"; }
trap cleanup EXIT
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
remaining=$((FILLER_DEADLINE-EPOCHSECONDS)); ((remaining>0))
setsid timeout --signal=TERM --kill-after=10 "${remaining}s" /usr/bin/python3 -I -B "$B/resource-watch.py" /usr/bin/python3 -I -B "$D/monitor.py" > "$D/monitor.log" 2>&1 &
active=$!
for _ in {1..20}; do bootstrap_capture && break; sleep 0.01; done
[[ -n $bootstrap_start ]]
rc=0; wait "$active" || rc=$?
if bootstrap_drain; then active=''; else exit 70; fi
((rc==0)) || exit "$rc"
[[ -s "$D/run/results.json" ]] || exit 70
printf 'source-seal-sha256=%s\nrecovery-accepted-sha256=%s\nresult-sha256=%s\nrc=0\ndrain=pass\n' "$(sha256sum "$D/SOURCES.sha256" | cut -d" " -f1)" "$(sha256sum "$R/RECOVERY-ACCEPTED" | cut -d" " -f1)" "$(sha256sum "$D/run/results.json" | cut -d" " -f1)" > "$D/ARCH-COMPLETE"
