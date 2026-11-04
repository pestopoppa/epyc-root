#!/usr/bin/env python3
"""Run before any grant: full weight and store verification, no inference."""
import hashlib,json,pathlib,subprocess,time
D=pathlib.Path(__file__).resolve().parent
B=pathlib.Path('/mnt/raid0/llm/kernels/builds/cpu-20261024-c72ec82f5-c5')
M=pathlib.Path('/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS')
S=pathlib.Path('/mnt/raid0/llm/worktrees/c5-fold-20261024')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def identity(p):
 s=p.stat();return dict(path=str(p.resolve()),size=s.st_size,mtime_ns=s.st_mtime_ns,device=s.st_dev,inode=s.st_ino,sha256=sha(p))
def main():
 assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()=='c72ec82f5417bb2937310326120f149b665e8400'
 assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain'],text=True).strip()
 subprocess.run(['sha256sum','--quiet','-c',str(B/'SHA256SUMS')],cwd=B/'bin',check=True)
 strings=subprocess.check_output(['strings',str(B/'bin/libggml-cpu.so')],text=True).splitlines()
 assert 'GGML_FA_VKQ_F16' in strings and 'GGML_FA_VKQ_F32' in strings
 ops=(S/'ggml/src/ggml-cpu/ops.cpp').read_text();assert 'FA_VKQ_HYBRID' in ops and 'vkq_check' in ops
 models=[]
 for p in sorted(M.glob('*.gguf')):
  v=identity(p);assert v['sha256']==p.with_suffix('.gguf.sha256').read_text().split()[0];models.append(v)
 assert len(models)==3
 products=[identity(B/'bin'/n) for n in ['llama-bench','libllama-bench-impl.so','libllama.so','libggml.so','libggml-base.so','libggml-cpu.so']]
 receipt=dict(schema='cpu-fa-vkq2.prepared.v1',prepared_at=time.time(),source_commit='c72ec82f5417bb2937310326120f149b665e8400',source_ops=identity(S/'ggml/src/ggml-cpu/ops.cpp'),store_manifest=identity(B/'SHA256SUMS'),products=products,models=models,knobs=['GGML_FA_VKQ_F16','GGML_FA_VKQ_F32'],input='llama-bench deterministic native depth prefill; no transcript')
 (D/'prepared.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('prepared',len(models),'shards',sum(x['size'] for x in models),'bytes')
if __name__=='__main__':main()
