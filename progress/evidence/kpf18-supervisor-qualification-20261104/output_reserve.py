"""Conservative KPF18 output-reserve arithmetic; sampled, not filesystem quota."""
import os
from pathlib import Path
GIB=1024**3
FLOOR=150*GIB
CAP=64*GIB
def check(free,used):
 if type(free) is not int or type(used) is not int or free<0 or used<0:raise ValueError('invalid disk values')
 if used>=CAP:raise RuntimeError('output budget exhausted')
 if free<FLOOR+(CAP-used):raise RuntimeError('disk floor plus remaining output reserve unavailable')
 return True
def owned_bytes(root):
 root=Path(root)
 if not root.exists():return 0
 if root.is_symlink() or not root.is_dir():raise RuntimeError('invalid output root')
 total=0;count=0
 for base,dirs,files in os.walk(root,followlinks=False,onerror=lambda e:(_ for _ in ()).throw(e)):
  for name in dirs+files:
   p=Path(base)/name
   if p.is_symlink():raise RuntimeError('output symlink')
   count+=1
   if count>10000:raise RuntimeError('output file count exceeded')
  for name in files:
   st=(Path(base)/name).stat();total+=max(st.st_size,st.st_blocks*512)
   if total>=CAP:raise RuntimeError('output budget exhausted')
 return total
