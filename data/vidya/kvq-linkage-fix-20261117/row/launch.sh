#!/bin/bash
# vidya-kvq-v10-sweep-20261117-r2 (vidya-belief-substrate-program.md:VB-KVQ-V10-INGEST)
# MI210 exclusive-quiet + GPU host threads 184-191. Binary = production kernel store (resolved by the producer).
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate-program/vidya-kvq-v10-sweep-20261117-r2
cd "$D"
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vidya-kvq-v10-sweep-20261117-r2 \
  --class gpu --gpu-quiet exclusive --claim-cpus 184-191 --role bench --min-window 7200 \
  --gpu-threads 184-191 --port 19960,19961,19962,19963,19964,19965,19966,19967,19968,19969,19970,19971,19972,19973,19974,19975,19976,19977,19978,19979,19980,19981,19982,19983,19984,19985,19986,19987,19988,19989 \
  --precond-cmd "/usr/bin/python3 -I $D/job.py --guard" \
  --cmd "/usr/bin/python3 -I $D/job.py" \
  --complete-cmd "test -f $D/out/COMPLETE" \
  --stop "$D/STOP" --workdir "$D"
