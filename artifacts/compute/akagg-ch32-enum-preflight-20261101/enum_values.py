#!/usr/bin/env python3
"""Read pinned ggml.h objects and derive literal enum/macro values, no checkout/build.
Usage: python3 enum_values.py SUMMARY.json OUTPUT.json
Refuses unsupported enum expressions. Different enum ordinals are not a verdict about a source port.
"""
import json,re,subprocess,sys
repo='/mnt/raid0/llm/llama.cpp';base='c72ec82f5417bb2937310326120f149b665e8400'
groups=json.load(open(sys.argv[1]))['groups']; refs={'C5':base,**{k:v['commit']+'^' for k,v in groups.items()}}
types=['GGML_TYPE_F32','GGML_TYPE_F16','GGML_TYPE_I32','GGML_TYPE_I64']; op=['GGML_OP_MUL_MAT'];macros=['GGML_MROPE_SECTIONS','GGML_ROPE_TYPE_NORMAL','GGML_ROPE_TYPE_NEOX','GGML_ROPE_TYPE_VISION']
def enum_values(text,name):
 m=re.search(r'\benum\s+'+re.escape(name)+r'\s*\{(.*?)\}\s*;',text,re.S)
 if not m:raise ValueError('missing enum '+name)
 body=re.sub(r'/\*.*?\*/|//[^\n]*','',m.group(1),flags=re.S);n=-1;out={}
 for part in body.split(','):
  part=part.strip()
  if not part:continue
  m=re.fullmatch(r'(GGML_[A-Z0-9_]+)(?:\s*=\s*(\d+))?',part)
  if not m:raise ValueError(f'unsupported enum element: {part!r}')
  n=int(m.group(2)) if m.group(2) is not None else n+1;out[m.group(1)]=n
 return out
out={}
for label,ref in refs.items():
 commit=subprocess.check_output(['git','-C',repo,'rev-parse',ref],text=True).strip()
 text=subprocess.check_output(['git','-C',repo,'show',commit+':ggml/include/ggml.h'],text=True)
 e={**enum_values(text,'ggml_op'),**enum_values(text,'ggml_type')}; vals={k:e[k] for k in types+op}
 for macro in macros:
  m=re.search(r'^\s*#\s*define\s+'+re.escape(macro)+r'\s+(\d+)\s*$',text,re.M)
  if not m:raise ValueError('missing/nonliteral macro '+macro+' at '+commit)
  vals[macro]=int(m.group(1))
 out[label]={'commit':commit,'values':vals}
json.dump({'base':base,'scope':'Parses literal enum ordinals and four literal macro values in pinned headers. No binary compatibility, backend behavior or source-port verdict follows.','refs':out},open(sys.argv[2],'w'),indent=2)
