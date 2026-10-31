#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/dsc25592
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1
export DSC_SMALL_SHA=c159d1518f16bc42533d9a09f034eb598b670341adc2b08b9a9751614aea71eb DSC_MODEL_SHA=c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131
umask 077
cd "$D"
printf '%s  %s\n' 3fbc59ed061f34df80b5afdf86c64a956666964dae703fee8a5dc03821fd1a48 "$D/SOURCE-SHA256SUMS" | sha256sum -c - >/dev/null
sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"
sha256sum -c --quiet "$D/RUNTIME-INPUTS.sha256"
sha256sum -c --quiet "$D/ADAPTER-SOURCE-SHA256SUMS"
sha256sum -c --quiet "$D/TOKENIZER-SOURCE-SHA256SUMS"
case ${1:-} in
 --job) sha256sum -c --quiet "$D/PRIVATE-SESSION-SHA256SUMS"; printf '%s  %s\n' "$DSC_MODEL_SHA" /mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf | sha256sum -c --quiet -; export DSC_MODE=full; exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/worker.py";;
 --smoke) export DSC_MODE=smoke FILLER_DEADLINE=$(( $(date +%s) + 250 )); exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/smoke-supervisor.py" 265 -- /usr/bin/python3 -B "$D/worker.py";;
 --engine) test -s "$D/CASE-PLAN.json"; export FILLER_RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock; exec /bin/bash "$D/engine/filler_run13.sh" --id codex3-dsc-25592-replay-20261031 --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 5700 --stop "$D/STOP" --workdir "$D" --complete-cmd "test -s $D/run/TERMINAL.json" --cmd 'env RUS3_DIAGNOSTIC=1 taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/dsc25592/launch.sh --job';;
 '') exec sudo -n --preserve-env=WS58_REGIONS,FILLER_CPUS /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/launch.sh" --engine;;
 *) exit 64;;
esac
