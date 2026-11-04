import hashlib,pathlib,subprocess
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf50-hip-build-20261104'); S=D/'source'
def git(*args):return subprocess.check_output(['git','-C',str(S),*args],text=True).strip()
assert (S/'.git').is_file() and not (S/'.git').is_symlink()
assert git('rev-parse','HEAD')=='1e8a6d5da9836a27e8f1d2010a02e6cebd95abdc'
assert subprocess.run(['git','-C',str(S),'symbolic-ref','-q','HEAD'],stdout=subprocess.DEVNULL).returncode==1
assert not git('status','--porcelain','--untracked-files=all')
assert all(x.startswith('H ') for x in git('ls-files','-v').splitlines())
