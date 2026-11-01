#!/usr/bin/env python3
"""Model-free proof that normal and cutoff cannot overwrite one another."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


with tempfile.TemporaryDirectory(prefix='df2-qual-isolation-', dir=ROOT) as tmp:
    base = pathlib.Path(tmp)
    results = base / 'results'
    results.mkdir()
    env = dict(os.environ, FILLER_ID='df2-model-free-isolation',
               WS58_QUAL_NONCE='model-free-isolation', WS58_QUAL='1',
               FILLER_DEADLINE=str(time.time()), PYTHONDONTWRITEBYTECODE='1')
    for phase, expected in (('normal', 0), ('cutoff', 75)):
        isolated = results / phase
        isolated.mkdir()
        env.update(FILLER_QUAL_PHASE=phase, FILLER_RESULTS_DIR=str(isolated),
                   WS58_QUAL_PROOF=str(base / ('proof-' + phase + '.json')))
        run = subprocess.run([sys.executable, str(ROOT / 'qual_fixture.py'),
                              '--mode', 'model-free', '--n-ctx-required', '32768'],
                             env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, timeout=15)
        if run.returncode != expected:
            raise RuntimeError(f'{phase} fixture rc {run.returncode} != {expected}: {run.stdout}')
        if phase == 'normal':
            normal_result = isolated / 'QUAL-RESULT.json'
            normal_sha = sha(normal_result)
            normal_proof = json.loads((base / 'proof-normal.json').read_text())
            if normal_proof['result_writer']['sha256'] != normal_sha:
                raise RuntimeError('normal producer proof not bound to its result')
    if sha(normal_result) != normal_sha or normal_proof['result_writer']['result_path'] != str(normal_result):
        raise RuntimeError('cutoff phase rewrote normal producer result')
    if not (results / 'cutoff/PARTIAL.json').exists():
        raise RuntimeError('cutoff partial result absent')
    print('normal producer SHA remains bound after cutoff; MODEL_FREE only')
