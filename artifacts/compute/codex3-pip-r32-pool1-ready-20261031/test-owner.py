import sys,os,tempfile,importlib.util
from pathlib import Path
sys.path=[p for p in sys.path if p not in ('',str(Path(__file__).resolve().parent))]
from unittest.mock import patch
p='/mnt/micron/codex3-pip-pool1-r32-20261031/pool.py';s=importlib.util.spec_from_file_location('pool',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);os.environ['FILLER_ID']='codex3-pip02-paddle-relocatable-r32-pool1-20261031'
assert not m.old_r22_retired();m.POOL_LOCKED=True;assert m.old_r22_retired();assert m.active_group(68) is None
with tempfile.TemporaryDirectory() as d:
 f=Path(d);(f/'grants').mkdir();(f/'ready').mkdir();(f/'ready/armed').mkdir();(f/'ws58-calendar-keeper.log').write_text('REARM-RESULT '+m.OLD_ID+': OK '+m.OLD_ID+' pid=2296183\n');stop=f/'STOP-1';stop.write_text('');m.F=f;m.OLD_STOP=stop
 exists=Path.exists; iterdir=Path.iterdir;read=Path.read_text
 def no_old(p):return False if str(p)=='/proc/2296183' else exists(p)
 def no_proc(p):return iter(()) if str(p)=='/proc' else iterdir(p)
 def netempty(p,*a,**kw):return 'header\n' if str(p) in ('/proc/net/tcp','/proc/net/tcp6') else read(p,*a,**kw)
 with patch.object(Path,'exists',no_old),patch.object(Path,'iterdir',no_proc),patch.object(Path,'read_text',netempty):
  assert m.old_r22_retired()
  grant=f/'grants'/f'{m.OLD_ID}.grant';grant.write_text('future');assert not m.old_r22_retired();grant.unlink()
  stop.unlink();assert not m.old_r22_retired();stop.write_text('')
  ready=f/'ready'/f'{m.OLD_ID}.json';ready.write_text('{}');assert not m.old_r22_retired();ready.unlink()
  with (f/'ws58-calendar-keeper.log').open('a') as z:z.write('REARM-RESULT '+m.OLD_ID+': OK '+m.OLD_ID+' pid=777777\n')
  assert not m.old_r22_retired()
print('actual source-pinned STOP idle owner accepted; simulated retired owner accepted; grant, removed STOP, READY, newer generation refused')
