#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id df2-cafe3-p9-cpu-20261119 --class cpu --role bench --min-window 3600 --stop "$D/STOP" --workdir "$D" --precond-cmd "python3 $D/runtime.py inputs fe6598567dfe2c13d641c4cf8f4ff237492c7bd8907c8e467d7a1da9856d5827" --cmd "python3 $D/runtime.py run fe6598567dfe2c13d641c4cf8f4ff237492c7bd8907c8e467d7a1da9856d5827" --complete-cmd "python3 $D/runtime.py check fe6598567dfe2c13d641c4cf8f4ff237492c7bd8907c8e467d7a1da9856d5827"
