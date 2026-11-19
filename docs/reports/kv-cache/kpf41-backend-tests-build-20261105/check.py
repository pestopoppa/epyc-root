import pathlib, subprocess, sys
s=pathlib.Path(__file__).resolve().parent/'source'
def git(*args): return subprocess.check_output(['git','-C',str(s),*args],text=True).strip()
try:
 assert git('rev-parse','HEAD')=='15caecbbf4cb27452dbd87fa1a68a0e75098388e'
 assert not git('status','--porcelain','--untracked-files=all')
 assert git('symbolic-ref','-q','HEAD') == ''
except subprocess.CalledProcessError as e:
 if e.cmd[-3:] == ['symbolic-ref','-q','HEAD'] and e.returncode == 1: sys.exit(0)
 sys.exit(1)
except AssertionError: sys.exit(1)
sys.exit(1)
