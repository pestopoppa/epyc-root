#!/usr/bin/env python3
"""Compare public-header return declaration prefixes textually for added ggml function tokens.
Usage: python3 return_scan.py SUMMARY.json TOKENS.json OUTPUT.json
Results are textual hints, not ABI proof. Git object reads only.
"""
import json,re,subprocess,sys
repo='/mnt/raid0/llm/llama.cpp';base='c72ec82f5417bb2937310326120f149b665e8400'
def git(*x):return subprocess.check_output(['git','-C',repo,*x],text=True,errors='replace')
def declarations(rev):
 r={}
 for f in git('ls-tree','-r','--name-only',rev,'ggml/include','include').splitlines():
  if not f.endswith('.h'):continue
  text=git('show',f'{rev}:{f}')
  text=re.sub(r'/\*.*?\*/|//[^\n]*',' ',text,flags=re.S)
  for m in re.finditer(r'(?m)^([^\n;{}#]*?\b(ggml_[A-Za-z0-9_]+)\s*\(([^;{}]*)\)\s*;)',text):
   prefix=m.group(1).split(m.group(2),1)[0];prefix=re.sub(r'\s+',' ',prefix).strip()
   r.setdefault(m.group(2),[]).append({'file':f,'prefix':prefix})
 return r
S=json.load(open(sys.argv[1]))['groups'];T=json.load(open(sys.argv[2]));b=declarations(base);out={}
for k,v in S.items():
 t=set(T[k]['introduced_ggml_tokens']); upstream=declarations(v['commit']+'^');both=sorted(t & b.keys() & upstream.keys()); delta={name:{'c5':b[name],'upstream_parent':upstream[name]} for name in both if b[name]!=upstream[name]}
 out[k]={'commit':v['commit'],'compared':both,'non_function_or_not_extracted':sorted(t-set(both)),'differences':delta}
json.dump({'base':base,'limitations':'Regex source declaration prefixes only; attributes/macros, definitions, calling conventions, binary layouts and behavior are not validated.', 'groups':out},open(sys.argv[3],'w'),indent=2)
