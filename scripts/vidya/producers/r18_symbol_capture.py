#!/usr/bin/env python3
"""Prospective R18 symbol finding capture, called inside the guarded build process.

Begin before the comparator starts. Complete only from its immediate guarded successor;
partial/failed attempts retain a terminal receipt and never project a finding.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

SCHEMA = 'epyc.autokernel.r18_symbol_capture.v1'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def atomic(path, obj):
    path = Path(path); tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('x') as f:
        json.dump(obj, f, sort_keys=True, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def window_check():
    deadline = os.environ.get('FILLER_DEADLINE')
    stop = os.environ.get('FILLER_STOPFILE')
    if (deadline and time.time() >= float(deadline) - 3) or (stop and Path(stop).exists()):
        raise ValueError('capture window stopped or expired')

def checked(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': sha(path)}

def begin(out, result, source, inputs, dependencies, commands, *, synthetic=False, build_env=None):
    out = Path(out); result = Path(result)
    if out.exists() or result.exists(): raise ValueError('fresh capture and absent comparator output required')
    dep = json.loads(Path(dependencies).read_text())
    if not isinstance(dep, dict) or not dep: raise ValueError('empty comparator dependencies')
    bound = {p: checked(Path(__file__).resolve().parent / 'r18_inputs' / 'perl-lib' / p[len('@bundle/'):] if p.startswith('@bundle/') else p) for p in dep}
    if any(bound[p]['sha256'] != digest for p, digest in dep.items()): raise ValueError('dependency digest mismatch')
    def git(*args): return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
    head, tree, status = git('rev-parse','HEAD'), git('rev-parse','HEAD^{tree}'), git('status','--porcelain','--untracked-files=all')
    if status: raise ValueError('source dirty')
    if not synthetic:
        window_check()
        if sha(dependencies) not in ('4c36a479297aa435589ee4604f68d516fe3efdacd535d80c8fc1b6bf1772d425', '5adb079828658d11dd393fa61f3e59712872ae635102c2543c7c9d8823c927fd', '5350aac873b0b3626851912dc44c1d3579467edacb6a999e4acfd70f83a587fd'): raise ValueError('comparator dependency manifest differs')
        pins = {'comparator':'08a5e9e15f8ac07d573d8e0c8c38ec4aef6d78820032ec4e2eb0325a3447bf61',
                'anchor_cpu':'3f4edd2fc0f1e78003735be59db987d43c4bc0e6a8f821bc419d7b6f492346c0',
                'anchor_hip':'f26a166b8ea3089d19a395ae00afa22e917df8eba71ca6ef4be5235d65ea8079'}
        if head != 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115' or any(sha(inputs[k]) != v for k,v in pins.items()):
            raise ValueError('not the pinned v10 comparator, source and anchors')
    out.mkdir(parents=True)
    build_env = dict(os.environ if build_env is None else build_env)
    record = {'schema': SCHEMA, 'started_at': now(), 'state': 'started', 'result': str(result.resolve()),
              'synthetic': synthetic, 'source': {'path': str(Path(source).resolve()), 'head': head, 'tree': tree, 'status': status},
              'inputs': {name: checked(path) for name, path in inputs.items()},
              'dependency_manifest': checked(dependencies), 'dependencies': bound,
              'commands': commands,
              'environment': {k: build_env[k] for k in ('FILLER_ID','FILLER_CPUS','FILLER_DEADLINE','PATH','CC','CXX','CFLAGS','CXXFLAGS','HIPFLAGS','CMAKE_PREFIX_PATH','LD_LIBRARY_PATH') if k in build_env}}

    atomic(out/'begin.json', record)
    return record

def terminal(out, state, detail):
    out=Path(out)
    atomic(out/'terminal.json', {'schema': SCHEMA, 'state': state, 'finished_at': now(),
                                'begin_sha256': sha(out/'begin.json'), 'detail': detail})

def complete(out, rc, capture_script):
    out=Path(out); begin_data=json.loads((out/'begin.json').read_text())
    if (out/'terminal.json').exists(): raise ValueError('already terminal')
    for item in list(begin_data['inputs'].values()) + list(begin_data['dependencies'].values()) + [begin_data['dependency_manifest']]:
        if sha(item['path']) != item['sha256']: raise ValueError('input changed during comparison')
    source=begin_data['source']
    def git(*args): return subprocess.check_output(['git','-C',source['path'],*args], text=True).strip()
    if git('rev-parse','HEAD') != source['head'] or git('rev-parse','HEAD^{tree}') != source['tree'] or git('status','--porcelain','--untracked-files=all'):
        raise ValueError('source changed during comparison')
    i=begin_data['inputs']; result=Path(begin_data['result'])
    if not begin_data['synthetic'] and checked(capture_script) != i['set_extractor']:
        raise ValueError('extractor differs from pre-comparison capture')
    # This process is supervised by the build's deadline/STOP/process-group guard.
    import importlib.util
    spec=importlib.util.spec_from_file_location('r18_symbol_sets', capture_script)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    window_check()
    manifest=mod.capture(i['comparator']['path'], result, rc, i['anchor_cpu']['path'], i['candidate_cpu']['path'],
                         i['anchor_hip']['path'], i['candidate_hip']['path'], out/'sets')
    window_check()
    for item in list(begin_data['inputs'].values()) + list(begin_data['dependencies'].values()) + [begin_data['dependency_manifest']]:
        if sha(item['path']) != item['sha256']: raise ValueError('input changed during capture')
    if git('rev-parse','HEAD') != source['head'] or git('rev-parse','HEAD^{tree}') != source['tree'] or git('status','--porcelain','--untracked-files=all'):
        raise ValueError('source changed during capture')
    atomic(out/'prepared.json', {'result_sha256': sha(result), 'sets_manifest_sha256': sha(out/'sets/manifest.json'),
                                 'verdict': rc == 0, 'returncode': rc, 'capture_script': checked(capture_script)})
    return manifest


def finalize(out, result, outcome):
    """Publish only after the parent has recorded a successful, drained run."""
    out, result, outcome = map(Path, (out, result, outcome))
    window_check()
    data = json.loads(result.read_text())
    parent = json.loads(outcome.read_text())
    detail = json.loads((out/'prepared.json').read_text())
    rc = detail['returncode']
    if (data.get('partial') is not False or data.get('exit_code') != rc
            or parent.get('exit_code') != rc or parent.get('partial') is not False
            or data.get('reason') not in ('independent_cpu_hip_symbol_identity_pass',
                                          'independent_cpu_hip_symbol_identity_valid_negative')):
        raise ValueError('parent run did not finish successfully')
    detail.update(full_result={'path': str(result.resolve()), 'sha256': sha(result)},
                  parent_outcome={'path': str(outcome.resolve()), 'sha256': sha(outcome)})
    window_check()
    terminal(out, 'complete', detail)
