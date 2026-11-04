#!/usr/bin/env python3
"""Read pinned C5 source and paired raw logs; no model, build, or inference."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
C5='c72ec82f5417bb2937310326120f149b665e8400'
p=argparse.ArgumentParser();p.add_argument('--repo',default='/mnt/raid0/llm/llama.cpp');p.add_argument('--raw-dir',default='/mnt/raid0/llm/tmp/akagg-ch31-rowexact-pair-20261101/full');args=p.parse_args()
def source(path):return subprocess.check_output(['git','-C',args.repo,'show',f'{C5}:{path}'],text=True)
def require(s,*fragments):
 for x in fragments:
  if x not in s:raise ValueError('source guard missing '+x)
cpu=source('ggml/src/ggml-cpu/ggml-cpu.c');iqk=source('ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp');mul=source('ggml/src/ggml-cpu/iqk/iqk_mul_mat.cpp'); row=source('examples/rowexact/rowexact.cpp');sg=source('ggml/src/ggml-cpu/llamafile/sgemm.cpp')
require(cpu,'ne11 > 1 && ne11 <= ggml_cpu_rowexact_n()','if (ggml_iqk_try_mul_mat(params, dst))','if (src1_cont && ggml_cpu_rowexact_batch(params, ne11))','goto UseGgmlGemm1;')
assert cpu.index('if (ggml_iqk_try_mul_mat(params, dst))')<cpu.index('if (src1_cont && ggml_cpu_rowexact_batch(params, ne11))')
require(iqk,'if (dst->type  != GGML_TYPE_F32) return false','if (src1->type != GGML_TYPE_F32) return false','src0->type == GGML_TYPE_Q8_0 && !iqk_q8_0_eligible(ne11)','!params->disable_rowexact, ith, nth','getenv("GGML_IQK_Q8_0")')
require(mul,'allow_rowexact && Ny > 1 && Ny <= iqk_rowexact_n()','info.allow_rowexact && n_y > 1 && n_y <= iqk_rowexact_n() && funcs[0]','funcs[0](n,')
require(row,'ggml_type_name(rb.type)','ggml_op_name(rb.op)','token_slice(rb, N, S, i, fb)')
require(sg,'// only enable sgemm for prompt processing','if (n < 2)')
raw=Path(args.raw_dir);cases=[]
for route in (0,4):
 for i in range(4):
  file=raw/f'four_seq_prompt_{i}_r{route}.out'; data=file.read_bytes();text=data.decode(errors='replace');nodes=re.findall(r'nodes multi-row vs alone-batch-row: compared (\d+), DIFFER (\d+), first=(\S+), shape-skip (\d+), unmatched-name (\d+)',text);logits=re.findall(r'logits multi-row vs alone-batch-row: (IDENTICAL|DIFFER) n_diff=(\d+)/(\d+) max\|d\|=(\S+) argmax (\d+)(==|!=)(\d+)',text)
  assert len(nodes)==len(logits)==4
  assert all(int(n[0])==1127 and int(n[3])==260 and int(n[4])==0 for n in nodes)
  if route==0:
   assert all(int(n[1])>0 and n[2]=='node_13' for n in nodes)
   assert re.search(r'node_13\s+MUL_MAT\s+\[6144,4,1,1\]\s+f32',text)
  else:assert all(int(n[1])==0 for n in nodes) and all(l[0]=='IDENTICAL' for l in logits)
  cases.append({'route':route,'rotation':i,'raw_sha256':hashlib.sha256(data).hexdigest(),'compared_per_row':1127,'first':nodes[0][2],'differ_per_row':[int(n[1]) for n in nodes]})
print(json.dumps({'source_commit':C5,'source_guards':'PASS','paired_raw_cases':cases,'limits':'f32 is output type; input types, actual dispatch, isolated-input cause and Q38FN server behavior unobserved'},indent=2))
