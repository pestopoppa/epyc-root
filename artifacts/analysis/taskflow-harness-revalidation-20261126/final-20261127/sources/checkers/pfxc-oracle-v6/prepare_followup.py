"""Prepare a sealed third-feedback mechanical exception; never launches inference."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import urllib.request

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
FROZEN=BASE.parent/'ws58-a3b-frozen-revalidation-20261126'
EPOCH=FROZEN/'quality-runs/cache-safe-01'
PRIOR=EPOCH/'units/gpu-PFXC-A3-on-coding-guidance-2'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def proc(pid):
    text=Path(f'/proc/{pid}/stat').read_text();fields=text[text.rfind(')')+2:].split()
    return {'pid':pid,'ppid':int(fields[1]),'start_ticks':int(fields[19]),'cmdline_sha256':digest(f'/proc/{pid}/cmdline')}

def state_function():
    path=BASE/'coverage/legacy-runner/engine/opencode_derived/__main__.py'
    body=path.read_text();tree=ast.parse(body);function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='state_digest')
    namespace=dict(os=os,stat=stat,hashlib=hashlib,json=json,Path=Path,digest=digest)
    source=ast.get_source_segment(body,function);exec(compile(source,str(path),'exec'),namespace)
    return namespace['state_digest'],{'source':str(path),'source_sha256':digest(path),'function_source_sha256':hashlib.sha256(source.encode()).hexdigest()}

def main():
    directory=HERE/'mechanical-followup';directory.mkdir(exist_ok=True)
    raw=json.loads((PRIOR/'RESULT.json').read_text())
    assert raw['slot']==3 and raw['backend']=='gpu' and raw['thinking'] is True
    assert raw['id'].endswith('-guidance-2') and raw.get('terminal_at')
    check=json.loads((HERE/'paid-on-coding-assessment/REPORT.json').read_text())
    assert check['rc']==1 and 'hyperlink target' in check['diagnostic']
    assert check['candidate_patch_sha256']==raw['patch_sha256']
    feedback=('Continue the same original task and scope from the saved workspace/session. '
              'An additional automated validation of the original required hyperlink reports:\n\n'
              +check['diagnostic']+'\n\n'
              'Correct only that mechanical hyperlink defect using the original staged inputs and document location; '
              'preserve all other deliverable content and the canonical recipe bytes. '
              'This is an explicitly additional post-review deterministic check, not another paid semantic-guidance round.\n')
    (directory/'FEEDBACK.md').write_text(feedback)
    state_digest,source=state_function()
    state=state_digest(PRIOR/'sandbox/work',PRIOR/'sandbox/session',PRIOR/'refs')
    prior={key:raw[key] for key in ('case','backend','thinking','profile','sampling','slot','cohort','request_cap','generated_ceiling','wall_s')}
    row={**prior,'id':'gpu-PFXC-A3-on-coding-post-review-mechanical-3','cohort':0,
         'feedback_class':'post-review deterministic mechanical repair','extra_feedback_ordinal':3,
         'native_protocol_cap2_result_retained':True,'extra_paid_semantic_guidance_rounds':0,
         'claim_minimum_guidance':False,
         'resume':{'initial_row':'gpu-PFXC-A3-on-coding','prior':str(PRIOR),'prior_result_sha256':digest(PRIOR/'RESULT.json'),
                   'prior_session_sha256':digest(PRIOR/'OPEN-CODE-SESSION.json'),'prior_state_sha256':state,
                   'feedback':str(directory/'FEEDBACK.md'),'feedback_sha256':digest(directory/'FEEDBACK.md'),
                   'ordinal':3,'exception_class':'additional-verifier-only-post-review-mechanical'}}
    assert row['wall_s']==1800 and row['request_cap']==32768 and row['generated_ceiling']==120000
    write(directory/'ROW.json',row)
    terminal={}
    for profile in ('on-coding','off-recommended'):
        for suffix in ('','-guidance-1','-guidance-2'):
            path=EPOCH/'units'/('gpu-PFXC-A3-'+profile+suffix)/'RESULT.json';value=json.loads(path.read_text());assert value.get('terminal_at')
            terminal[value['id']]={'result_sha256':digest(path),'terminal_at':value['terminal_at'],'status':value['status']}
    serving=json.loads((EPOCH/'out-gpu/live.json').read_text());server=proc(serving['pid']);controller=proc(server['ppid']);owner=proc(controller['ppid'])
    snapshots=[]
    for _ in range(2):
        with urllib.request.urlopen(f"http://127.0.0.1:{serving['port']}/slots",timeout=3) as response:slots=json.load(response)
        selected=next(s for s in slots if s['id']==3)
        snapshots.append({'observed_at':time.time(),'slot':3,'is_processing':selected['is_processing'],'id_task':selected.get('id_task')});time.sleep(.2)
    proof=json.loads((EPOCH/'out-gpu/proofs.json').read_text())
    snapshot={'owner':owner,'controller':controller,'server':server,'port':serving['port'],
              'server_executable_sha256':digest(f"/proc/{server['pid']}/exe"),'gpu_identity_receipt_sha256':digest(EPOCH/'out-gpu/proofs.json'),
              'gpu_identity':proof['identity'],'source_sha':proof['source_sha'],
              'actual_gpu_residency':Path(f"/sys/class/kfd/kfd/proc/{server['pid']}").exists(),
              'slot3_observations':snapshots,'all_existing_pfx_rows_terminal':terminal,
              'not_a_live_grant':'Re-probe at dispatch. These observations reserve no slot and extend no coordinator lifetime.'}
    write(directory/'PREPARATION-SNAPSHOT.json',snapshot)
    write(directory/'DISPATCH-PLAN.json',{'status':'prepared_not_authorized_not_launched','row':'ROW.json','feedback':'FEEDBACK.md',
       'checker':'../oracle.py','checker_package_required':['../vendor','../PARSER-PROVENANCE.json'],
       'checker_sha256':digest(HERE/'oracle.py'),'quality_module':str(FROZEN/'quality-v4/launch.py'),
       'quality_module_sha256':digest(FROZEN/'quality-v4/launch.py'),'entrypoint':'unchanged quality.run_row(epoch, port, row, quality_manifest_sha)',
       'quality_manifest_sha256':raw['manifest_sha256'],'saved_state_hash':state,'saved_state_hash_implementation':source,
       'full_tool_profile':'same qualified twelve direct tools and Code Mode catalog, title role64, primary32768, preserved thinking/sampler/session',
       'provider_config_wall_s':1800,'reason_for_unchanged_config':'Saved OpenCode config rejects altered provider chunkTimeout; preserve same-session config and use independent owner deadline.',
       'owner_observed_deadline_s':300,'lease_required':{'exclusive_gpu_slot':3,'owner_and_controller_start_ticks':True,
           'same_gpu_server_pid_start_and_executable_hash':True,'fresh_idle_slot3_and_no_outstanding_queue':True,
           'cancel_on_owner_controller_server_or_lease_loss':True,'cancellation_classification':'partial/interrupted grant loss; not quality failure',
           'stop_owned_worker_and_container_confirmed':True,'never_stop_shared_gpu_server':True},
       'executor_options':['Main explicit owner-held slot3 grant with cancellation/lifetime guard; old coordinator does not count this callback as pending.',
                           'pilot_runtime combined boundary coordinator schedules this slot3 row before legacy MM ON and owns its complete lifetime.'],
       'no_implicit_borrow_or_lifetime_extension':True,'native_cap2_and_final_REJECT_preserved':True,
       'reuse_previous_semantic_review_only_if':'V6 passes and the only candidate byte change is the required hyperlink target; otherwise additional source review is required.',
       'corrected_target_or_paid_final_review_text_in_feedback':False,'model_calls':0})
    files=[p for p in directory.iterdir() if p.is_file() and p.name not in {'SEAL.json','APPROVAL-TEMPLATE.json'}]
    write(directory/'SEAL.json',{'sha256':{p.name:digest(p) for p in files},'v6_oracle_sha256':digest(HERE/'oracle.py'),
          'prior_state_sha256':state,'third_feedback_exception_explicit':True,'no_model_calls':True})
    write(directory/'APPROVAL-TEMPLATE.json',{'approved_by':None,'mechanical_seal_sha256':digest(directory/'SEAL.json'),
          'owner_slot3_lease':None,'owner_deadline_s':300,'explicit_additional_third_feedback':False,
          'instruction':'Main selects a concrete lifetime-guarded executor and re-probes owner/server/idle slot before approving. This file authorizes no inference.'})
    print('Prepared mechanical row seal',digest(directory/'SEAL.json'),'state',state)

if __name__=='__main__':main()
