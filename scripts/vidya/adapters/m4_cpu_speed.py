"""Draft strict projection for producer-authored M4 recipe speed samples.

Not registered in production: owner reviews integration and source table before use.
No protocol or grade is invented; `claim_tuple.grade` remains the sole grader.
"""
from __future__ import annotations
import hashlib
import base64
import binascii
import json
import math
import os
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
    diagnostic_plan_sha256: str = ""

    def __post_init__(self):
        for field in ("capture_root", "producer_root"):
            path = getattr(self, field)
            if not isinstance(path, Path) or not path.is_absolute() or path.resolve() != path:
                raise ProjectionError(f"{field} must be an absolute canonical Path")



def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _verify_recipe_env(argv: list, environment: dict) -> None:
    if not isinstance(environment, dict) or set(environment) - {'GGML_FA_SPLIT_KV', 'GGML_NOHUGEPAGE_PROCESS', 'GGML_FUSED_DECODE_OFF'}:
        raise ProjectionError('invalid bound recipe environment')
    if not argv or argv[0] != 'env':
        raise ProjectionError('native environment prefix missing')
    allowed = set(environment) | {'GGML_IQK'}
    for token in argv:
        if not isinstance(token, str) or '=' not in token:
            continue
        key = token.split('=', 1)[0]
        if (key.startswith('GGML_') and key not in allowed) or key.startswith('LLAMA_ARG_') or key in {'LD_PRELOAD', 'LD_AUDIT'}:
            raise ProjectionError('unbound native environment override')
    for name, value in environment.items():
        assignments = [x for x in argv if isinstance(x, str) and x.startswith(name + '=')]
        unsets = sum(argv[i:i+2] == ['-u', name] for i in range(len(argv) - 1))
        if value is None:
            if assignments or unsets != 1:
                raise ProjectionError('required environment unset missing')
        elif not isinstance(value, str) or assignments != [name + '=' + value] or unsets:
            raise ProjectionError('recipe environment differs')


def _verify_bound_image_request(sample: dict, scenario: dict, capture_root: Path, prompt: str) -> None:
    """Reopen the producer's exact request and verify its image bytes and prompt."""
    expected = scenario.get('image_sha256')
    if not isinstance(expected, str) or len(expected) != 64:
        raise ProjectionError('vision image digest missing')
    try:
        path = Path(sample['request_path']).resolve(strict=True)
        if capture_root not in path.parents:
            raise ProjectionError('vision request outside capture root')
        request = json.loads(path.read_bytes())
        messages = request['messages']
        if len(messages) != 1 or messages[0]['role'] != 'user':
            raise ProjectionError('vision request messages changed')
        content = messages[0]['content']
        if not isinstance(content, list) or len(content) != 2 or content[0]['type'] != 'image_url' or content[1] != {'type': 'text', 'text': prompt}:
            raise ProjectionError('vision request content changed')
        url = content[0]['image_url']['url']
        prefix, payload = url.split(',', 1)
        if prefix not in ('data:image/png;base64', 'data:image/jpeg;base64', 'data:image/webp;base64'):
            raise ProjectionError('unsupported image data URL')
        image = base64.b64decode(payload, validate=True)
        if _sha(image) != expected:
            raise ProjectionError('vision request image digest mismatch')
    except (OSError, KeyError, TypeError, ValueError, IndexError, binascii.Error) as exc:
        raise ProjectionError(f'invalid bound vision request: {exc}') from exc


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
    for key, path in (('producer_sha256',config.producer_root.parent/'m4_cpu_recipe_compare.py' if config.diagnostic_plan_sha256 else config.producer_root/'dispatch.py'),('capture_sha256',config.producer_root/'capture.py'),('native_runner_sha256',config.producer_root/'native/k35_stack_context_matrix_runner.py'),('native_comparator_sha256',config.producer_root/'native/compare_v9_promotion_arms.py')):
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
    bound_recipe = native.get('recipe')
    bound_scenario = bound_recipe.get('scenario_config') if isinstance(bound_recipe, dict) else None
    if isinstance(bound_scenario, dict):
        if (native.get('role') in ('worker_vision', 'vision_escalation')
                and 'image_path' in bound_scenario and not bound_scenario['image_path']):
            raise ProjectionError('vision scenario lacks a bound image')
        recipe_env = bound_scenario.get('recipe_env')
        if recipe_env is not None:
            _verify_recipe_env(argv, recipe_env)
        bound_context = bound_scenario.get('server_context_size')
        if bound_context is not None and (type(bound_context) is not int or arg('-c') != str(bound_context)):
            raise ProjectionError('bound server context mismatch')
        if bound_scenario.get('image_path') is not None:
            _verify_bound_image_request(sample, bound_scenario, config.capture_root, prompt_path.read_text())
    if config.diagnostic_plan_sha256:
        _verify_diagnostic(native, config)
    if config.producer_root == TOPOLOGY_ROOT or config.diagnostic_plan_sha256:
        recipe = native['recipe']
        scenario = recipe.get('scenario_config') if isinstance(recipe,dict) else None
        if not isinstance(scenario,dict): raise ProjectionError('topology scenario missing')
        nodes, affinity, threads = scenario.get('numa_nodes'), scenario.get('cpu_affinity'), scenario.get('threads')
        vision_roles={'vision_escalation','worker_vision'}
        full_roles={'architect_general','frontdoor','toolrunner','worker','worker_explore','worker_general','worker_math','worker_summarize'}
        role=native['role']
        valid_topology = ((role in vision_roles and (nodes, affinity, threads) == ('0,1', '0-47,96-143', 48))
                          or (role in full_roles and (nodes, affinity) == ('all', '0-95') and type(threads) is int and 1 <= threads <= 96))
        if not valid_topology:
            raise ProjectionError('invalid production topology')
        try: pos=argv.index('numactl')
        except ValueError as exc: raise ProjectionError('topology command missing') from exc
        if argv[pos:pos+6] != ['numactl',f'--interleave={nodes}','--','taskset','-c',affinity] or arg('-t')!=str(threads):
            raise ProjectionError('native topology does not match captured recipe')
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



def _verify_diagnostic(native: dict, config: SourceConfig) -> None:
    """Bind each diagnostic process to the independently enrolled whole plan."""
    try:
        raw = (config.capture_root / 'comparison-plan.json').read_bytes()
        plan = json.loads(raw)
        if (_sha(raw) != config.diagnostic_plan_sha256
                or plan.get('schema') != 'epyc.m4.q38.recipe-comparison.v1'
                or plan.get('status') != 'REVIEWED_DIAGNOSTIC'
                or plan.get('decision_authority') != 'descriptive_only'):
            raise ProjectionError('diagnostic plan seal or purpose mismatch')
        receipt = Path(native['receipt'])
        cell_dir = receipt.parent.parent
        if cell_dir.parent != config.capture_root:
            raise ProjectionError('diagnostic cell path mismatch')
        row = native['row']; extra = row['extra']; pair = extra['pair']
        arm = row['category'].lower(); scenario = native['recipe']['scenario_config']
        recipes = plan['recipes']; cells = plan['cells']
        expected = {(i,a,r) for i in range(3) for a in ('baseline','candidate') for r in ('canonical_t48','configured_t96')}
        if (set(recipes) != {'canonical_t48','configured_t96'} or len(cells) != 12
                or {(c['rep'],c['arm'],c['recipe']) for c in cells} != expected):
            raise ProjectionError('diagnostic denominator mismatch')
        matches = [name for name, value in recipes.items() if value == scenario]
        if (len(matches) != 1 or native['role'] != 'architect_general'
                or native['model'] != plan['model']['path']
                or extra['model_sha256'] != plan['model']['sha256']
                or extra['context'] != 8192 or type(pair) is not int or pair not in range(3)):
            raise ProjectionError('diagnostic model or recipe binding mismatch')
        variant = matches[0]
        if (cell_dir.name != f'{pair:02d}-{arm}-{variant}'
                or receipt.name != f'{arm}-pair-{pair:02d}.json'
                or plan['cells'].count({'rep':pair,'arm':arm,'recipe':variant}) != 1
                or native['recipe'].get('scenario') != scenario.get('name')):
            raise ProjectionError('diagnostic cell identity mismatch')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ProjectionError(f'invalid diagnostic binding: {exc}') from exc

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

TOPOLOGY_ROOT = Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-full-fold-ready-20261028/cpu-fold')
TOPOLOGY_CAPTURE_ROOT = TOPOLOGY_ROOT / 'output'
TOPOLOGY_SEALS = {'dispatch.py': '29431e53b973be9a9392a450a66394aea7075cd57137a8f442ff522a2c21155f', 'capture.py': '701168d58ef67bdc1e130cff9a0fa0f8576516df9fe743bcdaf0794501965479', 'native/k35_stack_context_matrix_runner.py': '056bb6a0743dc52ccc063db2ecdb8bc1be554306fa6d37e664eaba00878fee89', 'native/compare_v9_promotion_arms.py': '83e1ea40499cbca531849af454209d45011b55bc2684c841a09068a15c3fd94e'}

def _verify_trusted(root, capture_root, seals):
    for name, digest in seals.items():
        try:
            if _sha((root / name).read_bytes()) != digest:
                raise ProjectionError(f'producer seal changed: {name}')
        except OSError as exc:
            raise ProjectionError(f'producer unavailable: {name}') from exc
    return SourceConfig(capture_root, root)

def _trusted_config():
    # Existing root and seals remain unchanged for all old captures.
    return _verify_trusted(PRODUCER_ROOT, CAPTURE_ROOT, SOURCE_SEALS)

# Disabled until an independent reviewer pins the exact future diagnostic deployment.
DIAGNOSTIC_CAPTURE_ROOT = None
DIAGNOSTIC_PRODUCER_ROOT = None
DIAGNOSTIC_SOURCE_SEALS = {}
DIAGNOSTIC_COMPARE_SHA256 = ''
DIAGNOSTIC_PLAN_SHA256 = ''

def _trusted_diagnostic():
    root, captures = DIAGNOSTIC_PRODUCER_ROOT, DIAGNOSTIC_CAPTURE_ROOT
    required = {'capture.py', 'native/k35_stack_context_matrix_runner.py', 'native/compare_v9_promotion_arms.py'}
    if not isinstance(root, Path) or not isinstance(captures, Path) or set(DIAGNOSTIC_SOURCE_SEALS) != required:
        raise ProjectionError('diagnostic enrollment absent')
    config = _verify_trusted(root, captures, DIAGNOSTIC_SOURCE_SEALS)
    try:
        if (len(DIAGNOSTIC_PLAN_SHA256) != 64 or len(DIAGNOSTIC_COMPARE_SHA256) != 64
                or _sha((root.parent/'m4_cpu_recipe_compare.py').read_bytes()) != DIAGNOSTIC_COMPARE_SHA256):
            raise ProjectionError('diagnostic source or plan enrollment invalid')
    except OSError as exc:
        raise ProjectionError(f'diagnostic source unavailable: {exc}') from exc
    return SourceConfig(config.capture_root, config.producer_root, DIAGNOSTIC_PLAN_SHA256)

def _trusted_config_for(path):
    if '..' in Path(path).parts:
        raise ProjectionError('parent traversal in capture path')
    requested = Path(os.path.abspath(path))
    resolved = Path(path).resolve()
    old_match = CAPTURE_ROOT in resolved.parents
    new_match = TOPOLOGY_CAPTURE_ROOT in resolved.parents
    diagnostic_match = DIAGNOSTIC_CAPTURE_ROOT is not None and DIAGNOSTIC_CAPTURE_ROOT in resolved.parents
    diagnostic_requested = DIAGNOSTIC_CAPTURE_ROOT is not None and DIAGNOSTIC_CAPTURE_ROOT in requested.parents
    if (CAPTURE_ROOT in requested.parents, TOPOLOGY_CAPTURE_ROOT in requested.parents, diagnostic_requested) != (old_match,new_match,diagnostic_match):
        raise ProjectionError('capture path crosses trusted root boundary')
    if sum((old_match,new_match,diagnostic_match)) != 1:
        raise ProjectionError('capture root unknown or ambiguous')
    if diagnostic_match:
        return _trusted_diagnostic()
    if new_match:
        return _verify_trusted(TOPOLOGY_ROOT, TOPOLOGY_CAPTURE_ROOT, TOPOLOGY_SEALS)
    return _trusted_config()

def native_rows(path: str | Path) -> tuple[dict, ...]:
    return _native_rows(path, _trusted_config_for(path))

@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get('receipt'),str) or not Path(native['receipt']).is_absolute():
        raise ProjectionError('absolute receipt required')
    return _project(native, _trusted_config_for(native['receipt']))

def frames_for_record(path: str | Path, *, as_of: str) -> list[dict]:
    return [frame for native in native_rows(path) for frame in to_frames(
        project(native), as_of=as_of, adapter_id=SOURCE_KIND, authority='measurement')]
