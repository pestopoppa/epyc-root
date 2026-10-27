"""Project producer-time DF2 AKX observations via the existing measurement ladder."""
from __future__ import annotations
import hashlib,importlib.util,json,re
from pathlib import Path
from claim_tuple import ClaimTuple,ProjectionError,register,to_frames
SOURCE_KIND='df2-row-exact-akx'; ADAPTER_ID='vidya.adapters.df2_row_exact/v1'; AUTHORITY='measurement'; SCHEMA='epyc.df2.row_exact.native.v1'
SHAPES={(5120,17408),(6144,5120),(17408,5120)}
_spec=importlib.util.spec_from_file_location('df2_native',Path(__file__).with_name('df2_native.py')); _native=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_native)
P=re.compile(r'GGML_CUDA_DF2_CHECK_BYTES (PASS|FAIL) node=(\S+) type=(Q8_0|Q4_K) k=(\d+) m=(\d+) width=(\d+) row=(\d+) bytes=(\d+)(?: fnv64=([0-9a-f]{16})| injected=(\d+))')
def _sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _fail(msg): raise ProjectionError(msg)
def _json(p):
 try: return json.loads(Path(p).read_text())
 except (OSError,ValueError) as e: raise ProjectionError('unreadable native JSON') from e
def _files(rec,path):
 out=path.parent; files={}
 for item in rec['artifacts']:
  p=Path(item['path'])
  if not p.is_absolute() or p.parent!=out or p.name in files or p.is_symlink() or not p.is_file() or _sha(p)!=item['sha256']: _fail('artifact missing, foreign or drifted')
  files[p.name]=p
 for item in rec['identities'].values():
  p=Path(item['path'])
  if not p.is_absolute() or p.is_symlink() or not p.is_file() or _sha(p)!=item['sha256']: _fail('identity missing or drifted')
 for label in ('source_seal','build_seal'):
  for line in Path(rec['identities'][label]['path']).read_text().splitlines():
   digest,filename=line.split('  ',1); p=Path(filename)
   if not p.is_absolute() or not p.is_file() or _sha(p)!=digest: _fail('sealed source drifted')
 return files
def _residency(files,stems,gpu):
 for stem in stems:
  receipt=_json(files[stem+'.receipt.json']); samples=[json.loads(x) for x in files[stem+'.samples.jsonl'].read_text().splitlines()]
  if not receipt.get('reaped') or not receipt.get('start_ticks') or _sha(files[stem+'.log'])!=receipt['log_sha256'] or _sha(files[stem+'.samples.jsonl'])!=receipt['samples_sha256']: _fail('bad receipt')
  if sum(receipt['started_ns']<=x.get('t_ns',0)<=receipt['ended_ns'] and x.get('pid')==receipt['pid'] and x.get('gpu_id')==gpu['kfd_gpu_id'] and x.get('pid_in_kfd') is True and x.get('vram_bytes',0)>0 and x.get('process_vram_bytes',0)>0 for x in samples)<2: _fail('missing same-device residency')
 return True
def _cells(path):
 cells={}
 for line in path.read_text().splitlines():
  x=json.loads(line)
  if x.get('record')!='cell': continue
  key=(x.get('id'),x.get('sub'),x.get('sub_label')); v=x.get('first_fail_k')
  if None in key or key in cells or x.get('status')!='OK' or 'first_fail_k' not in x or (v is not None and (type(v) is not int or not 2<=v<=8)): _fail('invalid cell')
  cells[key]=v
 if not cells: _fail('empty cells')
 return cells
def _output(files,gpu):
 result={}
 for cell in ('GPU-MM-Q8_0-D27','GPU-MM-Q4_K-D27'):
  off,on=(cell+'-off',cell+'-on'); _residency(files,(off,on),gpu)
  for stem,enabled in ((off,False),(on,True)):
   r=_json(files[stem+'.receipt.json'])
   if r.get('rc')!=0 or r.get('marker') is not enabled or r.get('flags',{}).get('GGML_CUDA_DF2_ROW_EXACT')!=('1' if enabled else None) or ('GGML_CUDA_DF2_ROW_EXACT active' in files[stem+'.log'].read_text(errors='replace'))!=enabled or _sha(files[stem+'.jsonl'])!=r.get('raw_sha256'): _fail('bad output receipt')
  a,b=_native.read_cells(files[off+'.jsonl'],cell),_native.read_cells(files[on+'.jsonl'],cell)
  if a.keys()!=b.keys(): _fail('mismatched cells')
  off_fail=any(x is not None for x in a.values()); on_fail=any(x is not None for x in b.values())
  result[cell]=('NO_REPRODUCTION_ON_REGRESSION' if on_fail else 'NO_REPRODUCTION') if not off_fail else ('NOT_FIXED' if on_fail else 'FIXED')
 return result
def _byte(files,gpu):
 _residency(files,('q8','q4','mutation'),gpu); seen=set()
 for kind,stem in (('Q8_0','q8'),('Q4_K','q4')):
  receipt=_json(files[stem+'.receipt.json']); flags=receipt.get('flags',{})
  if receipt.get('rc')!=0 or flags!={'GGML_CUDA_DF2_ROW_EXACT':'1','GGML_CUDA_DF2_CHECK_BYTES':'1','GGML_CUDA_DISABLE_GRAPHS':'1','GGML_CUDA_DF2_INJECT_BYTE_MISMATCH':None}: _fail('positive failed or wrong flags')
  for m in P.finditer(files[stem+'.log'].read_text()):
   status,node,typ,k,n,w,r,size,h,inj=m.groups(); k=int(k); n=int(n); w=int(w); r=int(r)
   if status!='PASS' or typ!=kind or (k,n) not in SHAPES or not node or int(size)<=0 or w not in range(2,9) or not 0<=r<w or h is None: _fail('invalid byte capture')
   seen.add((typ,k,n,w,r))
 expected={(typ,k,n,w,r) for typ in ('Q8_0','Q4_K') for k,n in SHAPES for w in range(2,9) for r in range(w)}
 if seen!=expected: _fail('byte coverage incomplete')
 mutation=_json(files['mutation.receipt.json'])
 if mutation.get('rc')==0 or mutation.get('flags',{}).get('GGML_CUDA_DF2_INJECT_BYTE_MISMATCH')!='1' or not any(x.group(1)=='FAIL' and x.group(10)=='1' for x in P.finditer(files['mutation.log'].read_text())): _fail('mutation not proven')
 return {'coverage':len(seen),'mutation':'FAILED_AS_INJECTED'}
def native_rows(path):
 path=Path(path).resolve(); rec=_json(path)
 if rec.get('schema')!=SCHEMA: return ()
 try:
  files=_files(rec,path); gpu=rec['gpu_identity']
  if gpu!=_json(files['gpu-identity.json']) or gpu.get('hip_ordinal_0_pci')!=gpu.get('pci','').lower() or not gpu.get('kfd_gpu_id'): _fail('GPU identity mismatch')
  verdicts=_output(files,gpu) if rec['mode']=='output' else _byte(files,gpu) if rec['mode']=='byte' else _fail('unknown mode')
  if rec.get('protocol_id')!='' or rec.get('backend')!='hip' or rec['verdicts']!=verdicts: _fail('verdict drift')
  if not rec.get('observed_at'): _fail('date missing')
  return tuple({'record_path':str(path),'record_sha256':_sha(path),'record':rec,'key':k,'value':v} for k,v in sorted(verdicts.items()) if k!='mutation')
 except (KeyError,TypeError,ValueError,OSError) as e:
  if isinstance(e,ProjectionError): raise
  raise ProjectionError('invalid DF2 native record') from e
@register(SOURCE_KIND)
def project(native):
 if native not in native_rows(native['record_path']): _fail('native row not rederived')
 r=native['record']; value=native['value']; metric='df2_row_exact_byte_rows' if r['mode']=='byte' else 'df2_row_exact_first_fail_reproduction'
 numeric=value if isinstance(value,int) else (1 if value=='FIXED' else 0)
 return ClaimTuple(measurement_id='df2-row-exact:'+native['record_sha256']+':'+native['key'],metric=metric,value=numeric,date=r['observed_at'],category='CANDIDATE',claim=f"DF2 native {native['key']}: {value} (observation only)",metric_direction='higher_better',protocol_id='',unit='rows' if r['mode']=='byte' else 'flag',attestation_path=native['record_path'],attestation_sha256=native['record_sha256'],attestation_locator='df2-row-exact:'+native['record_path'],attestation_present=True,attestation_verified=True,source_kind=SOURCE_KIND,applicability={'backend':'gpu','device':r['gpu_identity']['pci'],'op':'MUL_MAT','shape':native['key']},extra={'adapter':ADAPTER_ID,'mode':r['mode'],'native_backend':r['backend'],'outcome':value})
def frames_for_record(path,*,as_of):
 return [f for n in native_rows(path) for f in to_frames(project(n),as_of=as_of,adapter_id=ADAPTER_ID,authority='measurement')]
