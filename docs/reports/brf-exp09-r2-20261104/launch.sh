#!/bin/bash
# BRF-T4-EXP09 pilot launcher (ws58, 2026-11-02). Engine: filler_run15.sh. One CPU quarter, <=45 min.
# The job starts its OWN llama-server (production-consolidated-v10 kernel store, worker model) on the granted CPUs
# and port 18409, registers its pid in FILLER_PIDFILE, and stops it on exit. Scratch: /mnt/raid0/llm/tmp/brf-exp09-answerbudget-r2.
set -euo pipefail
D=/mnt/raid0/llm/tmp/brf-exp09-answerbudget-r2
PY=/mnt/raid0/llm/tmp/brf-exp09/pyenv/venv/bin/python  # pinned existing experiment venv; no venv copied into this bundle
printf '%s  %s\n' 130fb4248d9b093584f82cb81d5942c22f5231595678b677b21ed02ba79c55c5 "$D/job.py" | sha256sum -c --quiet -
printf '%s  %s\n' 6192e99a8422fbe965673338fe14a35ac7f422720ebb0716b65fcf682be3acf2 "$D/identity.json" | sha256sum -c --quiet -
printf '%s  %s\n' e17a230f33f8f8cdce9b2f5c04b86b33ac88bc7a553d59da50481366422e1b85 "$D/corpus/MANIFEST.json" | sha256sum -c --quiet -
export EXP09_CAP_S=2700
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id brf-exp09-answerbudget-r2-20261104 --class cpu --role build --gpu-quiet none --port 18419 --min-window 2700 --stop "$D/STOP" --workdir "$D" --precond-cmd "$PY $D/job.py --check" --cmd "exec $PY $D/job.py" --complete-cmd "test -s $D/out/COMPLETE"
