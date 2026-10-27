#!/usr/bin/env python3
"""Prospective coverage capture and strict projection inputs; no quality grading."""
import argparse, hashlib, importlib.util, json, os, re, sys, uuid
from pathlib import Path
import diagnostic as d

CARRIER=Path('/mnt/raid0/llm/views/epyc-root-main/scripts/vidya/adapters/_native_sidecar.py')
spec=importlib.util.spec_from_file_location('ufh12_shared_native',CARRIER)
c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
SCHEMA='epyc.vidya.ufh12_gs_coverage.v1'

def rederive(record):
    manifest=record['manifest']; facet=record['facet']; sha=hashlib.sha256(d.canonical(manifest)+b'\n').hexdigest()
    ids=manifest['corpus_ids']; rows=record['checkpoints']; seen=set(); count=0
    if manifest['seed']!=d.SEED or manifest['bge_query_prefix']!='' or manifest['eg2_query_prefix']!=d.QUERY or manifest['eg2_document_prefix']!=d.DOC or manifest['query_kind']!='stored-text proxy; not observed queries or relevance labels': raise ValueError('changed measurement definition')
    for kind,n in [('episodic',489),('strategy',11)]:
        if len(ids[kind])!=len(set(ids[kind])) or manifest['counts'][kind]!=len(ids[kind]): raise ValueError('bad corpus IDs')
        expected_ids=sorted(ids[kind],key=lambda x:(hashlib.sha256((d.SEED+'\0'+kind+'\0'+x).encode()).digest(),x))[:n]
        if manifest['selection'][kind]!=expected_ids: raise ValueError('bad selection')
    if facet=='tokens':
        for item in rows:
            name=item['name']; data=item['record']; match=re.fullmatch(r'tokens-(episodic|strategy)-(\d{6})\.json',name)
            if not match or name in seen: raise ValueError('token checkpoint name')
            seen.add(name); kind=match.group(1); start=int(match.group(2)); subset=ids[kind][start:start+32]
            if start%32 or not subset or not d.valid_seal(data) or data['manifest_sha256']!=sha or data['ids']!=subset[:len(data['counts'])] or len(data['counts'])>len(subset) or not data['captured_at'] or any(type(x)!=int or x<1 for x in data['counts']) or len(data['contexts'])!=len(data['counts']) or any(not d.valid_context(x) for x in data['contexts']): raise ValueError('invalid token checkpoint')
            count+=len(data['counts'])
        expected=sum(map(len,ids.values()))
    elif facet=='scores':
        for item in rows:
            name=item['name']; data=item['record']; kind=data['store']; ident=data['id']
            expected_name='score-'+hashlib.sha256((kind+'\0'+ident).encode()).hexdigest()+'.json'
            if kind not in ids or ident not in manifest['selection'][kind] or name!=expected_name or name in seen or not d.valid_score(data,kind,ident,sha,ids[kind],ids[kind]): raise ValueError('invalid score checkpoint')
            seen.add(name); count+=1
        expected=sum(map(len,manifest['selection'].values()))
    else: raise ValueError('bad facet')
    return count,expected

def emit(out,facet,context):
    out=Path(out).resolve(); manifest=d.load(out/'manifest.json')
    if not isinstance(context,dict) or not d.valid_context(context): raise ValueError('missing run context')
    checkpoints=[]
    for path in sorted(out.glob(('tokens-' if facet=='tokens' else 'score-')+'*.json')):
        if facet=='tokens' and path.name=='tokens-summary.json': continue
        checkpoints.append({'name':path.name,'record':d.load(path)})
    record={'schema':'epyc.ufh12-gs-native-record.v1','facet':facet,'captured_at':d.now(),'manifest':manifest,'context':context,'checkpoints':checkpoints,'descriptive_summary':d.load(out/(facet+'-summary.json')) if (out/(facet+'-summary.json')).exists() else None}
    count,expected=rederive(record); record['valid_count']=count; record['expected_count']=expected; record['complete']=count==expected
    if record['descriptive_summary'] is not None and (not record['complete'] or not record['descriptive_summary'].get('complete')): raise ValueError('summary without complete coverage')
    rid='ufh12-gs-'+facet+'-'+uuid.uuid4().hex; path=out/(rid+'.record.json'); d.save(path,record)
    emitted=d.now(); metric='valid_stored_text_token_records' if facet=='tokens' else 'valid_paired_query_records'
    row={'schema':SCHEMA,'run_id':rid,'producer':'ufh12-gs-coverage','measurement_id':'gs_'+hashlib.sha256((rid+'\0'+metric).encode()).hexdigest()[:24], 'metric':metric,'value':count,'unit':'records','metric_direction':'higher_better','category':'CANDIDATE','claim':f'{count} of {expected} validated {facet} records captured; coverage only, not quality','protocol_id':'','reps':1,'reps_basis':'native-capture-snapshot','results_path':str(path),'results_sha256':d.digest(path),'date':emitted,'emitted_at':emitted,'extra':{'facet':facet,'expected_count':expected,'complete':count==expected,'direction_scope':'coverage only; descriptive score and token values are not quality grades','manifest_sha256':d.digest(out/'manifest.json')}}
    c.seal(row)
    problems=c.common_problems(row,schema=SCHEMA,optional_text=('protocol_id',))+c.self_hash_problems(row)
    if problems: raise ValueError(str(problems))
    side=out/(rid+'.belief_measurements.jsonl'); c.write_rows_atomic(side,[row]); return path,side

def validate(row):
    errors=c.common_problems(row,schema=SCHEMA,optional_text=('protocol_id',))+c.self_hash_problems(row)
    try:
        if errors or not c.results_present(row): return errors+['attestation absent or changed']
        record=d.load(row['results_path']); count,expected=rederive(record)
        facet=record['facet']; metric='valid_stored_text_token_records' if facet=='tokens' else 'valid_paired_query_records'
        if row['metric']!=metric or row['value']!=count or row['extra']['expected_count']!=expected or row['extra']['complete']!=(count==expected) or record['valid_count']!=count or record['expected_count']!=expected or record['complete']!=(count==expected) or row['protocol_id']!='' or row['unit']!='records' or row['metric_direction']!='higher_better' or row['claim']!=f'{count} of {expected} validated {facet} records captured; coverage only, not quality' or row['extra']['direction_scope']!='coverage only; descriptive score and token values are not quality grades' or not d.valid_context(record['context']): return ['coverage projection mismatch']
        if row['measurement_id']!='gs_'+hashlib.sha256((row['run_id']+'\0'+metric).encode()).hexdigest()[:24]: return ['identity mismatch']
        return []
    except (KeyError,ValueError,TypeError,OSError): return ['invalid native record']

def project(row):
    problems=validate(row)
    if problems: raise ValueError(str(problems))
    return c.to_claim_tuple(row,source_kind='ufh12-gs-coverage',locator=row['results_path'])

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',required=True); p.add_argument('--facet',required=True,choices=['tokens','scores']); p.add_argument('--context',required=True); a=p.parse_args()
    print(*emit(a.out,a.facet,d.load(a.context)))
