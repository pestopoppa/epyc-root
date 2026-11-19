#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf17-gdb-continue-qual-r2-20261104
ENGINE=/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh
EXPECTED_SEAL_SHA256=b14ce65570f29e31d9891d1920b2b5b96b9df88b85c670b818554ddfad0783ae
[[ "$(sha256sum "$D/SEALED.sha256" | awk '{print $1}')" == "$EXPECTED_SEAL_SHA256" ]] || { echo 'sealed input manifest digest mismatch' >&2; exit 2; }
(cd "$D" && sha256sum -c SEALED.sha256)
export KPF17Q_ATTEMPT_ID=kvfork17-gdb-continue-qual-r2-20261104-attempt-7f3a91c6
export KPF17Q_ATTEMPT_NONCE=7f3a91c6-6d24-4c88-b0f1-a13fe8c5198a
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
  : "${FILLER_DRYRUN_RESULT_PATH:?smoke/dryrun requires FILLER_DRYRUN_RESULT_PATH}"
  [[ "$(realpath -m "$FILLER_DRYRUN_RESULT_PATH")" != "$(realpath -m "$D/out/full-attempt-kvfork17-gdb-continue-qual-r2-20261104-7f3a91c6/RESULT.json")" ]] || { echo 'smoke result collides with full attempt' >&2; exit 2; }
  [[ ! -e "$FILLER_DRYRUN_RESULT_PATH" && ! -L "$FILLER_DRYRUN_RESULT_PATH" ]] || { echo 'refusing smoke result collision' >&2; exit 2; }
  export KPF17Q_OUT="$FILLER_DRYRUN_RESULT_PATH"
else
  export KPF17Q_OUT="$D/out/full-attempt-kvfork17-gdb-continue-qual-r2-20261104-7f3a91c6/RESULT.json"
  [[ ! -e "$KPF17Q_OUT" && ! -L "$KPF17Q_OUT" ]] || { echo 'refusing full result collision' >&2; exit 2; }
fi
exec /bin/bash "$ENGINE" --id kvfork17-gdb-continue-qual-r2-20261104 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" \
  --complete-cmd "if [[ \${FILLER_SMOKE:-0} == 1 || \${FILLER_DRYRUN:-0} == 1 ]]; then test -s \"\${FILLER_DRYRUN_RESULT_PATH:-/nonexistent}\" && KPF17Q_ATTEMPT_ID='$KPF17Q_ATTEMPT_ID' KPF17Q_ATTEMPT_NONCE='$KPF17Q_ATTEMPT_NONCE' python3 '$D/qualify.py' --validate-result \"\${FILLER_DRYRUN_RESULT_PATH:-/nonexistent}\"; else test -s '$D/out/full-attempt-kvfork17-gdb-continue-qual-r2-20261104-7f3a91c6/RESULT.json' && python3 '$D/qualify.py' --validate-result '$D/out/full-attempt-kvfork17-gdb-continue-qual-r2-20261104-7f3a91c6/RESULT.json'; fi" \
  --cmd "python3 '$D/qualify.py'"
