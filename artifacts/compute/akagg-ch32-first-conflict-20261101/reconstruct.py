#!/usr/bin/env python3
"""Reconstruct group-first merge conflicts from retained staged blob IDs.
Usage: python3 reconstruct.py LOG_DIR OUTPUT_DIR
Only reads the object database; writes temporary blob files in OUTPUT_DIR and emits
JSON plus conflict-only excerpts. It does not mutate an index, ref, or source tree.
"""
import json,pathlib,re,subprocess,sys,tempfile
repo='/mnt/raid0/llm/llama.cpp';source=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
result={}
for group,first in [('B','B1'),('C','C1'),('D','D1')]:
 text=(source/f'group-{group}-{first}.log').read_text(); stages={}
 for mode,sha,stage,path in re.findall(r'^([0-7]{6}) ([a-f0-9]{40}) ([123])\t(.*)$',text,re.M): stages.setdefault(path,{})[int(stage)]=sha
 found=[]
 for path,blob in sorted(stages.items()):
  if set(blob)!={1,2,3}:raise ValueError((path,blob))
  with tempfile.TemporaryDirectory(dir=out) as td:
   t=pathlib.Path(td); files=[]
   for stage in (2,1,3):
    p=t/str(stage);p.write_bytes(subprocess.check_output(['git','-C',repo,'cat-file','blob',blob[stage]]));files.append(str(p))
   proc=subprocess.run(['git','merge-file','--diff3','-p','-L','C5','-L','upstream-parent','-L',first,*files],capture_output=True)
   if proc.returncode not in range(0,128):raise ValueError((path,proc.returncode,proc.stderr.decode(errors='replace')))
   merged=proc.stdout.decode('utf-8',errors='replace');chunks=re.findall(r'^<<<<<<< C5\n.*?^>>>>>>> '+first+r'\n',merged,re.M|re.S)
   if len(chunks)!=proc.returncode:raise ValueError((path,proc.returncode,len(chunks)))
   found.append({'path':path,'base_blob':blob[1],'c5_blob':blob[2],'feature_blob':blob[3],'conflict_hunks':len(chunks),'conflicts':chunks})
 result[group]={'first_patch':first,'files':found}
(out/'FIRST-PATCH-CONFLICTS.json').write_text(json.dumps({'scope':'Reconstruction from recorded merge stages, git merge-file --diff3. Conflict hunks are context, not proof of actual commit prerequisites or feature semantics.','groups':result},indent=2)+'\n')
