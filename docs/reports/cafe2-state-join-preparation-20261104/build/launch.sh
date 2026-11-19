#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/cafe2-expert-state-build
printf '%s  %s\n' bdd7df1445ff127e46cfeeaa62817ea758baaa71b8f133f3519d5d63c0464926 "$D/runtime.sha256" | sha256sum -c - >/dev/null
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id cafe2-v10-expert-state-build-20261104 --class cpu --role build --min-window 1800 --stop "$D/STOP" --workdir "$D" --precond-cmd "sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/proof.py check"
