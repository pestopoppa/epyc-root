#!/usr/bin/env python3
"""Assemble exact approved seven-file instrument on the C5 source baseline."""
import hashlib, json, subprocess
from pathlib import Path
BASE = Path(__file__).resolve().parent
CHAMPION = 'c72ec82f5417bb2937310326120f149b665e8400'
API = 'b40f8c60f36ad25a418ccc836d1ac0ab0a05a0c9'
ROOT = 'cec0d61c5127787648ef7bd913fcacf246241f5f'
NAMES = ('src/llama-context.cpp','src/llama-ext.h','src/llama-kv-cache.cpp','src/llama-kv-cache.h','src/llama-kv-cells.h','tests/test-chunk-kv.cpp','tests/CMakeLists.txt')
def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args])
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    source=BASE/'source-audit'; candidate=BASE/'candidate'; root=BASE/'root-reader'
    for p in (candidate,root):
        if p.exists(): raise ValueError('fresh candidate required')
    if git(source,'rev-parse','approved-kpf62').decode().strip()!=API: raise ValueError('approved ref drift')
    changed=git(source,'diff','--name-only',CHAMPION,API).decode().splitlines()
    if set(changed)!=set(NAMES): raise ValueError('approved source scope drift')
    subprocess.run(['git','clone','--shared','--no-checkout',str(source),str(candidate)],check=True)
    subprocess.run(['git','-C',str(candidate),'checkout','--detach',CHAMPION],check=True)
    for name in NAMES:
        path=candidate/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(git(source,'show',f'{API}:{name}'))
    subprocess.run(['git','clone','--shared','--no-checkout','/workspace',str(root)],check=True)
    subprocess.run(['git','-C',str(root),'checkout','--detach',ROOT],check=True)
    if 'no_protocol_ids=("unknown",)' not in (root/'scripts/vidya/adapters/chunk_kv.py').read_text(): raise ValueError('reader correction absent')
    m={'schema':'epyc.kpf62.source_assembly.v1','champion':CHAMPION,'api_origin':API,'root_adapter':ROOT,'files':{n:sha(candidate/n) for n in NAMES},'scope':'approved seven-file source, no promotion','candidate':str(candidate),'root_candidate':str(root)}
    m['source_digest']=hashlib.sha256(json.dumps(m,sort_keys=True).encode()).hexdigest()
    (BASE/'assembly.json').write_text(json.dumps(m,sort_keys=True,indent=2)+'\n')
    (BASE/'candidate.diff').write_bytes(git(candidate,'diff','--',*NAMES))
    print('SOURCE_ASSEMBLED_NOT_BUILT')
if __name__=='__main__': main()
