import collections, hashlib, json, os, pathlib, sys, time
D=pathlib.Path(__file__).resolve().parent
ID='kpf623-byte-align-r2-20261105'
target=D/'target.tsv'
aux=D/'aux.tsv'
prior=D/'prior.json'
records=D/'prior.pieces.json'
pins={str(target):'902ea571177dd0f5092b82e0aa39d562ede8d47efdd7fdde173ef9bf45227b1c',str(aux):'c2eb2f9537c5cd877d040f5dacc33ca87dba48c4aac0aa75cc6cd843cf7930af',str(prior):'3cda9af7ffbb5ca5ef266d7a8bd5d25c86bc188be28fd2c6a2bce11db7adf3fb',str(records):'777b546d6f630ef6420e20c57520e513f894a5cbbdf10346aee39c5bba0b1c59'}
smoke=os.getenv('FILLER_DRYRUN')=='1' or os.getenv('FILLER_SMOKE')=='1'
out=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
def check():
 if pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>float(os.environ['FILLER_END'])-10: raise RuntimeError('STOP/deadline')
def seal():
 for p,h in pins.items():
  if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=h: raise RuntimeError('input drift')
def rows(p):
 result=[]
 for i,line in enumerate(p.read_text().splitlines()):
  a,b=line.split('\t'); piece=bytes.fromhex(b)
  if int(a)!=i or len(piece)>65536: raise RuntimeError('piece ID/size')
  result.append(piece)
 if len(result)!=151936: raise RuntimeError('inventory size')
 return result
if len(sys.argv)>1:
 seal()
 if not out.is_file(): raise SystemExit(1)
 actual=json.loads(out.read_text())
 a=rows(aux); empty=[i for i,p in enumerate(a) if not p]
 old=json.loads(prior.read_text())
 valid=(actual.get('row_id')==ID and actual.get('status')==('SMOKE_ONLY' if smoke else 'EXPLORATORY_COMPLETE') and actual.get('input_seals')==pins and actual.get('counts')==old.get('counts') and actual.get('empty_auxiliary_ids')==empty and actual.get('empty_auxiliary_count')==len(empty) and actual.get('prior_record_sha256')==pins[str(records)])
 seal(); raise SystemExit(0 if valid else 1)
seal();check()
a=rows(aux); t=rows(target); old=json.loads(prior.read_text()); rr=json.loads(records.read_text())
if old.get('status')!='EXPLORATORY_COMPLETE' or old.get('records_sha256')!=pins[str(records)] or len(rr)!=len(t): raise RuntimeError('prior binding')
counts=collections.Counter()
for i,entry in enumerate(rr):
 if i%1024==0: check()
 if entry.get('target_id')!=i: raise RuntimeError('target id')
 kind=entry.get('classification'); counts[kind]+=1
 if kind=='unique':
  ids=entry.get('auxiliary_ids');
  if not isinstance(ids,list) or any(type(j)!=int or j<0 or j>=len(a) or not a[j] for j in ids) or b''.join(a[j] for j in ids)!=t[i]: raise RuntimeError('reconstruction')
 if kind not in ('unique','ambiguous','unrepresentable','empty_target') or (kind=='empty_target')!=(not t[i]): raise RuntimeError('classification')
if dict(counts)!={k:v for k,v in old['counts'].items() if v}: raise RuntimeError('counts')
empty=[i for i,p in enumerate(a) if not p]
seal();check()
result={'row_id':ID,'status':'SMOKE_ONLY' if smoke else 'EXPLORATORY_COMPLETE','input_seals':pins,'counts':old['counts'],'empty_auxiliary_ids':empty,'empty_auxiliary_count':len(empty),'prior_record_sha256':pins[str(records)],'scope':'retained byte inventories; no tokenizer compatibility, quality or native census claim'}
if smoke and D/'out' in out.resolve().parents: raise RuntimeError('smoke/full alias')
if out.exists(): raise RuntimeError('existing result')
out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x') as f: json.dump(result,f,indent=2); f.write('\n')
