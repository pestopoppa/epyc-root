#!/usr/bin/env python3
"""GPU smoke admission: read live scheduler state, never create a grant."""
import datetime,os,re,time,shutil
from pathlib import Path
import lock_witness, publisher_smoke
FLAGS=Path('/mnt/raid0/llm/tmp/compute-flags')
_owner=None;_identity=None
def check(admit_ram=False):
 global _owner,_identity
 cpus,deadline=publisher_smoke.context(Path(__file__).resolve().parent)
 if _owner is None:_owner,_identity=lock_witness.capture_gpu()
 lock_witness.verify_gpu(_owner,_identity)
 if list(FLAGS.glob('HOLD_*')):raise RuntimeError('global HOLD')
 if shutil.disk_usage(Path(__file__).resolve().parent).free < 214*1024**3:raise RuntimeError('disk floor plus 64 GiB reserve')
 outside=FLAGS.parent/'HOLD_GPU_FOR_QUIET_20261024'
 if outside.exists() or outside.is_symlink():raise RuntimeError('outside HOLD')
 now=time.time();rows=(FLAGS/'FILLERS.md').read_text().splitlines();commitments=0
 for p in sorted((FLAGS/'grants').glob('*.grant')):
  parts=p.read_text().split()
  if len(parts)!=3 or any(x.count('=')!=1 for x in parts):raise RuntimeError('malformed live grant')
  fields=dict(x.split('=',1) for x in parts)
  if set(fields)!={'regions','start','end'}:raise RuntimeError('unknown grant schema')
  def parse(v):
   t=datetime.datetime.fromisoformat(v.replace('Z','+00:00'))
   if t.tzinfo is None:raise RuntimeError('grant lacks timezone')
   return t.timestamp()
  start,end=parse(fields['start']),parse(fields['end'])
  if start>=end:raise RuntimeError('invalid grant interval')
  if end<=now or start>=deadline:continue
  regions=fields['regions'].split(',')
  for region in regions:
   if region=='mi210_0' or region in ('q0','q1','q2','q3'):continue
   m=re.fullmatch(r'(\d+)(?:-(\d+))?',region)
   if not m or int(m.group(1))>int(m.group(2) or m.group(1)) or int(m.group(2) or m.group(1))>=192:raise RuntimeError('unknown grant region')
   if cpus.intersection(range(int(m.group(1)),int(m.group(2) or m.group(1))+1)):raise RuntimeError('live grant overlaps actual smoke CPUs')
  matches=[x for x in rows if x.startswith('| '+p.stem+' |')]
  if len(matches)!=1:raise RuntimeError('live grant lacks unique FILLERS row')
  cells=[cell.strip() for cell in matches[0].strip().strip('|').split('|')]
  if len(cells)!=18 or cells[8] not in ('block-correctness','diagnostic'):raise RuntimeError('timing or unknown grant class')
  if not cells[5].isdigit():raise RuntimeError('unknown grant memory commitment')
  commitments+=int(cells[5])
  if 'mi210_0' in fields['regions'].split(','):raise RuntimeError('GPU grant overlap')
 if admit_ram:
  available=None
  for line in Path('/proc/meminfo').read_text().splitlines():
   if line.startswith('MemAvailable:'):available=int(line.split()[1])*1024
  if available is None or available<(192+64+commitments)*1024**3:raise RuntimeError('live memory plus grant commitments unavailable')
 return True
