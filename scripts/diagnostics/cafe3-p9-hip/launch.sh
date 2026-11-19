#!/bin/bash
set -euo pipefail
export HIP_VISIBLE_DEVICES=0 ROCR_VISIBLE_DEVICES=0
D=/mnt/raid0/llm/tmp/df2/cafe3-p9-hip-20261119/cafe3-p9
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id df2-cafe3-p9-hip-20261119 --class gpu --gpu-quiet exclusive --claim-cpus "${WS58_REGIONS:-184-191}" --role bench --min-window 3600 --stop "$D/STOP" --workdir "$D" --precond-cmd "python3 $D/runtime.py inputs 2bf64dedf6e473f99c83c9df5f731d3e6a8e4bbdd8677ec2e0d3bfec00ca1014" --cmd "python3 $D/runtime.py run 2bf64dedf6e473f99c83c9df5f731d3e6a8e4bbdd8677ec2e0d3bfec00ca1014" --complete-cmd "python3 $D/runtime.py check 2bf64dedf6e473f99c83c9df5f731d3e6a8e4bbdd8677ec2e0d3bfec00ca1014"
