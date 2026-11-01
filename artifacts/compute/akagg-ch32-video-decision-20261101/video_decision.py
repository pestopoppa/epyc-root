#!/usr/bin/env python3
"""Read-only CH-32 D8 video/decision context; usage: python3 video_decision.py OUTPUT.json.
Pinned Git objects only. Ancestry/context does not prove whole-commit necessity.
"""
import json,subprocess,sys
r='/mnt/raid0/llm/llama.cpp'
refs={'C5':'c72ec82f5417bb2937310326120f149b665e8400','C1':'a4cb4c61fd9d9c2066c7c1747821d3d65b8943bd','C2':'7e3eeee0480902c90cbdff172f407dc063cf0770','D3':'19cce6919992fdffd92e0ac152caaf1e2b8f254e','d1_model':'d05706b4f32a545814856e98ca518292585443b9','D8':'d4f1b18b3a1522eec48decbe9ff7dc66eb60a9f4'}
def git(*args,allow=(0,)):
 p=subprocess.run(['git','-C',r,*args],capture_output=True,text=True)
 if p.returncode not in allow:raise RuntimeError((args,p.returncode,p.stderr))
 return p.stdout,p.returncode
def ancestor(a,b):return git('merge-base','--is-ancestor',a,b,allow=(0,1))[1]==0
history,_=git('log','--first-parent','--reverse','--format=%H %s','-S','is_lfm3_d1',refs['D8']+'^','--','tools/server/server-decision.cpp')
paths=['common/common.h','conversion/lfm3.py','src/models/lfm3.cpp','tools/server/server-decision.cpp','tools/server/server-decision.h']
files={}
for label,ref in [('C5',refs['C5']),('C1',refs['C1']),('D3',refs['D3']),('d1_parent',refs['d1_model']+'^'),('d1_model',refs['d1_model']),('D8_parent',refs['D8']+'^'),('D8',refs['D8'])]:
 files[label]={}
 for path in paths:
  _,rc=git('cat-file','-e',ref+':'+path,allow=(0,1,128))
  files[label][path]=rc==0
patch,_=git('diff','--no-ext-diff','--unified=3',refs['D8']+'^',refs['D8'],'--','tools/server/server-decision.cpp')
changes,_=git('diff','--numstat',refs['d1_model']+'^',refs['d1_model'])
nums=[line.split('\t',2) for line in changes.splitlines()]
assert all(a.isdigit() and b.isdigit() for a,b,_ in nums)
D={'refs':refs,'scope':'Exact upstream ancestry, path-existence and source-diff context. Hand ports may adapt or intentionally scope out a surface; no minimum whole-commit requirement, ABI, build or runtime conclusion.', 'ancestry':{'C1_before_d1_parent':ancestor(refs['C1'],refs['d1_model']+'^'),'C2_before_d1_parent':ancestor(refs['C2'],refs['d1_model']+'^'),'D3_before_d1_parent':ancestor(refs['D3'],refs['d1_model']+'^'),'d1_before_D8_parent':ancestor(refs['d1_model'],refs['D8']+'^'),'d1_before_C5':ancestor(refs['d1_model'],refs['C5'])},'first_parent_is_lfm3_d1_history':history.splitlines(),'paths':files,'d1_numstat':{'files':len(nums),'added':sum(int(a) for a,b,p in nums),'deleted':sum(int(b) for a,b,p in nums),'entries':nums},'D8_decision_patch':patch}
json.dump(D,open(sys.argv[1],'w'),indent=2)
