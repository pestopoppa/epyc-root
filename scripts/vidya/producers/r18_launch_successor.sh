#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/r18-belief-successor-20261102
P=/mnt/raid0/llm/r18-belief-producer-20261102
ID=r18-belief-symbols-20261102
export FILLER_RL=/workspace/repos/epyc-orchestrator/scripts/region-lock
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --role build --gpu-quiet none --cmd "/bin/bash $P/r18_job_successor.sh" --complete-cmd "/usr/bin/python3 -B $P/r18_completion_successor.py" --stop "$D/STOP" --min-window 1080 --workdir "$D" --requires-tool /usr/bin/cmake --requires-tool /usr/bin/gmake --requires-tool /usr/bin/taskset --requires-tool /usr/bin/git --requires-tool /usr/bin/readelf --requires-tool /usr/bin/nm --requires-tool /opt/rocm/lib/llvm/bin/clang++ --requires-tool /opt/rocm/bin/roc-obj-ls
