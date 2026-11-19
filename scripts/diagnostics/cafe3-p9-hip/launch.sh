#!/bin/bash
set -euo pipefail
export HIP_VISIBLE_DEVICES=0 ROCR_VISIBLE_DEVICES=0
D=/mnt/raid0/llm/tmp/df2/cafe3-p9-hip-20261119/cafe3-p9
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id df2-cafe3-p9-hip-20261119 --class gpu --gpu-quiet exclusive --claim-cpus 184-191 --role bench --min-window 3600 --stop "$D/STOP" --workdir "$D" --precond-cmd "python3 $D/runtime.py inputs 751b336cb42b495b5a64257fb0d056ae472a7a539ca43d45f49f0e2d11b86f07" --cmd "python3 $D/runtime.py run 751b336cb42b495b5a64257fb0d056ae472a7a539ca43d45f49f0e2d11b86f07" --complete-cmd "python3 $D/runtime.py check 751b336cb42b495b5a64257fb0d056ae472a7a539ca43d45f49f0e2d11b86f07"
