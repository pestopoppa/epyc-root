"""Prospective finite attempt and disk admission policy; not a launcher."""
import os,re
from resource_budget import ResourcePause
from pathlib import Path
MAX_WINDOWS=64
STREAM_LIMIT=256*1024
RESPONSE_LIMIT=1024**2
RESULT_FILE_LIMIT=32*1024**2
SHARD_RESERVE=256*1024**2
FOUR_SHARD_RESERVE=4*SHARD_RESERVE
FLOOR=150*1024**3
def new_window(root):
 r=Path(root)
 if r.is_symlink() or not r.is_dir():raise ValueError("invalid campaign root")
 names=[p.name for p in r.iterdir() if p.name.startswith("window-")]
 if any(not re.fullmatch(r"window-[0-9]{3}",n) for n in names):raise ValueError("unrecognized window")
 nums=[int(n[7:]) for n in names]
 if len(set(nums))!=len(nums) or any(n>=MAX_WINDOWS for n in nums):raise ValueError("invalid window")
 if len(nums)>=MAX_WINDOWS:raise ResourcePause("window budget exhausted")
 st=os.statvfs(r)
 if st.f_bavail*st.f_frsize<FLOOR+FOUR_SHARD_RESERVE+128*1024**2:raise ResourcePause("four-shard reserve unavailable")
 n=max(nums,default=-1)+1
 if n>=MAX_WINDOWS:raise ResourcePause("window budget exhausted")
 p=r/("window-%03d"%n);p.mkdir(mode=0o700)
 return p

SMOKE_RESERVE=256*1024**2
SMOKE_MAX_FILES=4096

def smoke_budget(root,plan):
 r=Path(root)
 if r.is_symlink() or not r.is_dir():raise ValueError("unsafe smoke output root")
 count=total=0
 for parent,dirs,files in os.walk(r,followlinks=False):
  for name in dirs+files:
   p=Path(parent)/name;count+=1
   if count>SMOKE_MAX_FILES:raise RuntimeError("smoke file count exceeded")
   if p.is_symlink():
    if p==r/"plan" and p.resolve()==Path(plan).resolve():continue
    raise ValueError("unexpected smoke symlink")
   if p.is_file():
    st=p.stat();total+=max(st.st_size,st.st_blocks*512)
 if total>=SMOKE_RESERVE:raise RuntimeError("sampled smoke output cap exceeded")
 st=os.statvfs(r);free=st.f_bavail*st.f_frsize
 if free<FLOOR+(SMOKE_RESERVE-total):raise RuntimeError("sampled smoke output reserve unavailable")
 return {"sampled_output_bytes":total,"sampled_free_bytes":free,"remaining_reserved_bytes":SMOKE_RESERVE-total}

def new_smoke_window(root,plan):
 r=Path(root);smoke_budget(r,plan)
 if any(p.name.startswith("window-") for p in r.iterdir()):raise RuntimeError("smoke window already exposed")
 p=r/"window-000";p.mkdir(mode=0o700);return p
