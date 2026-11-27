"""Versioned PAW clean paid2 final review with explicit cross-epoch history."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def write(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,indent=2)+'\n')
OLD_HISTORY="""    prior=[]
    base_id=re.sub(r'-guidance-[12]$','',result['id'])
    for n in range(1,native_ordinal+1):
        prompt=unit.parent/(base_id+f'-guidance-{n}')/'PROMPT.md'
        text=prompt.read_text();digest=sha(prompt);sources[str(prompt)]=digest
        prior.append({'native_ordinal':n,'help_kind':'deterministic-check-report' if n==1 else 'paid-main-guidance',
                      'sha256':digest,'text':text[:12000],'truncated':len(text)>12000})
"""
def qualified_inputs():
    lock=load(HERE/'CODE-LOCK.json')
    for name,digest in lock['sha256'].items():assert sha(name)==digest,('source changed',name)
    history=load(HERE/'HISTORY-INPUTS.json')
    for name,digest in history['expected_sha256'].items():assert sha(name)==digest,('actual history changed',name)
    return lock,history

def explicit_prior(result,unit,sources):
    _,history=qualified_inputs();sources.update(history['expected_sha256'])
    paths=[(1,'neutral-self-check; no failure or semantic diagnosis',Path(history['neutral_prompt'])),(2,'one measured paid main source-guidance round',Path(history['paid_guidance']))]
    prior=[]
    for ordinal,kind,path in paths:
        text=path.read_text();assert len(text)<=12000,'preserve actual feedback verbatim; do not silently truncate'
        sources[str(path)]=sha(path);prior.append({'native_ordinal':ordinal,'help_kind':kind,'sha256':sha(path),'text':text,'truncated':False})
    return prior

def wrapper():
    lock,_=qualified_inputs();source=Path(lock['expert_wrapper']);raw=source.read_bytes();assert raw.count(OLD_HISTORY.encode())==1
    adapted=raw.replace(OLD_HISTORY.encode(),b'    prior=explicit_prior(result,unit,sources)\n')
    spec=importlib.util.spec_from_file_location('qualified_paw_clean_final',source);module=importlib.util.module_from_spec(spec);module.__dict__['explicit_prior']=explicit_prior;exec(compile(adapted,str(source),'exec'),module.__dict__)
    module.HERE=HERE
    def ordinal(result):
        assert result['id']=='gpu-PAW-5-off-recommended-clean-paid-2';return 2
    module.infer_ordinal=ordinal
    old_write=module.write
    def scoped_write(path,value):
        if Path(path).name=='feedback.json':
            value['clean_replay_protocol']='original0 -> neutral1/guidance0 -> one measured paid semantic correction2 -> final independent acceptance'
            value['old_false_pin_feedback_branch_excluded']=True
        if Path(path).name=='plan.json':
            value['command_affinity']='180-183';value['cross_epoch_history_adapter_sha256']=sha(Path(__file__))
        return old_write(path,value)
    module.write=scoped_write
    return module

def stage():
    lock,history=qualified_inputs();result_path=Path(history['expected_final_result'])
    if not result_path.is_file():raise FileNotFoundError('actual clean paid2 terminal RESULT not yet present: '+str(result_path))
    result=load(result_path);unit=result_path.parent;expected=history['expected_row']
    assert result.get('terminal_at') and result.get('status') not in ['starting','running','queued']
    for key in ['id','case','backend','thinking','profile','sampling','slot','request_cap','generated_ceiling','wall_s']:
        assert result[key]==expected[key],('actual mode/profile changed',key)
    for key in ['prior','prior_result_sha256','prior_session_sha256','feedback','feedback_sha256','ordinal']:
        assert result['resume'][key]==expected['resume'][key],('paid2 history differs',key)
    assert sha(unit/'PROMPT.md')==history['expected_sha256'][history['paid_guidance']]
    assert not result.get('outside_scope') and not result.get('unsafe_paths')
    target='docs/reference/harness-candidates/paw-5-compile-once-candidates.md'
    assert set(result['changed_files'])=={target}
    assert sha(unit/'independent/work'/target)==result['changed_files'][target]['sha256']
    assert sha(unit/'independent/candidate.patch')==result['patch_sha256']
    checker=Path(lock['v5_checker']);assert sha(checker)==lock['sha256'][str(checker)]
    out=HERE/'structural';out.mkdir(exist_ok=True)
    q=subprocess.run(['/usr/bin/python3','-IB',str(checker),str(unit/'independent/work')],capture_output=True,text=True,timeout=20)
    (out/'stdout.log').write_text(q.stdout);(out/'stderr.log').write_text(q.stderr)
    receipt={'case':'PAW-5','candidate_patch_sha256':result['patch_sha256'],'checked_candidate_files':result['changed_files'],'source_result_sha256':sha(result_path),'checker_sha256':sha(checker),'rc':q.returncode,'diagnostic':q.stderr.strip(),'candidate_unchanged':sha(unit/'independent/work'/target)==result['changed_files'][target]['sha256'],'scope':'versioned structural reassessment only; source semantic acceptance remains independent'}
    write(out/'RECEIPT.json',receipt)
    return wrapper().stage(result_path,'final-acceptance',2,out/'RECEIPT.json')

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);sub.add_parser('stage')
    for command in ['verify','launch','report']:
        q=sub.add_parser(command);q.add_argument('root',type=Path)
        if command=='launch':q.add_argument('--approval',type=Path,required=True)
    a=p.parse_args()
    if a.command=='stage':out=stage()
    elif a.command=='verify':out=wrapper().verify(a.root)
    elif a.command=='launch':raise SystemExit(wrapper().launch(a.root,a.approval))
    else:out=wrapper().report(a.root)
    print(json.dumps(out,indent=2))
