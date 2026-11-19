#!/usr/bin/env python3
"""Capture/verify an isolated installed-tool snapshot, including symlinks."""
import hashlib, json, os, stat, sys
from pathlib import Path
ROOT=Path('/mnt/raid0/llm/tmp/kvu/kpf131-impact-r4-20261105/tool')
MANIFEST=Path('/mnt/raid0/llm/tmp/kvu/kpf131-impact-r4-20261105/tool-manifest.json')
def digest(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def snapshot():
 output={}
 for base, dirs, files in os.walk(ROOT, followlinks=False):
  for name in sorted(dirs+files):
   p=Path(base)/name; mode=p.lstat().st_mode; relative=p.relative_to(ROOT).as_posix()
   if stat.S_ISLNK(mode):
    target=os.readlink(p); resolved=p.resolve(strict=False)
    if not resolved.is_relative_to(ROOT):raise RuntimeError(f'external tool symlink {relative}')
    output[relative]=['link',target]
   elif stat.S_ISREG(mode):output[relative]=['file',digest(p),stat.S_IMODE(mode)]
   elif not stat.S_ISDIR(mode):raise RuntimeError(f'unsupported tool object {relative}')
 return output
def verify():
 expected=json.loads(MANIFEST.read_text()); actual=snapshot()
 if actual!=expected:raise RuntimeError('tool snapshot drift')
if __name__=='__main__':
 if sys.argv[1:] == ['capture']: MANIFEST.write_text(json.dumps(snapshot(),sort_keys=True,separators=(',',':'))+'\n')
 elif sys.argv[1:] == ['verify']:verify()
 else:raise SystemExit('expected capture or verify')
