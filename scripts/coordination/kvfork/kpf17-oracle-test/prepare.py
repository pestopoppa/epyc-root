#!/usr/bin/env python3
"""Prepare only after the prerequisite build has been filed PASS."""
import json, hashlib, shutil, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode = True
import custody
import gdb_job
HERE=Path(__file__).resolve().parent
D=Path('/mnt/raid0/llm/tmp/kvfork/kpf17-oracle-test-20261104')
model_path=Path('/mnt/raid0/llm/tmp/kvfork/kpf17-partial-row/model.json')
build=custody.build_identity();model=custody.model_identity(model_path)
symbols=subprocess.check_output(['/usr/bin/nm','--defined-only',build['binary']],text=True)
for name in (gdb_job.ENTRY,gdb_job.DECODE,gdb_job.RESTORE):
    if sum(line.split()[-1:]==[name] for line in symbols.splitlines())!=1:
        raise SystemExit('INVALID: build lacks unique required in-test symbol '+name)
D.mkdir(parents=True,exist_ok=False)
names=('custody.py','cleanup.py','gdb_job.py','witness.py','complete.py','precondition.py')
for name in names:shutil.copy2(HERE/name,D/name)
shutil.copy2(model_path,D/'model.json')
for name in ('filler_run15.sh','filler_lib.sh'):
    shutil.copy2(Path('/mnt/raid0/llm/tmp/compute-flags/bin/rowflow')/name,D/name)
names=(*names,'filler_run15.sh','filler_lib.sh','model.json')
b={'build':build,'model':model,'gdb_sha256':custody.digest('/usr/bin/gdb'),
   'runner_files':{n:custody.digest(D/n) for n in names}}
(D/'binding.json').write_text(json.dumps(b,sort_keys=True)+'\n')
launch=(HERE/'launch.sh').read_text().replace('BINDING_SHA256',custody.digest(D/'binding.json'))
(D/'launch.sh').write_text(launch)
print('prepared after accepted build; submit spec to publish_row.py')
