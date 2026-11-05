#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kvu11c-completion-reconciliation-20261105
printf '%s  %s\n' 3083a4d789663e5dbd9d8669080e22f2f1a1a6dd490ecfd945386dc419067a9f "$D/job.py" | sha256sum -c
printf '%s  %s\n' 669634775337c1aa9fcde17bb0ad2b1700a76530264feba677710afcc871d2b5 "$D/custody.json" | sha256sum -c
printf '%s  %s\n' df1edf33ebd95897311f2cb28653f0bc379184371f2575e388f437158ca90279 "$D/original-job.py" | sha256sum -c
printf '%s  %s\n' 7a8254c6b44c9eb04b51bb7ed7bcdeaaf8345f4d1164b3feb9365aae86655e91 "$D/original-result.json" | sha256sum -c
printf '%s  %s\n' 37d91fba0f47b28b27e8db6d1b2a3416670472d85ef9cc812b006f1638f31feb "$D/original-ended.txt" | sha256sum -c
printf '%s  %s\n' 21987e52ee02c609cd5a80f7b493b2d69fbaf367b4dd44bd9ff9fa3ec20c51b2 "$D/original-runner.sh" | sha256sum -c
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id kvu11c-retained-result-reconcile-r1-20261105 --class cpu --role build --min-window 300 --stop "$D/STOP" --workdir "$D" \
  --complete-cmd "/usr/bin/env -u PYTHONOPTIMIZE /usr/bin/python3 -I '$D/job.py' --complete" \
  --cmd "/usr/bin/env -u PYTHONOPTIMIZE /usr/bin/python3 -I '$D/job.py'"
