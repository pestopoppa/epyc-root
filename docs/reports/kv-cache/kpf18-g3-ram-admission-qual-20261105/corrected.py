"""Conservative live commitments before loading; never modify scheduler state."""
import datetime,time
from pathlib import Path
FLAGS=Path('/mnt/raid0/llm/tmp/compute-flags')
GIB=1024**3

def commitments(records,rows,own_id,now,deadline):
 total=0;own_seen=False
 for ident,line in records:
  parts=line.split()
  if len(parts)!=3 or any(p.count('=')!=1 for p in parts):raise ValueError('malformed grant')
  fields=dict(p.split('=',1) for p in parts)
  if set(fields)!={'regions','start','end'}:raise ValueError('grant schema')
  def epoch(v):
   t=datetime.datetime.fromisoformat(v.replace('Z','+00:00'))
   if t.tzinfo is None:raise ValueError('grant timezone')
   return t.timestamp()
  start,end=epoch(fields['start']),epoch(fields['end'])
  if start>=end:raise ValueError('grant interval')
  if end<=now or start>=deadline:continue
  if ident==own_id:
   if start>now:raise ValueError('own grant not active yet')
   if own_seen:raise ValueError('duplicate own grant')
   own_seen=True;continue
  matches=[r for r in rows if r.startswith('| '+ident+' |')]
  if len(matches)!=1:raise ValueError('unknown live grant row')
  cells=[c.strip() for c in matches[0].strip().strip('|').split('|')]
  if len(cells)!=18 or not cells[5].isdigit():raise ValueError('unknown grant memory')
  total+=int(cells[5])
 if not own_seen:raise ValueError('missing active own grant')
 return total

def check(own_id,deadline):
 records=[]
 for p in sorted((FLAGS/'grants').glob('*.grant')):
  if p.is_symlink() or not p.is_file():raise ValueError('unsafe grant')
  records.append((p.stem,p.read_text()))
 rows=(FLAGS/'FILLERS.md').read_text().splitlines()
 other=commitments(records,rows,own_id,time.time(),deadline)
 available=None
 for line in Path('/proc/meminfo').read_text().splitlines():
  if line.startswith('MemAvailable:'):available=int(line.split()[1])*1024
 if available is None or available<(192+64+other)*GIB:raise ValueError('live RAM plus other overlapping commitments unavailable')
 return other
