#!/usr/bin/env python3
"""Read-only quiet GPU / q3 timing gate; never alters scheduler state."""
import pathlib,sys
F=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags');rows={}
for line in (F/'FILLERS.md').read_text().splitlines():
 if not line.startswith('|'):continue
 c=[x.strip() for x in line.split('|')]
 if len(c)>9:rows[c[1]]=c
for g in (F/'grants').glob('*.grant'):
 text=g.read_text(errors='replace');rid=g.name[:-6]
 if 'mi210' in text:print('GPU grant active',rid);sys.exit(75)
 if 'regions=72-95' in text or 'regions=0-95' in text or 'regions=q3' in text:
  row=rows.get(rid)
  if not row or 'timing' in row[9].lower():print('q3 timing or unknown grant',rid);sys.exit(75)
p=pathlib.Path('/sys/class/kfd/kfd/proc')
if not p.is_dir():print('KFD process state unavailable');sys.exit(75)
active=[q.name for q in p.iterdir() if q.name.isdigit()]
if active:print('GPU KFD process active',','.join(active));sys.exit(75)
print('GPU no active grant/KFD process; no q3 timing/unknown grant')
