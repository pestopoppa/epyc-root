"""Task-local sampled continuation budget; no completion or hard-quota claim."""
import os
from pathlib import Path
G=1024**3
SHARD_CAP=256*1024**2
FOUR_RESERVE=G
SAFETY=128*1024**2
FLOOR=150*G
class ResourcePause(RuntimeError):pass
def check(root):
 root=Path(root);total=0;count=0
 try:
  for parent,dirs,files in os.walk(root,followlinks=False):
   for n in dirs+files:
    p=Path(parent)/n;count+=1
    if count>4096:raise ResourcePause('output file count')
    if p.is_symlink():
     if p==root/'plan':continue
     raise ValueError('unexpected output symlink')
   for n in files:
    p=Path(parent)/n
    if p.is_symlink():continue
    st=p.stat();total+=max(st.st_size,st.st_blocks*512)
 except FileNotFoundError as exc:raise ResourcePause('output changed during sample') from exc
 if total>=SHARD_CAP:raise ResourcePause('sampled256MiB cohort cap')
 st=os.statvfs(root)
 if st.f_bavail*st.f_frsize<FLOOR+FOUR_RESERVE+SAFETY:raise ResourcePause('150GiB floor plus1GiB aggregate reserve and128MiB safety')
 if Path('/mnt/raid0/llm/tmp/yarn-s2-v15-candidate-20261101/OUTPUT-PAUSE').exists():raise ResourcePause('bounded outer log cap')
 return {'sampled_output_bytes':total,'cap_bytes':SHARD_CAP,'sampled_free_bytes':st.f_bavail*st.f_frsize,'aggregate_reserved_bytes':FOUR_RESERVE,'safety_bytes':SAFETY}
