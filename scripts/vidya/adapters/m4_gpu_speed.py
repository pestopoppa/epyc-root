"""Draft projection of native M4 GPU process rows; no grading ladder."""
from __future__ import annotations
import hashlib, importlib.util, json, math, sys
from pathlib import Path
from claim_tuple import ClaimTuple, ProjectionError, register
ROOT=Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-fold-gates/speed-gpu').resolve()
SOURCE_KIND='m4-gpu-recipe-speed-measurement'

def units(path):
    p=Path(path)
    if p.is_file(): return [p]
    return sorted(p.rglob('cells.jsonl')) if p.is_dir() else []

def canonical(x): return json.dumps(x,sort_keys=True,separators=(',', ':'),ensure_ascii=False,allow_nan=False).encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def module():
    spec=importlib.util.spec_from_file_location('m4_gpu_native_projection',ROOT/'native/server_np_sweep.py')
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m

def native_rows(path):
    p=Path(path).resolve()
    if ROOT not in p.parents or p.name!='cells.jsonl': raise ProjectionError('cell path outside GPU producer')
    try: rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    except (OSError,ValueError) as exc: raise ProjectionError(f'cannot read cells: {exc}') from exc
    if len(rows)!=1 or not isinstance(rows[0],dict) or len(rows[0].get('belief_measurements',[]))!=1: raise ProjectionError('expected one producer-authored process row')
    return ({'cell':rows[0],'cells_path':str(p)},)

@register(SOURCE_KIND)
def project(native):
    if not isinstance(native,dict) or native not in native_rows(native.get('cells_path','')): raise ProjectionError('row not present in native cell')
    cell=native['cell']; row=cell['belief_measurements'][0]; unsigned=dict(row); recorded=unsigned.pop('measurement_sha256','')
    if sha(canonical(unsigned))!=recorded: raise ProjectionError('native capture hash mismatch')
    value=row.get('value'); extra=row.get('extra',{})
    try:
        if sha((ROOT/'native/server_np_sweep.py').read_bytes()) != extra.get('producer_sha256'):
            raise ProjectionError('GPU producer source changed')
    except OSError as exc:
        raise ProjectionError(f'GPU producer source unavailable: {exc}') from exc
    if (row.get('metric')!='aggregate_decode_tokens_per_s' or type(value) not in (int,float) or not math.isfinite(value) or value<=0
        or row.get('category') not in ('BASELINE','CANDIDATE') or row.get('protocol_id')!='' or row.get('reps')!=1
        or extra.get('context_size')!=65536 or extra.get('np') not in (1,2,4,8)):
        raise ProjectionError('invalid GPU capture')
    expected_commit='c72ec82f5417bb2937310326120f149b665e8400' if row['category']=='BASELINE' else 'bc441f1a261766d11bfeff21668a1031c4dbf8cd'
    if extra.get('source_commit')!=expected_commit or not extra.get('role'): raise ProjectionError('source commit or role unbound')
    command=cell.get('server_command')
    if not isinstance(command,list): raise ProjectionError('missing server command')
    def arg(flag):
        return command[command.index(flag)+1] if flag in command and command.index(flag)+1<len(command) else None
    if (arg('-c')!='65536' or arg('-np')!=str(extra['np']) or arg('-m')!=cell.get('model_path')
            or str(Path(extra['binary']).resolve()) not in command): raise ProjectionError('server command does not match captured scope')
    if row['category']=='CANDIDATE':
        if arg('--prefill-order')!='srpf' or arg('--prefill-contend-cap')!='512': raise ProjectionError('candidate treatment mismatch')
    elif '--prefill-order' in command or '--prefill-contend-cap' in command:
        raise ProjectionError('baseline treatment mismatch')
    samples=extra.get('gpu_residency_during')
    if not isinstance(samples,list) or not samples or any(s.get('own_vram_bytes',0)<=0 or s.get('device_vram_bytes',0)<=0 or s.get('kfd_process_count',0)<1 for s in samples): raise ProjectionError('unproven during-run residency')
    path=Path(row.get('attestation_locator','')).resolve()
    if ROOT not in path.parents or path.name!='requests.jsonl': raise ProjectionError('request path outside GPU producer')
    try:
        raw=path.read_bytes(); requests=[json.loads(x) for x in raw.splitlines() if x.strip()]
        events=[json.loads(x) for x in (path.parent/'events.jsonl').read_text().splitlines() if x.strip()]
        maps=Path(extra['ggml_maps']).read_text()
    except (OSError,ValueError,KeyError) as exc: raise ProjectionError(f'missing native proof: {exc}') from exc
    if sha(raw)!=row.get('attestation_sha256'): raise ProjectionError('request digest mismatch')
    if not events or not any(e.get('event')=='server_stopped' and (e.get('result') or {}).get('ps_verified_dead') is True for e in events): raise ProjectionError('server cleanup not proven')
    ggml=[line for line in maps.splitlines() if 'libggml' in line]
    if not ggml or any(not line.split()[-1].startswith(str(Path(extra['binary']).resolve().parent)+'/') for line in ggml): raise ProjectionError('wrong ggml mapping')
    m=module()
    try:
        parsed=[m.RequestResult(**x) for x in requests]
        replay=m.summarize_cell(model=m.ModelSpec(label=cell['model'],path=Path(cell['model_path'])),np_level=cell['np'],results=parsed,wall_s=cell['wall_seconds'],ttft_ms=cell['ttft_ms'],server_pid=cell['server_pid'],server_command=cell['server_command'])
    except (TypeError,KeyError,ValueError) as exc: raise ProjectionError(f'cannot replay native metric: {exc}') from exc
    if replay['error_rate']!=0 or not math.isclose(replay['aggregate_decode_tps'],value,rel_tol=1e-12,abs_tol=1e-12): raise ProjectionError('native aggregate does not re-derive')
    return ClaimTuple(measurement_id=row['measurement_id'],metric=row['metric'],value=value,date=row['date'],category=row['category'],claim=row['claim'],metric_direction='higher_better',protocol_id='',reps=1,reps_basis=row['reps_basis'],unit=row['unit'],attestation_path=str(path),attestation_locator=str(path),attestation_sha256=sha(raw),attestation_present=True,attestation_verified=True,source_kind=SOURCE_KIND,extra=extra,observation={})
