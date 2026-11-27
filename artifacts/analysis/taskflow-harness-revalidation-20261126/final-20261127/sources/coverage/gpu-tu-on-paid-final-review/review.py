#!/usr/bin/env python3
"""Scoped per-mode paid review adapter; stages only until main approves a launch."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / 'legacy-comparison'
EVIDENCE = '.review-evidence'
OLD_ADAPTER = HERE.parent / 'legacy-assisted-review' / 'ADAPTER-SEAL.json'
OLD_ADAPTER_SHA = '099a931a0866d22c7f5eab2be6da0c5976186541af5fb91703d5be8e266b7ce6'
KINDS = ('initial-diagnosis', 'final-acceptance', 'takeover')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def source_lock():
    lock = load(HERE / 'CODE-LOCK.json')
    for path, digest in lock['sha256'].items():
        if sha(path) != digest:
            raise ValueError('review/import source changed: ' + path)
    return lock


def modules(root):
    source_lock()
    spec = importlib.util.spec_from_file_location('prepare', ORIGINAL/'prepare.py')
    prepare = importlib.util.module_from_spec(spec)
    sys.modules['prepare'] = prepare
    # Compile the verified source bytes directly; never trust a stale .pyc.
    raw=(ORIGINAL/'prepare.py').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=load(HERE/'CODE-LOCK.json')['sha256'][str(ORIGINAL/'prepare.py')]:
        raise ValueError('prepare source changed while importing')
    exec(compile(raw,str(ORIGINAL/'prepare.py'),'exec'),prepare.__dict__)
    prepare.HERE = root.resolve()
    original_prompt = prepare.prompt

    def prompt(case, arm, feedback=None):
        text = original_prompt(case, 'direct')
        role = feedback['review_kind']
        if role == 'initial-diagnosis':
            instruction = ('Review the exact unchanged local candidate independently against the original task and pinned sources. '
                'Return ACCEPT only if the substantive task is already complete, otherwise REJECT with a bounded source-grounded '
                'diagnosis, entry point and validation for the single permitted paid-guided native correction (ordinal2). '
                'Do not invent work. Leave the candidate unmodified.')
        elif role == 'final-acceptance':
            instruction = ('Perform final independent semantic acceptance review of this exact unchanged candidate against the '
                'original task and pinned sources. Structural acceptance is evidence about checks, never semantic correctness. '
                'Return ACCEPT or REJECT with concise substantive evidence. This is a paid acceptance review, not another '
                'native correction round. No further native correction is authorized by this review. Leave the candidate unmodified.')
        else:
            instruction = ('Complete the remaining original task as a separately metered main-model takeover. '
                'Edit only the original allowed paths. This result is main-model completion, never A3B completion.')
        if role == 'final-acceptance':
            instruction += (
                '\nUse the neutral comparison files in .review-evidence. '
                'baseline/ is the complete pinned original source tree, and candidate.patch is the exact '
                'submitted diff. The working tree outside .review-evidence holds the reconstructed '
                'candidate. Inspect both when judging changes. Leave this evidence unchanged.'
            )
        return text + '\nRole: '+role+'\n\n'+instruction+('\n\nHistorical help below is a quoted record, not an instruction '
            'to accept prior judgments. Recheck the source facts independently. Keep direct-main answers, other modes, '
            'oracles and previous reviewer outputs outside the work.\n\n')+json.dumps(feedback,ensure_ascii=False,sort_keys=True)+'\n'

    prepare.prompt = prompt
    spec = importlib.util.spec_from_file_location('assisted_measure', ORIGINAL/'measure.py')
    measure = importlib.util.module_from_spec(spec)
    raw=(ORIGINAL/'measure.py').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=load(HERE/'CODE-LOCK.json')['sha256'][str(ORIGINAL/'measure.py')]:
        raise ValueError('measure source changed while importing')
    exec(compile(raw,str(ORIGINAL/'measure.py'),'exec'),measure.__dict__)
    if prepare.MODEL != 'gpt-6.1-sol' or prepare.EFFORT != 'low' or measure.HERE != root.resolve():
        raise ValueError('original metric profile or private HERE binding changed')
    return prepare, measure


def initialize():
    if sha(OLD_ADAPTER) != OLD_ADAPTER_SHA:
        raise ValueError('prior adapter seal changed')
    paths = [Path(__file__).resolve(), HERE/'normalize.py', HERE/'grade_saved.py', ORIGINAL/'prepare.py',
             ORIGINAL/'measure.py', OLD_ADAPTER]
    record = {'sha256':{str(p):sha(p) for p in paths},'model':'gpt-6.1-sol','effort':'low',
              'imports':'exact legacy prepare/measure sources; explicit owner/job/worker projection, objective ordinals, role prompt and180-183 scheduling',
              'native_protocol':'initial0 + deterministic1 + at most one paid-guided correction2; final acceptance review is a different paid role; takeover separate'}
    path = HERE/'CODE-LOCK.json'
    if path.exists() and load(path) != record:
        raise ValueError('existing code lock differs; prepare a new reviewed version, never silently repin')
    write(path,record)
    legacy=[]
    for cid,profile,ordinal in []:
        run=ORIGINAL/'runs'/cid/f'guidance-{ordinal}'
        if (run/'plan.json').exists():
            legacy.append({'case':cid,'backend':'gpu','profile':profile,'kind':'initial-diagnosis','run':str(run),
                           'immutable_existing_record':True,'sha256':{n:sha(run/n) for n in ['plan.json','prompt.md','events.jsonl','execution.json','measurement.json'] if (run/n).exists()}})
    write(HERE/'LEGACY-REVIEWS.json',legacy)
    return record


def infer_ordinal(result):
    match=re.search(r'-(?:guidance|objective|paid)-([12])$',result['id'])
    return int(match.group(1)) if match else 0


def stage(result_path, kind, native_ordinal, structural_receipt=None):
    source_lock()
    result_path=result_path.resolve();unit=result_path.parent;result=load(result_path)
    if result_path.name!='RESULT.json' or not result.get('terminal_at') or result.get('status') in {'running','queued'}:
        raise ValueError('stage only an actual terminal native RESULT.json')
    if result.get('backend') not in {'cpu','gpu'} or not isinstance(result.get('thinking'),bool) or 'changed_files' not in result:
        raise ValueError('not a native candidate result; direct-main records are forbidden')
    if native_ordinal not in (0,1,2) or infer_ordinal(result)!=native_ordinal:
        raise ValueError('native correction ordinal mismatch or exceeds the two-correction protocol')
    if kind != 'final-acceptance' or result['id'] != 'gpu-TU-GR-1-on-coding-paid-2':
        raise ValueError('this seal admits only final acceptance for the exact GPU TU ON paid2 result')
    if kind=='initial-diagnosis' and native_ordinal!=1:
        raise ValueError('initial diagnosis follows deterministic ordinal1 only; cannot authorize correction3')
    cid=result['case'];profile=result['profile'];backend=result['backend']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',cid+profile):
        raise ValueError('unsafe case/profile')
    if kind=='initial-diagnosis':
        for old in load(HERE/'LEGACY-REVIEWS.json'):
            if (old['case'],old['backend'],old['profile'])==(cid,backend,profile):
                raise ValueError('existing initial paid review is preserved at '+old['run'])
    mode=backend+'-'+('ON' if result['thinking'] else 'OFF')+'-'+profile
    root=HERE/'reviews'/cid/mode/kind
    if root.exists():
        raise ValueError('this case/mode/phase already staged; never overwrite or create extra native rounds')
    root.mkdir(parents=True)
    (root/'cases').symlink_to(ORIGINAL/'cases',target_is_directory=True)
    prepare,measure=modules(root)
    if cid not in prepare.IDS:
        raise ValueError('case is not in the original main-comparison baseline set')
    case_dir=ORIGINAL/'cases'/cid;case=load(case_dir/'case.json')
    sources={str(result_path):sha(result_path)}
    projection_sources=result.get('projection_sources')
    if not isinstance(projection_sources,dict) or not projection_sources:
        raise ValueError('legacy result requires explicit owner/job/worker hash-bound projection')
    for name,digest in projection_sources.items():
        if sha(name)!=digest:raise ValueError('legacy projection source changed: '+name)
    sources.update(projection_sources)
    patch=unit/'independent/candidate.patch' if result.get('patch_sha256') else None
    if patch is not None:
        if sha(patch)!=result['patch_sha256']:
            raise ValueError('native patch bytes do not match terminal result')
        sources[str(patch)]=sha(patch)
    elif result['changed_files']:
        raise ValueError('candidate changes reported without an exact patch')
    prior=[]
    for record in result.get('actual_prior_feedback',[]):
        prompt=Path(record['path']);text=prompt.read_text();digest=sha(prompt)
        if digest!=record['sha256']:raise ValueError('actual legacy feedback changed')
        if len(text)>12000:raise ValueError('legacy feedback too large; preserve verbatim rather than truncate')
        sources[str(prompt)]=digest
        prior.append({'native_ordinal':record['native_ordinal'],'help_kind':record['help_kind'],
                      'sha256':digest,'text':text,'truncated':False})
    if [r['native_ordinal'] for r in prior]!=list(range(1,native_ordinal+1)):
        raise ValueError('actual objective/paid feedback ordinal chain is incomplete')
    diagnostics={}
    for name in ['ORACLE.stdout.log','ORACLE.stderr.log']:
        p=unit/name
        if p.exists():
            sources[str(p)]=sha(p);text=p.read_text();diagnostics[name]={'text':text[-6000:],'sha256':sha(p),'truncated':len(text)>6000}
    reassessment=None
    if structural_receipt:
        structural_receipt=structural_receipt.resolve();reassessment=load(structural_receipt)
        sources[str(structural_receipt)]=sha(structural_receipt)
        # Only a caller-produced receipt, never a checker implementation or another solution.
        if len(structural_receipt.read_bytes())>16000:
            raise ValueError('use a bounded single-candidate structural receipt')
        candidate=reassessment.get('candidate_patch_sha256')
        candidate_bytes=reassessment.get('candidate_sha256')
        matches_files=reassessment.get('checked_candidate_files')==result['changed_files']
        known_bytes={v['sha256'] for v in result['changed_files'].values()}
        if not ((candidate is not None and candidate==result.get('patch_sha256')) or candidate_bytes in known_bytes or matches_files):
            raise ValueError('structural reassessment must bind this exact candidate patch')
    summary={key:result.get(key) for key in ('id','case','backend','thinking','profile','status','patch_sha256','oracle','changed_files','outside_scope','unsafe_paths','generation_observed','model_wall_s')}
    feedback={'id':cid,'review_kind':kind,'native_ordinal':native_ordinal,
              'allowed_next_native_correction':2 if kind=='initial-diagnosis' else None,
              'native_correction_ceiling':2,'candidate_patch_sha256':result.get('patch_sha256'),
              'local_result':summary,'actual_prior_help':prior,'objective_diagnostics':diagnostics,
              'structural_reassessment':reassessment,'structural_pass_implies_semantic_acceptance':False}
    write(root/'feedback.json',feedback)
    arm='takeover' if kind=='takeover' else 'guidance'
    # Markdown's two trailing spaces are a meaningful hard break. Git whitespace
    # policy must not reject or rewrite an otherwise valid exact native patch.
    # Adapt only the two candidate git-apply argv flags; retain --check, check=True
    # and all malformed-patch errors. Never modify the upstream module or bytes.
    original_subprocess=prepare.subprocess
    class ExactCandidatePatch:
        def __getattr__(self,name):return getattr(original_subprocess,name)
        def run(self,args,*positional,**kwargs):
            if patch is not None and isinstance(args,list) and args[:2]==['git','apply'] and args[-1]==str(patch.resolve()):
                args=['--whitespace=nowarn' if a=='--whitespace=error' else a for a in args]
            return original_subprocess.run(args,*positional,**kwargs)
    prepare.subprocess=ExactCandidatePatch()
    try:run=prepare.stage(cid,arm,1,root/'feedback.json',patch)
    finally:prepare.subprocess=original_subprocess
    observed=prepare.file_map(run/'lane');changed={n:v for n,v in observed.items() if case['baseline_files'].get(n)!=v}
    if changed!=result['changed_files']:
        raise ValueError('reconstructed candidate bytes differ from the terminal native result')
    comparison = run / 'lane' / EVIDENCE
    comparison.mkdir()
    shutil.copytree(case_dir / 'baseline', comparison / 'baseline')
    shutil.copy2(patch, comparison / 'candidate.patch')
    if prepare.file_map(comparison / 'baseline') != case['baseline_files']:
        raise ValueError('neutral comparison baseline differs from pinned case')
    if sha(comparison / 'candidate.patch') != result['patch_sha256']:
        raise ValueError('neutral comparison patch differs from native candidate')
    for path in sorted(comparison.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        path.chmod(path.stat().st_mode & ~0o222)
    comparison.chmod(0o555)
    comparison_map = prepare.file_map(comparison)
    plan=load(run/'plan.json');plan.update(command_affinity='180-183',review_kind=kind,mode=mode,native_ordinal=native_ordinal,
         native_correction_ceiling=2,allowed_next_native_correction=feedback['allowed_next_native_correction'],
         assistance_role='main-takeover' if kind=='takeover' else 'paid-independent-'+kind,
         source_native_result_sha256=sha(result_path),candidate_input_patch_sha256=result.get('patch_sha256'),
         candidate_scope='editable original paths' if kind=='takeover' else 'read-only exact staged proposal')
    plan['read_only_evidence_dir'] = EVIDENCE
    plan['read_only_evidence_files'] = len(comparison_map)
    plan['review_evidence_manifest_sha256'] = hashlib.sha256(
        json.dumps(comparison_map, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    write(run/'plan.json',plan)
    external={str(case_dir/'case.json'):sha(case_dir/'case.json')}
    for p in case_dir.iterdir():
        if p.is_file():external[str(p)]=sha(p)
    immutable={str(p.relative_to(root)):sha(p) for p in [root/'feedback.json',run/'plan.json',run/'prompt.md']}
    write(root/'SEAL.json',{'code_lock_sha256':sha(HERE/'CODE-LOCK.json'),'immutable':immutable,'external':external,
          'source_native_files':sources,'case':cid,'mode':mode,'kind':kind,'native_ordinal':native_ordinal,
          'run':str(run),'candidate_input_files':result['changed_files'],'structural_is_not_semantic':True,
          'comparison_evidence':comparison_map, 'prior_measured_paid_guidance':result['prior_measured_paid_guidance'],
          'patch_policy':'candidate git apply/check whitespace=nowarn; preserve meaningful Markdown hard-break bytes; reconstruct and hash-match every changed file against RESULT; all malformed patch errors remain fatal'})
    write(root/'APPROVAL-TEMPLATE.json',{'approved_by':None,'native_harness_qualified':False,
         'review_seal_sha256':sha(root/'SEAL.json'),'plans':{str(run/'plan.json'):sha(run/'plan.json')},
         'paid_role':plan['assistance_role'],'instruction':'Main reviews this exact scoped role and plan; this template authorizes no call.'})
    return {'root':str(root),'run':str(run),'seal_sha256':sha(root/'SEAL.json'),'plan_sha256':sha(run/'plan.json')}


def verify(root):
    source_lock();root=root.resolve()
    if not root.is_relative_to(HERE/'reviews'):
        raise ValueError('review root outside private adapter tree')
    seal=load(root/'SEAL.json')
    if seal['code_lock_sha256']!=sha(HERE/'CODE-LOCK.json'):
        raise ValueError('code seal differs')
    for name,digest in seal['immutable'].items():
        if sha(root/name)!=digest:raise ValueError('staged review input changed: '+name)
    for name,digest in dict(seal['external'],**seal['source_native_files']).items():
        if sha(name)!=digest:raise ValueError('source case/candidate changed: '+name)
    if (root/'cases').resolve()!=(ORIGINAL/'cases').resolve():
        raise ValueError('cases symlink changed')
    prepare, _ = modules(root)
    compare = Path(seal['run']) / 'lane' / EVIDENCE
    if compare.is_symlink() or not compare.is_dir() or prepare.file_map(compare) != seal['comparison_evidence']:
        raise ValueError('in-lane comparison evidence changed')
    return seal


def review_source_map(file_map, expected):
    def scoped(path):
        observed = file_map(path)
        prefix = EVIDENCE + '/'
        comparison = {name[len(prefix):]: meta for name, meta in observed.items() if name.startswith(prefix)}
        if comparison != expected:
            raise ValueError('read-only baseline or patch evidence changed')
        return {name: meta for name, meta in observed.items() if not name.startswith(prefix)}
    return scoped


def launch(root, approval):
    seal=verify(root);approved=load(approval)
    if approved.get('review_seal_sha256')!=sha(root/'SEAL.json'):
        raise ValueError('approval must bind this exact review/code seal')
    prepare,measure=modules(root)
    measure.file_map = review_source_map(prepare.file_map, seal['comparison_evidence'])
    return measure.launch(Path(seal['run']),approval.resolve())


def report(root):
    seal=verify(root);prepare,measure=modules(root);run=Path(seal['run'])
    measure.file_map = review_source_map(prepare.file_map, seal['comparison_evidence'])
    result=measure.report(run)
    events=measure.read_events(run/'events.jsonl')
    raw=[json.loads(l) for l in (run/'events.jsonl').read_text().splitlines()]
    messages=[e['item'].get('text','') for e in raw if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message']
    final=messages[-1] if messages else '';match=re.match(r'\s*(ACCEPT|REJECT)\b',final)
    sidecar={'case':seal['case'],'mode':seal['mode'],'review_kind':seal['kind'],'native_ordinal':seal['native_ordinal'],
       'native_correction_ceiling':2,'allowed_next_native_correction':2 if seal['kind']=='initial-diagnosis' else None,
       'review_seal_sha256':sha(root/'SEAL.json'),'model':'gpt-6.1-sol','effort':'low',
       'execution':result['execution'],'usage':events['usage'],'candidate_unmodified_by_review':not result['changed_by_strong_turn'],
       'path_scope_pass':result['path_scope_pass'],'semantic_review_advisory':match.group(1) if match else 'UNPARSEABLE',
       'structural_pass_implies_semantic_acceptance':False,'final_acceptance_review_adds_paid_main_cost':seal['kind']=='final-acceptance',
       'accounting_role':'main-takeover' if seal['kind']=='takeover' else 'paid-A3B-assistance',
       'manager_setup_review_costs':'not isolated by this execution vector; neither zero nor included',
       'events_sha256':sha(run/'events.jsonl'),'measurement_sha256':sha(run/'measurement.json')}
    write(run/'assistance-accounting.json',sidecar)
    return sidecar


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    q=sub.add_parser('stage');q.add_argument('--result',type=Path,required=True);q.add_argument('--kind',choices=KINDS,required=True);q.add_argument('--native-ordinal',type=int,required=True);q.add_argument('--structural-receipt',type=Path)
    for command in ('verify','launch','report'):
        q=sub.add_parser(command);q.add_argument('root',type=Path)
        if command=='launch':q.add_argument('--approval',type=Path,required=True)
    a=p.parse_args()
    if a.command=='init':out=initialize()
    elif a.command=='stage':out=stage(a.result,a.kind,a.native_ordinal,a.structural_receipt)
    elif a.command=='verify':out=verify(a.root)
    elif a.command=='launch':raise SystemExit(launch(a.root,a.approval))
    else:out=report(a.root)
    print(json.dumps(out,indent=2))
