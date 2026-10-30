#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-cs26-lid1-20261030
export FILLER_RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
printf '%s  %s\n' b3f171407fa4bdaafc8b4158203e602e3d23faa2b99656c8368f66347e4c8ac3 "$D/CRISP-SOURCE-SHA256SUMS" | sha256sum -c - >/dev/null
sudo chroot /proc/1/root setpriv --reuid=1000 --regid=1000 --groups=992 sha256sum --check "$D/CRISP-SOURCE-SHA256SUMS" >/dev/null
sudo chroot /proc/1/root setpriv --reuid=1000 --regid=1000 --groups=992 env LD_LIBRARY_PATH=/mnt/micron/codex3-cs8-stt2-crisp-20261030/install/lib /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$D/firered_probe" /mnt/micron/codex3-cs8-stt2-crisp-20261030 >/dev/null
exec bash "$D/filler_run13.sh" --id codex3-cs26-lid1-firered-20261030 --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 900 --complete-cmd "test -s $D/results/firered/COMPLETE.json" --cmd 'sudo chroot /proc/1/root setpriv --reuid=1000 --regid=1000 --groups=992 env FILLER_END="$FILLER_END" FILLER_STOPFILE="$FILLER_STOPFILE" LD_LIBRARY_PATH=/mnt/micron/codex3-cs8-stt2-crisp-20261030/install/lib HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 taskset -c "$FILLER_CPUS" python3 /mnt/raid0/llm/tmp/codex3-cs26-lid1-20261030/crisp_job.py firered' --stop "$D/STOP-firered" --workdir "$D"
