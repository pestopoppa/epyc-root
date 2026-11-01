#!/usr/bin/env python3
"""Pin D4 depthwise-convolution source use and GPU supports-op delta.
Usage: python3 depthwise_provenance.py OUTPUT.json
Read-only source objects; observed dtype and actual device placement are not established.
"""
import json,re,subprocess,sys
r='/mnt/raid0/llm/llama.cpp';base='c72ec82f5417bb2937310326120f149b665e8400';feat='19ff817fb25e9a1b838b1d7f9f4325f7bf9779c4';fix='a72e04abe0f'
def git(*a,allowed=(0,)):
 p=subprocess.run(['git','-C',r,*a],capture_output=True,text=True)
 if p.returncode not in allowed:raise RuntimeError((a,p.returncode,p.stderr))
 return p.stdout,p.returncode
def anc(a,b):return git('merge-base','--is-ancestor',a,b,allowed=(0,1))[1]==0
parent=git('rev-parse',feat+'^')[0].strip();fixfull=git('rev-parse',fix)[0].strip()
path='ggml/src/ggml-cuda/ggml-cuda.cu';cases={}
for label,ref in [('C5',base),('D4_parent',parent)]:
 text=git('show',ref+':'+path)[0]
 all_cases=re.findall(r'(?m)^\s*case\s+GGML_OP_CONV_2D_DW\s*:\s*\n(.*?)(?=^\s*case\s+GGML_OP_|^\s*default\s*:)',text,re.M|re.S)
 assert len(all_cases)==2,(label,len(all_cases))
 cases[label]={'dispatch_case':all_cases[0].strip(),'supports_op_case':all_cases[1].strip()}
uses=git('grep','-n','-w','-F','ggml_conv_2d_dw_direct',feat,'--','tools/mtmd/models/lfm3a.cpp')[0].splitlines()
assert uses
constructor=git('show',base+':ggml/src/ggml.c')[0]
start=constructor.index('struct ggml_tensor * ggml_conv_2d_dw_direct(');stop=constructor.index('\n}',start)+2
constructor=constructor[start:stop];assert 'GGML_OP_CONV_2D_DW' in constructor
blame=git('blame','-L',':ggml_backend_cuda_device_supports_op',parent,'--',path)[0]
matching=[line for line in blame.splitlines() if 'GGML_OP_CONV_2D_DW' in line or 'op->src[0]->type == GGML_TYPE_F16 || op->src[0]->type == GGML_TYPE_F32' in line]
stat=git('show','--stat','--oneline',fixfull)[0]
json.dump({'C5':base,'D4':feat,'D4_parent':parent,'upstream_fix':fixfull,'ancestor_fix_C5':anc(fixfull,base),'ancestor_fix_D4_parent':anc(fixfull,parent),'D4_use':uses,'C5_constructor':constructor,'cases':cases,'upstream_fix_stat':stat,'selected_blame_lines':matching,'scope':'Source dispatch and supports-op only. No actual tensor dtype, model load, fallback, ROCm execution, or correctness verdict. Equivalent focused support may avoid a full ggml bump.'},open(sys.argv[1],'w'),indent=2)
