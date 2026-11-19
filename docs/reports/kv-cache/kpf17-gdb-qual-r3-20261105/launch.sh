#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf17-gdb-continue-qual-r3-20261105
ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh
EXPECTED_SEAL_SHA256=0c13750d86f4571ff647241d47faff625373e35dce349f7b8b033460b92f113b
[[ "$(sha256sum "$D/SEALED.sha256" | awk '{print $1}')" == "$EXPECTED_SEAL_SHA256" ]] || { echo 'sealed input manifest digest mismatch' >&2; exit 2; }
(cd "$D" && sha256sum -c SEALED.sha256)
export KPF17Q_ATTEMPT_ID=kvfork17-gdb-continue-qual-r3-20261105-attempt-a742c
export KPF17Q_ATTEMPT_NONCE=a742c-r3-qualification-20261105
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
  : "${FILLER_DRYRUN_RESULT_PATH:?smoke/dryrun requires FILLER_DRYRUN_RESULT_PATH}"
  [[ "$(realpath -m "$FILLER_DRYRUN_RESULT_PATH")" != "$(realpath -m "$D/out/full-attempt-kvfork17-gdb-continue-qual-r3-20261105-a742c/RESULT.json")" ]] || { echo 'smoke result collides with full attempt' >&2; exit 2; }
  [[ ! -e "$FILLER_DRYRUN_RESULT_PATH" && ! -L "$FILLER_DRYRUN_RESULT_PATH" ]] || { echo 'refusing smoke result collision' >&2; exit 2; }
  export KPF17Q_OUT="$FILLER_DRYRUN_RESULT_PATH"
else
  export KPF17Q_OUT="$D/out/full-attempt-kvfork17-gdb-continue-qual-r3-20261105-a742c/RESULT.json"
  [[ ! -e "$KPF17Q_OUT" && ! -L "$KPF17Q_OUT" ]] || { echo 'refusing full result collision' >&2; exit 2; }
fi
exec /bin/bash "$ENGINE" --id kvfork17-gdb-continue-qual-r3-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" \
  --complete-cmd "if [[ \${FILLER_SMOKE:-0} == 1 || \${FILLER_DRYRUN:-0} == 1 ]]; then test -s \"\${FILLER_DRYRUN_RESULT_PATH:-/nonexistent}\" && KPF17Q_ATTEMPT_ID='$KPF17Q_ATTEMPT_ID' KPF17Q_ATTEMPT_NONCE='$KPF17Q_ATTEMPT_NONCE' python3 '$D/qualify.py' --validate-result \"\${FILLER_DRYRUN_RESULT_PATH:-/nonexistent}\"; else test -s '$D/out/full-attempt-kvfork17-gdb-continue-qual-r3-20261105-a742c/RESULT.json' && python3 '$D/qualify.py' --validate-result '$D/out/full-attempt-kvfork17-gdb-continue-qual-r3-20261105-a742c/RESULT.json'; fi" \
  --cmd "python3 '$D/qualify.py'"
