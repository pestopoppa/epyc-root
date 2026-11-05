#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kvu19b-native-custody-20261105
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu19b-native-custody-qual-20261105 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 184-187 --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' ad1ed000b642424a0e4a214606765660f0fbc3df0c5f4485d3902411905f8d1a '$D/runtime.sha256' | sha256sum -c && sha256sum -c '$D/runtime.sha256' && printf '%s  %s\\n' 441809fbb29dc499f32a07d0e838365c6fd20f203c355a443664d2f789ba825a '$D/inputs.json' | sha256sum -c && python3 '$D/check.py'" --cmd "bash '$D/job.sh'" --complete-cmd "python3 '$D/complete.py'"
