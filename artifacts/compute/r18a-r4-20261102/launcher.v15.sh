#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/refactor-01a16fc3/r18a-verified-anchor-20261031/refactor-r18a-v10-independent-symbols-r4-20261102
ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh
ID=refactor-r18a-v10-independent-symbols-r4-20261102
[[ "$(sha256sum "$D/CLOSURE.sha256" | cut -d " " -f 1)" == f253b566966a63e2d65373bc75e959b3041cd26336a3b8a6b5d82202f4eb66c2 ]] && sha256sum -c "$D/CLOSURE.sha256" >/dev/null || { echo "closure changed" >&2; exit 70; }
export FILLERS_MD="$D/epyc.ready.v2.row.md"
export FILLER_RL=/workspace/repos/epyc-orchestrator/scripts/region-lock
CMD="/bin/bash $D/job.sh"
DONE="/usr/bin/python3 -B $D/complete.py $D/scratch/full"
exec "$ENGINE" --id "$ID" --class cpu --role build --gpu-quiet none --cmd "$CMD" --complete-cmd "$DONE" \
  --stop "$D/STOP" --min-window 1080 --workdir "$D" \
  --requires-tool bash --requires-tool python3 --requires-tool ss \
  --requires-tool /workspace/repos/epyc-orchestrator/scripts/region-lock \
  --requires-tool /usr/bin/cmake --requires-tool /usr/bin/gmake --requires-tool /usr/bin/taskset \
  --requires-tool /usr/bin/git --requires-tool /usr/bin/readelf --requires-tool /usr/bin/nm --requires-tool /usr/bin/sha256sum \
  --requires-tool /opt/rocm/lib/llvm/bin/clang++ --requires-tool /opt/rocm/bin/roc-obj-ls
