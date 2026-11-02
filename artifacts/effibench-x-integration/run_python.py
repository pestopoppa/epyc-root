#!/usr/bin/env python3
"""Guarded preparation wrapper; a caller's content manifest is not provenance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
COMMIT = '21b6668a49a342c843e679cc5ed16081064a5768'
PATCH_DIGEST = 'b87733644b59545737a3a50ce0a5350265a0b80680fd21cb8a09ee6fce6c6534'
EXCLUDED = {'leetcode_3264_maximum-points-after-enemy-battles', 'leetcode_3451_string-compression-iii'}


def load(path):
    return json.loads(path.read_text())


def check(tree, dataset, manifest):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tree), *args])
    if git('rev-parse', 'HEAD').decode().strip() != COMMIT:
        raise ValueError('wrong upstream commit')
    if hashlib.sha256(git('diff', '--no-ext-diff', 'HEAD')).hexdigest() != PATCH_DIGEST:
        raise ValueError('upstream tracked changes do not match the accepted patches')
    extras = git('ls-files', '--others', '--exclude-standard', '-z')
    ignored = git('ls-files', '--others', '--ignored', '--exclude-standard', '-z')
    if extras or ignored:
        raise ValueError('upstream checkout contains untracked or ignored files; use a clean checkout')
    expected = set(load(HERE / 'dated-308.json')) - EXCLUDED
    files = {p.name: p for p in dataset.glob('*.json')}
    if len(expected) != 306 or set(files) != {name + '.json' for name in expected}:
        raise ValueError('dataset is not the 306-item cohort')
    pins = load(manifest)
    if not isinstance(pins, dict) or set(pins) != set(files):
        raise ValueError('content manifest does not cover the cohort exactly')
    for name, path in files.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != pins[name]:
            raise ValueError(f'dataset content mismatch: {name}')
    return expected


def generated(solutions, model, expected):
    directory = solutions / model
    wanted = {name + '_python3.json' for name in expected}
    if not directory.is_dir() or {p.name for p in directory.glob('*.json')} != wanted:
        raise ValueError('generation incomplete or unexpected outputs')
    for filename in wanted:
        row = load(directory / filename)
        if not isinstance(row, dict) or not isinstance(row.get('raw'), str) or ('code' not in row) or not (row['code'] is None or isinstance(row['code'], str)):
            raise ValueError(f'invalid generated response: {filename}')


def merged(solutions, model, expected):
    data = load(solutions / f'{model}.json')
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError('merged solution denominator mismatch')
    for name, row in data.items():
        if not isinstance(row, dict) or set(row) != {'python3'} or not (row['python3'] is None or isinstance(row['python3'], str)):
            raise ValueError(f'invalid merged solution: {name}')
    return {name for name, row in data.items() if row['python3'] is not None}


def evaluation(dataset, output, model, expected, attempted):
    if not attempted:
        raise ValueError('zero non-null solutions: no evaluations to execute')
    directory = output / model
    wanted = {name + '_python3.json' for name in attempted}
    if not directory.is_dir() or {p.name for p in directory.glob('*.json')} != wanted:
        raise ValueError('evaluation output denominator mismatch')
    for name in attempted:
        tests = load(dataset / f'{name}.json')['generated_tests']
        if isinstance(tests, str):
            tests = json.loads(tests)
        results = load(directory / f'{name}_python3.json')
        if not isinstance(tests, list) or not tests or not isinstance(results, list) or len(results) != len(tests) or not all(isinstance(r, dict) and isinstance(r.get('passed'), bool) for r in results):
            raise ValueError(f'incomplete or malformed test results: {name}')
    print(f'Validated {len(attempted)} evaluated and {len(expected)-len(attempted)} null-code cases of {len(expected)}; no score calculated.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['check', 'generate', 'merge', 'evaluate'])
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--content-manifest', type=Path, required=True, help='filename-to-SHA256 mapping; consistency only, not source provenance')
    p.add_argument('--solutions', type=Path)
    p.add_argument('--evaluation', type=Path)
    p.add_argument('--model')
    a = p.parse_args()
    tree, dataset = a.upstream.resolve(), a.dataset.resolve()
    expected = check(tree, dataset, a.content_manifest)
    if a.stage == 'check':
        print('Verified tracked patch and dataset against supplied hashes; provenance not established.')
        return
    if not a.solutions or not a.model or not re.fullmatch(r'[A-Za-z0-9_.-]+', a.model) or a.model in {'.', '..'}:
        p.error('stage requires --solutions and a safe single-component --model')
    solutions = a.solutions.resolve()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    gen = str(tree / 'generate_solution.py')
    if a.stage == 'generate':
        if solutions.exists():
            raise ValueError('generation requires a new solutions directory to prevent stale outputs')
        subprocess.run([sys.executable, gen, 'generate', str(dataset), str(solutions), '--model', a.model, '--langs', 'python3'], cwd=tree, check=True, env=env)
        generated(solutions, a.model, expected)
    elif a.stage == 'merge':
        generated(solutions, a.model, expected)
        if (solutions / f'{a.model}.json').exists():
            raise ValueError('merged output already exists')
        subprocess.run([sys.executable, gen, 'merge', str(dataset), str(solutions), '--model', a.model, '--langs', 'python3'], cwd=tree, check=True, env=env)
        merged(solutions, a.model, expected)
    else:
        if not a.evaluation:
            p.error('evaluate requires --evaluation')
        out = a.evaluation.resolve()
        if out.exists():
            raise ValueError('evaluation requires a new output directory to prevent stale outputs')
        attempted = merged(solutions, a.model, expected)
        if not attempted:
            raise ValueError('zero non-null solutions: no evaluations to execute')
        subprocess.run([sys.executable, str(tree / 'evaluate_solution.py'), 'evaluate', str(dataset), str(solutions), '--output-dir', str(out), '--model', a.model, '--langs', 'python3'], cwd=tree, check=True, env=env)
        evaluation(dataset, out, a.model, expected, attempted)


if __name__ == '__main__':
    main()
