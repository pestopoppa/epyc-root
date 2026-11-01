#!/usr/bin/env python3
"""Compare C5/D4-parent GPU SSM convolution widths from pinned Git sources.
Usage: python3 ssm_width_provenance.py OUTPUT.json
No build, run, device placement or model weight shape observation.
"""
import json,re,subprocess,sys
repo='/mnt/raid0/llm/llama.cpp';base='c72ec82f5417bb2937310326120f149b665e8400';feat='19ff817fb25e9a1b838b1d7f9f4325f7bf9779c4';fix='39da130fcd1b6ca47d3c0522a40eccff41ea3dfb'
def git(*args,allowed=(0,)):
 p=subprocess.run(['git','-C',repo,*args],capture_output=True,text=True)
 if p.returncode not in allowed:raise RuntimeError((args,p.returncode,p.stderr))
 return p.stdout,p.returncode
def anc(a,b):return git('merge-base','--is-ancestor',a,b,allowed=(0,1))[1]==0
parent=git('rev-parse',feat+'^')[0].strip();fixfull=git('rev-parse',fix)[0].strip();states={}
for label,ref in [('C5',base),('D4_parent',parent)]:
 src=git('show',ref+':ggml/src/ggml-cuda/ssm-conv.cu')[0]
 matches=re.findall(r'switch\s*\(nc\)\s*\{(.*?)\n\s*\}',src,re.S)
 if len(matches)!=1:raise ValueError('expected unique nc switch')
 cases=[int(k) for k in re.findall(r'\bcase\s+(\d+)\s*:',matches[0])]
 ncline=re.findall(r'^.*\bnc\s*=\s*src1->ne\[0\].*$',src,re.M)
 src1line=re.findall(r'^.*\*\s*src1\s*=\s*dst->src\[1\].*$',src,re.M)
 support=git('show',ref+':ggml/src/ggml-cuda/ggml-cuda.cu')[0];at=support.index('ggml_backend_cuda_device_supports_op(');support=support[at:]
 m=re.search(r'case\s+GGML_OP_SSM_CONV\s*:\s*\{(.*?)\}',support,re.S)
 if not m or len(ncline)!=1 or len(src1line)!=1:raise ValueError('missing unique binding or support case')
 states[label]={'kernel_width_cases':cases,'switch':matches[0].strip(),'src1_binding':src1line[0].strip(),'nc_binding':ncline[0].strip(),'supports_op_body':m.group(1).strip()}
assert 7 not in states['C5']['kernel_width_cases'] and 7 in states['D4_parent']['kernel_width_cases']
uses,rc=git('grep','-n','-w','-F','ggml_ssm_conv',feat,'--','tools/mtmd/models/lfm3a.cpp','tools/mtmd/models/lfm3a-gen.cpp',allowed=(0,1));assert rc==0
stat=git('show','--stat','--oneline',fixfull)[0]
patch=git('diff',base,parent,'--','ggml/src/ggml-cuda/ssm-conv.cu')[0]
json.dump({'C5':base,'D4':feat,'D4_parent':parent,'upstream_fix':fixfull,'ancestor_fix_C5':anc(fixfull,base),'ancestor_fix_D4_parent':anc(fixfull,parent),'states':states,'D4_use':uses.splitlines(),'source_diff':patch,'fix_stat':stat,'scope':'Source condition only: if actual src1 ne0=7, src0 ne1 divisible by 128 and GPU executes this kernel, C5 takes abort. Actual model widths, device residency, routing/fallback and correctness not measured.'},open(sys.argv[1],'w'),indent=2)
