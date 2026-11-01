#!/usr/bin/env python3
"""Compare C5 vs D4-parent GPU CONV_2D eligibility source; no build or checkout.
Usage: python3 conv2d_eligibility.py OUTPUT.json
Explicitly bounded source text; no inference about actual tensor layouts or device execution.
"""
import json,re,subprocess,sys
R='/mnt/raid0/llm/llama.cpp';base='c72ec82f5417bb2937310326120f149b665e8400';feature='19ff817fb25e9a1b838b1d7f9f4325f7bf9779c4';fix='958d9c0b61d'
def git(*a,allow=(0,)):
 p=subprocess.run(['git','-C',R,*a],capture_output=True,text=True)
 if p.returncode not in allow:raise RuntimeError((a,p.returncode,p.stderr))
 return p.stdout,p.returncode
def anc(a,b):return git('merge-base','--is-ancestor',a,b,allow=(0,1))[1]==0
parent=git('rev-parse',feature+'^')[0].strip();fixfull=git('rev-parse',fix)[0].strip();cases={}
for label,ref in [('C5',base),('D4_parent',parent)]:
 text=git('show',ref+':ggml/src/ggml-cuda/ggml-cuda.cu')[0]
 start=text.index('ggml_backend_cuda_device_supports_op(')
 body=text[start:]
 match=re.search(r'case\s+GGML_OP_CONV_2D\s*:\s*(return\s+[^;]+;)',body)
 if not match:raise ValueError('missing eligibility '+label)
 cases[label]=match.group(1).strip()
assert cases['C5']=='return true;'
assert cases['D4_parent']=='return (ggml_is_contiguous(op->src[0]) && ggml_is_contiguous(op->src[1]));'
core=git('show',base+':ggml/src/ggml.c')[0];a=core.index('struct ggml_tensor * ggml_conv_2d_direct(');b=core.index('\n}',a)+2;constructor=core[a:b]
assert 'GGML_OP_CONV_2D' in constructor
uses,rc=git('grep','-n','-w','-F','ggml_conv_2d_direct',feature,'--','tools/mtmd/models/lfm3a.cpp',allow=(0,1));assert rc==0
stat=git('show','--stat','--oneline',fixfull)[0];patch=git('show','--format=',fixfull,'--','ggml/src/ggml-cuda/ggml-cuda.cu')[0]
json.dump({'C5':base,'D4':feature,'D4_parent':parent,'upstream_change':fixfull,'upstream_change_ancestor_C5':anc(fixfull,base),'upstream_change_ancestor_D4_parent':anc(fixfull,parent),'D4_uses':uses.splitlines(),'C5_constructor':constructor,'supports_op_return':cases,'upstream_change_stat':stat,'upstream_cuda_patch':patch,'scope':'GPU supports-op source eligibility only. No runtime tensor strides, device residency, fallback or model correctness evidence.'},open(sys.argv[1],'w'),indent=2)
