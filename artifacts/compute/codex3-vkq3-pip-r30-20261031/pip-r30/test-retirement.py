import importlib.util,tempfile,os
from pathlib import Path
P='/mnt/micron/codex3-pip-pool2-r30-v2-20261031/pool.py';s=importlib.util.spec_from_file_location('p',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert m.old_r22_retired() is False
m.POOL_LOCKED=True;assert m.old_r22_retired() is True
with tempfile.TemporaryDirectory() as d:
 f=Path(d);(f/'grants').mkdir();(f/'ready').mkdir();(f/'ready/armed').mkdir();src=m.F;end=src/'grants'/f'{m.OLD_ID}.ended';(f/'grants'/end.name).write_bytes(end.read_bytes());log=src/'ws58-calendar-keeper.log';(f/'ws58-calendar-keeper.log').write_text(log.read_text());m.F=f
 assert m.old_r22_retired()
 grant=f/'grants'/f'{m.OLD_ID}.grant';grant.write_text('future');assert not m.old_r22_retired();grant.unlink()
 queue=f/'future.queue';queue.write_text(m.OLD_ID);assert not m.old_r22_retired();queue.unlink()
 ready=f/'ready'/f'{m.OLD_ID}.json';ready.write_text('{}');assert not m.old_r22_retired();ready.unlink()
 e=f/'grants'/end.name;e.write_bytes(end.read_bytes()+b'changed');assert not m.old_r22_retired();e.write_bytes(end.read_bytes())
 with (f/'ws58-calendar-keeper.log').open('a') as z:z.write('\nREARM-RESULT '+m.OLD_ID+': OK '+m.OLD_ID+' pid=111111\n')
 assert not m.old_r22_retired()
print('old retirement: unlocked refusal, live positive, active/future grant/queue/ready, changed terminal and newer generation negatives passed')
