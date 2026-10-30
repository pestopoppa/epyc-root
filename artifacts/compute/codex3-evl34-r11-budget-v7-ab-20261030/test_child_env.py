import os
from pathlib import Path
from control_driver import child_env
os.environ['EVL34_TEST_SECRET']='fixture-only'
env=child_env(Path('/tmp/fixture'),{'EPYC_FENCE_KERNEL_EXTRA':'[]'})
assert 'EVL34_TEST_SECRET' not in env and env['HOME']=='/tmp/fixture' and env['EPYC_FENCE_KERNEL_EXTRA']=='[]'
print('private model child receives explicit environment allowlist')
