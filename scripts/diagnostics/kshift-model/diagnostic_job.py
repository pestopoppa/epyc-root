"""Bounded Qwen f16 diagnostic; model execution belongs to the keeper grant."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

D = Path(sys.argv[1])
THREADS = 24
SMOKE = os.environ.get('FILLER_SMOKE') == '1' or os.environ.get('FILLER_DRYRUN') == '1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    pins = json.loads((D / 'pins.json').read_text())
    for path, digest in pins['files'].items():
        if sha(path) != digest:
            raise RuntimeError('input changed: ' + path)
    out = D / ('smoke' if SMOKE else 'out')
    out.mkdir(exist_ok=True)
    binary = out / 'test-kshift-diagnostic'
    includes = pins['include']
    argv = ['g++-15', '-std=c++17', '-O2', '-I' + includes[0], '-I' + includes[1], '-I' + str(D),
            str(D / 'test.cpp'), '-L' + pins['libs']['cand'], '-Wl,-rpath-link,' + pins['libs']['cand'], '-lllama', '-o', str(binary)]
    subprocess.run(argv, check=True)
    if SMOKE:
        # No model inference or tokenization in the dry run.
        (out / 'PASS.json').write_text(json.dumps({'ok': True, 'binary_sha256': sha(binary), 'inputs_pinned': len(pins['files'])}))
        return
    cpus = sorted(os.sched_getaffinity(0))
    if len({c % 96 for c in cpus}) != THREADS:
        raise RuntimeError('requires exactly 24 physical cores')
    records = []
    for label, libdir in pins['libs'].items():
        # The one diagnostic pair is indivisible; no retries or interim qualification.
        if os.path.exists(os.environ.get('FILLER_STOPFILE', str(D / 'STOP'))):
            return 75
        env = dict(os.environ, FILLER_ID=os.environ.get('FILLER_ID', 'kshift-diagnostic-20261120'), LD_LIBRARY_PATH=libdir, HIP_VISIBLE_DEVICES='-1', ROCR_VISIBLE_DEVICES='-1',
                   GGML_IQK='1', GGML_NOHUGEPAGE_PROCESS='1')
        cmd = [str(binary), '-m', pins['model'], '--corpus', str(D / 'corpus.txt'), '-t', '24']
        with (out / (label + '.stdout')).open('w') as fo, (out / (label + '.stderr')).open('w') as fe:
            subprocess.run(cmd, env=env, stdout=fo, stderr=fe, check=True, timeout=300)
        rows = [json.loads(line) for line in (out / (label + '.stdout')).read_text().splitlines() if line.startswith('{')]
        meta = next(r for r in rows if r['scenario'] == 'meta')
        mapped = [p for p in meta['libs'].split(';') if 'libllama' in p or 'libggml-cpu' in p]
        if len(mapped) < 2 or any(Path(p).resolve().parent != Path(libdir).resolve() for p in mapped):
            raise RuntimeError('mapped library proof failed')
        if rows[-1]['scenario'] != 'done':
            raise RuntimeError('missing done')
        comparisons = {}
        for r in rows:
            if r['scenario'] == 'position':
                comparisons.setdefault(r['comparison'], []).append(r)
        summary = {}
        for name, positions in comparisons.items():
            if len(positions) != 64 or [r['index'] for r in positions] != list(range(64)):
                raise RuntimeError('incomplete position records')
            summary[name] = {'first8_kld': sum(r['kld'] for r in positions[:8]) / 8,
                             'last8_kld': sum(r['kld'] for r in positions[-8:]) / 8,
                             'mismatches': [r for r in positions if r['ref_top1'] != r['test_top1']]}
        record = {'unit_id': label, 'ok': True, 'meta': meta, 'details': summary,
                  'aggregates': [r for r in rows if r['scenario'] not in ('position', 'meta', 'done')],
                  'stdout_sha256': sha(out / (label + '.stdout')), 'binary_sha256': sha(binary)}
        records.append(record)
        with (out / 'results.jsonl').open('a') as f:
            f.write(json.dumps(record) + '\n')
    (out / 'RESULT.json').write_text(json.dumps({'complete': True, 'verdict': 'DIAGNOSTIC_COMPLETE',
        'units': len(records), 'question': pins['question'], 'qualification': False}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
