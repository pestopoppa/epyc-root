from pathlib import Path
import json
base=Path('/mnt/raid0/llm/tmp');digest='cfde3734fb4367cc748fefb7ac6df034269a8f40f20bfa05c81e69eaea7eeadb'; found=[]
for directory in base.iterdir():
 if not directory.is_dir():continue
 try: files=list(directory.glob('*DECLARATION*.json'))+list(directory.glob('*MANIFEST*.json'))+list(directory.glob('*SOURCE*.json'))
 except PermissionError:continue
 for path in files:
  try:
   data=path.read_text()
   if digest not in data:continue
   obj=json.loads(data);ids=[]
   def walk(x):
    if isinstance(x,dict):
     if type(x.get('source_index')) is int:ids.append(x['source_index'])
     for v in x.values():walk(v)
    elif isinstance(x,list):
     for v in x:walk(v)
   walk(obj)
   if ids:found.append({'file':str(path),'indices':sorted(set(ids))})
  except (OSError,ValueError,UnicodeError):continue
conflicts=[x for x in found if set(x['indices']) & set(range(39,50))]
print(json.dumps({'scope':'top-level temporary campaign declaration and manifest JSON; reservations conservatively treated as exposed','source_sha256':digest,'records':len(found),'candidate_39_49_conflicts':conflicts},indent=2))
if conflicts:raise SystemExit(1)
