"""Hosted-only setup: verify frozen source and unpack four known NLTK archives."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import zipfile
W = Path(os.environ['GITHUB_WORKSPACE'])
R = W / 'recipe/proposed/cj567'
M = json.loads((R / 'source-map.json').read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()
for name, pin in {**M['repositories'], 'enrollment': M['enrollment']}.items():
    actual = subprocess.check_output(['git', '-C', str(W/name), 'rev-parse', 'HEAD']).decode().strip()
    if actual != pin: raise RuntimeError('repository boundary differs '+name)
if sha((W/'official/uv.lock').read_bytes()) != M['official_uv_lock_sha256']: raise RuntimeError('official lock differs')
for row in M['source_payloads']:
    if sha((W/'recipe'/row['path']).read_bytes()) != row['sha256']: raise RuntimeError('six source payload differs')
for repo, rows in [('app', M['app_python_envelope']), ('research', M['research_sources'])]:
    for row in rows:
        b = (W/repo/row['path']).read_bytes()
        blob = hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        if blob != row['blob']: raise RuntimeError('pinned source blob differs '+row['path'])
lock = json.loads((R/'nltk-seed-lock.json').read_bytes())
seed = W/'official/ifbench/.nltk_data'
seed.mkdir(exist_ok=False)
for row in lock['archives']:
    path = W/'nltk'/row['path']
    if sha(path.read_bytes()) != row['sha256']: raise RuntimeError('seed archive differs')
    parent = seed / Path(row['path']).parts[1]
    parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(path) as z:
        names = set()
        for item in z.infolist():
            p = PurePosixPath(item.filename)
            if p.is_absolute() or '..' in p.parts or item.filename in names or '\\' in item.filename or ((item.external_attr>>16)&0o170000)==0o120000: raise RuntimeError('unsafe seed archive')
            names.add(item.filename)
        if z.testzip() is not None: raise RuntimeError('seed CRC differs')
        z.extractall(parent)
for rel, row in lock['seed_files'].items():
    p = seed/rel
    if p.is_symlink() or not p.is_file() or sha(p.read_bytes()) != row['sha256']: raise RuntimeError('seed file differs '+rel)
fixture = Path(os.environ['RUNNER_TEMP'])/'cj567-fixture'
fixture.mkdir()
for row in M['source_payloads']:
    shutil.copy2(W/'recipe'/row['path'], fixture/Path(row['path']).name)
shutil.copy2(R/'test_official_oracles.py', fixture/'test_official_oracles.py')
shutil.copy2(W/'research/scripts/benchmark/code_exec_scorer.py', fixture/'code_exec_scorer.py')
