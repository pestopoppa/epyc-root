import hashlib,os,sys
from pathlib import Path
pins={
'/mnt/raid0/llm/models/gemma-3-1b-it-Q8_0.gguf':(1069306368,'7313b8d49aeb93d1e187130722a3cb8d6b18f7c8c47555926d001b7863cf92d2'),
'/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf':(29047086048,'7fb575fe9cecac00633ef8d939a472037750d54399fef69e9d07e74a6b815134')}
p=Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf');size,digest=pins[str(p)]
h=hashlib.sha256();n=p.stat().st_size
with p.open('rb') as f:h.update(f.read(64*1024**2));f.seek(max(0,n-64*1024**2));h.update(f.read(64*1024**2))
h.update(str(n).encode())
if n!=size or h.hexdigest()!=digest:raise SystemExit('canonical model edge mismatch')
print('model_edge_ok',p,flush=True)
