import hashlib, importlib.util, json, sys
from pathlib import Path
import torch
from lsa.core.index_space import regroup_partial
from lsa.core.reference import build_buckets, read
import ast
import torch.nn.functional as F
source=Path("/tmp/latent-sparse-attention-inspect/src/lsa/sglang/index/layer_index.py").read_text()
node=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=="KeyAndQueryProjection")
exec(compile("from __future__ import annotations\n"+ast.get_source_segment(source,node),"upstream-KeyAndQueryProjection","exec"))
P=Path('/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/llama-champion/experiments/lsa-screen/reference.py')
spec=importlib.util.spec_from_file_location('candidate_reference',P); ref=importlib.util.module_from_spec(spec); spec.loader.exec_module(ref)
map_path=Path('/tmp/lsa-release-inspect/qwen38_27b__long-16k-1M-heavy-key-and-query-d2048.pt')
torch.set_num_threads(2); torch.manual_seed(20261103)
# Queries sampled at fixed positions; same K sequence feeds both implementations.
positions=torch.tensor([0,511,512,1023,1024,1535,4095,4607,5199])
q=torch.randn(len(positions),24,256); k=torch.randn(5200,4,256)
maps=ref.load_maps(map_path,'distilled'); wq=maps['3.W_Q_idx']; wk=maps['3.W_K_idx']
cq,ck=ref.project(q,k,wq,wk)
gq,gk=regroup_partial(q[:,:,64:].permute(1,0,2).unsqueeze(0), k[:,:,64:].permute(1,0,2).unsqueeze(0))
projection=KeyAndQueryProjection(wq,wk,'cpu')
uq=projection.index_queries(gq.squeeze(0).unsqueeze(1)); uk=projection.index_keys(gk.squeeze(0))
assert torch.equal(cq,uq) and torch.equal(ck,uk), 'projection differs'
b=build_buckets(uk,4,8,16,512); ui,_=read(uq,positions,b,1024,4096,4,512); ci=ref.select(cq,ck,positions)
assert torch.equal(ci,ui), 'indices differ'
H=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
print(json.dumps({'status':'pass','seed':20261103,'layer':3,'keys':len(k),'positions':positions.tolist(),'index_queries_equal':True,'index_keys_equal':True,'selected_indices_equal':True,'selected_counts':(ci>=0).sum(1).tolist(),'map_sha256':H(map_path),'reference_sha256':H(P),'upstream_core_index_space_sha256':H('/tmp/latent-sparse-attention-inspect/src/lsa/core/index_space.py'),'upstream_layer_index_sha256':H('/tmp/latent-sparse-attention-inspect/src/lsa/sglang/index/layer_index.py'),'upstream_reference_sha256':H('/tmp/latent-sparse-attention-inspect/src/lsa/core/reference.py')},indent=2))
