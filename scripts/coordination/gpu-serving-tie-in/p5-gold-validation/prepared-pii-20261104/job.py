#!/usr/bin/env python3
"""Run real staged-blob controls; derive completion only from actual JUnit."""
import hashlib
import json
import importlib.metadata
import sys
import os
from pathlib import Path
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

D = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify():
    pins = json.loads((D / 'pins.json').read_text())
    for path, digest in pins['sources'].items():
        if sha(path) != digest:
            raise RuntimeError('sealed source mismatch')
    return pins

def main():
    for name in ('RESULT.json', 'INCOMPLETE.json', 'junit.xml'):
        (D / name).unlink(missing_ok=True)
    started = time.time()
    result = {'schema': 'p5.candidate-pii-controls.v1', 'status': 'INCOMPLETE'}
    base = D / 'pytest-tmp'
    try:
        pins = verify()
        result['python_version'] = sys.version
        result['python_executable'] = sys.executable
        result['pytest_version'] = importlib.metadata.version('pytest')
        result['sources'] = pins['sources']
        result['pins_sha256'] = sha(D / 'pins.json')
        result['launcher_sha256'] = sha(D / 'launch.sh')
        result['source_manifest_sha256'] = sha(D / 'SOURCE.sha256')
        cpus = os.environ['FILLER_CPUS']
        # Parse exact granted CPUs, enforce this instrument's four-CPU budget.
        granted = set()
        for group in cpus.split(','):
            endpoints = group.split('-')
            a, b = (int(endpoints[0]), int(endpoints[-1]))
            granted.update(range(a, b + 1))
        if len(granted) != 4 or not granted <= os.sched_getaffinity(0):
            raise RuntimeError('requires exactly four granted CPUs')
        ttl = min(270, int(float(os.environ['FILLER_DEADLINE']) - time.time()) - 10)
        if ttl < 30:
            raise RuntimeError('insufficient execution window')
        # Never clear an earlier run's leftover repository and claim cleanup.
        if base.exists() and any(base.iterdir()):
            raise RuntimeError('pytest basetemp must be empty before run')
        tmp = D / 'control-tmp'
        tmp.mkdir(exist_ok=True)
        env = dict(os.environ, TMPDIR=str(tmp), PYTHONDONTWRITEBYTECODE='1',
                   PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
        for key in ('GIT_INDEX_FILE', 'GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR',
                    'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                    'PYTEST_ADDOPTS', 'PYTEST_PLUGINS'):
            env.pop(key, None)
        with (D / 'pytest.log').open('wb') as log:
            proc = subprocess.run(['taskset', '-c', cpus, '/usr/bin/python3', '-B',
                '-m', 'pytest', '-q', '--tb=no', '-p', 'no:cacheprovider',
                '-o', 'addopts=', pins['test_path'],
                '--confcutdir', str(Path(pins['test_path']).parent),
                '--basetemp', str(base), '--junitxml', str(D / 'junit.xml')],
                env=env, stdout=log, stderr=subprocess.STDOUT, timeout=ttl)
        result['pytest_exit'] = proc.returncode
        junit = ET.parse(D / 'junit.xml').getroot()
        cases = junit.findall('.//testcase')
        suites = junit.findall('.//testsuite')
        counts = {key: sum(int(s.attrib.get(key, '0')) for s in suites)
                  for key in ('tests', 'failures', 'errors', 'skipped')}
        result['junit_counts'] = counts
        result['testcases'] = len(cases)
        result['junit_sha256'] = sha(D / 'junit.xml')
        verify()
        result['sources_verified_pre_post'] = True
        leftovers = list(base.rglob('.git')) if base.exists() else []
        leftovers += list(tmp.rglob('.git'))
        result['test_repositories_removed'] = not leftovers
        if (proc.returncode != 0 or counts != {'tests': 7, 'failures': 0, 'errors': 0, 'skipped': 0}
                or len(cases) != 7 or any(c.find(x) is not None for c in cases
                for x in ('failure', 'error', 'skipped')) or leftovers):
            raise RuntimeError('strict actual-test completion predicate failed')
        if base.exists():
            shutil.rmtree(base)
        result['status'] = 'COMPLETE'
    except BaseException as exc:
        # No source text, account values or captured pytest output in JSON.
        result['error_type'] = type(exc).__name__
    result['elapsed_s'] = time.time() - started
    output = 'RESULT.json' if result['status'] == 'COMPLETE' else 'INCOMPLETE.json'
    (D / output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return 0 if result['status'] == 'COMPLETE' else 1

if __name__ == '__main__':
    raise SystemExit(main())
