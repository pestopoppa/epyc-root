#!/usr/bin/env python3
"""Pin D1's ggml_conv_1d source use and upstream layout fix, without checkout/build.
Usage: python3 conv1d_provenance.py OUTPUT.json
Ancestry and source use do not prove the D1 input shape exercises the changed behavior.
"""
import json,subprocess,sys
r='/mnt/raid0/llm/llama.cpp';base='c72ec82f5417bb2937310326120f149b665e8400';feat='2851b3bcbf8d993a2243ae751c0a7dfa8e944a40';fix='6868a52cb337450658006ad2f9281c2eb63f1666'
def git(*a,allowed=(0,)):
 p=subprocess.run(['git','-C',r,*a],capture_output=True,text=True)
 if p.returncode not in allowed:raise RuntimeError((a,p.returncode,p.stderr))
 return p.stdout,p.returncode
def anc(a,b):return git('merge-base','--is-ancestor',a,b,allowed=(0,1))[1]==0
uses,rc=git('grep','-n','-w','-F','ggml_conv_1d',feat,'--','tools/mtmd/models/voxtral-rt.cpp',allowed=(0,1))
assert rc==0
history,_=git('log','--first-parent','--reverse','--format=%H %s','-S','ggml_cont(ctx, ggml_permute(ctx, result, 0, 2, 1, 3))',feat+'^','--','ggml/src/ggml.c')
patch,_=git('show','--format=fuller','--stat',fix)
diff,_=git('diff',base,feat+'^','--','ggml/src/ggml.c')
json.dump({'C5':base,'D1':feat,'upstream_fix':fix,'ancestor_fix_C5':anc(fix,base),'ancestor_fix_D1_parent':anc(fix,feat+'^'),'D1_use':uses.splitlines(),'first_parent_search':history.splitlines(),'upstream_fix_stat':patch,'scope':'Source ancestry/usage and function text only. #28738 concerns batched layout; no D1 input-shape or correctness/runtime verdict, and no proof a whole ggml bump is necessary.','whole_ggml_c_diff_sha256_only_note':'Use separate GGML-FUNCTIONS.json for exact extracted function diffs.'},open(sys.argv[1],'w'),indent=2)
