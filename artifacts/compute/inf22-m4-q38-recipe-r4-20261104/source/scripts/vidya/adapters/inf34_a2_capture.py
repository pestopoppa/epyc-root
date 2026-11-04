"""Prospective raw capture only; no grading, receipt or protocol attestation."""
import hashlib,json,os,time
from pathlib import Path
SCHEMA='epyc.inf34.raw_a2_observation.v1'
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def file_sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def create(path,value):
 raw=canonical(value)+b'\n';fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  view=memoryview(raw)
  while view:
   n=os.write(fd,view)
   if n<=0:raise OSError("short raw capture write")
   view=view[n:]
  os.fsync(fd)
 finally:os.close(fd)
 parent=os.open(Path(path).parent,os.O_DIRECTORY|os.O_RDONLY)
 try:os.fsync(parent)
 finally:os.close(parent)
def begin(root,intent):
 root=Path(root)
 if root.is_symlink() or not root.is_dir() or intent['run_id']!=root.name:raise ValueError('run identity')
 row=dict(intent,schema=SCHEMA,producer_sha256=file_sha(Path(__file__)),started_monotonic=time.monotonic())
 row['content_sha256']=digest(row);create(root/'intent.json',row)
 return row
def finish(root,intent,attempts,state,cleanup):
 root=Path(root)
 if state not in ('complete','partial','failed') or not isinstance(cleanup,bool) or (state=='complete' and not cleanup):raise ValueError('terminal custody')
 if json.loads((root/'intent.json').read_bytes())!=intent:raise ValueError('intent mutated')
 files={}
 for attempt in attempts:
  for key in ('stdout','stderr','telemetry'):
   name=attempt[key];p=root/name
   if Path(name).name!=name or p.is_symlink() or not p.is_file():raise ValueError('native file identity')
   files[name]=file_sha(p)
 for name in ('INHERITED-START.json','INHERITED-SAMPLES.jsonl','INHERITED-FINISH.json'):
  if (root/name).is_file():files[name]=file_sha(root/name)
 row={'schema':SCHEMA,'run_id':root.name,'intent_sha256':file_sha(root/'intent.json'),'intent':intent,'attempts':attempts,'state':state,'cleanup_verified':cleanup,'files':files,'finished_monotonic':time.monotonic()}
 row['content_sha256']=digest(row);create(root/'raw-a2.observation.json',row)
 return row

"""Strict raw readback; the full single-cell predicate and qualifier stay separate."""
import math,re
from pathlib import Path
HEAD='ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
OVERRIDE=r'\.ffn_(up|down|gate|gate_up)_(ch|)exps=CPU'
HIP_SHA='f26a166b8ea3089d19a395ae00afa22e917df8eba71ca6ef4be5235d65ea8079'
def image_witness(sample,intent):
 aliases=intent['view_aliases'];expected={a['target']:a['sha256'] for a in aliases.values()}
 needed=('libggml-base.so.0.16.0','libggml-cpu.so.0.16.0','libllama-bench-impl.so')
 if intent['backend']=='gpu':
  needed+=('libggml-hip.so.0.16.0',)
  if aliases['libggml-hip.so.0.16.0']['sha256']!=HIP_SHA:return False
 required={aliases[n]['target'] for n in needed}
 maps=sample.get('mapped_images')
 if not isinstance(maps,list) or sample.get('actual_cpu_affinity')!=intent.get('actual_cpu_affinity'):return False
 actual={m.get('path'):m.get('sha256') for m in maps}
 return required<=actual.keys() and all(p in expected and expected[p]==h for p,h in actual.items())
def checked_hash(row):
 if row.get('content_sha256')!=digest({k:v for k,v in row.items() if k!='content_sha256'}):raise ValueError('content tampered')
def parse_output(path,length,reps):
 text=Path(path).read_text();decoder=json.JSONDecoder();rows=[]
 for i,c in enumerate(text):
  if c!='{':continue
  try:row,_=decoder.raw_decode(text[i:])
  except ValueError:continue
  if isinstance(row,dict) and row.get('n_prompt')==length and row.get('n_gen')==0:rows.append(row)
 if len(rows)!=1:raise ValueError('exact native row missing or duplicated')
 row=rows[0]
 if row.get('build_number')!=10303 or not re.fullmatch('[0-9a-f]{7,40}',str(row.get('build_commit',''))) or not HEAD.startswith(str(row.get('build_commit','!'))):raise ValueError('v10 source mismatch')
 if row.get('tensor_buft_overrides')!=OVERRIDE:raise ValueError('A2 override mismatch')
 for key in ('samples_ts','samples_ns'):
  values=row.get(key)
  if not isinstance(values,list) or len(values)!=reps or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in values):raise ValueError('native sample denominator')
 return row
def read(root):
 root=Path(root);path=root/'raw-a2.observation.json'
 if root.is_symlink() or path.is_symlink() or path.stat().st_size>4*1024**2:raise ValueError('raw path')
 row=json.loads(path.read_bytes());checked_hash(row)
 if row.get('schema')!=SCHEMA or row.get('run_id')!=root.name or row.get('cleanup_verified') is not True:raise ValueError('terminal identity')
 intent=row['intent'];checked_hash(intent)
 if intent.get('schema')!=SCHEMA or intent.get('run_id')!=root.name or file_sha(root/'intent.json')!=row['intent_sha256'] or json.loads((root/'intent.json').read_bytes())!=intent:raise ValueError('intent/replay mismatch')
 for name,expected in row['files'].items():
  p=root/name
  if Path(name).name!=name or p.is_symlink() or file_sha(p)!=expected:raise ValueError('native raw custody')
 if intent['backend']=='gpu' and row['state']=='complete':
  for name in ('INHERITED-START.json','INHERITED-SAMPLES.jsonl','INHERITED-FINISH.json'):
   if name not in row['files']:raise ValueError('inherited calendar observation missing')
  start=json.loads((root/'INHERITED-START.json').read_bytes());end=json.loads((root/'INHERITED-FINISH.json').read_bytes())
  if start.get('state')!='inherited-held' or end.get('state')!='inherited-held' or end.get('outer_lock_held_at_finish') is not True or end.get('samples',0)<2:raise ValueError('inherited outer claim not continuously observed')
 shape=intent['geometry'];complete=[]
 affinity=intent.get('actual_cpu_affinity')
 if not isinstance(affinity,list) or len(affinity)!=shape['threads'] or len(set(affinity))!=len(affinity) or any(type(x) is not int or not 0<=x<192 for x in affinity):raise ValueError('actual CPU placement')
 for attempt in row['attempts']:
  samples=json.loads((root/attempt['telemetry']).read_bytes())
  if attempt['state']=='complete':
   if attempt['returncode']!=0:raise ValueError('successful native rc')
   native=parse_output(root/attempt['stdout'],shape['n_prompt'],shape['reps'])
   witnessed=[s for s in samples if s.get('pid')==attempt['pid'] and s.get('birth')==attempt['birth'] and image_witness(s,intent) and (intent['backend']=='cpu' or (s.get('vram_bytes',0)>0 and s.get('kfd_pid_directory') is True and s.get('device')=='0'))]
   witnessed=[w for w in witnessed if isinstance(w.get('monotonic'),(int,float)) and intent['started_monotonic']<=w['monotonic']<=row['finished_monotonic']]
   if len({w['monotonic'] for w in witnessed})<2:raise ValueError('in-window own native image witness missing')
   complete.append(native)
 row['native_rows']=complete;row['public_locator']=str(path)
 return row
def require_complete(root,mode):
 row=read(root)
 if row['intent']['mode']!=mode or row['state']!='complete':raise ValueError('wrong completion scope')
 if mode=='official' and (row['intent']['backend']!='gpu' or len(row['attempts'])!=1 or len(row['native_rows'])!=1 or row['intent']['geometry']['n_prompt']!=16384 or row['intent']['geometry']['reps']!=1):raise ValueError('original single-cell scope')
 return row
