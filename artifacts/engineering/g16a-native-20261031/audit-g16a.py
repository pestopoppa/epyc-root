import json,re,hashlib
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/codex-ni-g16a-build-prep-20261031/native/review')
shapes=[(64,1),(256,1),(2048,1),(4096,1),(8192,1),(2048,2),(4096,2),(8192,2)]
hip='2c944080746d671414d0cf80fa17e60aca3082e7706a26a973751395d7eb2b56'
ans=[]
for t,s in shapes:
 stem=f't{t}-s{s}'; j=json.loads((p/(stem+'.receipt.json')).read_text()); out=re.sub(r'\x1b\[[0-9;]*m','',(p/(stem+'.stdout.log')).read_text()); err=(p/(stem+'.stderr.log')).read_text()
 assert j['tokens']==t and j['seqs']==s and j['rc']==0
 line=f'GATED_DELTA_NET(type=f32,head_count=32,head_size=128,n_seq_tokens={t},n_seqs={s},v_repeat=1,permuted=0,kda=0,K=1): OK'
 assert out.count(line)==1 and '1/1 tests passed' in out and 'Backend ROCm0: OK' in out
 trace=f'[gdn] chunked dispatch: H=32 S_v=128 n_tokens={t} n_seqs=2 blocks=512 (floor 312), keep_rs=0 K=1'
 assert (trace in err)==(s==2)
 assert hip in j['loaded_images'].values()
 samples=j['residency_samples']; assert all(v['pid']==j['pid'] and v['birth']==j['birth'] and v['kfd_pid_present'] and sum(v['own_kfd_vram_bytes'].values())>0 for v in samples)
 post=sum(v['monotonic']>j['dispatch_events'][0]['monotonic'] for v in samples) if s==2 else None
 if s==2: assert post>0
 ans.append({'tokens':t,'sequences':s,'samples':len(samples),'post_dispatch':post,'stdout_sha256':hashlib.sha256((p/(stem+'.stdout.log')).read_bytes()).hexdigest()})
print(json.dumps({'cases':ans,'nmse_magnitudes':'not reported','hip_sha256':hip,'scope':'G16a only'},indent=2))
