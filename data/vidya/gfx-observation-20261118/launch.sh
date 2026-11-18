#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118
/usr/bin/sha256sum --check --status <<'SEAL'
ee22008823dfa16280e607c353ec7ddb7ece205350f064d02337fecc333aecb0  /mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118/source-manifest.json
755b5fe72fa5bc257e00e880bb0df1bcca8e56b5b3f704fb2d083ff1663dc634  /mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118/reader-manifest.json
1f34fb48243a26f8e51d0f9c9c361f295a406d5b31532ce29e6270e68d760b07  /mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118/gpu_counter.py
6f1502f6796169fcd4bf2cc217fa866922117ae343fc79265f40ee2fcbc69989  /mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118/native.py
01d47dbcae99f1708b4cd7f87a99ff4272860c77a54a59568d92e2e63c65a48d  /mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118/observation.py
e13c7e300b4fc1034d941b6847daa6e0f68a34380311c65e49384a3a4ae565aa  /mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118/reader.py
57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33  /mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118/verify_ggml_linkage.sh
d2b888ca9b4025a17878efae16a3b3f594cd01f6da0f3b782c3117f88071d1af  /mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118/weights.sha256
b29ca8de7cbbe378f8916c944477061c29cb613df72418a45762c3fa0534de77  /mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118/weights.stat.before
b29ca8de7cbbe378f8916c944477061c29cb613df72418a45762c3fa0534de77  /mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118/weights.stat.after
SEAL
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id vb-ak-r18-gfx-observation-20261118 --class gpu --gpu-quiet exclusive --no-fold-siblings \
  --gpu-threads 184-187 --port 19831 --min-window 300 --stop-grace 12 --workdir "$D" --stop "$D/STOP" \
  --complete-cmd '/usr/bin/python3 -BI /mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118/native.py complete' \
  --cmd '/usr/bin/python3 -BI /mnt/raid0/llm/tmp/vidya-belief-substrate/gfx-observation-20261118/native.py run'
