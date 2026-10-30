"""Draft strict projection for producer-authored M4 recipe speed samples.

Not registered in production: owner reviews integration and source table before use.
No protocol or grade is invented; `claim_tuple.grade` remains the sole grader.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from typing import Any
from claim_tuple import ClaimTuple, ProjectionError, register

SOURCE_KIND = 'm4-cpu-recipe-speed-measurement'
SCHEMA = 'epyc.m4.recipe_to_recipe_cpu_speed.v1'
ROOT = Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-fold-gates/speed-generic').resolve()


def units(path: str | Path) -> list[Path]:
    p = Path(path)
    if p.is_file(): return [p]
    return sorted(p.rglob('throughput.json')) if p.is_dir() else []


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def native_rows(path: str | Path) -> tuple[dict, ...]:
    p = Path(path).resolve()
    if ROOT not in p.parents or p.name != 'throughput.json':
        raise ProjectionError('receipt outside permitted scratch producer tree')
    try:
        document = json.loads(p.read_bytes())
    except (OSError, ValueError) as exc:
        raise ProjectionError(f'cannot read receipt: {exc}') from exc
    if document.get('schema') != SCHEMA or document.get('quality_gate') != 'separate':
        raise ProjectionError('wrong producer schema')
    rows = document.get('belief_measurements')
    if not isinstance(rows, list) or len(rows) != 10:
        raise ProjectionError('need 5 process measurements per arm')
    if sorted(row.get('category') for row in rows if isinstance(row, dict)) != ['BASELINE'] * 5 + ['CANDIDATE'] * 5:
        raise ProjectionError('arm coverage')
    if len({r.get('measurement_id') for r in rows}) != 10:
        raise ProjectionError('duplicate measurement id')
    return tuple({'row': row, 'receipt': str(p), 'role':document['role'], 'model': document['model_path'], 'recipe': document[row['category'].lower() + '_recipe']} for row in rows)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get('row'), dict):
        raise ProjectionError('missing producer row')
    row = native['row']
    if native not in native_rows(native.get('receipt', '')):
        raise ProjectionError('row not present in producer receipt')
    unsigned = dict(row); recorded = unsigned.pop('measurement_sha256', '')
    if recorded != _sha(_canonical(unsigned)):
        raise ProjectionError('producer row hash mismatch')
    value = row.get('value')
    if (row.get('metric') != 'decode_tokens_per_s' or type(value) not in (int,float) or not math.isfinite(value) or value <= 0
            or row.get('unit') != 'tokens_per_second' or row.get('metric_direction') != 'higher_better'
            or row.get('protocol_id') != '' or row.get('reps') != 1 or row.get('category') not in ('BASELINE','CANDIDATE')):
        raise ProjectionError('invalid native measurement')
    if row.get('role') != native.get('role') or row.get('model_path') != native.get('model') or row.get('recipe') != native.get('recipe'):
        raise ProjectionError('producer scope drift')
    locator = Path(row.get('attestation_locator', '')).resolve()
    if ROOT not in locator.parents or locator.name != 'summary.json':
        raise ProjectionError('summary path outside producer tree')
    try:
        raw = locator.read_bytes(); summary = json.loads(raw)
        plan = json.loads((locator.parent / 'plan.json').read_bytes())
    except (OSError, ValueError) as exc:
        raise ProjectionError(f'cannot re-read native process: {exc}') from exc
    if _sha(raw) != row.get('attestation_sha256') or summary.get('status') != 'ok':
        raise ProjectionError('summary digest or status mismatch')
    results = summary.get('results')
    extra = row.get('extra', {})
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        raise ProjectionError('not one fresh-server process')
    sample = results[0]
    for key, path in (('producer_sha256',ROOT/'dispatch.py'),('native_runner_sha256',ROOT/'native/k35_stack_context_matrix_runner.py'),('native_comparator_sha256',ROOT/'native/compare_v9_promotion_arms.py')):
        try:
            if _sha(path.read_bytes()) != extra.get(key): raise ProjectionError(f'{key} changed')
        except OSError as exc:
            raise ProjectionError(f'{key} unavailable: {exc}') from exc
    try:
        prompt_path=Path(sample['prompt_path']).resolve(); prompt_hash_path=Path(sample['prompt_sha256_path']).resolve()
        if ROOT not in prompt_path.parents or ROOT not in prompt_hash_path.parents:
            raise ProjectionError('prompt proof outside producer tree')
        if _sha(prompt_path.read_bytes()) != prompt_hash_path.read_text().strip():
            raise ProjectionError('native prompt digest mismatch')
    except (OSError,KeyError) as exc:
        raise ProjectionError(f'missing native prompt proof: {exc}') from exc
    cells = plan.get('cells')
    if not isinstance(cells,list) or len(cells)!=1 or not isinstance(cells[0],dict):
        raise ProjectionError('not one planned process')
    argv = cells[0].get('server_argv')
    if not isinstance(argv,list) or '-m' not in argv or argv.index('-m')+1>=len(argv) or str(Path(argv[argv.index('-m')+1]).resolve())!=str(Path(native['model']).resolve()):
        raise ProjectionError('planned model does not match captured scope')
    def arg(flag):
        return argv[argv.index(flag)+1] if flag in argv and argv.index(flag)+1<len(argv) else None
    expected_commit='c72ec82f5417bb2937310326120f149b665e8400' if row['category']=='BASELINE' else 'bc441f1a261766d11bfeff21668a1031c4dbf8cd'
    if extra.get('source_commit')!=expected_commit: raise ProjectionError('source commit mismatch')
    if row['category']=='CANDIDATE':
        if arg('--prefill-order')!='srpf' or arg('--prefill-contend-cap')!='512': raise ProjectionError('candidate treatment mismatch')
    elif '--prefill-order' in argv or '--prefill-contend-cap' in argv:
        raise ProjectionError('baseline treatment mismatch')
    if (sample.get('status') != 'ok' or sample.get('passed_min_completion') is not True
            or sample.get('scenario') != extra.get('native_scenario') or sample.get('decode_tps') != value
            or sample.get('nominal_context') != extra.get('context')
            or (sample.get('cleanup') or {}).get('completed') is not True
            or (sample.get('cleanup') or {}).get('dead') is not True
            or str(Path(plan.get('binary', '')).resolve()) != str(Path(extra.get('binary', '')).resolve())):
        raise ProjectionError('native sample, binary or cleanup mismatch')
    return ClaimTuple(measurement_id=row['measurement_id'], metric=row['metric'], value=value,
        date=row['date'], category=row['category'], claim=row['claim'],
        metric_direction='higher_better', protocol_id='', reps=1, reps_basis=row['reps_basis'],
        unit=row['unit'], attestation_path=str(locator), attestation_locator=str(locator),
        attestation_sha256=_sha(raw), attestation_present=True, attestation_verified=True,
        source_kind=SOURCE_KIND, extra={'model':native['model'], 'recipe':native['recipe'], **extra}, observation={})
