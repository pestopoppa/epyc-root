#!/usr/bin/env python3
"""Owner-granted build/capture bodies. DRY mode never assembles, builds or loads a model."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
BASE = Path(__file__).resolve().parent
FLAGS = Path('/mnt/raid0/llm/tmp/compute-flags')

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''): h.update(block)
    return h.hexdigest()

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
def write(path, obj): path.write_text(json.dumps(obj, sort_keys=True, indent=2) + '\n')
def hold():
    if list(FLAGS.rglob('HOLD_*')) or list(Path('/mnt/raid0/llm/tmp').glob('HOLD_*')) or (BASE / 'STOP').exists():
        raise ValueError('HOLD/STOP')

def guard():
    hold()
    ident = os.environ.get('FILLER_ID', '')
    if ident not in ('kpf62-yarn-selfcheck-20261027', 'kpf62-yarn-selfcheck-20261027'):
        raise ValueError('actual official filler identity required')
    if os.environ.get('FILLER_STOPFILE') != str(BASE / 'STOP'):
        raise ValueError('wrong owner STOP')
    p = FLAGS / 'grants' / (ident + '.grant')
    if not p.is_file() or p.is_symlink(): raise ValueError('canonical grant missing')
    fields = dict(piece.split('=', 1) for piece in p.read_text().strip().split())
    if set(fields) != {'regions', 'start', 'end'}: raise ValueError('grant syntax')
    current = now()
    if not datetime.fromisoformat(fields['start'].replace('Z','+00:00')) <= datetime.now(timezone.utc) <= datetime.fromisoformat(fields['end'].replace('Z','+00:00')): raise ValueError('grant not live')
    if int(datetime.now(timezone.utc).timestamp()) >= int(os.environ['FILLER_DEADLINE']):
        raise ValueError('no new work after filler deadline')
    if set(os.sched_getaffinity(0)) != expand(os.environ['FILLER_CPUS']):
        raise ValueError('actual affinity differs from official literal CPU list')
    tokens = fields['regions'].replace(';', ',').split(',')
    numeric = [t for t in tokens if t and t[0].isdigit()]
    quarters = [t for t in tokens if t in ('q0','q1','q2','q3')]
    if len(numeric) + len(quarters) != len(tokens): raise ValueError('unexpected non-CPU grant region')
    declared = expand(','.join(numeric)) if numeric else set()
    if not numeric:
        for q in quarters:
            first = int(q[1]) * 24
            declared.update(range(first, first + 24))
            declared.update(range(first + 96, first + 112))
    if declared != set(os.sched_getaffinity(0)): raise ValueError('canonical grant/actual CPU shape mismatch')
    if len({c % 96 for c in declared}) != 24 or len({(c % 96) // 24 for c in declared}) != 1:
        raise ValueError('this row is predeclared for one CPU quarter')
    threads = int(os.environ['FILLER_THREADS'])
    if threads < 1 or threads > len({x % 96 for x in os.sched_getaffinity(0)}): raise ValueError('thread cap')
    # The claimed official region-lock launcher must be OUR ancestor.
    parent, found = os.getppid(), False
    while parent > 1:
        cmd = Path(f'/proc/{parent}/cmdline').read_bytes().replace(b'\0', b' ')
        if b'src.runtime.region_lock_cli run --cpu-list ' in cmd and b' --role build ' in cmd:
            found = True
        status = Path(f'/proc/{parent}/status').read_text()
        parent = int(next(line.split()[1] for line in status.splitlines() if line.startswith('PPid:')))
    if not found: raise ValueError('official ancestor claim missing')
    return {'grant_id': ident, 'path': str(p), 'sha256': sha(p), 'regions': fields['regions'],
            'start_utc': fields['start'], 'end_utc': fields['end']}, threads

def expand(s):
    out = set()
    for part in s.split(','):
        a, _, b = part.partition('-')
        out.update(range(int(a), int(b or a) + 1))
    return out

def run(argv, log, env=None, expected=0):
    guard()
    started = now()
    with log.open('wb') as stdout, log.with_suffix('.stderr').open('wb') as stderr:
        child = subprocess.Popen([str(x) for x in argv], stdout=stdout, stderr=stderr, env=env)
        rc = child.wait()
    # All compute subprocesses remain in the launcher's captured session/group.
    # Never use setsid or detached children here. Official launcher owns hard timeout.
    result = {'argv': [str(x) for x in argv], 'pid': child.pid, 'started_at_utc': started,
              'finished_at_utc': now(), 'exit_code': rc, 'child_drained': child.poll() is not None,
              'stdout': {'path': str(log), 'sha256': sha(log)},
              'stderr': {'path': str(log.with_suffix('.stderr')), 'sha256': sha(log.with_suffix('.stderr'))}}
    write(log.with_suffix('.receipt.json'), result)
    if rc != expected: raise ValueError(f'child exit {rc}, expected {expected}: {argv[0]}')
    return result

def validate(lines):
    import re, math
    context = re.search(r'^freq_scale=([^ ]+) yarn_ext_factor=([^ ]+) yarn_attn_factor=([^ ]+) ggml_mscale=([^\n]+)$', lines, re.M)
    if not context: raise ValueError('missing context parameters')
    values = list(map(float, context.groups()))
    if any(not math.isfinite(v) for v in values) or abs(values[0]-.25)>1e-6 or abs(values[1]-1)>1e-6 or abs(values[2]-1.25)>1e-5 or values[3] <= 1.1:
        raise ValueError('wrong actual context')
    records = re.findall(r'^delta=(\d+) selfcheck=(\d+) nmse=([^\n]+)$', lines, re.M)
    if len(records)!=4 or {int(r[0]) for r in records}!={1,17,300,4096}: raise ValueError('delta coverage')
    results = []
    for delta, passed, raw in records:
        value=float(raw)
        if passed!='1' or not math.isfinite(value) or not 0<=value<=1e-6: raise ValueError('selfcheck threshold')
        results.append({'delta':int(delta),'nmse':value})
    if not re.search(r'^invalid_delta_refused=1$',lines,re.M): raise ValueError('invalid delta control')
    return {'context': values, 'results': results}

def capture():
    grant, threads=guard()
    subprocess.run(['sha256sum','--quiet','-c',str(BASE/'SOURCE.sha256')],check=True)
    fixed=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-fixed-build')
    if sha(fixed/'build-receipt.json') != '6cddb24429ce2a590f83a0303d88719ee2183b5c036ee4ac861d42f1a883fdca': raise ValueError('accepted receipt drift')
    receipt=json.loads((fixed/'build-receipt.json').read_text())
    for name,digest in receipt['files'].items():
        if sha(name)!=digest: raise ValueError('accepted build drift')
    out=BASE/('native-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    out.mkdir()
    env={k:os.environ[k] for k in ('PATH','HOME','TMPDIR','LANG','TZ') if k in os.environ}
    env.update(LD_LIBRARY_PATH=str(fixed/'build/bin'), OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', LD_DEBUG='libs')
    generator=fixed/'build/bin/test-llama-archs'
    generated=out/'qwen3-dense.gguf'; yarn=out/'qwen3-yarn.gguf'
    run([generator,'-a','qwen3','-s','1234','-o',out],out/'generate.log',env)
    run([sys.executable,'-B',BASE/'make_fixture.py',generated,yarn],out/'fixture.log',env)
    run([BASE/'context_probe',yarn],out/'selfcheck.log',env)
    result=validate((out/'selfcheck.log').read_text())
    artifacts={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}
    write(out/'capture.json',{'schema':'epyc.kpf62.yarn-selfcheck.v1','protocol':'unknown','classification':'observation','grant':grant,'cpus':os.environ['FILLER_CPUS'],'threads':threads,'result':result,'model_sha256':sha(yarn),'helper_sha256':sha(BASE/'context_probe'),'source_sha256':sha(BASE/'context_probe.cpp'),'accepted_build_receipt_sha256':sha(fixed/'build-receipt.json'),'artifacts':artifacts,'captured_at_utc':now()})
    write(BASE/'CAPTURE-DONE.json',{'path':str(out/'capture.json'),'sha256':sha(out/'capture.json'),'finished_at_utc':now()})

if __name__ == '__main__':
    try: capture()
    except Exception as exc:
        print('CAPTURE REFUSED/FAILED:',exc,file=sys.stderr)
        sys.exit(70)
