#!/usr/bin/env python3
import hashlib,json,os,pathlib,subprocess,sys
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf17-partial-row-v2'); S=D/'source'; M=json.loads((D/'model.json').read_text()); p=pathlib.Path(M['path']); st=p.stat()
if {x:getattr(st,'st_'+x) for x in ('dev','ino','size','mtime_ns','ctime_ns')}!=M['stat']: raise SystemExit('model identity metadata changed')
if subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()!='a1f0c8cf9bd7102415a72577474f307b8ba94db9': raise SystemExit('source HEAD mismatch')
if any(line[:1] != 'H' for line in subprocess.check_output(['git','-C',str(S),'ls-files','-v'],text=True).splitlines()): raise SystemExit('source contains assume-unchanged or skip-worktree entries')
if subprocess.run(['git','-C',str(S),'diff','--cached','--quiet'],check=False).returncode != 0: raise SystemExit('staged source modifications refused')
if subprocess.check_output(['git','-C',str(S),'diff','--name-only'],text=True).strip()!='tests/test-save-load-state.cpp': raise SystemExit('source modifications differ')
if subprocess.check_output(['git','-C',str(S),'ls-files','--others','--exclude-standard'],text=True).strip(): raise SystemExit('untracked source files')
if hashlib.sha256((S/'tests/test-save-load-state.cpp').read_bytes()).hexdigest()!='33c2e9e54376515febeae3531ef4f5fa7038033bf7589516fda5a732428d0d5f': raise SystemExit('test source mismatch')
print('static source and prepared model identity verified')
