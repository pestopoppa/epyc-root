"""Create a pre-observation request/order pin and enforce its use; diagnostic only."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import secrets

ROOT = Path('/mnt/raid0/llm/worktrees/research-ds41-run10')
MANIFEST_SHA = 'cb033a1d30099e99f33cf91ad96d5e3d841c717cb4eca1e06e5a76f1fa74a190'
SOURCES = {
 'scripts/kernel_rnd/autokernel/loop/serving.py':'84dbf2912e8e07ded0ad1464528754b62420d972c4db8f11dbc4e86e230a1e11',
 'scripts/kernel_rnd/autokernel/loop/planned_serving.py':'216384bd4200612f7caa451830723efb5b34d61b6ff90b4f577797e10205980b',
 'scripts/kernel_rnd/autokernel/evaluator/statistics.py':'19620e357ccc3f3b32b1b9a1a88f979922135c585176af814c6dff1633a94140',
}


def sha(b): return hashlib.sha256(b).hexdigest()


def verify_sources(native, manifest_cls):
    for rel, digest in SOURCES.items():
        if sha((ROOT / rel).read_bytes()) != digest: raise ValueError('native source digest mismatch: ' + rel)
    if Path(native.__file__).resolve() != ROOT / 'scripts/kernel_rnd/autokernel/loop/serving.py':
        raise ValueError('unexpected native serving module')
    import inspect
    if Path(inspect.getfile(manifest_cls)).resolve() != ROOT / 'scripts/kernel_rnd/autokernel/loop/planned_serving.py':
        raise ValueError('unexpected frozen manifest implementation')


def request_identity(frozen):
    if not isinstance(frozen, (tuple,list)) or len(frozen) != 1: raise ValueError('exactly one frozen request required')
    prompt_id, body = frozen[0]
    if not isinstance(prompt_id,str) or not prompt_id.strip() or type(body) is not bytes or not body:
        raise ValueError('invalid frozen request')
    body_sha = sha(body)
    digest = sha(json.dumps([[prompt_id,body_sha]],ensure_ascii=False,separators=(',',':')).encode())
    return {'prompt_id':prompt_id, 'request_sha256':body_sha, 'request_digest':digest}


def prepare(path, manifest_path, recipe, frozen, native, manifest_cls):
    """Re-derive exact frozen bytes, draw native plan, publish new pin once."""
    verify_sources(native, manifest_cls)
    manifest_bytes = Path(manifest_path).read_bytes()
    if sha(manifest_bytes) != MANIFEST_SHA: raise ValueError('frozen manifest digest mismatch')
    manifest = manifest_cls.from_dict(json.loads(manifest_bytes))
    derived = manifest.requests(tuple(p.prompt_id for p in manifest.prompts), recipe)
    if tuple(frozen) != tuple(derived): raise ValueError('runtime request differs from pinned manifest')
    request = request_identity(derived)
    if native.request_digest(recipe, derived) != request['request_digest']: raise ValueError('native request digest mismatch')
    seed=secrets.token_hex(16)
    plan=native._matched_plan(24,seed=seed)
    if plan != native._matched_plan(24,seed=seed): raise ValueError('native schedule is unstable')
    pin={'schema':'epyc.ch26.pre-observation-verification-pin.v1','request':request,
         'calibration_plan':plan,'source_sha256':SOURCES,'manifest_sha256':MANIFEST_SHA,
         'recipe_hash':recipe.recipe_hash,'producer_scope':'pre-observation-consistency-only'}
    payload=(json.dumps(pin,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    fd=os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC, 0o600)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(payload);f.flush();os.fsync(f.fileno())
    except BaseException:
        os.unlink(path)
        raise
    dirfd=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(dirfd)
    finally: os.close(dirfd)
    return pin, sha(payload)


def verify_calibration_inputs(calibrate, args, kwargs, pin, frozen, recipe):
    import inspect
    bound=inspect.signature(calibrate).bind(*args, **kwargs)
    bound.apply_defaults()
    values=bound.arguments
    actual=values.get('recipe')
    if (values.get('samples') != 24 or values.get('pairs') != 5
        or values.get('instrument') != 'matched_process_v2'
        or getattr(actual,'recipe_hash',None) != recipe.recipe_hash
        or tuple(values.get('frozen_requests') or ()) != tuple(frozen)
        or request_identity(frozen) != pin['request']):
        raise ValueError('calibration arguments differ from prepared request, recipe, or plan')


@contextlib.contextmanager
def use_pinned_plan(native, pin_path, pin, pin_sha, frozen, recipe, manifest_cls):
    """Temporarily force native calibration's one random-plan draw to the sealed plan."""
    verify_sources(native,manifest_cls)
    raw = Path(pin_path).read_bytes()
    if sha(raw) != pin_sha or json.loads(raw) != pin: raise ValueError('verification pin changed')
    if request_identity(frozen) != pin['request'] or recipe.recipe_hash != pin['recipe_hash']:
        raise ValueError('calibration request or recipe differs from prepared pin')
    original=native._matched_plan; plan=pin['calibration_plan']
    if original(24,seed=plan.get('seed')) != plan: raise ValueError('pin differs from native seeded plan')
    consumed=0
    def fixed(pairs, *, seed=None):
        nonlocal consumed
        if consumed or pairs != 24 or seed is not None: raise ValueError('unexpected calibration plan draw')
        consumed+=1
        return json.loads(json.dumps(plan))
    native._matched_plan=fixed
    try:
        yield
        if consumed != 1: raise ValueError('native calibration did not consume pinned plan')
    finally:
        native._matched_plan=original
