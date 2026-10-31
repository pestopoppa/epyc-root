"""Real run admission: only read a live scheduler grant and verify CPU lock."""
import datetime,hashlib,os,time
from pathlib import Path
import lock_witness
ROOT=Path(__file__).resolve().parent
FLAGS=Path('/mnt/raid0/llm/tmp/compute-flags')
ID='codex3-paw-standard-a-t1-20261030'

def capture():
 if os.environ.get('FILLER_PREFLIGHT')=='1' or os.environ.get('FILLER_ID')!=ID or os.environ.get('FILLER_NEEDGPU')!='0' or os.environ.get('FILLER_CPUS') not in ('0-23','24-47','48-71','72-95') or os.environ.get('WS58_REGIONS') != os.environ.get('FILLER_CPUS') or os.environ.get('FILLER_STOPFILE')!=str(ROOT/'STOP'):
  raise ValueError('missing genuine CPU grant context')
 p=FLAGS/'grants'/f'{ID}.grant';raw=p.read_bytes();parts=raw.decode().split()
 if len(parts)!=3 or any(x.count('=')!=1 for x in parts):raise ValueError('invalid grant syntax')
 fields=dict(x.split('=',1) for x in parts)
 if set(fields)!={'regions','start','end'} or fields['regions']!=os.environ['FILLER_CPUS']:raise ValueError('wrong CPU region')
 def ts(s):
  value=datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
  if value.tzinfo is None:raise ValueError('missing grant timezone')
  return value.timestamp()
 start,end=ts(fields['start']),ts(fields['end'])
 if start>=end or int(os.environ['FILLER_END'])!=int(end) or int(os.environ['FILLER_DEADLINE'])!=int(end)-90:raise ValueError('invalid grant deadline')
 quarter={'0-23':0,'24-47':1,'48-71':2,'72-95':3}[os.environ['FILLER_CPUS']]; lock=Path(f'/mnt/raid0/llm/tmp/cpu_region.GLOBAL.q{quarter}.lock');st=lock.stat();lines=Path('/proc/locks').read_text()
 owners=[p for p in lock_witness.ancestors() if lock_witness.lock_matches(lines,p,st)]
 if len(owners)!=1:raise ValueError('missing unique CPU region lock owner')
 owner=owners[0];birth=lock_witness.birth(owner);digest=hashlib.sha256(raw).digest()
 def active():
  try:
   return (hashlib.sha256(p.read_bytes()).digest()==digest and start<=time.time()<end-90
           and not (ROOT/'STOP').exists() and not any(FLAGS.glob('HOLD_*'))
           and owner in lock_witness.ancestors() and lock_witness.birth(owner)==birth
           and lock_witness.lock_matches(Path('/proc/locks').read_text(),owner,lock.stat()))
  except OSError:return False
 if not active():raise ValueError('inactive grant')
 return active
