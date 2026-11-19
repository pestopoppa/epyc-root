import hashlib,json,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent; S=D/'source'; x=json.loads((D/'identity.json').read_text())
def git(*a): return subprocess.check_output(['git','-C',str(S),*a])
assert (S/'.git').is_file() and not (S/'.git').is_symlink()
assert git('rev-parse','HEAD').decode().strip()==x['source_commit']
assert subprocess.run(['git','-C',str(S),'symbolic-ref','-q','HEAD'],stdout=subprocess.DEVNULL).returncode==1
assert subprocess.run(['git','-C',str(S),'diff','--cached','--quiet']).returncode==0
assert git('status','--porcelain','--untracked-files=all').decode().splitlines()==x['status']
assert hashlib.sha256(git('diff','--binary')).hexdigest()==x['diff_sha256']
assert all(z.startswith('H ') for z in git('ls-files','-v').decode().splitlines())
for p,h in x['source_files'].items(): assert hashlib.sha256((S/p).read_bytes()).hexdigest()==h
