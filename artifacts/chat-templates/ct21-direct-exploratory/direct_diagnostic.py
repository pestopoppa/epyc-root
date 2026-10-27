#!/usr/bin/env python3
"""Prospective CT21 direct-only diagnostic. Never reads old result files."""
import argparse, hashlib, json, os, sys, time, urllib.request
from pathlib import Path
D=Path(__file__).resolve().parent
WT=Path('/mnt/raid0/llm/worktrees/prep-01a16fc3-ct21')
sys.path[:0]=[str(D),str(WT),str(WT/'scripts/security'),str(WT/'scripts/benchmark'),'/mnt/raid0/llm/tmp/refactor-01a16fc3/ct21-parse-outcome-unblock-20261027']
import ct21_architect_arms as c
import debug_scorer as native
from decision_envelope import score_direct, complete_metric
from process_identity import identity

def fixtures():
    raw=(D/'fixtures.json').read_bytes(); rows=json.loads(raw)
    assert len(rows)==20 and len({r['id'] for r in rows})==20
    for r in rows:
        assert len(r['choices'])==4 and len(set(r['choices']))==4
        assert r['expected'] in 'ABCD' and r['choices']['ABCD'.index(r['expected'])]==str(r['a']+r['b'])
    return raw, rows

def plans():
    _, rows=fixtures()
    for surface in ('investigate','synthesis'):
        c._SURFACE=surface
        for i,r in enumerate(rows):
            # Reverse order on alternating items; both arms receive identical task/evidence.
            for arm in (('OFF','ON') if i%2==0 else ('ON','OFF')):
                yield surface,r,arm,c.render(arm,r['prompt'],'No specialist evidence is available.',r['id'])

def request_body(messages):
    return {'messages':messages,'temperature':0,'seed':7,'max_tokens':256,
            'cache_prompt':False,'chat_template_kwargs':{'enable_thinking':False}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--url');ap.add_argument('--output');a=ap.parse_args()
    raw,rows=fixtures(); digest=hashlib.sha256(raw).hexdigest(); plan=list(plans())
    if a.dry_run:
        encoded=json.dumps([(s,r['id'],arm,request_body(msg)) for s,r,arm,msg in plan],sort_keys=True).encode()
        print(json.dumps({'fixtures_sha256':digest,'items':len(rows),'requests':len(plan),'request_plan_sha256':hashlib.sha256(encoded).hexdigest(),'network':False,'profile':'ct21-direct-exploratory-v1'}));return
    if os.environ.get('WINDOW_CONFIRMED')!='1' or not a.url or not a.output:raise SystemExit('requires owner window, URL and fresh output path')
    receipt=Path(os.environ.get('CT21_ENROLLMENT_RECEIPT','/nonexistent'))
    if not receipt.is_file(): raise SystemExit('owner source-enrollment receipt required')
    enrollment=json.loads(receipt.read_text())
    if enrollment.get('approved') is not True or enrollment.get('profile')!='ct21-direct-exploratory-v1' or enrollment.get('source_sha256')!=hashlib.sha256(Path(__file__).read_bytes()).hexdigest() or enrollment.get('fixture_sha256')!=digest or enrollment.get('profile_sha256')!=hashlib.sha256((D/'DIAGNOSTIC-PROFILE.md').read_bytes()).hexdigest() or enrollment.get('manifest_sha256')!=hashlib.sha256((D/'source-manifest.sha256').read_bytes()).hexdigest(): raise SystemExit('owner receipt does not bind this profile, source, fixtures and manifest')
    runtime=json.loads(Path(os.environ['CT21_RUNTIME_IDENTITY']).read_text())
    if not runtime.get('source_commit') or not runtime.get('binary_version') or not runtime.get('template_sha256'): raise SystemExit('missing measured runtime identity')
    out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    pid,uid,birth=(int(os.environ['CT21_SERVER_'+x]) for x in ('PID','UID','BIRTH'))
    mpid,muid,mbirth=(int(os.environ['CT21_MONITOR_'+x]) for x in ('PID','UID','BIRTH'))
    deadline=int(os.environ['FILLER_DEADLINE']);stop=Path(os.environ['FILLER_STOPFILE'])
    results=[]
    for n,(surface,r,arm,msg) in enumerate(plan):
        if stop.exists() or time.time()>=deadline:raise SystemExit('incomplete: stop/deadline; no aggregate')
        if identity(pid)!=(uid,birth) or identity(mpid)!=(muid,mbirth):raise RuntimeError('server or monitor identity changed')
        body=json.dumps(request_body(msg)).encode(); req=urllib.request.Request(a.url.rstrip('/')+'/v1/chat/completions',body,{'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=600) as reply: response=reply.read()
        trace={'id':r['id'],'surface':surface,'arm':arm,'fixture_sha256':digest,'request_utf8':body.decode(),'request_sha256':hashlib.sha256(body).hexdigest(),'response_utf8':response.decode(),'response_sha256':hashlib.sha256(response).hexdigest(),'server_identity':[pid,uid,birth],'monitor_identity':[mpid,muid,mbirth]}
        with (out/f'{n:03}.raw.json').open('x') as f:json.dump(trace,f);f.flush();os.fsync(f.fileno())
        if identity(pid)!=(uid,birth) or identity(mpid)!=(muid,mbirth):raise RuntimeError('identity changed during request')
        choice=json.loads(response)['choices'][0]
        answer=choice['message'].get('content') or ''
        if choice.get('finish_reason') != 'stop':
            score={'status':'unobservable','reason':'finish_reason_'+str(choice.get('finish_reason')),'correct':None}
        else:
            score=score_direct(answer,r['expected'],'multiple_choice',{'choices':r['choices']},native.score_answer,native.AnswerParseError,parse_errors_enabled=native.EXCLUDE_UNPARSEABLE_ANSWERS)
        results.append({'id':r['id'],'surface':surface,'arm':arm,'raw':f'{n:03}.raw.json',**score})
        with (out/'results.jsonl').open('a') as f:f.write(json.dumps(results[-1])+'\n');f.flush();os.fsync(f.fileno())
    summary={f'{s}/{arm}':complete_metric([r for r in results if r['surface']==s and r['arm']==arm]) for s in ('investigate','synthesis') for arm in ('OFF','ON')}
    inconclusive=any(cell['status']!='complete' for cell in summary.values())
    (out/'summary.json').write_text(json.dumps({'profile':'ct21-direct-exploratory-v1','status':'INCONCLUSIVE' if inconclusive else 'COMPLETE','results':summary,'note':'exploratory only; not CT21 noninferiority or gate'},indent=2)+'\n')
    if inconclusive:
        raise SystemExit(2)  # all raw rows retained; no accuracy tuple or success
    sys.path.insert(0,str(D/'private/vidya'))
    from adapters.chat_template_ab_capture import write_belief_measurements
    marker={'profile':'ct21-direct-exploratory-v1','profile_path':str(D/'DIAGNOSTIC-PROFILE.md'),'source_path':str(Path(__file__).resolve()),'profile_sha256':enrollment['profile_sha256'],'source_sha256':enrollment['source_sha256']}
    cells={s:{f'arm{i}':{'n':summary[f'{s}/{arm}']['n'],'correct':summary[f'{s}/{arm}']['correct'],'errors':0,'truncated':0} for i,arm in enumerate(('OFF','ON'))} for s in ('investigate','synthesis')}
    spec={i:{'label':arm,'template_sha256':runtime['template_sha256'],'results_path':str(out/'results.jsonl')} for i,arm in enumerate(('OFF','ON'))}
    write_belief_measurements(out,run_id=out.name,producer='direct_diagnostic.py',model_path=runtime['model_path'],model_name='Qwen3.8-27B',quant='Q8_0',kernel={'source_commit':runtime['source_commit'],'binary_version':runtime['binary_version']},serving={'mode':'test_port','url':a.url},sampling={'temperature':0,'seed':7,'max_tokens':256,'thinking':False,'cache_prompt':False},arms=spec,summary=cells,exploratory=marker)
if __name__=='__main__':main()
