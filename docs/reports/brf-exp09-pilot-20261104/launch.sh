#!/bin/bash
# BRF-T4-EXP09 pilot launcher (ws58, 2026-11-02). Engine: filler_run15.sh. One CPU quarter, <=45 min.
# The job starts its OWN llama-server (production-consolidated-v10 kernel store, worker model) on the granted CPUs
# and port 18409, registers its pid in FILLER_PIDFILE, and stops it on exit. Scratch: /mnt/raid0/llm/tmp/brf-exp09.
set -euo pipefail
D=/mnt/raid0/llm/tmp/brf-exp09
PY=/mnt/raid0/llm/tmp/brf-exp09/pyenv/venv/bin/python  # frozen copy of the orchestrator venv and its cpython, 2026-11-02
printf '%s  %s\n' f0196ae6be177f4de2c3998b0b982bf029705a39b192a9719b4818114aed637e "$D/job.py" | sha256sum -c --quiet -
printf '%s  %s\n' 67f41238d28e60f9abaed637ce50442d514a3e30af0fd55016f55a3c4a1e3afb "$D/identity.json" | sha256sum -c --quiet -
printf '%s  %s\n' a041e07afd399d17f75a6ab61b7efed3346bb8fa3408d414965fd8b7012336fa "$D/corpus/MANIFEST.json" | sha256sum -c --quiet -
export EXP09_CAP_S=2700
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id brf-exp09-pilot-20261102 --class cpu --role build --gpu-quiet none --port 18409 --min-window 2700 --stop "$D/STOP" --workdir "$D" --precond-cmd "$PY $D/job.py --check" --cmd "exec $PY $D/job.py" --complete-cmd "test -s $D/out/COMPLETE"
