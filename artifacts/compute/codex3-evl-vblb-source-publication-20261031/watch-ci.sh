#!/bin/bash
set -euo pipefail
packet=/mnt/raid0/llm/tmp/codex3-evl-vblb-source-publish-20261031
printf '%s\n' "$$" > "$packet/ci-watch.pid"
watch_rc=0
gh run watch 41202443172 --repo pestopoppa/epyc-root --exit-status --interval 20 > "$packet/ci-source-watch.log" 2>&1 || watch_rc=$?
gh run view 41202443172 --repo pestopoppa/epyc-root --json status,conclusion,headSha,url > "$packet/CI-TERMINAL.tmp.json"
python3 - <<'PY'
import json,pathlib
p=pathlib.Path('/mnt/raid0/llm/tmp/codex3-evl-vblb-source-publish-20261031')
r=json.loads((p/'CI-TERMINAL.tmp.json').read_text())
assert r['headSha']=='1103bccc540a04c535a5fa3baf7a81cdea512595',r
assert r['status']=='completed',r
(p/'CI-TERMINAL.tmp.json').replace(p/'CI-TERMINAL.json')
PY
exit "$watch_rc"
