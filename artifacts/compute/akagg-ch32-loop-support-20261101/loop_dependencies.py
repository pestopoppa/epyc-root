#!/usr/bin/env python3
"""Verify bounded C5/B1/B2 loop-support dependencies using Git objects only.
Usage: python3 loop_dependencies.py OUTPUT.json
Does not compile or prove model functionality or minimum whole-commit chain.
"""
import json, subprocess, sys
repo='/mnt/raid0/llm/llama.cpp'
c5='c72ec82f5417bb2937310326120f149b665e8400';b1='b77d646751d01c0962bc203b6809e9d94f7d50b7';b2='e79d8cab590ae0a040e1562d09e46b0bfab8cc2d'
def git(*args):
 p=subprocess.run(['git','-C',repo,*args],capture_output=True,text=True)
 if p.returncode not in (0,1):raise RuntimeError((args,p.returncode,p.stderr))
 return p.stdout,p.returncode
checks=[('runtime_key','LLM_KV_NUM_LOOPS','src/llama-arch.h','src/models/ouro.cpp'),('conversion_writer','add_num_loops','gguf-py/gguf/gguf_writer.py','conversion/ouro.py'),('conversion_writer','add_skip_loop_final_norm','gguf-py/gguf/gguf_writer.py','conversion/ouro.py'),('conversion_key','NUM_LOOPS','gguf-py/gguf/constants.py','conversion/ouro.py'),('conversion_key','SKIP_LOOP_FINAL_NORM','gguf-py/gguf/constants.py','conversion/ouro.py')]
result=[]
for kind,token,definition_path,use_path in checks:
 item={'kind':kind,'token':token,'definition_path':definition_path,'use_path':use_path,'definition':{}}
 for n,r in [('C5',c5),('B1_parent',b1+'^'),('B1',b1),('B2_parent',b2+'^'),('B2',b2)]:
  text,rc=git('grep','-n','-w','-F',token,r,'--',definition_path)
  item['definition'][n]={'present':rc==0,'lines':text.splitlines()}
 text,rc=git('grep','-n','-w','-F',token,b2,'--',use_path)
 item['B2_use']={'present':rc==0,'lines':text.splitlines()}
 patch,_=git('diff','--no-ext-diff','--unified=3',b1+'^',b1,'--',definition_path)
 item['B1_added_lines']=[line for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++') and token in line]
 patch,_=git('diff','--no-ext-diff','--unified=3',b2+'^',b2,'--',definition_path)
 item['B2_added_definition_lines']=[line for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++') and token in line]
 result.append(item)
_,rc=git('merge-base','--is-ancestor',b1,b2+'^')
json.dump({'C5':c5,'B1':b1,'B2':b2,'B1_ancestor_B2_parent':rc==0,'scope':'Exact-token presence in listed files and direct patch-added lines only. Shared functionality, not necessarily entire B1, must be supplied for the unchanged Ouro port. This is not a build, runtime or complete minimal-dependency proof.','checks':result},open(sys.argv[1],'w'),indent=2)
