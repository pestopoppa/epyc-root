#!/usr/bin/env python3
"""Read pinned git objects to check C2 decision-context source dependencies."""
import json
import subprocess
REPO='/mnt/raid0/llm/llama.cpp'
C5='c72ec82f5417bb2937310326120f149b665e8400'
C1='a4cb4c61fd9d9c2066c7c1747821d3d65b8943bd'
C2='7e3eeee0480902c90cbdff172f407dc063cf0770'
ITEMS={
 'COMMON_DECISION_TYPE_LFM2_D1_OMNI':'a657f7e981ff8764d2ccce1e74ec3c7e9bf2cfa2',
 'COMMON_DECISION_TYPE_VLLM_D3':'efe3626b119ff81033e309c3ba07a770bef2c546',
 'COMMON_DECISION_TYPE_GRANITE_SWITCH':'23f7aabc16c72f6f707dba227251c35d7bd1ed96',
}
def git(*args):return subprocess.check_output(['git','-C',REPO,*args],text=True)
def show(rev,path):return git('show',f'{rev}:{path}')
def ancestor(a,b):
 rc=subprocess.run(['git','-C',REPO,'merge-base','--is-ancestor',a,b]).returncode
 if rc not in (0,1):raise RuntimeError(f'ancestry error {rc}')
 return rc==0
header='common/common.h';src='tools/server/server-decision.cpp'
c5,c1,parent,current=(show(r,header) for r in (C5,C1,C2+'^',C2))
code=show(C2,src);patch=git('show','--format=',C2,'--',src)
assert ancestor(C1,C2)
evidence={}
for symbol,commit in ITEMS.items():
 prior=show(commit+'^',header);introduced=show(commit,header)
 assert symbol not in c5 and symbol not in c1 and symbol not in prior
 assert symbol in introduced and symbol in parent and symbol in current and symbol in code
 assert symbol in patch and ancestor(C1,commit) and ancestor(commit,C2+'^')
 evidence[symbol]={'introduced_by':commit,'absent_c5_and_c1':True,'present_c2_parent_and_c2':True,'c2_source_and_patch_context_reference':True}
print(json.dumps({'schema':'akagg.ch32.c2-decision-context.v1','revisions':{'c5':C5,'c1':C1,'c2':C2},'enum_evidence':evidence,'scope':'Unchanged C2 decision source references these preexisting types. Equivalent source or a modified port is required; whole upstream commits and behavioral compatibility are not proven minimal.'},indent=2,sort_keys=True))
