import hashlib,json,pathlib,subprocess
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf62-g3-build-20261104'); S=D/'source'; x=json.loads((D/'source.json').read_text())
git=lambda *a:subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
assert (S/'.git').is_file() and not (S/'.git').is_symlink()
assert git('rev-parse','HEAD')==x['commit']
assert subprocess.run(['git','-C',str(S),'symbolic-ref','-q','HEAD'],stdout=subprocess.DEVNULL).returncode==1
assert subprocess.run(['git','-C',str(S),'diff','--cached','--quiet']).returncode==0
assert subprocess.check_output(['git','-C',str(S),'status','--porcelain','--untracked-files=all'],text=True).splitlines()==x['status']
assert all(z.startswith('H ') for z in git('ls-files','-v').splitlines())
for p,h in x['files'].items(): assert hashlib.sha256((S/p).read_bytes()).hexdigest()==h
