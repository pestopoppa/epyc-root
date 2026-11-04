"""Prospective frozen-query coverage: native custody, not a quality grader."""
import hashlib, importlib.util, json, math, os
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
carrier=HERE/'_native_sidecar.py' if (HERE/'_native_sidecar.py').exists() else HERE.parent/'adapters'/'_native_sidecar.py'
cs=importlib.util.spec_from_file_location('gs_shared_sidecar', carrier)
c=importlib.util.module_from_spec(cs);cs.loader.exec_module(c)
vs=importlib.util.spec_from_file_location('gs_frozen_contract', HERE/'ufh12_gs_frozen_contract.py')
v=importlib.util.module_from_spec(vs);vs.loader.exec_module(v)
SCHEMA='epyc.vidya.ufh12_gs_frozen_coverage.v2'
LEGACY_SCHEMA='epyc.vidya.ufh12_gs_frozen_coverage.v1'
NATIVE_SCHEMA='epyc.ufh12-gs-frozen-native.v2'
SOURCE_KIND='ufh12-gs-coverage'

def rederive(native):
    context=Path(native['context_path']).read_bytes(); cohort_raw=Path(native['cohort_path']).read_bytes()
    if v.digest(context)!=native['context_sha256'] or v.digest(cohort_raw)!=native['cohort_sha256']:
        raise ValueError('context or cohort changed')
    ctx=json.loads(context); cohort=json.loads(cohort_raw)
    if ctx.get('schema')!='epyc.gs-frozen-query-native-context.v2' or type(ctx.get('synthetic')) is not bool:
        raise ValueError('legacy-unverified or invalid producer fixture declaration')
    if ctx['cohort_sha256']!=v.digest(cohort_raw) or ctx['phase']!='run' or ctx['scope']!=cohort['scope']:
        raise ValueError('foreign context')
    if cohort['n']!=500 or len(cohort['rows'])!=500 or len({q['id'] for q in cohort['rows']})!=500:
        raise ValueError('cohort denominator')
    byid={q['id']:q for q in cohort['rows']}
    contents=Path(native['results_path']).read_bytes()
    if v.digest(contents)!=native['results_sha256']:raise ValueError('results digest changed')
    seen=set(); valid=0
    for line in contents.splitlines():
        r=json.loads(line);v.validate(r,context);qid=r['id'];q=byid.get(qid)
        if not q or qid in seen or r['stratum']!=q['stratum']:raise ValueError('duplicate or foreign query')
        seen.add(qid)
        if r.get('status')=='error':continue
        if r.get('query_sha256')!=v.digest(q['text'].encode()):raise ValueError('query digest mismatch')
        if r.get('answer_named_verbatim')!=q.get('answer_named_verbatim') or r.get('code_intent')!=q.get('code_intent'):
            raise ValueError('query flags mismatch')
        if set(r['stores'])!={'episodic','strategy'}:raise ValueError('stores incomplete')
        for lanes in r['stores'].values():
            if set(lanes)!={'bge','eg2'}:raise ValueError('lanes incomplete')
            for vals in lanes.values():
                if len(vals)!=10 or len({it['id'] for it in vals})!=10:raise ValueError('bad top-k')
                if any(not isinstance(it['cosine'],(int,float)) or isinstance(it['cosine'],bool) or not math.isfinite(it['cosine']) or abs(it['cosine'])>1.0001 for it in vals):raise ValueError('bad cosine')
                if any(vals[i]['cosine']<vals[i+1]['cosine'] for i in range(9)):raise ValueError('unsorted cosine')
        valid+=1
    return valid,len(seen),500,ctx,cohort

def emit(root):
    root=Path(root).resolve();ctxpath=root/'run-context.json';cohort=root/'cohort.json';results=root/'results.jsonl'
    if not results.exists():return None
    context=ctxpath.read_bytes();data=results.read_bytes();cohort_bytes=cohort.read_bytes()
    native={'schema':NATIVE_SCHEMA,'context_path':str(ctxpath),'context_sha256':v.digest(context),'cohort_path':str(cohort),'cohort_sha256':v.digest(cohort_bytes),'results_path':str(results),'results_sha256':v.digest(data)}
    valid,seen,expected,ctx,co=rederive(native);native.update(valid=valid,seen=seen,expected=expected)
    rec=root/'frozen-coverage.record.json';tmp=rec.with_suffix('.tmp');tmp.write_text(json.dumps(native,sort_keys=True)+'\n');os.replace(tmp,rec)
    now=datetime.now(timezone.utc).isoformat();rid=ctx['filler_id']+'-'+ctx['cohort_sha256'][:12]
    row={'schema':SCHEMA,'run_id':rid,'producer':'ufh12-gs-frozen-query-coverage','measurement_id':'gs_'+hashlib.sha256((rid+'\0valid_frozen_query_records').encode()).hexdigest()[:24],'metric':'valid_frozen_query_records','value':valid,'unit':'records','metric_direction':'higher_better','category':'CANDIDATE','claim':f'{valid} of {expected} frozen-query records captured; coverage only, not quality','protocol_id':'','reps':1,'reps_basis':'native-capture-snapshot','results_path':str(rec),'results_sha256':c.file_sha256(rec),'date':now,'emitted_at':now,'extra':{'expected_count':expected,'attempted_count':seen,'complete':valid==expected,'scope':co['scope'],'context_sha256':native['context_sha256'],'synthetic':ctx['synthetic'],'synthetic_scope':'producer-declared'}}
    c.seal(row); side=root/'frozen-coverage.belief_measurements.jsonl';c.write_rows_atomic(side,[row]);return side

def validate(row):
    try:
        if row.get('schema')==LEGACY_SCHEMA:
            return ['legacy frozen-query fixture declaration is unverified']
        errors=c.common_problems(row,schema=SCHEMA,optional_text=('protocol_id',))+c.self_hash_problems(row)
        if errors or not c.results_present(row):return errors+['native attestation absent or changed']
        native=json.loads(Path(row['results_path']).read_text()); valid,seen,expected,ctx,co=rederive(native)
        rid=ctx['filler_id']+'-'+ctx['cohort_sha256'][:12]
        expected_id='gs_'+hashlib.sha256((rid+'\0valid_frozen_query_records').encode()).hexdigest()[:24]
        if (native['schema']!=NATIVE_SCHEMA or native['valid']!=valid or native['seen']!=seen or native['expected']!=expected or row['measurement_id']!=expected_id or row['run_id']!=rid or row['metric']!='valid_frozen_query_records' or row['value']!=valid or row['extra']!={'expected_count':expected,'attempted_count':seen,'complete':valid==expected,'scope':co['scope'],'context_sha256':native['context_sha256'],'synthetic':ctx['synthetic'],'synthetic_scope':'producer-declared'} or row['claim']!=f'{valid} of {expected} frozen-query records captured; coverage only, not quality' or row['protocol_id']!='' or row['unit']!='records' or row['metric_direction']!='higher_better' or row['category']!='CANDIDATE'):
            return ['coverage projection mismatch']
        return []
    except (KeyError,ValueError,TypeError,OSError,json.JSONDecodeError):return ['invalid frozen-query native record']

def project(row):
    problems=validate(row)
    if problems:raise ValueError(str(problems))
    from dataclasses import replace
    return replace(c.to_claim_tuple(row,source_kind=SOURCE_KIND,locator=row['results_path']),applicability={'backend':'cpu'},observation={'outcome_native':'complete' if row['extra']['complete'] else 'partial'})
