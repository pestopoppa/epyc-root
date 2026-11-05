#!/usr/bin/env python3
import hashlib, json, os, subprocess
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/kvfork/kvu11c-rebuild-diagnostic-20261105')
S=Path('/mnt/raid0/llm/tmp/kvfork/kvu11c-source-20261104')
for root,rev in [(S,'aca703283192f892f1e85636fbc48832c4d5560a'),(S/'ggml','b86f660238dcc1a83b7cbf5a72d355a965de9245')]:
 def git(*args): return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
 assert git('rev-parse','HEAD')==rev
 assert (root/'.git').is_file()
 assert subprocess.run(['git','-C',str(root),'symbolic-ref','-q','HEAD'],stdout=subprocess.DEVNULL).returncode==1
 assert not git('status','--porcelain','--untracked-files=all')
 assert not [x for x in git('ls-files','-v').splitlines() if x and x[0] != 'H'], 'hidden index flags'
for name,digest in json.loads((D/'runtime.json').read_text()).items():
 assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest, name
print('detached qwentts and ggml source, runtime inputs verified')
