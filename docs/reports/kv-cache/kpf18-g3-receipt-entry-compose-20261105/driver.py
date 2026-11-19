"""Protocol/record integration over the unchanged pinned gate lifecycle.

No socket/process-control functions are replaced. The gate's only private
source diff is two logging callbacks on bytes it has already read.
"""
import json
import os
from pathlib import Path
import sys
from copy import deepcopy
import time
import subprocess

BASE=Path(__file__).resolve().parent
DATA=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-normalization-r13/data')
sys.path[:0]=[str(BASE),str(DATA),str(BASE/'vendor'),str(BASE/'research/scripts/benchmark/kpf18')]
import guard
from ledger import Ledger,file_sha
from preload_integration import load_preload_models, unchanged_models as _unchanged_models
from controller import run
import native_group3 as g
import pipeline
import kpf18_gate as gate

OUT=guard.attempt_root()
PRELOAD_MODELS=None
RETAINED_PRELOAD_RECEIPT=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-native-control-r15/out/PRELOAD-MODEL-IDENTITY.json')

def unchanged_models():
    _unchanged_models(PRELOAD_MODELS)

def setup(ctx,srv,state):
    guard.boundary();guard.sources();guard.tests_and_enrollment()
    ledger=Ledger(OUT/'capture',guard.ContextBoundary(ctx),srv);state['ledger']=ledger
    R=gate.Run(ctx,3,'g3_native_control_raw_capture',srv,True);state['R']=R
    group=gate.G(ctx,3);source=group['trunk']+group['src_tail'];child=group['trunk']+group['suffixes'][2]
    model=Path(gate.flag_val(srv.argv,('-m','--model')));draft=Path(gate.flag_val(srv.argv,('-md','--model-draft')))
    unchanged_models();model_manifest=PRELOAD_MODELS
    if (model_manifest['target']['path'],model_manifest['drafter']['path'])!=(str(model),str(draft)):
        raise ValueError('actual launched models differ from sealed preload model identities')
    dso=[{'path':name,'sha256':file_sha(name)} for name in srv.readback['ggml_libs']]
    rb=srv.readback
    actual_env={item.split('=',1)[0]:item.split('=',1)[1] for item in Path(f'/proc/{srv.proc.pid}/environ').read_bytes().decode().split('\0') if '=' in item}
    if actual_env.get('LLAMA_KV_CACHE_DEBUG')!='3' or actual_env.get('HSA_OVERRIDE_CPU_AFFINITY_DEBUG')!='0' or 'GGML_CUDA_DISABLE_GRAPHS' in actual_env:
        raise ValueError('not exact grids3/HSA0/original graphsON environment')
    escaped=[]
    for task in Path(f'/proc/{srv.proc.pid}/task').iterdir():
        if not os.sched_getaffinity(int(task.name))<=set(range(184,192)):escaped.append(int(task.name))
    if escaped:raise ValueError('server task affinity escaped actual host grant')
    identity={'fixture_mode':False,'measurement_revision':'a1f0c8cf9','binary_sha256':file_sha(srv.binary),
        'trunk_prefix_hash':gate.ARMS.prefix_hashes(group['trunk'],[g.T])[g.T],
        'prompt_set_sha256':file_sha(ctx.ps.path),'recipe_file_sha256':file_sha(ctx.args.argv_file),
        'launch_argv_sha256':g.digest(srv.argv),'model_file':str(model),'draft_model_file':str(draft),'backend':'ROCm0',
        'producer_source_sha256':file_sha(BASE/'controller.py'),'source_manifest_sha256':file_sha(BASE/'SOURCES.sha256'),
        'predeclaration_sha256':file_sha(BASE/'PROTOCOL.md'),'layout_normalizer_sha256':g.digest({
            'r13_normalizer_manifest':file_sha(DATA/'SHA256SUMS'),'r13_bridge':file_sha(BASE/'normalize_bridge.py')}),
        'dso_manifest_sha256':g.digest(dso),'model_manifest_sha256':g.digest(model_manifest),
        'source_prompt_ids_sha256':g.digest(source),'child_prompt_ids_sha256':g.digest(child),
        'foreign_filler_ids_sha256':g.digest(group['filler']),
        'recipe':{'n_batch':int(gate.flag_val(srv.argv,('-b','--batch-size'))),'n_ubatch':int(gate.flag_val(srv.argv,('-ub','--ubatch-size'))),
            'np':int(gate.flag_val(srv.argv,('-np','--parallel'))),'n_ctx':int(gate.flag_val(srv.argv,('-c','--ctx-size'))),
            'kv_unified':'--kv-unified' in srv.argv,'seed':42,'spec_type':gate.flag_val(srv.argv,('--spec-type',)),
            'cpu_list':os.environ['FILLER_CPUS'],'graphs':'ON','diagnostic_grid_level':int(actual_env['LLAMA_KV_CACHE_DEBUG']),
            'HSA_OVERRIDE_CPU_AFFINITY_DEBUG':actual_env['HSA_OVERRIDE_CPU_AFFINITY_DEBUG']}}
    if g.identity_errors(identity,identity):raise ValueError('actual identity violates pinned original protocol: '+str(g.identity_errors(identity,identity)))
    att={}
    for key,value in (('ELF',{'path':str(srv.binary),'sha256':identity['binary_sha256']}),('DSO',dso),('source',identity),
        ('recipe',{'path':ctx.args.argv_file,'sha256':identity['recipe_file_sha256'],'actual_argv':srv.argv}),
        ('model',model_manifest),('prompt',{'path':str(ctx.ps.path),'sha256':identity['prompt_set_sha256']}),
        ('argv_readback',{'readback':rb,'actual_env':actual_env,'actual_affinity':srv.env_note.get('launch_affinity'),'escaped_tasks':escaped})):
        att[key]=ledger.json('identity-'+key+'.json',value)
    ticks=int(Path(f'/proc/{srv.proc.pid}/stat').read_text().rsplit(') ',1)[1].split()[19])
    record={'schema':g.SCHEMA,'native_block_schema':g.BLOCK_SCHEMA,'kpf_task':g.TASK,'arm':g.ARM,'group':3,
        'identity':identity,'rules_sha256':g.RULES_SHA,'category':'CANDIDATE','instrument_class':'serving','fixture_mode':False,
        'run_id':'kpf18-g3-native-control-'+gate.utc_tag(),'load_id':srv.label,'window_id':ctx.args.window_id,'host':ctx.host,
        'start_utc':gate.now_iso(),'end_utc':gate.now_iso(),'rows':str(OUT/'conformance/rows.jsonl'),
        'argv':srv.argv,'binary':str(srv.binary),'binary_realpath':str(srv.binary.resolve()),'binary_sha256':identity['binary_sha256'],
        'prompt_set_sha256':identity['prompt_set_sha256'],'server_instance':{'pid':srv.proc.pid,'startticks':ticks,'binary_sha256':identity['binary_sha256']},
        'dflash2':True,'spec_off':False,'seed':42,'n_predict':g.N,'argv_readback':{key:rb.get(key) for key in ('proc_cmdline_matches_argv','exe_matches_binary')},
        'load_counts':{'independent_loads':1,'same_load_controls':0,'same_load_forks':0,'generated_positions_per_trial':g.N},
        'execution_order':[],'planned_execution_order':list(g.ORDER),'historical_verdict_policy':'preserve_original_verdicts',
        'historical_verdicts':deepcopy(g.HISTORICAL),'program_closure':False,'cell_attempt_started':True,
        'runtime_checks':{'own_hip_mapping':bool(rb.get('hip_mapped')),'ggml_linkage':srv.linkage.get('pass') is True,
            'argv_and_env_readback':not rb.get('problems') and rb.get('proc_cmdline_matches_argv') is True,
            'source_and_ELF_seals':True,'source_completed_before_native_fork':False,'guard_trip':False,
            'own_vram_nonzero_samples':0,'unpinned_threads':len(escaped)},
        'raw_inventory':ledger.inventory,'identity_attestations':att,'construction_attempts':[],'trials':[]}
    state.update(record=record,identity=identity)

def publish(ctx,srv,state):
    ledger=state.get('ledger');record=state.get('record')
    if ledger is None or record is None:return
    guard.sources();unchanged_models()
    ledger.close();record['raw_inventory']=ledger.inventory;record['end_utc']=gate.now_iso()
    judged=[event for event in ledger.events if event.get('label','').endswith('-child')]
    record['execution_order']=[trial['name'] for trial in record['trials']]
    record['load_counts']['same_load_controls']=sum(trial['name'].startswith('C') for trial in record['trials'])
    record['load_counts']['same_load_forks']=sum(trial['name'].startswith('X') for trial in record['trials'])
    record['raw_judged_request_attempts']=[{'label':event['label'],'raw_ref':event['raw_ref']} for event in judged]
    forks=[trial for trial in record['trials'] if trial['name'].startswith('X')]
    record['runtime_checks']['source_completed_before_native_fork']=bool(forks) and all(
        trial['source_end_ns']<trial['child_begin_ns'] for trial in forks)
    record['runtime_checks']['own_vram_nonzero_samples']=(srv.sampler.n_own_nonzero-state.get('block_vram_start',srv.sampler.n_own_nonzero)) if srv.sampler else 0
    record['runtime_checks']['guard_trip']=bool(srv.sampler and srv.sampler.abort.is_set())
    record['raw_runtime']={'readback':srv.readback,'linkage':srv.linkage,'env':srv.env_note,
        'residency':srv.sampler.summary() if srv.sampler else None,'stop':srv.stop_rec,'event_ledger':str(ledger.directory/'EVENT-LEDGER.json')}
    directory=OUT/'conformance';directory.mkdir(parents=True,exist_ok=False)
    rows=pipeline.raw_rows(record);(directory/'rows.jsonl').write_bytes(rows)
    sealed=g.prepare_record(record,state['identity'],rows)
    (directory/'belief_measurements.jsonl').write_text(json.dumps(sealed,sort_keys=True,allow_nan=False)+'\n')
    (directory/'VERDICT.json').write_text(json.dumps(sealed['decisions'],sort_keys=True,indent=2)+'\n')
    # Real existing shared source/carrier only; no grading implementation here.
    enrollment=guard.tests_and_enrollment();sys.path.insert(0,enrollment['canonical_export'])
    from scripts.vidya.adapters import kv_prefix_fork as adapter
    from scripts.vidya.claim_tuple import grade
    errors=adapter.validate_row(sealed)
    if errors:raise ValueError('canonical adapter refused actual native record: '+str(errors))
    claims=adapter.native_rows(directory/'belief_measurements.jsonl')
    projected=[adapter.project(item) for item in claims]
    (directory/'SHARED-PROJECTION.json').write_text(json.dumps([{'metric':item.metric,'value':item.value,
        'reps':item.reps,'grade':grade(item),'source':'actual canonical registered carrier'} for item in projected],sort_keys=True)+'\n')

def item3(ctx):
    srv=gate.Server(ctx,'kpf18-g3-diagnostic-v1-20261029',guard.BIN,1024,extra_args=['--log-verbosity','5','--log-colors','off'])
    state={};steps=gate.start_steps(ctx,srv)
    steps.append(gate.Step('capture actual sealed identity before original group3 diagnostic',120,lambda:setup(ctx,srv,state)))
    def cell():
        state['block_vram_start']=srv.sampler.n_own_nonzero if srv.sampler else 0
        try:run(gate,guard.ContextBoundary(ctx),state['R'],srv,state['record'],state['identity'],state['ledger'])
        except Exception as error:
            state['record']['diagnostic_error']=type(error).__name__+': '+str(error)
            state['ledger'].json('DIAGNOSTIC-REFUSAL.json',state['record']['diagnostic_error'])
    steps.append(gate.Step('X1 C1 X2 C2 C3; max3 exactT constructions/control; preserve every refusal',6400,cell))
    steps.append(gate.stop_step(srv))
    steps.append(gate.Step('r4 normalized conformance record + actual shared projection; no program closure',120,lambda:publish(ctx,srv,state)))
    return steps

def item3_smoke(ctx):
    """Same native gate/server; one short real request, no geometry claim."""
    srv=gate.Server(ctx,'kpf18-g3-diagnostic-smoke',guard.BIN,1024,extra_args=['--log-verbosity','5','--log-colors','off'])
    steps=gate.start_steps(ctx,srv)
    def first_request():
        guard.boundary();ctx.check_boundary()
        ids=gate.G(ctx,3)['trunk'][:32]
        status,response=ctx.client._req('POST','/completion',gate.body_for(ids,1,0,fork=False,cache=False),timeout=60)
        if status!=200 or not isinstance(response,dict) or not response.get('tokens'):raise ValueError('real smoke request missing token')
        if not srv.sampler or srv.sampler.n_own_nonzero<1:raise ValueError('GPU residency not sampled')
        result={'scope':'one native gate request; no group3 verdict','first_request_ok':True,'gpu_samples':srv.sampler.n_own_nonzero,'tokens':len(response['tokens'])}
        with (OUT/'SMOKE-REQUEST.json').open('x') as f:json.dump(result,f)
        if os.environ.get('KPF_SMOKE_CUTOFF')=='1':
            while True:guard.boundary();time.sleep(.1)
    steps.append(gate.Step('one real request and sampled GPU residency',60,first_request))
    steps.append(gate.stop_step(srv))
    return steps

def main():
    global PRELOAD_MODELS
    dry='--dry-run' in sys.argv
    guard.sources()
    if not dry:
        guard.boundary();guard.tests_and_enrollment()
        PRELOAD_MODELS=load_preload_models(RETAINED_PRELOAD_RECEIPT,BASE/'ORIGINAL-MODELS.json')
        (OUT/'PRELOAD-MODEL-IDENTITY.json').write_text(json.dumps(
            {role:PRELOAD_MODELS[role] for role in ('target','drafter')},sort_keys=True)+'\n')
        unchanged_models();guard.boundary()
    # Recipe DATA change only. Existing Server.build_env/start/stop unchanged.
    gate.PROD_ENV['LLAMA_KV_CACHE_DEBUG']='3'
    gate.ITEMS[3]=item3_smoke if os.environ.get('KPF_SMOKE')=='1' else item3
    sys.argv=[str(BASE/'research/scripts/benchmark/kpf18/kpf18_gate.py'),*sys.argv[1:]]
    import gpu_witness
    gpu_witness.install(gate)
    return gate.main()

if __name__=='__main__':raise SystemExit(main())
