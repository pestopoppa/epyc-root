#!/usr/bin/env python3
"""Text-compare selected ggml function implementations from pinned Git objects.
Usage: python3 compare_impl.py OUTPUT.json
This lightweight parser refuses ambiguous definitions, ignores comments/string literals while
balancing braces; it is not a C/C++ compiler or a semantic comparison.
"""
import difflib,hashlib,json,re,subprocess,sys
R='/mnt/raid0/llm/llama.cpp';C5='c72ec82f5417bb2937310326120f149b665e8400';P='2851b3bcbf8d993a2243ae751c0a7dfa8e944a40^'
def git(*x):return subprocess.check_output(['git','-C',R,*x],text=True)
def mask(s):
 pat=r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
 return re.sub(pat,lambda m:''.join('\n' if c=='\n' else ' ' for c in m.group()),s,flags=re.S)
def function(text,name):
 clean=mask(text);matches=list(re.finditer(r'\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',clean,re.S))
 if len(matches)!=1:raise ValueError(f'{name}: expected one definition, got {len(matches)}')
 m=matches[0];pos=clean.find('{',m.start());depth=1;i=pos+1
 while i<len(clean) and depth:
  depth+=(clean[i]=='{')-(clean[i]=='}');i+=1
 if depth:raise ValueError('unbalanced '+name)
 return text[m.start():i]
checks=[('ggml/src/ggml.c',x) for x in ('ggml_set_rows','ggml_conv_1d','ggml_gelu_erf','ggml_rope_ext','ggml_new_tensor_2d','ggml_view_2d','ggml_get_rows','ggml_concat')]
checks += [('ggml/src/ggml-cpu/ops.cpp','ggml_compute_forward_set_rows'),('ggml/src/ggml-cuda/set-rows.cu','ggml_cuda_op_set_rows')]
cache={};result=[]
for path,name in checks:
 vals={}
 for label,ref in [('C5',C5),('D1_parent',P)]:
  key=(ref,path)
  if key not in cache:cache[key]=git('show',ref+':'+path)
  body=function(cache[key],name);vals[label]={'sha256':hashlib.sha256(body.encode()).hexdigest(),'body':body}
 a=vals['C5']['body'];b=vals['D1_parent']['body']
 result.append({'path':path,'function':name,'c5_sha256':vals['C5']['sha256'],'upstream_parent_sha256':vals['D1_parent']['sha256'],'byte_identical':a==b,'diff':list(difflib.unified_diff(a.splitlines(),b.splitlines(),fromfile='C5/'+name,tofile='D1_parent/'+name,lineterm=''))})
json.dump({'C5':C5,'D1_parent':git('rev-parse',P).strip(),'scope':'Exact function-body text, lexical parser. Changes in helpers, compile flags, kernels and dependent structures are not included; absence of a diff is not semantic/runtime evidence.', 'checks':result},open(sys.argv[1],'w'),indent=2)
