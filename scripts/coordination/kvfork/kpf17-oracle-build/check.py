#!/usr/bin/env python3
"""Verify the exact reviewed source and no other modifications."""
import hashlib, pathlib, subprocess
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf17-oracle-build-20261104'); S=D/'source'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(S),*args],text=True).strip()
assert (S/'.git').is_file() and not (S/'.git').is_symlink()
assert git('rev-parse','HEAD')=='8952a0f693fb923918157eb25117641b74766230'
assert subprocess.run(['git','-C',str(S),'symbolic-ref','-q','HEAD'],stdout=subprocess.DEVNULL).returncode==1
assert subprocess.run(['git','-C',str(S),'diff','--cached','--quiet']).returncode==0
assert set(git('status','--porcelain','--untracked-files=all').splitlines())=={'M tests/test-save-load-state.cpp','?? tests/kpf17-mutation-oracle.h'}
assert all(x.startswith('H ') for x in git('ls-files','-v').splitlines())
assert sha(S/'tests/test-save-load-state.cpp')=='b2f7085c3b772b58d6e9eb5ec33f217f22e9e1987bb8f51f040094eb586ef2ab'
assert sha(S/'tests/kpf17-mutation-oracle.h')=='90787c4a526d2dedd3d3d11bf944ea81eeb1c2efd77e5e6862e8e69a57b26249'
assert sha(D/'verify_ggml_linkage.sh')=='57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33'
