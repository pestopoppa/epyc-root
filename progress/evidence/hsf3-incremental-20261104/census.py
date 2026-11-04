#!/usr/bin/env python3
"""Fresh append-only progress census, matched to sealed prior byte frontiers."""
import glob,hashlib,json,os
from pathlib import Path
EVENTS={'session_created','session_resumed','session_checkpointed'}
MAX=1024*1024
D=Path(__file__).resolve().parent

def scan(paths, prior):
    seals={}
    for x in prior['source_frontiers']:
        if x.get('source_class')!='progress_jsonl': continue
        key=(x['bytes_hashed_and_scanned'],x['sha256_hashed_and_scanned_bytes'])
        if key in seals: raise ValueError('ambiguous prior frontier')
        seals[key]=0
    if not seals: raise ValueError('missing prior progress frontiers')
    result={'files_matched':0,'files_unmatched':0,'prior_frontiers_unmatched':0,'appended_bytes':0,'json_records':0,'invalid_json':0,'oversize_records':0,'target_events':0,'target_with_both':0}
    receipts=[]
    for name in sorted(paths):
        with open(name,'rb') as f:
            b=os.fstat(f.fileno())
            if b.st_size > 64*1024*1024: raise ValueError('source exceeds bounded file limit')
            content=f.read(); a=os.fstat(f.fileno())
        if (b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns)!=(a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns) or len(content)!=b.st_size: raise ValueError('unstable source frontier')
        matches=[key for key in seals if key[0]<=len(content) and key[0]>0 and content[key[0]-1:key[0]]==b'\n' and hashlib.sha256(content[:key[0]]).hexdigest()==key[1]]
        if len(matches)>1: raise ValueError('ambiguous matching prior frontier')
        if not matches: result['files_unmatched']+=1; continue
        key=matches[0]; seals[key]+=1
        if seals[key]>1: raise ValueError('multiple files match one prior frontier')
        tail=content[key[0]:]; result['files_matched']+=1; result['appended_bytes']+=len(tail)
        receipts.append({'previous_bytes':key[0], 'previous_sha256':key[1], 'appended_bytes':len(tail), 'appended_sha256':hashlib.sha256(tail).hexdigest()})
        for line in tail.splitlines(keepends=True):
            if not line.endswith(b'\n'): continue
            if len(line)>MAX: result['oversize_records']+=1; continue
            try: row=json.loads(line)
            except (ValueError,UnicodeDecodeError): result['invalid_json']+=1; continue
            if not isinstance(row,dict): result['invalid_json']+=1; continue
            result['json_records']+=1
            et=row.get('event_type') or row.get('event')
            if not isinstance(et,str) or et not in EVENTS: continue
            result['target_events']+=1
            data=row.get('data') if isinstance(row.get('data'),dict) else {}
            result['target_with_both']+=int(bool(data.get('session_id')) and any(bool(row.get(k)) for k in ('timestamp','ts','created_at')))
    result['prior_frontiers_unmatched']=sum(v==0 for v in seals.values())
    return {'schema':'hsf3_incremental_progress.v1','scope':'only append bytes after exact prior full-line byte frontier; unmatched files unknown; SQLite and tap excluded; no gap distribution or independent replicate','progress':result,'frontiers':receipts}

def main():
    prior_bytes=(D/'prior.json').read_bytes(); expected='0ed72adbb2d088f6f50b43df5a34026d47872c5380b889f3bafbfbfa2f9f075e'
    if hashlib.sha256(prior_bytes).hexdigest()!=expected: raise ValueError('prior result seal mismatch')
    if os.environ.get('FILLER_SMOKE')=='1':
        import tempfile
        with tempfile.TemporaryDirectory(dir=D) as tmp:
            p=Path(tmp)/'input'; base=b'{"event":"old"}\n'; p.write_bytes(base+b'{"event":"session_created"}\n'); prior={'source_frontiers':[{'source_class':'progress_jsonl','bytes_hashed_and_scanned':len(base),'sha256_hashed_and_scanned_bytes':hashlib.sha256(base).hexdigest()}]}; result=scan([p],prior)
            if result['progress']['json_records']!=1 or result['progress']['target_events']!=1: raise ValueError('synthetic counter failed')
        out=Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
    else:
        paths=glob.glob('/mnt/raid0/llm/epyc-orchestrator/logs/progress/*.jsonl')
        if not paths: raise ValueError('missing input')
        result=scan(paths,json.loads(prior_bytes)); out=D/'out'/'RESULT.json'
    result['prior_result_sha256']=expected; out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f: json.dump(result,f,indent=2,sort_keys=True); f.write('\n')
if __name__=='__main__': main()
