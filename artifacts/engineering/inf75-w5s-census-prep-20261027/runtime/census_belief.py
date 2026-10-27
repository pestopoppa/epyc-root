"""Prospective W5s structural census carrier, no protocol or retrospective reconstruction.

Private draft: write immediately after native journal/record seal. Three boolean
shape observations are separately located; they are not rates or quality scores.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, sys, time
ROOT=Path(os.environ.get('EPYC_ROOT_REPO','/workspace'))/'scripts/vidya'
sys.path.insert(0,str(ROOT))
from claim_tuple import ProjectionError, register, to_frames
from adapters import _native_sidecar as ns
SCHEMA='epyc.vidya.workload_census_capture.v1'
SOURCE='workload-census-measurement'
ADAPTER='vidya.adapters.workload_census/v1'
PHASES=('prefill','decode','verify')

def _digest(p): return ns.file_sha256(Path(p))
def _read(p): return json.loads(Path(p).read_text())
def _verify_journal(p):
    rows=[json.loads(x) for x in Path(p).read_text().splitlines()]
    if len(rows)!=2: raise ValueError('exactly start and terminal required')
    previous=''
    for row in rows:
        content=dict(row); seal=content.pop('content_sha256',None)
        raw=json.dumps(content,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
        if content.get('schema')!='epyc.autokernel.census_capture_event.v1' or content.get('previous_sha256')!=previous or hashlib.sha256(raw).hexdigest()!=seal:
            raise ValueError('journal chain invalid')
        previous=seal
    start,end=rows
    if start.get('kind')!='start' or end.get('kind')!='terminal' or start['attempt_id']!=end['attempt_id']:
        raise ValueError('journal lifecycle invalid')
    if not (0<start['started_ns']<=end['spawned_ns']<=end['ended_ns']) or end.get('error') or end.get('rc')!=0:
        raise ValueError('unsuccessful or nonprospective attempt')
    return start,end

def begin_capture(path, *, workload_id):
    """Create the intent before any server is launched; it is retained in every journal."""
    if not workload_id: raise ValueError('workload identity required')
    body=json.dumps({'schema':'epyc.vidya.workload_census_intent.v1',
                     'workload_id':workload_id,'created_ns':time.time_ns()},sort_keys=True).encode()
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:
        f.write(body);f.flush();os.fsync(f.fileno())
    return Path(path)

def _check_record(record_path, journals, intent_path):
    record=_read(record_path)
    intent=_read(intent_path); intent_hash=_digest(intent_path)
    if intent.get('schema')!='epyc.vidya.workload_census_intent.v1' or intent.get('workload_id')!=record.get('identity',{}).get('workload_id'):
        raise ValueError('invalid prospective intent')
    if record.get('schema')!='epyc.autokernel.workload_census.v1' or record.get('validity',{}).get('state')!='OBSERVED':raise ValueError('not observed native census')
    graph=record.get('graph',{}); envelope=graph.get('shape_envelope',[]); rows=graph.get('per_shape',[])
    if len(journals)!=3 or len(envelope)!=3 or len(rows)!=3 or [x.get('phase') for x in envelope]!=list(PHASES):raise ValueError('incomplete envelope')
    if [(x.get('n_tokens'),x.get('n_seq')) for x in envelope]!=[(2048,1),(1,1),(5,1)]:raise ValueError('wrong registered shape')
    identity=record.get('identity',{}); model=identity.get('model',{})
    shards=model.get('shards'); head=model.get('head')
    if not isinstance(shards,list) or len(shards)!=3 or not isinstance(head,dict):raise ValueError('missing model artifact identity')
    for ref in [*shards,head]:
        if not isinstance(ref,dict) or not ns.SHA256.fullmatch(str(ref.get('sha256',''))) or not ref.get('path'):raise ValueError('invalid artifact identity')
    weights=record.get('weights',{}); types=weights.get('tensor_types',{})
    if (weights.get('path')!=shards[0]['path'] or weights.get('architecture')!='qwen4exp'
            or weights.get('n_embd')!=2560 or not isinstance(types,dict)
            or any(type(v) is not int or v<0 for v in types.values()) or sum(types.values())!=1224):
        raise ValueError('incomplete registered model tensor census')
    pins=identity.get('recipe',{}).get('builder_source_pins')
    if not isinstance(pins,list) or not pins:raise ValueError('missing builder source pins')
    for shape,row,journal in zip(envelope,rows,journals):
        start,end=_verify_journal(journal)
        ref=start.get('inputs',{}).get('belief_intent',{})
        if ref.get('sha256')!=intent_hash or start['started_ns']<intent['created_ns']:
            raise ValueError('attempt lacks prospective intent')
        for key,ref in zip(('model','model_shard_2','model_shard_3','drafter'),[*shards,head]):
            captured=start['inputs'].get(key,{})
            if captured.get('path')!=ref['path'] or captured.get('sha256')!=ref['sha256']:
                raise ValueError('attempt model identity mismatch')
        for i,pin in enumerate(pins):
            captured=start['inputs'].get(f'builder_input_{i}',{})
            if captured.get('origin_path')!=pin['path'] or captured.get('sha256')!=pin['sha256']:
                raise ValueError('attempt builder source mismatch')
        if start['shape']!=shape or row.get('shape')!=shape or row.get('state')!='OBSERVED' or row.get('nodes_total',0)<=1000:
            raise ValueError('shape or observed evidence mismatch')
        if not {'MUL_MAT','MUL_MAT_ID'} <= set(row.get('op_backend',{})):
            raise ValueError('expected native operations missing')
        guards=row.get('native_shape_evidence',{}).get('guards',{})
        required={'configured_parallelism','request_count','slot_occupancy_observed','terminal_responses',
                  'prompt_counters_present','native_instrument_mapping','native_ggml_mapping',
                  'native_tensor_width_and_api_sequences'}
        phase=shape['phase']
        required |= ({'configured_ubatch','frozen_token_width','native_prompt_width'} if phase=='prefill' else
                     {'plain_decode_request','plain_decode_response'} if phase=='decode' else
                     {'native_verify_width','native_draft_counters','request_verify_budget'})
        if not required <= set(guards) or not all(guards.values()):
            raise ValueError('native witness missing')
        request_path=row.get('request_log'); foreign_path=row.get('foreign_load')
        if _digest(request_path)!=row.get('request_log_sha256') or _digest(foreign_path)!=row.get('foreign_load_sha256'):
            raise ValueError('request or foreign evidence drift')
        req=_read(request_path); windows=req.get('request_windows',[])
        foreign=[json.loads(line) for line in Path(foreign_path).read_text().splitlines()]
        covered=[item for item in foreign if type(item.get('window_start_ns')) is int and type(item.get('window_end_ns')) is int
                 and any(w['start_ns']<=item['window_start_ns']<=item['window_end_ns']<=w['end_ns'] for w in windows)]
        if len(covered)<2:raise ValueError('foreign sampling absent during request')
    return record

def validate_row(row):
    problems=ns.common_problems(row,schema=SCHEMA,optional_text=('protocol_id',))
    if not isinstance(row,dict):return problems
    x=row.get('extra',{})
    if row.get('protocol_id')!='' or row.get('metric')!='workload_shape_observed' or row.get('value')!=1 or row.get('unit')!='observed' or row.get('metric_direction')!='higher_better' or row.get('reps')!=1 or row.get('reps_basis')!='scored:shape observation': problems.append('invalid structural metric')
    if x.get('phase') not in PHASES or not isinstance(x.get('journals'),list) or len(x['journals'])!=3:problems.append('invalid shape or journal references')
    if not problems:
        problems+=ns.check_identity(row,{'record':row['results_sha256'],'phase':x['phase']},'wcensus')
    return problems+ns.self_hash_problems(row)

def write_belief_measurements(out_dir, *, record_path, journals, intent_path, emitted_at=None):
    record_path=Path(record_path).resolve(strict=True); journals=[Path(p).resolve(strict=True) for p in journals]
    intent_path=Path(intent_path).resolve(strict=True)
    record=_check_record(record_path,journals,intent_path); digest=_digest(record_path)
    refs=[{'path':str(p),'sha256':_digest(p)} for p in journals]
    when=emitted_at or datetime.now(timezone.utc).isoformat(); rows=[]
    for phase in PHASES:
        row={'schema':SCHEMA,'run_id':record['identity']['workload_id'],'producer':'w5s.census_belief/v1',
            'emitted_at':when,'date':when[:10],'measurement_id':'wcensus_'+ns.content_hash({'record':digest,'phase':phase})[:24],
            'metric':'workload_shape_observed','value':1,'unit':'observed','metric_direction':'higher_better','category':'CANDIDATE',
            'claim':f'{phase} primary-target structural shape observed; draft-head graphs and tensors excluded; no performance claim',
            'protocol_id':'','reps':1,'reps_basis':'scored:shape observation','results_path':str(record_path),'results_sha256':digest,
            'extra':{'phase':phase,'journals':refs,'intent':{'path':str(intent_path),'sha256':_digest(intent_path)},'scope':'primary target tensors and graphs only; separate head identity bound but head tensor inventory and draft graphs excluded; not P0d closure','identity':record['identity']}}
        ns.seal(row); bad=validate_row(row)
        if bad:raise ValueError('; '.join(bad))
        rows.append(row)
    root=Path(out_dir);root.mkdir(parents=True,exist_ok=True); target=root/'workload-census.claims.jsonl'
    if target.exists():raise ValueError('refuse sidecar reuse')
    return ns.write_rows_atomic(target,rows)

def native_rows(path):
    rows=ns.native_rows(path,validate_row)
    if len(rows)!=3 or [r['row']['extra']['phase'] for r in rows]!=list(PHASES):return ()
    try:
        for n in rows:
            r=n['row']; refs=r['extra']['journals']
            if not ns.results_present(r) or any(_digest(x['path'])!=x['sha256'] for x in refs):return ()
            intent=r['extra']['intent']
            if _digest(intent['path'])!=intent['sha256']:return ()
            record=_check_record(r['results_path'],[x['path'] for x in refs],intent['path'])
            if r['extra']['identity']!=record['identity']:return ()
    except (OSError,ValueError,KeyError,TypeError):return ()
    return rows

@register(SOURCE)
def project(native):
    row=native.get('row') if isinstance(native,dict) else None
    if not row or validate_row(row):raise ProjectionError('invalid native census row')
    try:
        refs=row['extra']['journals']; intent=row['extra']['intent']
        if not ns.results_present(row) or _digest(intent['path'])!=intent['sha256'] or any(_digest(x['path'])!=x['sha256'] for x in refs):
            raise ValueError('evidence digest mismatch')
        record=_check_record(row['results_path'],[x['path'] for x in refs],intent['path'])
        if row['extra']['identity']!=record['identity']:raise ValueError('identity mismatch')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise ProjectionError('census evidence invalid') from exc
    return ns.to_claim_tuple(row,source_kind=SOURCE,locator='workload-census:'+row['measurement_id']+':'+row['results_path'],sidecar_path=native.get('sidecar_path',''))

def frames_for_sidecar(path,*,as_of):
    return [frame for n in native_rows(path) for frame in to_frames(project(n),as_of=as_of,adapter_id=ADAPTER,authority='measurement')]
