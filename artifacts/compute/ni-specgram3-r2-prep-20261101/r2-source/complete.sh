#!/bin/bash
set -euo pipefail
if [[ ${WS58_QUAL:-0} == 1 ]]; then
  : "${FILLER_RESULTS_DIR:?qualification result namespace missing}"
  /usr/bin/python3 -I - "$FILLER_RESULTS_DIR/QUAL-RESULT.json" <<'PY'
import json,sys
p=sys.argv[1]
d=json.load(open(p))
assert d.get('complete') is True
assert isinstance(d.get('first_request'),dict) and d['first_request'].get('ok') is True
PY
  exit 0
fi
/usr/bin/python3 -I - /mnt/raid0/llm/tmp/codex-ni-specgram3-repair-20261101/cpu-r2-20261101/out/RESULT.json <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))['complete'] is True
PY
