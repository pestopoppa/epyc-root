import hashlib,json,os,pathlib,sys,time
D=pathlib.Path(__file__).resolve().parent
ID='kpf623-byte-alignment-exploratory-20261105'
S=json.loads((D/'inputs.json').read_text())
smoke=os.getenv('FILLER_DRYRUN')=='1' or os.getenv('FILLER_SMOKE')=='1'
out=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
def seal():
 for p,h in S['files'].items():
  if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=h:raise RuntimeError('input drift '+p)
def check():
 if pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>float(os.environ['FILLER_END'])-10:raise RuntimeError('STOP/deadline')
def rows(p):
 result=[]
 for i,line in enumerate(pathlib.Path(p).read_text().splitlines()):
  a,b=line.split('\t');piece=bytes.fromhex(b)
  if int(a)!=i or len(piece)>65536:raise RuntimeError('piece ID/size')
  result.append(piece)
 if len(result)!=151936:raise RuntimeError('inventory size')
 return result
if len(sys.argv)>1:
 seal();r=json.loads(out.read_text());raise SystemExit(0 if r.get('row_id')==ID and r.get('status')==('SMOKE_ONLY' if smoke else 'EXPLORATORY_COMPLETE') and r.get('input_seals')==S['files'] else 1)
seal();check()
if smoke and D/'out' in out.resolve().parents:raise SystemExit('smoke/full alias')
if out.exists():raise SystemExit('existing result')
out.parent.mkdir(parents=True,exist_ok=True)
target,aux=rows(S['target']),rows(S['auxiliary'])
# Enumerate all segmentations modulo count saturation at two. Empty auxiliary
# pieces are excluded explicitly: including them yields infinite decompositions.
trie={}
for i,piece in enumerate(aux):
 if not piece:continue
 node=trie
 for byte in piece:node=node.setdefault(byte,{})
 node.setdefault('ids',[]).append(i)
counts={'unique':0,'ambiguous':0,'unrepresentable':0,'empty_target':0};records=[]
for i,piece in enumerate(target[:256] if smoke else target):
 check()
 if not piece:records.append({'target_id':i,'classification':'empty_target'});counts['empty_target']+=1;continue
 ways=[0]*(len(piece)+1);paths=[None]*(len(piece)+1);ways[0]=1;paths[0]=[]
 for start in range(len(piece)):
  if not ways[start]:continue
  node=trie
  for end in range(start,len(piece)):
   node=node.get(piece[end])
   if node is None:break
   ids=node.get('ids',[])
   if ids:
    prior=ways[end+1];ways[end+1]=min(2,prior+ways[start]*len(ids))
    paths[end+1]=paths[start]+[ids[0]] if prior==0 and ways[start]==1 and len(ids)==1 else None
 kind=('unrepresentable','unique','ambiguous')[ways[-1]];counts[kind]+=1
 record={'target_id':i,'classification':kind,'decomposition_count_capped_at_2':ways[-1]}
 if kind=='unique':
  record['auxiliary_ids']=paths[-1]
  if b''.join(aux[j] for j in paths[-1])!=piece:raise RuntimeError('reconstruction')
 records.append(record)
seal();check()
record_path=out.with_suffix('.pieces.json');payload=json.dumps(records,separators=(',',':')).encode()
with record_path.open('xb') as f:f.write(payload)
r={'row_id':ID,'status':'SMOKE_ONLY' if smoke else 'EXPLORATORY_COMPLETE','input_seals':S['files'],'counts':counts,'records':str(record_path),'records_sha256':hashlib.sha256(payload).hexdigest(),'prior_rc':75,'original_census_verdict':'INCONCLUSIVE','tokenizer_compatibility':'UNKNOWN','span_alignment':'UNKNOWN','budget_readmission':'UNKNOWN','scope':'byte-inventory decomposition only; special token semantics not inferred; empty auxiliary pieces excluded; no model/context/tokenizer execution'}
with out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
