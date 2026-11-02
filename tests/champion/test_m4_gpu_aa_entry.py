import copy
import importlib.util
import sys
import types
from pathlib import Path
import pytest

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / 'scripts/champion/m4'))
sys.modules.setdefault('write_capture', types.ModuleType('write_capture'))
v2 = types.ModuleType('m4_gpu_speed_v2')
v2.validate_capture = lambda *args, **kwargs: None
sys.modules.setdefault('m4_gpu_speed_v2', v2)
spec = importlib.util.spec_from_file_location('aa_entry', ROOT/'scripts/champion/m4/run_gpu_aa.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


def fixture():
    sweep = {'question_pool':'/prompts', 'prompt_limit':8, 'prompt_seed':42, 'tier':1, 'threads':8,
             'context_size':65536, 'ubatch_size':512, 'kv_type':'q8_0', 'n_predict':256,
             'warmup_prompts':2, 'warmup_n_predict':32, 'startup_timeout':900, 'request_timeout':900,
             'port_base':18070, 'extra_server_args':[]}
    cell = {'role':'critic','arm':'BASELINE','source_commit':'c5','model':'/model', 'recipe':{},
            'argv':['/bin/server','-m','/model'], 'environment':{},'device':'gpu0','np':4,
            'files':{'binary':{'path':'/bin/server','sha256':'a'},'model':{'path':'/model','sha256':'b'},'prompt':{'path':'/prompts','sha256':'c'}},
            'ggml':{},'grant':{},'request_count':8,'vram_limit_bytes':10,'kfd_vram_file':'vram_0',
            'device_vram_path':'/sys/vram','watch_result_path':'/run/a/watch-result.json'}
    other = copy.deepcopy(cell); other['watch_result_path']='/run/b/watch-result.json'
    native={'cells':{'x':cell,'y':other}}
    aa={'schema':'epyc.m4.gpu.aa.execution.v1','intent':'descriptive_only','cells':[
       {'id':'a','native_cell':'x','arm':'A1','pair':0,'sweep':sweep},
       {'id':'b','native_cell':'y','arm':'A2','pair':0,'sweep':copy.deepcopy(sweep)}]}
    return aa,native


def test_pair_is_two_independent_off_processes():
    aa,native=fixture(); selected=mod.validate_plans(aa,native)
    assert len(selected)==2
    assert all(c['arm']=='BASELINE' for _,c in selected)
    cmd=mod.command(*selected[0],Path('/out'))
    assert '--dry-run' not in cmd and '--skip-clean-check' not in cmd

@pytest.mark.parametrize('mutate', [
 lambda a,n: n['cells']['y'].update(arm='CANDIDATE'),
 lambda a,n: n['cells']['y']['argv'].extend(['--prefill-order','srpf']),
 lambda a,n: n['cells']['y']['argv'].append('--prefill-order=srpf'),
 lambda a,n: a['cells'][0]['sweep']['extra_server_args'].append('--prefill-contend-cap=512'),
 lambda a,n: n['cells']['y'].update(watch_result_path=n['cells']['x']['watch_result_path']),
 lambda a,n: n['cells']['y'].update(source_commit='other'),
 lambda a,n: a['cells'][1]['sweep'].update(n_predict=500),
 lambda a,n: a['cells'][1].update(arm='A1'),
 lambda a,n: a['cells'][1].update(native_cell='x'),
 lambda a,n: a['cells'][1]['sweep'].update(question_pool='/other'),
 lambda a,n: a.update(intent='gate'),
])
def test_refuse_unmatched_or_changed_cells(mutate):
    aa,native=fixture(); mutate(aa,native)
    with pytest.raises((ValueError,KeyError)):
        mod.validate_plans(aa,native)


def test_default_enrollment_refuses():
    with pytest.raises(RuntimeError, match='not configured'):
        mod.main()


def test_entry_orchestrates_validated_native_pairs(tmp_path, monkeypatch):
    import hashlib
    import json
    aa,native=fixture()
    capture_root = tmp_path / 'capture'; capture_root.mkdir()
    for key in ('x','y'):
        native['cells'][key]['watch_result_path'] = str(capture_root / key / 'watch-result.json')
    aa['native_plan_sha256'] = 'f'*64
    aa['result_path'] = str(capture_root / 'result.json')
    raw=json.dumps(aa, sort_keys=True).encode(); plan=tmp_path/'plan.json'; plan.write_bytes(raw)
    monkeypatch.setattr(mod.aa_enrollment,'EXECUTION_ENABLED',True)
    monkeypatch.setattr(mod.aa_enrollment,'PLAN_PATH',str(plan))
    monkeypatch.setattr(mod.aa_enrollment,'PLAN_SHA256',hashlib.sha256(raw).hexdigest())
    seals=[]
    for name in ('run_gpu_aa.py','aa_enrollment.py','calibrate_gpu_aa.py','launch_gpu_aa.py'):
        p=mod.HERE/name; seals.append((p, hashlib.sha256(p.read_bytes()).hexdigest()))
    engine=mod.ROOT/'scripts/coordination/rowflow/filler_run15.sh'
    seals.append((engine, hashlib.sha256(engine.read_bytes()).hexdigest()))
    class Trust:
        sources=tuple(seals)
        plan_sha256='f'*64
        def plan(self): return native
    trust=Trust(); trust.capture_root=capture_root
    monkeypatch.setattr(mod.write_capture,'enrolled',lambda:trust,raising=False)
    runs=[]
    def fake_run(cmd, env, check):
        assert check and env['M4_PLAN_CELL'] in ('x','y')
        runs.append(env['M4_PLAN_CELL'])
        path=Path(env['M4_WATCH_DIR'])/'native/run'; path.mkdir(parents=True)
        requests=path/'requests.jsonl'
        requests.write_text('\n'.join(json.dumps({'request_index':i,'stream_id':i%4,'success':True,'http_status':200,'predicted_tokens':100,'predicted_ms':1000}) for i in range(8)))
        (path/'capture-v2-0.json').write_text(str(requests))
    def fake_validate(path, actual_trust):
        assert actual_trust is trust
        return {'requests_path':Path(path).read_text()}, {}, 400.0
    monkeypatch.setattr(mod.subprocess,'run',fake_run)
    monkeypatch.setattr(mod,'validate_capture',fake_validate)
    assert mod.main()==0
    result=json.loads((capture_root/'result.json').read_text())
    assert runs==['x','y'] and len(result['pairs'])==1
    assert result['pairs'][0]['a2_over_a1']==1 and result['gate_authorized'] is False


def test_launcher_binds_actual_row_and_fails_changed_grant(tmp_path):
    sys.modules['run_gpu_aa'] = mod
    spec=importlib.util.spec_from_file_location('aa_launch',ROOT/'scripts/champion/m4/launch_gpu_aa.py')
    launch=importlib.util.module_from_spec(spec); spec.loader.exec_module(launch)
    aa,native=fixture(); cap=tmp_path/'capture'; cap.mkdir(); stop=tmp_path/'STOP'
    row={'id':'m4-aa','regions':'mi210_0,184-191','stopfile':str(stop),'min_window_s':3600,'port':18070}
    aa.update(row=row,result_path=str(cap/'result.json'))
    for cell in native['cells'].values():
        cell['grant']={'id':row['id'],'regions':row['regions'],'stopfile':str(stop)}
    trust=types.SimpleNamespace(capture_root=cap)
    args=launch.launch_spec(aa,native,trust)
    assert args[args.index('--gpu-quiet')+1]=='exclusive'
    assert args[args.index('--claim-cpus')+1]=='184-191'
    assert args[args.index('--port')+1]=='18070'
    native['cells']['y']['grant']['id']='other'
    with pytest.raises(ValueError):
        launch.launch_spec(aa,native,trust)


def test_default_launcher_enrollment_refuses():
    sys.modules['run_gpu_aa'] = mod
    spec=importlib.util.spec_from_file_location('aa_launch',ROOT/'scripts/champion/m4/launch_gpu_aa.py')
    launch=importlib.util.module_from_spec(spec); spec.loader.exec_module(launch)
    with pytest.raises(RuntimeError, match='not configured'):
        launch.load()
