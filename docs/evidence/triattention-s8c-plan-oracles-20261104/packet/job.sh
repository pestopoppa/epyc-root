#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/triattention-s8c-plan-oracles-20261104
[[ ! -e ${FILLER_STOPFILE:?} && $(date +%s) -lt ${FILLER_DEADLINE:?} ]] || exit 75
python3 - "$R/input-pins.json" <<'PY2'
import hashlib,json,pathlib,sys
x=json.load(open(sys.argv[1]));assert x['base_commit']=='ffc1bac82eeca6f9099e1ccd9ba49703c460a115' and x['patch_sha256']=='e7be5790af2d0fc132f9242473a768bdcb3e5b3991eaacef2711f5b30bbe8dca'
for name,h in x['headers'].items():assert hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()==h,name
PY2
mkdir -p "$R/output"
g++ -std=c++17 -O2 -I "$R/include" "$R/packet/plan_test.cpp" -o "$R/output/plan-test"
[[ ! -e $FILLER_STOPFILE && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75
set +e
"$R/output/plan-test" > "$R/output/cases.jsonl" 2> "$R/output/stderr.txt"
rc=$?
set -e
python3 - "$R" "$rc" <<'PY3'
import hashlib,json,pathlib,sys
r=pathlib.Path(sys.argv[1]);rc=int(sys.argv[2]); cases=[json.loads(x) for x in (r/'output/cases.jsonl').read_text().splitlines()];assert len(cases)==26 and len({x['case'] for x in cases})==26 and rc in (0,1)
failed=[x['case'] for x in cases if not x['pass']];assert (rc==0)==(not failed)
result={'unit':'s8c-planner-oracles','status':'fail' if failed else 'pass','count':len(cases),'failed_cases':failed,'base_commit':'ffc1bac82eeca6f9099e1ccd9ba49703c460a115','patch_sha256':'e7be5790af2d0fc132f9242473a768bdcb3e5b3991eaacef2711f5b30bbe8dca','cases_sha256':hashlib.sha256((r/'output/cases.jsonl').read_bytes()).hexdigest(),'test_binary_sha256':hashlib.sha256((r/'output/plan-test').read_bytes()).hexdigest(),'scope':'header-only planner on synthetic cells; no model, actual eviction, server lifecycle, inference, quality, GPU or speed claim'}
(r/'results.jsonl').write_text(json.dumps(result,sort_keys=True)+'\n');(r/'complete').touch()
PY3
