#!/bin/bash
# usage: run.sh <gitnexus-package-root> <fresh-workdir>
# Indexes fixture/kern.cu in an isolated GITNEXUS_HOME and asserts:
#   1. flash_attn_ext_vec (template<> __launch_bounds__(..) static __global__) is a Function node,
#      and no symbol is named __launch_bounds__;
#   2. launch_direct has CALLS edges to flash_attn_ext_vec and plain_kernel (<<<>>> launches);
#   3. case_impl / fused (kernel handle `k = flash_attn_ext_vec<..>` passed to a launcher) CALL the kernel.
# Exit 0 = PASS, 1 = FAIL. Expected: FAIL on unpatched 1.6.8, PASS after fix.patch.
set -euo pipefail
pkg=${1:?package root}; work=${2:?fresh workdir}
here=$(cd -- "$(dirname -- "$0")" && pwd)
[[ ! -e "$work" ]] || { echo "workdir must not exist: $work" >&2; exit 2; }
mkdir -p "$work/repo"; cp "$here/kern.cu" "$work/repo/"
cd "$work/repo"; git init -q; git add kern.cu; git -c user.email=fx@local -c user.name=fx commit -qm fx
export GITNEXUS_HOME="$work/home" GITNEXUS_REPO_NAME="cudafx"
node "$pkg/dist/cli/index.js" analyze --skip-agents-md --skip-skills --workers 1 --force > "$work/analyze.log" 2>&1
node "$pkg/dist/cli/index.js" cypher "MATCH (a)-[r:CodeRelation]->(b) RETURN a.id AS src, r.type AS t, b.id AS dst" > "$work/edges.json"
python3 - "$work/edges.json" <<'PY'
import json,sys
j=json.load(open(sys.argv[1])); md=j.get("markdown","") if isinstance(j,dict) else ""
rows=[[c.strip() for c in l.strip('|').split('|')] for l in md.splitlines()[2:]]
name=lambda x: x.split(':',2)[-1].split('~')[0]
calls={(name(s),name(d)) for s,t,d in rows if t=='CALLS'}
defs={d for s,t,d in rows if t=='DEFINES'}
checks={
 "kernel_indexed": any(x.startswith('Function:kern.cu:flash_attn_ext_vec') for x in defs),
 "no_launch_bounds_symbol": not any('__launch_bounds__' in x for x in defs),
 "launch_calls_template_kernel": ('launch_direct','flash_attn_ext_vec') in calls,
 "launch_calls_plain_kernel": ('launch_direct','plain_kernel') in calls,
 "handle_ref_init_declarator": ('case_impl','flash_attn_ext_vec') in calls,
 "handle_ref_auto": ('fused','flash_attn_ext_vec') in calls,
}
ok=all(checks.values()); print(json.dumps({"result":"PASS" if ok else "FAIL",**checks}))
sys.exit(0 if ok else 1)
PY
