import sys,os
from pathlib import Path
from evl34_supervisor import supervise
r=Path(__file__).parent/('supervisor-fixture-'+str(os.getpid()));r.mkdir()
result=supervise([sys.executable,'-c','import time; time.sleep(5)'],r/'stop.log',seconds=10,stop=lambda:True)
assert result['reason']=='stop' and result['drained'] and result['samples']>=1 and result['owned_pids']
try:supervise([sys.executable,'-c','pass'],r/'refused.log',seconds=1,required_headroom=10**18)
except RuntimeError as e:assert 'disk admission' in str(e)
else:raise AssertionError('disk admission accepted')
assert not (r/'refused.log').exists()
print('synthetic supervisor stop/drain, sampled RSS and disk pre-admission refusal passed')
