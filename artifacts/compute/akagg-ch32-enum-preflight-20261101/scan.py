#!/usr/bin/env python3
"""Read-only lexical preflight of GGML_* uppercase symbols introduced by CH-32 patches.
Usage: python3 scan.py SUMMARY.json OUT.json
Requires pinned git objects; flags lexical absence, not a compile or semantic check.
"""
import json,re,subprocess,sys
repo='/mnt/raid0/llm/llama.cpp'
base='c72ec82f5417bb2937310326120f149b665e8400'
def git(*args): return subprocess.check_output(['git','-C',repo,*args],text=True,errors='replace')
# Index all C5 tracked text containing tokens, not only headers; inclusion alone is not declaration proof.
base_text=git('grep','-h','-I','-E',r'GGML_[A-Z0-9_]+',base,'--','.'); base_tokens=set(re.findall(r'\bGGML_[A-Z0-9_]+\b',base_text))
groups=json.load(open(sys.argv[1]))['groups']; result={}
for key,info in groups.items():
 c=info['commit']; d=git('diff','--no-ext-diff','--unified=0',c+'^',c,'--','.')
 added='\n'.join(x[1:] for x in d.splitlines() if x.startswith('+') and not x.startswith('+++'))
 tokens=sorted(set(re.findall(r'\bGGML_[A-Z0-9_]+\b',added)))
 missing=sorted(set(tokens)-base_tokens)
 evidence={}
 for token in missing:
  hits=[]
  for line in d.splitlines():
   if line.startswith('+++ b/'): path=line[6:]
   elif line.startswith('+') and not line.startswith('+++') and re.search(r'\b'+re.escape(token)+r'\b',line): hits.append({'path':path,'line':line[1:][:300]})
  evidence[token]=hits[:12]
 result[key]={'commit':c,'introduced_tokens':tokens,'absent_from_c5_all_tracked_text':missing,'example_added_lines':evidence}
json.dump({'base':base,'scope':'Lexical diff scan; comments, strings, deleted context, generated code and declarations are not type checked. Absence is not proof of a needed ggml bump or inability to hand-port; presence is not compatibility.','groups':result},open(sys.argv[2],'w'),indent=2)
