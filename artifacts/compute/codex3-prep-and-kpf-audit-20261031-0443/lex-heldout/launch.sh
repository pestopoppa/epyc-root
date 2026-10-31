#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/lex2-heldout
L=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/lex2
M=/mnt/raid0/llm/models/nemo-speech-nemotron35-1c8deae
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1
export LEX2_NEMO_MODEL_SHA=a5c435f294eea8f88ce68dd27b8c3bfea7f777cb2fbba04fcd30eaa555f429ae LEX2_WHISPER_MODEL_SHA=1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69 LEX2_SPM_SHA=ce3895e40806f02a26c3a225161b96ef682d6c0054bae32a245dec4258d7d291
cd "$D"
printf '%s  %s\n' f90e194bb493314f7351570ee67722e9e67dabfea70c64c1e4003a0527b49c3e "$D/SOURCE-SHA256SUMS" | sha256sum -c - >/dev/null
sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"
sha256sum -c --quiet "$L/SOURCE-SHA256SUMS"
printf '%s  %s\n' "$LEX2_NEMO_MODEL_SHA" "$M/nemotron-3.5-asr-streaming-0.6b.q8_0.gguf" "$LEX2_WHISPER_MODEL_SHA" /mnt/raid0/llm/models/whisper-ggml/ggml-large-v3-turbo.bin | sha256sum -c --quiet -
case ${1:-} in
 --job) export LEX2_TEST_MODE=full; exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/heldout_capture.py";;
 --smoke) export LEX2_TEST_MODE=smoke FILLER_DEADLINE=$(( $(date +%s) + 250 )); exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/smoke-supervisor.py" 265 -- /usr/bin/python3 -B "$D/heldout_capture.py";;
 --engine) test -s "$L/DEV-SELECTION.json"; if ! test -s "$L/HELDOUT-PLAN.json"; then /usr/bin/python3 -B "$L/make_heldout_plan.py"; fi; if ! test -s "$D/INSTANCE-PLAN.json"; then /usr/bin/python3 -B "$D/make_instance_plan.py"; fi; export FILLER_RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock; exec /bin/bash "$D/engine/filler_run13.sh" --id codex3-cs8-lex2-heldout-20261031 --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 3600 --stop "$D/STOP" --workdir "$D" --complete-cmd "test -s $D/run/TERMINAL.json" --cmd 'env RUS3_DIAGNOSTIC=1 taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/lex2-heldout/launch.sh --job';;
 '') exec sudo -n --preserve-env=WS58_REGIONS,FILLER_CPUS /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/launch.sh" --engine;;
 *) exit 64;;
esac
