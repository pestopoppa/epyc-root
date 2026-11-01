#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/refactor-r18a-v10-independent-symbols-r3-20261101-candidate-b7
ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh
ID=refactor-r18a-v10-independent-symbols-r3-20261101
R18_ROWFLOW_RESULT_ROOT=/mnt/raid0/llm/tmp/compute-flags/rowflow-results/refactor-r18a-v10-independent-symbols-r3-20261101
export R18_ROWFLOW_RESULT_ROOT
SOURCE_MANIFEST_SHA256=cc3a18cb6b520add4b73c396d6d469cb7edd6f5198214b598ced70ab02413039
export FILLERS_MD="$D/epyc.ready.v2.row.md"
export FILLER_RL=/workspace/repos/epyc-orchestrator/scripts/region-lock
CMD="/bin/bash $D/job.sh"
DONE="/usr/bin/python3 -B $D/complete.py $D/scratch/full"
manifest_sha=$(sha256sum "$D/SOURCE-MANIFEST.sha256") || { echo "source manifest missing" >&2; exit 65; }
manifest_sha=${manifest_sha%% *}
[[ "$manifest_sha" == "$SOURCE_MANIFEST_SHA256" ]] || { echo "source manifest digest mismatch" >&2; exit 65; }
( cd "$D" && sha256sum --strict --quiet -c SOURCE-MANIFEST.sha256 ) || { echo "source manifest check failed" >&2; exit 65; }
exec "$ENGINE" --id "$ID" --class cpu --role build --gpu-quiet none --cmd "$CMD" --complete-cmd "$DONE" \
  --stop "$D/STOP" --min-window 1080 --workdir "$D" \
  --requires-tool bash --requires-tool python3 --requires-tool ss \
  --requires-tool /workspace/repos/epyc-orchestrator/scripts/region-lock \
  --requires-tool /usr/bin/cmake --requires-tool /usr/bin/gmake --requires-tool /usr/bin/taskset \
  --requires-tool /usr/bin/git --requires-tool /usr/bin/readelf --requires-tool /usr/bin/nm --requires-tool /usr/bin/sha256sum \
  --requires-tool /opt/rocm/lib/llvm/bin/clang++ --requires-tool /opt/rocm/bin/roc-obj-ls
