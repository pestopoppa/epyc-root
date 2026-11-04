#!/usr/bin/env python3
"""One-time preparation outside a keeper grant. Never overwrites an existing row."""
import hashlib,json,pathlib,re,shutil,subprocess
HERE=pathlib.Path(__file__).resolve().parent
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf17-partial-row-v2')
REPO='/mnt/raid0/llm/llama.cpp-experimental'
MODEL=pathlib.Path('/mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf')
HELPER=pathlib.Path('/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh')
PATCH=HERE.parent/'kpf17-partial-test/test-save-load-partial.patch'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
assert sha(PATCH)=='55c1bfb69ee6d193f05fb57c09f2de3feb3a9491babe697a8822722e080f61e0'
assert sha(HELPER)=='57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33'
identity=json.loads(pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf17-partial-row/model.json').read_text())
st=MODEL.stat()
assert identity['path']==str(MODEL) and identity['sha256']=='0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c'
assert identity['stat']=={x:getattr(st,'st_'+x) for x in ('dev','ino','size','mtime_ns','ctime_ns')}
D.mkdir(parents=True,exist_ok=False)
subprocess.run(['git','-C',REPO,'worktree','add','--detach',str(D/'source'),'a1f0c8cf9bd7102415a72577474f307b8ba94db9'],check=True)
subprocess.run(['git','-C',str(D/'source'),'apply',str(PATCH)],check=True)
(D/'model.json').write_text(json.dumps(identity,indent=2)+'\n')
for name in ('check.py','complete.py','job.sh','supervise.py'):shutil.copy2(HERE/name,D/name)
shutil.copy2('/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh',D/'filler_run15.sh')
shutil.copy2('/mnt/raid0/llm/tmp/kvfork17a-cpu-successor/filler_lib.sh',D/'filler_lib.sh')
paths=[D/n for n in ('check.py','complete.py','job.sh','supervise.py','filler_lib.sh','filler_run15.sh','model.json')]+[HELPER]
manifest=''.join(f'{sha(p)}  {p}\n' for p in paths); (D/'runtime.sha256').write_text(manifest)
h=hashlib.sha256(manifest.encode()).hexdigest(); launch=(HERE/'launch.sh').read_text(); launch=re.sub(r'93edca3088046b16b5abb0a07f5ccdf33bbb51c739f236247dec4da4929fb363',h,launch)
(D/'launch.sh').write_text(launch)
subprocess.run(['python3',str(D/'check.py')],check=True)
print('Prepared; inspect successor and publish its spec. No row was published.')
