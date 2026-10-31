#!/bin/bash
set -euo pipefail
test "$(git rev-parse --show-toplevel)" = /mnt/micron/codex3-lanes/root
test -z "$(git status --porcelain)"
git checkout -b codex3/evl-vblb-source-20261031 origin/main
git merge --no-commit --no-ff e4adf8d645d6b6ac9f26c680cd07f63928e0333c
git -c core.hooksPath=/mnt/raid0/llm/epyc-root/.git/hooks commit -m "Integrate duplicate-frame repair and prospective dev-harness capture"
git diff --check origin/main..HEAD
python3 - <<'PY'
import hashlib,json,pathlib,subprocess
p=pathlib.Path('/mnt/raid0/llm/tmp/codex3-evl-vblb-source-publish-20261031')
r=json.loads((p/'integration-receipt.json').read_text())
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
base=subprocess.check_output(['git','rev-parse','origin/main'],text=True).strip()
names=subprocess.check_output(['git','diff','--name-only',base,head],text=True).splitlines()
assert set(names)=={x['path'] for x in r['files']},names
for f in r['files']:
    raw=subprocess.check_output(['git','show',head+':'+f['path']])
    assert hashlib.sha256(raw).hexdigest()==f['sha256'],f
(p/'final-private-candidate.json').write_text(json.dumps({'candidate':head,'base_main':base,'approved_preliminary':'e4adf8d645d6b6ac9f26c680cd07f63928e0333c','source_file_count':len(names),'source_bytes_match_integration_receipt':True,'normal_precommit_hook':'/mnt/raid0/llm/epyc-root/.git/hooks/pre-commit','publication':False},indent=2)+'\n')
print(head)
PY
