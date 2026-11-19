#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kpf18-g3-live-residency-fixture-20261105
printf '%s  %s\n' 7b8196f3089da113ee5f977a987984e8b2ef1c22b383fc3ea36469b8a9a3b3c2 "$D/fixture.cpp" | sha256sum --status -c -
printf '%s  %s\n' e5efee459c0f68613ea7cf92c33286b1ff2930060d0a30aeb3681534ee9a2707 "$D/job.py" | sha256sum --status -c -
printf '%s  %s\n' 27665b3a961ffd793c2c46ded39f2e90711e8ec6f47594d27140d73e45c71ed3 "$D/gpu_witness.py" | sha256sum --status -c -
printf '%s  %s\n' dd36ae78e28f4fd048ed6411a038386410cfd6853b5c7ffc9194308b412e68a9 "$D/sysfs_residency.py" | sha256sum --status -c -
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf18-g3-live-residency-fixture-20261105 --class gpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/job.py' --complete" --cmd "python3 -B '$D/job.py'"
