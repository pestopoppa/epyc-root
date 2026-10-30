"""Independent sampled RAID metadata and Micron campaign-output budgets."""
import os
from pathlib import Path
G=1024**3;FLOOR=150*G;META_CAP=128*1024**2;NATIVE_CAP=512*1024**2
D=Path('/mnt/raid0/llm/tmp/codex3-evl34-r11-budget-v7-ab-20261030')
M=Path('/mnt/micron/codex3-evl34-r11-budget-v7-ab-20261030')
def size(root):
 total=0;seen=set()
 for parent,dirs,files in os.walk(root,followlinks=False):
  for name in dirs+files:
   p=Path(parent)/name
   if p.is_symlink():raise RuntimeError('storage symlink refused')
   if p.is_file():
    s=p.stat();key=(s.st_dev,s.st_ino)
    if key not in seen:seen.add(key);total+=s.st_size
 return total

def evaluate(raid_free,native_free,meta,output,raid_dev,native_dev,other=0):
 if other<0:raise RuntimeError('negative concurrent reserve')
 if raid_dev==native_dev:raise RuntimeError('native output device equals RAID')
 if meta>META_CAP or output>NATIVE_CAP:raise RuntimeError('sampled storage budget exceeded')
 if raid_free<FLOOR+META_CAP+other:raise RuntimeError('RAID floor plus reservations')
 if native_free<FLOOR+NATIVE_CAP-output:raise RuntimeError('Micron floor plus remaining output budget')
 return {'raid_free':raid_free,'native_free':native_free,'metadata_bytes':meta,'output_bytes':output,'raid_device':raid_dev,'native_device':native_dev}

def check(other=0):
 a=D.stat();b=M.stat();x=os.statvfs(D);y=os.statvfs(M)
 return evaluate(x.f_bavail*x.f_frsize,y.f_bavail*y.f_frsize,size(D),max(size(M/'control'),size(M/'pilot')),a.st_dev,b.st_dev,other)
