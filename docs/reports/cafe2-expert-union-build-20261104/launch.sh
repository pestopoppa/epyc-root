#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/cafe2-expert-build
printf '%s  %s\n' c18bfd275a9abdc26c2767bd9d25b559fc19c653f9f872939514f77cc4de0717 "$D/runtime.sha256" | sha256sum -c - >/dev/null
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id cafe2-v10-expert-union-build-20261104 --class cpu --role build --min-window 1800 --stop "$D/STOP" --workdir "$D" --precond-cmd "sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/proof.py check"
