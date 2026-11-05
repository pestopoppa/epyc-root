#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kvu19b-native-custody-r4-20261105
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu19b-native-custody-r4-20261105 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 184-187 --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' e0b29f504a2c2c9f18f8debd682613dce6c4a28c8e22c3de2372b28f9ce49f84 '$D/runtime.sha256' | sha256sum -c && sha256sum -c '$D/runtime.sha256' && printf '%s  %s\\n' b687fb0d8b7b6556bfd2d910824bb3b2c7ef025145d28f74a10953e14f55ce3e '$D/inputs.json' | sha256sum -c && python3 '$D/check.py'" --cmd "bash '$D/job.sh'" --complete-cmd "python3 '$D/complete.py'"
