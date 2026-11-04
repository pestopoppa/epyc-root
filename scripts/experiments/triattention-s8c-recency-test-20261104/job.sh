#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/triattention-s8c-recency-test-20261104
P="$R/packet"
[[ ! -e ${FILLER_STOPFILE:?} && $(date +%s) -lt ${FILLER_DEADLINE:?} ]] || exit 75
python3 - "$R/candidate-pin.json" <<'PY'
import hashlib,json,pathlib,sys
p=json.load(open(sys.argv[1]));assert p['base_commit']=='ffc1bac82eeca6f9099e1ccd9ba49703c460a115' and p['patch_sha256']=='7a0c3a7f3cffb3317330cc7efdf9dfe0b3981e2c6c54183610a83be4e1b82f35'
for name,h in p['files'].items():assert hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()==h,name
PY
mkdir -p "$R/output"
unset LD_PRELOAD GGML_BACKEND_PATH
export LD_LIBRARY_PATH="$R/pinned-build/bin"
g++ -std=c++17 -O2 -rdynamic -I "$R/include" "$P/recency_test.cpp" -L "$R/pinned-build/bin" -Wl,-rpath,"$R/pinned-build/bin" -lllama -o "$R/output/recency-test"
/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$R/output/recency-test" "$R/pinned-build" > "$R/output/linkage.txt"
[[ ! -e $FILLER_STOPFILE && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75
set +e
"$R/output/recency-test" > "$R/output/cases.jsonl" 2> "$R/output/stderr.txt"
rc=$?
set -e
python3 - "$R" "$rc" <<'PY'
import hashlib,json,pathlib,sys
r=pathlib.Path(sys.argv[1]);rc=int(sys.argv[2]);lines=(r/'output/cases.jsonl').read_text().splitlines();cases=[json.loads(x) for x in lines]
expected={'legacy_default','recent_absolute','recent_ratio','overlap_budget','legacy_ties','legacy_full_compression','all_sink','conflicting_controls','invalid_nan','gapped_kv_accounting','seq_rm_failure'}
assert len(cases)==len(expected) and {x['case'] for x in cases}==expected and rc in (0,1), 'incomplete harness execution'
assert (rc==0)==all(x['pass'] for x in cases)
result={'unit':'recency-eviction-mock-memory','status':'pass' if rc==0 else 'fail','failed_cases':[x['case'] for x in cases if not x['pass']], 'candidate_pin':str(r/'candidate-pin.json'),'cases_sha256':hashlib.sha256((r/'output/cases.jsonl').read_bytes()).hexdigest(),'test_binary_sha256':hashlib.sha256((r/'output/recency-test').read_bytes()).hexdigest(),'scope':'Actual compiled eviction with injected deterministic scores and mocked memory; no real model, cache, server API, quality, performance, or deployment claim.'}
(r/'results.jsonl').write_text(json.dumps(result,sort_keys=True)+'\n');(r/'complete').touch()
PY
