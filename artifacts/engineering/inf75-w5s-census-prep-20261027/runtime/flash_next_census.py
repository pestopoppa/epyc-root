"""Private exact-set census; never changes workload_contract routing."""
from collections import Counter
from pathlib import Path
from split_inspect import inspect
from autokernel.controller.workload_contract import WorkloadCensus, GGML_TYPE_NAMES

NAMES=tuple(f'Qwen3.8-Flash-Next-UD-IQ4_XS-{i:05d}-of-00003.gguf' for i in range(1,4))

def validate_parts(paths, parts):
    paths=tuple(Path(p) for p in paths)
    if len(paths)!=3 or len(set(paths))!=3 or tuple(p.name for p in paths)!=NAMES or len({p.parent for p in paths})!=1:
        raise ValueError('incorrect ordered exact shard set')
    if len(parts)!=3: raise ValueError('missing shard metadata')
    names=set(); types=Counter(); total=0
    for i,part in enumerate(parts):
        m=part['metadata']
        if part['version']!=3 or m.get('split.no')!=i or m.get('split.count')!=3 or m.get('split.tensors.count')!=1224:
            raise ValueError('invalid split metadata')
        if m.get('general.architecture','qwen4exp')!='qwen4exp' or m.get('qwen4exp.embedding_length',2560)!=2560:
            raise ValueError('inconsistent architecture')
        if i==0 and (m.get('general.architecture')!='qwen4exp' or m.get('qwen4exp.embedding_length')!=2560):
            raise ValueError('missing primary architecture')
        these=part['names']
        if len(these)!=part['count'] or len(set(these))!=len(these) or names.intersection(these):
            raise ValueError('duplicate or inconsistent tensor names')
        names.update(these); total+=part['count']; types.update(part['types'])
    if total!=1224 or sum(types.values())!=total: raise ValueError('inconsistent tensor total')
    return WorkloadCensus(path=str(paths[0]),architecture='qwen4exp',n_embd=2560,
        tensor_types={GGML_TYPE_NAMES.get(t,f'type_{t}'):n for t,n in types.items()})

def read_flash_next_weights(paths):
    paths=tuple(Path(p) for p in paths)
    return validate_parts(paths,[inspect(p) for p in paths])
