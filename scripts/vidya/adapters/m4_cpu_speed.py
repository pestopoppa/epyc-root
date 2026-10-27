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
from dataclasses import dataclass
from claim_tuple import ClaimTuple, ProjectionError, register, to_frames

SOURCE_KIND = 'm4-cpu-recipe-speed-measurement'
ADAPTER_ID = 'vidya.adapters.m4_cpu_speed/v1'
AUTHORITY = 'measurement'
SCHEMA = 'epyc.m4.recipe_to_recipe_cpu_speed.v1'
@dataclass(frozen=True)
class SourceConfig:
    capture_root: Path
    producer_root: Path

    def __post_init__(self):
        for field in ("capture_root", "producer_root"):
            path = getattr(self, field)
            if not isinstance(path, Path) or not path.is_absolute() or path.resolve() != path:
                raise ProjectionError(f"{field} must be an absolute canonical Path")



def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _native_rows(path: str | Path, config: SourceConfig) -> tuple[dict, ...]:
    if not isinstance(config, SourceConfig):
        raise ProjectionError('explicit source configuration required')
    p = Path(path).resolve()
    if config.capture_root not in p.parents or p.suffix != '.json' or p.parent.name != 'process-captures':
        raise ProjectionError('capture outside permitted root')
    try:
        document = json.loads(p.read_bytes())
    except (OSError, ValueError) as exc:
        raise ProjectionError(f'cannot read capture: {exc}') from exc
    row = document.get('measurement')
    if document.get('schema') != 'epyc.m4.cpu_speed_process.v1' or not isinstance(row, dict):
        raise ProjectionError('wrong capture schema')
    return ({'row':row, 'receipt':str(p), 'role':row.get('role'), 'model':row.get('model_path'), 'recipe':row.get('recipe')},)


def _project(native: Any, config: SourceConfig) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get('row'), dict):
        raise ProjectionError('missing producer row')
    row = native['row']
    if native not in _native_rows(native.get('receipt', ''), config):
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
    if config.capture_root not in locator.parents or locator.name != 'summary.json':
        raise ProjectionError('summary path outside producer tree')
    try:
        raw = locator.read_bytes(); summary = json.loads(raw)
        plan_raw = (locator.parent / 'plan.json').read_bytes(); plan = json.loads(plan_raw)
    except (OSError, ValueError) as exc:
        raise ProjectionError(f'cannot re-read native process: {exc}') from exc
    if _sha(raw) != row.get('attestation_sha256') or summary.get('status') != 'ok':
        raise ProjectionError('summary digest or status mismatch')
    results = summary.get('results')
    extra = row.get('extra', {})
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        raise ProjectionError('not one fresh-server process')
    sample = results[0]
    if _sha(plan_raw) != extra.get('plan_sha256'):
        raise ProjectionError('plan digest mismatch')
    for key, path in (('producer_sha256',config.producer_root/'dispatch.py'),('capture_sha256',config.producer_root/'capture.py'),('native_runner_sha256',config.producer_root/'native/k35_stack_context_matrix_runner.py'),('native_comparator_sha256',config.producer_root/'native/compare_v9_promotion_arms.py')):
        try:
            if _sha(path.read_bytes()) != extra.get(key): raise ProjectionError(f'{key} changed')
        except OSError as exc:
            raise ProjectionError(f'{key} unavailable: {exc}') from exc
    try:
        prompt_path=Path(sample['prompt_path']).resolve(); prompt_hash_path=Path(sample['prompt_sha256_path']).resolve()
        if config.capture_root not in prompt_path.parents or config.capture_root not in prompt_hash_path.parents:
            raise ProjectionError('prompt proof outside producer tree')
        if _sha(prompt_path.read_bytes()) != prompt_hash_path.read_text().strip() or _sha(prompt_path.read_bytes()) != extra.get('prompt_sha256'):
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


# Trusted deployment configuration is code-owned, never supplied by a native record.
# This prospective campaign packet remains unarmed; change requires source review.
PRODUCER_ROOT = Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-full-gate-next-source/cpu-packet')
CAPTURE_ROOT = PRODUCER_ROOT / 'output'
SOURCE_SEALS = {
    'dispatch.py': '5dd57151c293c794cd32d108129f784ff3863179a27f81e522705ce6665b67c1',
    'capture.py': '701168d58ef67bdc1e130cff9a0fa0f8576516df9fe743bcdaf0794501965479',
    'native/k35_stack_context_matrix_runner.py': '79a5744f60f980e2eb99727890e199de45d076549820ca1f14347570987d34f5',
    'native/compare_v9_promotion_arms.py': '83e1ea40499cbca531849af454209d45011b55bc2684c841a09068a15c3fd94e',
}

def _trusted_config():
    for name, digest in SOURCE_SEALS.items():
        try:
            if _sha((PRODUCER_ROOT / name).read_bytes()) != digest:
                raise ProjectionError(f'producer seal changed: {name}')
        except OSError as exc:
            raise ProjectionError(f'producer unavailable: {name}') from exc
    return SourceConfig(CAPTURE_ROOT, PRODUCER_ROOT)

def native_rows(path: str | Path) -> tuple[dict, ...]:
    return _native_rows(path, _trusted_config())

@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    return _project(native, _trusted_config())

def frames_for_record(path: str | Path, *, as_of: str) -> list[dict]:
    return [frame for native in native_rows(path) for frame in to_frames(
        project(native), as_of=as_of, adapter_id=SOURCE_KIND, authority='measurement')]
