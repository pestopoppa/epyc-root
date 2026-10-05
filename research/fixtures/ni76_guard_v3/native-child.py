"""Hosted native-CLI child: capture actual owner and grants before guard invocation."""
import json
import os
from pathlib import Path
import subprocess
import sys

assert os.environ.get('GITHUB_ACTIONS') == 'true'
guard, repo, label = sys.argv[1:]
out = Path(os.environ['NI76_SCOPE'])/'originals'
owner = os.getppid()
(out/(label+'.native-owner-stat')).write_text(Path(f'/proc/{owner}/stat').read_text())
(out/(label+'.native-owner-status')).write_text(Path(f'/proc/{owner}/status').read_text())
raw = Path('/proc/locks').read_text()
(out/(label+'.native-proc-locks')).write_text(raw)
records = {}
for line in raw.splitlines():
    p=line.split()
    if len(p)>=8 and p[1:4]==['FLOCK','ADVISORY','WRITE'] and p[4]==str(owner):
        major,minor,inode=p[5].split(':')
        records[(int(major,16),int(minor,16),int(inode,10))]=line
proof=[]
for role in ['GLOBAL','build']:
    for q in ['q0','q1','q2','q3']:
        path=Path('/mnt/raid0/llm/tmp')/f'cpu_region.{role}.{q}.lock';s=path.lstat()
        key=(os.major(s.st_dev),os.minor(s.st_dev),s.st_ino)
        assert key in records,(role,q,'native owner does not hold actual inode')
        item={'path':str(path),'uid':s.st_uid,'dev':s.st_dev,'inode':s.st_ino,'grant':records[key]}
        if role=='build':
            item['payload']=json.loads(path.read_text());assert item['payload']['pid']==owner
        proof.append(item)
(out/(label+'.native-grant-proof.json')).write_text(json.dumps({'native_owner':owner,'records':proof},indent=2))
result=subprocess.run(['/usr/bin/python3','-I',guard,'--repo',repo],timeout=10)
raise SystemExit(result.returncode)
