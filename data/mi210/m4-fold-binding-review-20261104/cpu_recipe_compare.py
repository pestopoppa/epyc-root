#!/usr/bin/env python3
"""Run the predeclared M4 same-frame CPU recipe comparison under an owned lease.

The output is a diagnostic capture, not a best-recipe, fold or promotion verdict.
It is launched by m4_cpu_recipe_entry.py under watch.run, which supplies the server
PID registry; the seal is the plan digest plus the image manifests the plan names.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import stat
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT/'scripts/benchmark/m4_cpu_producer'
OWNERSHIP = ROOT/'scripts/benchmark/m4_cpu_ownership'
sys.path.insert(0,str(PRODUCER)); sys.path.insert(0,str(OWNERSHIP))
import capture
import owned
import entry


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def module(name: str,path: Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if not spec or not spec.loader: raise ValueError('native module unavailable')
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod)
    return mod


def _strip_loader_args(args: list) -> tuple:
    # The native runner owns the loader-knob definition; load it lazily.
    native=sys.modules.get('m4_compare_native') or module('m4_compare_native',PRODUCER/'native/k35_stack_context_matrix_runner.py')
    return native.strip_loader_args(args)


def _checked(path: Path, digest: str) -> Path:
    if not path.is_absolute() or '..' in path.parts or not path.is_file(): raise ValueError('unbound input path')
    if not isinstance(digest,str) or len(digest)!=64 or sha(path)!=digest: raise ValueError(f'input digest mismatch: {path}')
    return path


def _identity(st) -> dict:
    return {'device':st.st_dev,'inode':st.st_ino,'size':st.st_size,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}


def _check_custody(item: dict) -> None:
    receipt=_checked(Path(item['custody_path']),item['custody_sha256'])
    doc=json.loads(receipt.read_bytes());path=Path(item['path'])
    if (doc.get('schema')!='epyc.m4.file-custody.v1' or doc.get('path')!=str(path)
            or doc.get('sha256')!=item.get('sha256') or not path.is_absolute()
            or '..' in path.parts or path.resolve(strict=True)!=path):
        raise ValueError('pre-admission input custody mismatch')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        state=os.fstat(fd)
        if not stat.S_ISREG(state.st_mode) or _identity(state)!=doc.get('identity') or _identity(path.stat())!=doc.get('identity'):
            raise ValueError('pre-admission input identity changed')
    finally: os.close(fd)


def verify(plan_path: Path, expected_sha: str, *, full_hash: bool=True) -> dict:
    _checked(plan_path,expected_sha); plan=json.loads(plan_path.read_bytes())
    if plan.get('schema')!='epyc.m4.q38.recipe-comparison.v1' or plan.get('status')!='REVIEWED_DIAGNOSTIC':
        raise ValueError('comparison is not independently reviewed for diagnostic execution')
    if plan.get('decision_authority')!='descriptive_only' or os.environ.get('FILLER_ID') not in (None,'',plan.get('row_id')):
        raise ValueError('diagnostic purpose or row identity mismatch')
    if plan.get('champion')!='c72ec82f5417bb2937310326120f149b665e8400' or plan.get('candidate')!='bc441f1a261766d11bfeff21668a1031c4dbf8cd':
        raise ValueError('candidate source mismatch')
    current=subprocess.check_output(['git','-C','/mnt/raid0/llm/llama.cpp','rev-parse',
        'refs/heads/ak/champion/llama-cpp-ffc1bac82eec'],text=True).strip()
    if current!=plan['champion']: raise ValueError('champion moved; rebind comparison')
    # Sealed: the plan (by digest) and the image manifests it names. The harness never
    # hashes its own source; a legacy plan 'sources' block is ignored.
    images={}
    for arm,commit in [('baseline',plan['champion']),('candidate',plan['candidate'])]:
        info=plan['images'][arm]; manifest=_checked(Path(info['path']),info['sha256'])
        record=json.loads(manifest.read_bytes())
        if record.get('source_commit')!=commit: raise ValueError('image source mismatch')
        image=Path(record['root']).resolve(strict=True)
        files=record.get('files')
        if not isinstance(files,dict) or 'bin/llama-server' not in files: raise ValueError('image manifest incomplete')
        actual={str(p.relative_to(image)) for p in (image/'bin').glob('libggml*.so*') if p.is_file()}
        if not actual or not actual.issubset(files): raise ValueError('image-local ggml manifest incomplete')
        for name,digest in files.items():
            rel=Path(name)
            if rel.is_absolute() or '..' in rel.parts: raise ValueError('image path escape')
            resolved=(image/rel).resolve(strict=True);resolved.relative_to(image)
            _checked(resolved,digest)
        images[arm]=image
    inputs=plan.get('inputs')
    if not isinstance(inputs,list) or not inputs: raise ValueError('model inputs missing')
    by_path={}
    for item in inputs:
        path=item['path']; value=item['sha256']
        if path in by_path: raise ValueError('duplicate model input')
        by_path[path]=value
        if full_hash: _check_custody(item)
    model=plan.get('model')
    if not isinstance(model,dict) or by_path.get(model.get('path'))!=model.get('sha256'):
        raise ValueError('target model not independently sealed')
    recipes=plan.get('recipes');cells=plan.get('cells')
    if not isinstance(recipes,dict) or set(recipes)!={'canonical_t48','configured_t96'}: raise ValueError('recipe set mismatch')
    if not isinstance(cells,list) or len(cells)!=12: raise ValueError('comparison denominator incomplete')
    expected={(rep,arm,variant) for rep in range(3) for arm in ('baseline','candidate') for variant in recipes}
    observed={(c['rep'],c['arm'],c['recipe']) for c in cells}
    if len(observed)!=len(cells) or observed!=expected: raise ValueError('comparison cells differ from predeclared frame')
    if any(c.get('role')!='architect_general' or c.get('server_context_size')!=262144 for c in recipes.values()):
        raise ValueError('role or server capacity mismatch')
    if recipes['canonical_t48'].get('threads')!=48 or recipes['configured_t96'].get('threads')!=96:
        raise ValueError('comparison thread settings changed')
    expected_env={'canonical_t48':{'GGML_FA_SPLIT_KV':'0','GGML_NOHUGEPAGE_PROCESS':'1','GGML_FUSED_DECODE_OFF':'1'},
                  'configured_t96':{'GGML_FA_SPLIT_KV':'0','GGML_NOHUGEPAGE_PROCESS':None,'GGML_FUSED_DECODE_OFF':None}}
    stripped=[]
    for name,cfg in sorted(recipes.items()):
        if cfg.get('recipe_env') != expected_env[name] or cfg.get('model')!=model['path']:
            raise ValueError('comparison recipe or environment mismatch')
        if cfg.get('draft_model') not in by_path or cfg.get('image_path') is not None:
            raise ValueError('draft is unsealed or unexpected image supplied')
        fixed=dict(cfg)
        for key in ('name','threads','recipe_env'): fixed.pop(key,None)
        # Loader knobs (--load-threads) cannot change a result: not a recipe difference.
        if isinstance(fixed.get('extra_args'),list):
            fixed['extra_args']=list(_strip_loader_args(fixed['extra_args']))
        stripped.append(fixed)
    if stripped[0] != stripped[1]: raise ValueError('comparison has unintended recipe differences')
    return {'plan':plan,'images':images}


def run(plan_path: Path, expected_sha: str, output: Path, *, grant: Path, stop: Path, hold: Path,
        deadline: float, load_threads: int | None = None) -> int:
    bound=verify(plan_path,expected_sha);plan=bound['plan'];images=bound['images']
    # Loader knobs are not part of the seal: --load-threads only changes how fast weights
    # are read, so it is appended at run time and recorded beside the sealed scenario.
    loader_args=[] if load_threads is None else ['--load-threads',str(load_threads)]
    if load_threads is not None and (type(load_threads) is not int or not 1<=load_threads<=192):
        raise ValueError('invalid --load-threads')
    entry._row_id(plan['row_id'])
    entry._grant(grant,'0-95',deadline,require_host_holds=True)
    if not hold.is_dir() or stop.exists() or any(hold.glob('HOLD_*')): raise ValueError('STOP or HOLD')
    # watch.run always provides the registry; a delegated cgroup (M4_OWNED_CGROUP) is optional.
    if not os.environ.get('M4_SERVER_PID_REGISTRY'):
        raise ValueError('server PID registry missing: run under the M4 watcher')
    if output.exists(): raise ValueError('output already exists')
    output.mkdir(parents=True)
    (output/'comparison-plan.json').write_bytes(plan_path.read_bytes())
    native=module('m4_compare_native',PRODUCER/'native/k35_stack_context_matrix_runner.py')
    comparator=module('m4_compare_comparator',PRODUCER/'native/compare_v9_promotion_arms.py')
    records=[]
    for cell in plan['cells']:
        if time.time()>=deadline or stop.exists() or any(hold.glob('HOLD_*')): raise ValueError('STOP, HOLD or deadline')
        for item in plan['inputs']: _check_custody(item)
        arm,variant,rep=cell['arm'],cell['recipe'],cell['rep']
        cfg=plan['recipes'][variant];image=images[arm];server=image/'bin/llama-server'
        case=output/f'{rep:02d}-{arm}-{variant}'
        cmd=[sys.executable,'-B',str(PRODUCER/'native/k35_stack_context_matrix_runner.py'),'--execute',
             '--only',cfg['name'],'--context','8192','--max-tokens','128','--min-completion-tokens','128',
             '--reps','1','--binary',str(server),'--output-dir',str(case)]
        effective=dict(cfg)
        if loader_args:  # an explicit --load-threads replaces any planned or runner default
            base=list(cfg.get('extra_args') or [])
            effective['extra_args']=[*(_strip_loader_args(base) if base else ()),*loader_args]
        env=dict(os.environ,M4_SCENARIO_JSON=json.dumps(effective,sort_keys=True,separators=(',',':')),
                 M4_TREATMENT='default-off' if arm=='baseline' else 'srpf-cap512')
        env.pop('LLAMA_ARG_PREFILL_ORDER',None);env.pop('LLAMA_ARG_PREFILL_CONTEND_CAP',None)
        child,fd,birth=owned.spawn(cmd,env=env)
        try:
            while child.poll() is None:
                if time.time()>=deadline or stop.exists() or any(hold.glob('HOLD_*')):
                    raise RuntimeError('STOP, HOLD or deadline during native cell')
                time.sleep(0.5)
            if child.returncode: raise RuntimeError(f'native cell failed: {child.returncode}')
        finally:
            try: owned.stop(child,fd,birth)
            finally: os.close(fd)
        summary=case/'summary.json';rows=comparator.load_arm([summary],server,arm)
        if len(rows)!=1: raise ValueError('native cell incomplete')
        recipe={'scenario':cfg['name'],'scenario_config':cfg,'treatment':env['M4_TREATMENT'],'loader_args':loader_args}
        measurement=capture.capture(directory=case/'process-captures',row=rows[0],arm=arm,pair=rep,
            role='architect_general',model=plan['model']['path'],model_sha=plan['model']['sha256'],recipe=recipe,
            context=8192,binary=server,commit=plan['champion'] if arm=='baseline' else plan['candidate'],
            producer=Path(__file__),runner=PRODUCER/'native/k35_stack_context_matrix_runner.py',
            comparator=PRODUCER/'native/compare_v9_promotion_arms.py')
        records.append({'rep':rep,'arm':arm,'recipe':variant,'measurement':measurement})
    result={'schema':'epyc.m4.q38.recipe-comparison.result.v1','status':'COMPLETE_DIAGNOSTIC',
            'decision':None,'gate_authorized':False,'plan_sha256':expected_sha,'records':records}
    (output/'RESULT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return 0


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--execute',action='store_true')
    for name in ('grant','stop','hold'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--deadline',type=float,required=True)
    p.add_argument('--load-threads',type=int,default=None,help='loader knob, outside the plan seal')
    args=p.parse_args()
    if not args.execute: raise SystemExit('REFUSED: explicit diagnostic execution required')
    return run(args.plan,args.plan_sha256,args.output,grant=args.grant,stop=args.stop,hold=args.hold,
               deadline=args.deadline,load_threads=args.load_threads)

if __name__=='__main__': raise SystemExit(main())
