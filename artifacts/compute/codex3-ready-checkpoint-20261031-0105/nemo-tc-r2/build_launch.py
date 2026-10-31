import hashlib,json,pathlib
D=pathlib.Path(__file__).parent;pin=json.loads((D/'INPUT-PINS.json').read_text());cat=hashlib.sha256((D/'SOURCE-SHA256SUMS').read_bytes()).hexdigest()
s='''#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-cs8-stt5-validation-nemotron-tc-r2-20261030
export FILLER_RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
export LD_LIBRARY_PATH=/mnt/raid0/llm/whisper.cpp/build/bin OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1
cd "$D"
export CS8_SOURCE_SHA=__SOURCE__
export CS8_PLAN_SHA=__PLAN__
export CS8_INPUT_SHA=__INPUT__
printf '%s  %s\\n' "$CS8_SOURCE_SHA" "$D/SOURCE-SHA256SUMS" | sha256sum -c - >/dev/null
sha256sum --check "$D/SOURCE-SHA256SUMS" >/dev/null
P=/mnt/raid0/llm/tmp/codex3-cs8-stt2-transcribe-20261030
SRC=/mnt/raid0/llm/tmp/dive-transcribe-cpp/tc
[[ $(git -C "$SRC" rev-parse HEAD) == db678a031cf4c524bcab2c45a0dc6a7813106e4a ]]
git -C "$SRC" diff --quiet
git -C "$SRC" diff --cached --quiet
export LD_LIBRARY_PATH="$P/install/lib"
/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh /mnt/raid0/llm/tmp/codex3-cs8-stt5-accuracy-20261030/nemo-traced-v2/transcribe-cli "$P" >/dev/null
if [[ ${1:-} == --smoke ]]; then
 [[ $# == 1 ]] || exit 64
 exec taskset -c "${FILLER_CPUS:?}" python3 "$D/smoke-supervisor.py" 265 -- env CS8_SMOKE=1 python3 "$D/nemo_job.py"
fi
[[ $# == 0 ]] || exit 64
exec bash "$D/engine/filler_run13.sh" --id codex3-cs8-stt5-validation-nemotron-tc-r2-20261030 --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 900 --complete-cmd "test -s $D/validation-results/COMPLETE.json || test -s $D/validation-results/TERMINAL-INCOMPLETE.json" --cmd 'taskset -c "$FILLER_CPUS" python3 /mnt/raid0/llm/tmp/codex3-cs8-stt5-validation-nemotron-tc-r2-20261030/nemo_job.py' --stop "$D/STOP" --workdir "$D"
'''.replace('__SOURCE__',cat).replace('__PLAN__',pin['plan_sha256']).replace('__INPUT__',pin['validation_sha256'])
p=D/'launch.sh';p.write_text(s);p.chmod(0o755);print('launcher',hashlib.sha256(p.read_bytes()).hexdigest(),'catalog',cat)
