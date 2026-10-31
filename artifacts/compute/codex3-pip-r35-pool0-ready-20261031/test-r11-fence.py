import sys
from pathlib import Path
sys.path.insert(0,'/mnt/micron/codex3-pip-pool0-merged-r35-20261031')
from unittest.mock import patch
import r11_retirement as r
assert r.safe();old=Path.exists
for suffix in (f'{r.ID}.grant','/proc/1176173',f'{r.ID}.json'):
 def altered(p, suffix=suffix):return True if str(p).endswith(suffix) and (suffix!=(f'{r.ID}.json') or str(p.parent)==str(r.F/'ready')) else old(p)
 with patch.object(Path,'exists',altered):assert not r.safe(),suffix
raw=Path.read_bytes;target=r.F/'grants'/f'{r.ID}.ended'
with patch.object(Path,'read_bytes',lambda p:b'changed' if p==target else raw(p)):assert not r.safe()
print('actual terminal/dead-owner positive; grant, PID, live READY and terminal drift negatives passed')
