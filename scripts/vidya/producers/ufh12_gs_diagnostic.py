#!/usr/bin/env python3
"""G-S proxy diagnostic. Never mutates source stores; all output under --out."""
import argparse, hashlib, importlib.util, json, math, os, sys, time, urllib.request
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

DOC = 'title: none | text: '
QUERY = 'task: search result | query: '
OLD = {'episodic': 'sessions.pre-eg2-20261026T054229Z-3a990d', 'strategy': 'strategies.pre-eg2-20261026T054229Z-3a990d'}
NEW = {'episodic': 'sessions', 'strategy': 'strategies'}
FILES = {'episodic': ('embeddings.faiss','id_map.npy','episodic.db'), 'strategy': ('strategy_embeddings.faiss','strategy_id_map.npy','strategies.db')}
SEED = 'ufh12-gs-20261027-v1'

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def seal(obj):
    obj['record_sha256']=hashlib.sha256(canonical({k:v for k,v in obj.items() if k!='record_sha256'})).hexdigest()
    return obj
def valid_seal(obj):
    return obj.get('record_sha256')==hashlib.sha256(canonical({k:v for k,v in obj.items() if k!='record_sha256'})).hexdigest()
@lru_cache(maxsize=1024)
def proof_valid(path,sha,mtime,size): return digest(Path(path))==sha
def valid_context(ctx):
    try:
        def check(path,sha):
            p=Path(path); st=p.stat(); return p.is_file() and proof_valid(path,sha,st.st_mtime_ns,st.st_size)
        return bool(ctx['region_lock_claim'] and ctx['server_proof']) and all(check(path,sha) for path,sha in ctx['server_proof'].items())
    except (KeyError,TypeError,OSError): return False
def save(path, obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    with open(tmp,'wb') as f:
        f.write(canonical(obj)); f.write(b'\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)
def load(path):
    with open(path) as f: return json.load(f)
def now(): return datetime.now(timezone.utc).isoformat()
def stopped(args): return time.monotonic()>=args.deadline or bool(os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists())
def post(url, endpoint, obj, timeout=45):
    req=urllib.request.Request(url.rstrip('/')+endpoint,data=canonical(obj),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)
def module(path):
    spec=importlib.util.spec_from_file_location('ufh12_migration',path); m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m

def pin(root, tool):
    paths={}
    for kind in FILES:
        for lane, d in [('old',OLD[kind]),('new',NEW[kind])]:
            for f in FILES[kind]:
                p=root/d/f; paths[str(p)] = digest(p)
    paths[str(tool)]=digest(tool); paths[str(Path(__file__).resolve())]=digest(Path(__file__))
    return paths

def sources(root, tool):
    import numpy as np
    m=module(tool); result={}
    for kind, cls in [('episodic',m.EpisodicComponent),('strategy',m.StrategyComponent)]:
        comp=cls(root/OLD[kind]); ids=comp._load_id_map()
        new=np.load(root/NEW[kind]/FILES[kind][1],allow_pickle=True).tolist(); new=[str(x) for x in new]
        if len(set(ids)) != len(ids) or len(set(new))!=len(new) or len(ids)!=len(new) or set(ids)!=set(new): raise ValueError('ID sets differ or duplicates: '+kind)
        result[kind]=(comp,ids,new)
    return result

def prepare(args):
    root=Path(args.copy).resolve(); tool=Path(args.tool).resolve(); out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=True)
    if out==root or root in out.parents or out in root.parents: raise ValueError('output overlaps source')
    src=sources(root,tool); pins=pin(root,tool)
    for identity in (args.bge_model,args.eg2_model,args.server_bin):
        path=Path(identity).resolve(); pins[str(path)]=digest(path)
    selections={}
    for kind,n in [('episodic',489),('strategy',11)]:
        ids=src[kind][1]
        if len(ids)<n: raise ValueError('not enough IDs')
        selections[kind]=sorted(ids,key=lambda x: (hashlib.sha256((SEED+'\0'+kind+'\0'+x).encode()).digest(),x))[:n]
    manifest={'schema':'ufh12-gs-proxy-manifest/v1','seed':SEED,'selection':selections,'corpus_ids':{k:v[1] for k,v in src.items()},'counts':{k:len(v[1]) for k,v in src.items()},'pins':pins,'copy':str(root),'tool':str(tool),'query_kind':'stored-text proxy; not observed queries or relevance labels','bge_query_prefix':'','eg2_query_prefix':QUERY,'eg2_document_prefix':DOC,'score_dims':[1024,256],'k':[5,10],'self_excluded':True,'ties':'score descending, ID ascending','percentiles':[0,5,25,50,75,95,100],'quantile_method':'linear','thresholds':[0.1,0.3,0.4,0.6,0.7,0.75,0.85,0.9]}
    target=out/'manifest.json'
    if target.exists():
        if load(target)!=manifest: raise ValueError('manifest or inputs changed; refuse resume')
    else: save(target,manifest)
    return manifest,src

def resolve(comp, ids, m):
    with m._ro_connect(comp.dir/comp.db_name) as con:
        found={}
        for start in range(0,len(ids),500): found.update(comp.resolve_rows(con,ids[start:start+500]))
    texts=[]
    for i in ids:
        t,reason=found.get(i,(None,'no_db_row'))
        if not t: raise ValueError('unresolved source '+i+' '+str(reason))
        texts.append(t)
    return texts

def tokens(args, manifest, src, m):
    out=Path(args.out); total=0; manifest_sha=digest(out/'manifest.json')
    for kind,(comp,ids,_) in src.items():
        for start in range(0,len(ids),32):
            name=out/f'tokens-{kind}-{start:06d}.json'; subset=ids[start:start+32]
            if name.exists():
                record=load(name)
                if (not valid_seal(record) or record['manifest_sha256']!=manifest_sha or record['ids']!=subset[:len(record['counts'])]
                    or len(record['counts'])>len(subset) or any(type(x)!=int or x<0 for x in record['counts'])
                    or not record.get('captured_at') or len(record['contexts'])!=len(record['counts']) or any(not valid_context(x) for x in record['contexts'])): raise ValueError('invalid token checkpoint')
            else:
                record={'manifest_sha256':manifest_sha,'ids':[],'counts':[],'contexts':[],'captured_at':now()}
            remaining=subset[len(record['counts']):]
            texts=resolve(comp,remaining,m)
            for ident,text in zip(remaining,texts):
                left=args.deadline-time.monotonic()
                if left<=0 or stopped(args): break
                response=post(args.eg2_url,'/tokenize',{'content':DOC+text,'add_special':True},timeout=min(45,left))
                ts=response['tokens']
                if not isinstance(ts,list) or not ts or any(type(t)!=int for t in ts): raise ValueError('invalid token response')
                record['ids'].append(ident); record['counts'].append(len(ts)); record['contexts'].append(args.context); record['captured_at']=now()
                save(name,seal(record))
            total+=len(record['counts'])
            if len(record['counts'])<len(subset) or stopped(args): return False
    records=[]
    for kind,(_,ids,_) in src.items():
        counts=[]
        for start in range(0,len(ids),32): counts.extend(load(out/f'tokens-{kind}-{start:06d}.json')['counts'])
        if len(counts)!=len(ids): raise ValueError('token count mismatch')
        records.append({'store':kind,'n':len(counts),'percentiles':pct(counts),'over_2048':sum(v>2048 for v in counts),'max':max(counts)})
    save(out/'tokens-summary.json',{'schema':'ufh12-gs-token-diagnostic/v1','manifest_sha256':digest(out/'manifest.json'),'records':records,'complete':True,'add_special':True})
    return True

def pct(x):
    import numpy as np
    return {str(q):float(np.percentile(x,q,method='linear')) for q in [0,5,25,50,75,95,100]}
def query(url,text,dim,eg2,timeout=45):
    import numpy as np
    r=post(url,'/v1/embeddings',{'input':(QUERY if eg2 else '')+text},timeout=timeout)
    rows=r['data']
    if not isinstance(rows,list) or len(rows)!=1 or rows[0].get('index')!=0: raise ValueError('invalid embedding row/index')
    values=rows[0]['embedding']
    if not isinstance(values,list) or any(type(x) not in (int,float) for x in values): raise ValueError('invalid embedding vector')
    a=np.asarray(values,dtype=np.float32)
    if eg2:
        if len(a)!=768: raise ValueError('EG2 native dimension')
        a=a[:256]
    elif len(a)!=dim: raise ValueError('BGE dimension')
    if not np.isfinite(a).all() or np.linalg.norm(a)==0: raise ValueError('invalid query vector')
    return a/np.linalg.norm(a)
def index(root,folder,kind,dim,ids):
    import numpy as np
    import faiss
    idx=faiss.read_index(str(root/folder/FILES[kind][0]));
    if idx.d!=dim or idx.ntotal!=len(ids) or type(idx).__name__!='IndexFlatIP': raise ValueError('invalid index')
    vectors=idx.reconstruct_n(0,idx.ntotal)
    norm=np.linalg.norm(vectors,axis=1)
    if not np.isfinite(vectors).all() or not np.allclose(norm,1,atol=1e-3): raise ValueError('non-unit or non-finite index')
    return vectors

def valid_score(row,kind,ident,manifest_sha,oldids,newids):
    try:
        if not valid_seal(row) or row['manifest_sha256']!=manifest_sha or row['store']!=kind or row['id']!=ident or not row['captured_at'] or not valid_context(row['context']):
            return False
        for lane,ids in [('bge',oldids),('eg2',newids)]:
            items=row[lane]
            if not isinstance(items,list) or len(items)!=10: return False
            names=[x['id'] for x in items]; allowed=set(ids)
            if len(set(names))!=10 or ident in names or not set(names)<=allowed: return False
            if any(type(x['cosine']) not in (int,float) or not math.isfinite(x['cosine']) or abs(x['cosine'])>1.00001 for x in items): return False
            if items!=sorted(items,key=lambda x:(-x['cosine'],x['id'])): return False
        return True
    except (KeyError,TypeError,ValueError): return False

def scores(args,manifest,src,m):
    root=Path(manifest['copy']); out=Path(args.out); results=[]; manifest_sha=digest(out/'manifest.json')
    for kind,(comp,oldids,newids) in src.items():
        old=index(root,OLD[kind],kind,1024,oldids); new=index(root,NEW[kind],kind,256,newids)
        selected=manifest['selection'][kind]; texts=resolve(comp,selected,m)
        for ident,text in zip(selected,texts):
            if stopped(args): return False
            key=hashlib.sha256((kind+'\0'+ident).encode()).hexdigest(); path=out/('score-'+key+'.json')
            if path.exists():
                row=load(path)
                if not valid_score(row,kind,ident,manifest_sha,oldids,newids): raise ValueError('invalid score checkpoint')
            else:
                lanes=[]
                for url,dim,eg,vec,ids in [(args.bge_url,1024,False,old,oldids),(args.eg2_url,256,True,new,newids)]:
                    left=args.deadline-time.monotonic()
                    if left<=0 or stopped(args): return False
                    sims=vec@query(url,text,dim,eg,min(45,left)); order=sorted((i for i in range(len(ids)) if ids[i]!=ident),key=lambda i:(-float(sims[i]),ids[i]))[:10]
                    lanes.append([{'id':ids[i],'cosine':float(sims[i])} for i in order])
                row=seal({'manifest_sha256':manifest_sha,'store':kind,'id':ident,'bge':lanes[0],'eg2':lanes[1],'captured_at':now(),'context':args.context})
                if not valid_score(row,kind,ident,manifest_sha,oldids,newids): raise ValueError('invalid generated score')
                save(path,row)
            results.append(row)
            if stopped(args): return False
    summaries=[]
    for kind in src:
        rows=[r for r in results if r['store']==kind]
        if len(rows)!=len(manifest['selection'][kind]): raise ValueError('incomplete scores')
        for k in [5,10]:
            overlap=[len({v['id'] for v in r['bge'][:k]} & {v['id'] for v in r['eg2'][:k]})/k for r in rows]
            summaries.append({'store':kind,'k':k,'n_queries':len(rows),'overlap_fraction_percentiles':pct(overlap),'cosine_percentiles':{lane:pct([x['cosine'] for r in rows for x in r[lane][:k]]) for lane in ['bge','eg2']},'threshold_counts':{lane:{str(t):sum(x['cosine']>=t for r in rows for x in r[lane][:k]) for t in manifest['thresholds']} for lane in ['bge','eg2']}})
    save(out/'scores-summary.json',{'schema':'ufh12-gs-score-diagnostic/v1','manifest_sha256':digest(out/'manifest.json'),'proxy':True,'complete':True,'records':summaries})
    return True

def main():
    p=argparse.ArgumentParser(); p.add_argument('facet',choices=['prepare','tokens','scores']); p.add_argument('--copy',required=True); p.add_argument('--tool',required=True); p.add_argument('--out',required=True); p.add_argument('--bge-model',required=True); p.add_argument('--eg2-model',required=True); p.add_argument('--server-bin',required=True); p.add_argument('--eg2-url'); p.add_argument('--bge-url'); p.add_argument('--context'); p.add_argument('--budget-seconds',type=int,default=900); a=p.parse_args()
    if a.budget_seconds<1 or a.budget_seconds>900: p.error('budget must be 1..900')
    a.deadline=time.monotonic()+a.budget_seconds; man,src=prepare(a)
    if a.facet=='prepare': return
    if not a.eg2_url or (a.facet=='scores' and not a.bge_url): p.error('missing endpoint')
    if not a.context: p.error('missing run context')
    a.context=load(Path(a.context))
    if not valid_context(a.context): p.error('incomplete run context')
    m=module(Path(a.tool)); complete=tokens(a,man,src,m) if a.facet=='tokens' else scores(a,man,src,m)
    print('COMPLETE' if complete else 'PARTIAL',flush=True)
    if not complete: sys.exit(75)
if __name__=='__main__': main()
