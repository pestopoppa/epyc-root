"""Bind prospective Oolong server to predecessor model/recipe identity."""
import hashlib,json,urllib.request
from pathlib import Path
import server_witness
PRIOR=Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/heavy-yarn-quarter-ready/v3-s2-independent-20261028/out-v3/shard-2/identity.json')
PRIOR_SHA='ea07360713d0dd16288dd0623f30993073dd40e0569630875316b9966340ad89'
MODEL=Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
SERVER=Path('/mnt/raid0/llm/kernels/production/cpu/llama-server')
TEMPLATE=Path('/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja')
LIBNAMES=('libggml-base.so.0.16.0','libggml-cpu.so.0.16.0','libggml.so.0.16.0','libllama-common.so.0.0.10303','libllama-server-impl.so','libllama.so.0.0.10303')
def prepare(arm,port,active):
 if arm not in ('A0','A1') or type(port)!=int or not 1024<=port<=65535:raise ValueError('bad server parameters')
 if hashlib.sha256(PRIOR.read_bytes()).hexdigest()!=PRIOR_SHA:raise ValueError('predecessor identity changed')
 inst=json.loads(PRIOR.read_bytes())['instrument']
 if server_witness.digest(TEMPLATE,active)!=inst['template']:raise ValueError('template hash changed')
 recipe=inst['recipe_'+arm];argv=[str(port) if x=='PORT' else x for x in recipe]
 if argv.count('PORT') or argv[0]!=str(SERVER):raise ValueError('recipe mismatch')
 build=Path(inst['ld_library_path'])
 libs=[]
 for name in LIBNAMES:
  path=str(build/name);sha=inst['dsos'].get(path)
  if not sha:raise ValueError('missing library pin')
  libs.append((path,sha))
 witness=None;initial_props=False
 def ready(child,identity):
  nonlocal witness,initial_props
  if not active():return False
  if witness is None:
   try:witness=server_witness.Witness(child,port,SERVER,MODEL,inst['model'],inst['binary'],argv,libs,active)
   except (FileNotFoundError,ProcessLookupError):return False
  try:witness.check()
  except RuntimeError as exc:
   if not initial_props and str(exc) in ('listener ambiguous or shared','pinned library not mapped'):return False
   raise
  if not initial_props:
   with urllib.request.urlopen('http://127.0.0.1:%d/props'%port,timeout=2) as r:
    data=r.read(1024*1024+1)
    if len(data)>1024*1024:raise ValueError('props oversized')
   props=json.loads(data)
   if props.get('model_path')!=str(MODEL):raise ValueError('served model mismatch')
   initial_props=True
  return True
 return argv,ready

def prepare_smoke(port,active):
 if type(port)!=int or not 1024<=port<=65535:raise ValueError("bad smoke port")
 model=Path('/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf')
 msha='c159d1518f16bc42533d9a09f034eb598b670341adc2b08b9a9751614aea71eb'
 bsha='4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c'
 if hashlib.sha256(PRIOR.read_bytes()).hexdigest()!=PRIOR_SHA:raise ValueError("predecessor changed")
 inst=json.loads(PRIOR.read_bytes())['instrument'];build=Path(inst['ld_library_path'])
 libs=[(str(build/n),inst['dsos'][str(build/n)]) for n in LIBNAMES]
 argv=[str(SERVER),'-m',str(model),'--host','127.0.0.1','--port',str(port),'-np','1','-t','2','-c','4096','-b','512','-ub','512','-ngl','0','--no-mmap','--cache-ram','0','--jinja']
 witness=None;seen=False
 def ready(child,identity):
  nonlocal witness,seen
  if not active():return False
  if witness is None:
   try:witness=server_witness.Witness(child,port,SERVER,model,msha,bsha,argv,libs,active)
   except (FileNotFoundError,ProcessLookupError):return False
  try:witness.check()
  except RuntimeError as exc:
   if not seen and str(exc) in ('listener ambiguous or shared','pinned library not mapped'):return False
   raise
  if not seen:
   with urllib.request.urlopen('http://127.0.0.1:%d/props'%port,timeout=2) as r:
    data=r.read(1024*1024+1)
    if len(data)>1024*1024:raise ValueError("props oversized")
   if json.loads(data).get('model_path')!=str(model):raise ValueError("smoke served model mismatch")
   seen=True
  return True
 return argv,ready
