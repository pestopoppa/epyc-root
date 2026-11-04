#!/usr/bin/env python3
"""INF-22 M4 fold gate: bind, verify, report and dispatch one sealed plan.

  bind   --spec FOLD-SPEC.json --out DIR   resolve champion/candidate/images/models/
                                           recipes/rule and write DIR/FOLD-PLAN.json
  verify --plan DIR/FOLD-PLAN.json         re-check every seal against live content
  status --plan DIR/FOLD-PLAN.json         fixed-format status (no side effects)
  run    --plan DIR/FOLD-PLAN.json         verify, then run each cell's declared entry
                                           sequentially; one RESULT.json per cell

Deterministic and model-free except `run`, which only executes the entry argv the
sealed plan names. Nothing here starts a server by itself, chooses a threshold or
writes a verdict: the decision rule is an input with an authority, and a missing
rule leaves the plan DESCRIPTIVE_ONLY (run refuses).

Status lines (stable, grep-able):
  M4-FOLD status=<BOUND|DESCRIPTIVE_ONLY|REFUSED> champion=<sha> candidate=<sha> roles=<n> cells=<n> plan=<sha256|->
  NEED <item>        operator input missing (rule, authority)
  REFUSE <reason>    hard failure
  CELL <id> <state>  run-time per-cell state (PENDING|COMPLETE rc=0|FAILED rc=N)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PLAN_SCHEMA = 'epyc.m4.fold_plan.v1'
SPEC_SCHEMA = 'epyc.m4.fold_spec.v1'
RULE_SCHEMA = 'epyc.m4.fold_rule.v1'
M4_FLAG = '--prefill-order'
M4_ON = ['--prefill-order', 'srpf']
# Never measure from frozen production or an in-tree build of the production clone.
FORBIDDEN_ROOTS = ('/mnt/raid0/llm/kernels/production', '/mnt/raid0/llm/llama.cpp/build')
HIDDEN_ENV_PREFIXES = ('LLAMA_ARG_PREFILL', 'LLAMA_ARG_PREFILL_ORDER', 'M4_')
IMAGE_FILES = ('bin/llama-server',)


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()


def git(tree: str, *args: str) -> str:
    return subprocess.check_output(['git', '-C', tree, *args], text=True,
                                   stderr=subprocess.DEVNULL).strip()


def real(path: str, errors: list, what: str) -> Path | None:
    try:
        p = Path(path).resolve(strict=True)
    except (OSError, TypeError):
        errors.append(f'{what}: missing {path}')
        return None
    prod = set(FORBIDDEN_ROOTS)
    for r in FORBIDDEN_ROOTS:  # the production store is a symlink farm: forbid its targets too
        for q in (Path(r).glob('*') if Path(r).is_dir() else ()):
            prod.add(str(q.resolve().parent if q.resolve().name == 'bin' else q.resolve()))
    if any(s == r or s.startswith(r.rstrip('/') + '/') for s in (str(path), str(p)) for r in prod):
        errors.append(f'{what}: resolves into frozen production {p}')
        return None
    return p


def image_source(root: Path) -> str | None:
    bc = root / 'BUILD_COMPLETE'
    if bc.is_file():
        for tok in bc.read_text().split():
            if tok.startswith('source='):
                return tok.split('=', 1)[1]
    bi = root / 'BUILD-IDENTITY.json'
    if bi.is_file():
        return json.loads(bi.read_text()).get('source_sha')
    return None


def seal_image(root: Path, probe: dict, want_knob: bool, errors: list, what: str) -> dict:
    """Bind an image by content: its SHA256SUMS must match the files we seal."""
    sums = {}
    sf = root / 'SHA256SUMS'
    if not sf.is_file():
        errors.append(f'{what}: no SHA256SUMS')
        return {}
    for line in sf.read_text().splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            sums[parts[1].lstrip('*').lstrip('./')] = parts[0]
    files = sorted({*IMAGE_FILES, probe['file'],
                    *(f'bin/{p.name}' for p in (root / 'bin').glob('lib*.so*') if not p.is_symlink())})
    sealed = {}
    for rel in files:
        p = root / rel
        if not p.is_file():
            errors.append(f'{what}: missing {rel}')
            continue
        d = sha_file(p)
        if sums.get(rel) not in (None, d):
            errors.append(f'{what}: {rel} differs from SHA256SUMS')
        if rel in IMAGE_FILES and rel not in sums:
            errors.append(f'{what}: {rel} absent from SHA256SUMS')
        sealed[rel] = d
    blob = (root / probe['file']).read_bytes() if (root / probe['file']).is_file() else b''
    has = probe['needle'].encode() in blob
    if has != want_knob:
        errors.append(f'{what}: knob probe {probe["needle"]!r} in {probe["file"]} '
                      f'{"absent" if want_knob else "present"} (content, not path)')
    return {'root': str(root), 'source': image_source(root), 'files': sealed}


def load_rule(path: str | None, backends: set, errors: list, needs: list) -> dict | None:
    if not path:
        needs.append('decision_rule: no authorized M4 fold rule bound (operator decision)')
        return None
    p = real(path, errors, 'decision_rule')
    if p is None:
        return None
    rule = json.loads(p.read_text())
    if rule.get('schema') != RULE_SCHEMA:
        errors.append('decision_rule: wrong schema')
        return None
    if not rule.get('authority') or not rule.get('authority_sha256'):
        needs.append('decision_rule: authority/authority_sha256 missing')
    else:
        a = real(rule['authority'].split('#')[0], errors, 'decision_rule.authority')
        if a is not None and sha_file(a) != rule['authority_sha256']:
            errors.append('decision_rule: authority digest mismatch')
    if rule.get('metric_direction') != 'higher':
        errors.append('decision_rule: metric_direction must be explicit "higher" (tok/s)')
    for b in sorted(backends):
        r = rule.get(b) or {}
        if not isinstance(r.get('pass_ratio'), (int, float)) or not isinstance(r.get('fail_ratio'), (int, float)):
            needs.append(f'decision_rule.{b}: pass_ratio/fail_ratio not set (operator decision)')
        elif not r['fail_ratio'] <= r['pass_ratio']:
            errors.append(f'decision_rule.{b}: fail_ratio > pass_ratio')
    if not rule.get('quality'):
        needs.append('decision_rule.quality: required quality checks not bound')
    return {'path': str(p), 'sha256': sha_file(p), 'rule': rule}


def bind(spec: dict, model_digest=sha_file, env=None) -> dict:
    env = os.environ if env is None else env
    errors: list[str] = []
    needs: list[str] = []
    if spec.get('schema') != SPEC_SCHEMA:
        errors.append('spec: wrong schema')
    tree = spec.get('llama_tree', '')
    champion, candidate = spec.get('champion', ''), spec.get('candidate', '')
    try:
        ref = git(tree, 'rev-parse', spec['champion_ref'])
        if ref != champion:
            errors.append(f'champion moved: {spec["champion_ref"]}={ref} != {champion}; recut M4 on the new tip')
        if git(tree, 'rev-parse', f'{candidate}^') != champion:
            errors.append('candidate is not exactly one commit on the champion tip')
    except (subprocess.CalledProcessError, KeyError, OSError):
        errors.append('git: champion ref or candidate unresolvable')
    for k in env:
        if k.startswith(HIDDEN_ENV_PREFIXES):
            errors.append(f'hidden M4 override in environment: {k}')
    probe = spec.get('knob_probe') or {}
    if not probe.get('file') or not probe.get('needle'):
        errors.append('knob_probe: file and needle required')
        probe = {'file': 'bin/llama-server', 'needle': '\0'}
    images = {}
    roles = spec.get('roles') or []
    backends = {r.get('backend') for r in roles}
    for b in sorted(backends):
        for arm, want, src in (('baseline', False, champion), ('candidate', True, candidate)):
            what = f'image.{b}.{arm}'
            root = real((spec.get('images', {}).get(b) or {}).get(arm, ''), errors, what)
            if root is None:
                continue
            sealed = seal_image(root, probe, want, errors, what)
            if sealed and sealed['source'] != src:
                errors.append(f'{what}: built from {sealed["source"]}, expected {src}')
            images[f'{b}.{arm}'] = sealed
    if not roles:
        errors.append('roles: empty scope')
    pairs = spec.get('pairs', 2)
    if not isinstance(pairs, int) or isinstance(pairs, bool) or pairs < 2 or pairs % 2:
        errors.append('pairs: must be an even integer >= 2 (ABBA cancels launch-order bias)')
        pairs = 2
    seen, cells, models = set(), [], {}
    for r in roles:
        rid = r.get('role')
        if rid in seen or not isinstance(rid, str):
            errors.append(f'role {rid}: duplicate or invalid')
            continue
        seen.add(rid)
        if r.get('backend') not in ('cpu', 'gpu'):
            errors.append(f'role {rid}: backend must be cpu or gpu')
            continue
        if not r.get('recipe_authority'):
            errors.append(f'role {rid}: no evidenced best-recipe authority')
        argv = r.get('server_args')
        if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
            errors.append(f'role {rid}: server_args must be a list of strings')
            continue
        if M4_FLAG in argv:
            errors.append(f'role {rid}: recipe already sets {M4_FLAG}; arms must differ only by M4')
        for key in ('model', *r.get('aux_models', [])):
            path = r.get(key) if key == 'model' else key
            p = real(path, errors, f'role {rid} model')
            if p is None:
                continue
            if str(p) not in models:
                models[str(p)] = model_digest(p)
            want = r.get('model_sha256') if key == 'model' else (r.get('aux_sha256') or {}).get(path)
            if models[str(p)] != want:
                errors.append(f'role {rid}: model digest mismatch for {p}')
        # ABBA (operator 2026-11-04, M4-FOLD-RULE option 2): the A/A noise run showed the
        # second-launched arm ~3 % slow, so launch order alternates per pair (AB, BA, AB, ...)
        # and an even pair count cancels the order bias. Cell list order IS launch order.
        for k in range(pairs):
            order = ('baseline', 'candidate') if k % 2 == 0 else ('candidate', 'baseline')
            for pos, arm in enumerate(order):
                cells.append({'id': f'{rid}.p{k}.{arm}', 'role': rid, 'backend': r['backend'],
                              'arm': arm, 'pair': k, 'position': pos,
                              'image': f'{r["backend"]}.{arm}',
                              'server_args': argv + (M4_ON if arm == 'candidate' else []),
                              'env': r.get('env', {}), 'placement': r.get('placement'),
                              'entry': spec.get('entries', {}).get(r['backend'])})
    for c in cells:
        if not isinstance(c['entry'], list) or not c['entry']:
            needs.append(f'entries.{c["backend"]}: no launch entry argv bound')
            break
    pool = spec.get('prompt_pool') or {}
    pp = real(pool.get('path', ''), errors, 'prompt_pool')
    if pp is not None and sha_file(pp) != pool.get('sha256'):
        errors.append('prompt_pool: digest mismatch')
    rule = load_rule(spec.get('decision_rule'), backends, errors, needs)
    status = 'REFUSED' if errors else ('DESCRIPTIVE_ONLY' if needs else 'BOUND')
    return {'schema': PLAN_SCHEMA, 'status': status, 'errors': errors, 'needs': sorted(set(needs)),
            'champion': champion, 'candidate': candidate, 'champion_ref': spec.get('champion_ref'),
            'llama_tree': tree, 'images': images, 'models': models, 'cells': cells,
            'prompt_pool': {'path': str(pp) if pp else None, 'sha256': pool.get('sha256')},
            'limits': spec.get('limits', {}), 'decision_rule': rule, 'pairs': pairs,
            'arm_order': 'ABBA',
            'result_root': spec.get('result_root'), 'knob_probe': probe,
            'spec_sha256': hashlib.sha256(canon(spec)).hexdigest()}


def plan_digest(plan: dict) -> str:
    return hashlib.sha256(canon({k: v for k, v in plan.items() if k != 'plan_sha256'})).hexdigest()


def verify(plan: dict, model_digest=sha_file, env=None) -> list[str]:
    """Re-check live content against the sealed plan; empty list = still valid."""
    errs = []
    if plan.get('plan_sha256') != plan_digest(plan):
        return ['plan: seal broken (edited after bind)']
    env = os.environ if env is None else env
    errs += [f'hidden M4 override in environment: {k}' for k in env if k.startswith(HIDDEN_ENV_PREFIXES)]
    try:
        if git(plan['llama_tree'], 'rev-parse', plan['champion_ref']) != plan['champion']:
            errs.append('champion moved since bind')
    except (subprocess.CalledProcessError, OSError):
        errs.append('git: champion ref unresolvable')
    for name, img in plan['images'].items():
        for rel, d in img['files'].items():
            p = Path(img['root']) / rel
            if not p.is_file() or sha_file(p) != d:
                errs.append(f'image.{name}: {rel} changed')
    for path, d in plan['models'].items():
        if not Path(path).is_file() or model_digest(Path(path)) != d:
            errs.append(f'model changed: {path}')
    pp = plan['prompt_pool']
    if pp['path'] and sha_file(Path(pp['path'])) != pp['sha256']:
        errs.append('prompt_pool changed')
    rule = plan.get('decision_rule')
    if rule and sha_file(Path(rule['path'])) != rule['sha256']:
        errs.append('decision_rule changed')
    return errs


def status_lines(plan: dict, extra: list[str] = (), cell_state: dict | None = None) -> list[str]:
    out = [f'M4-FOLD status={plan["status"]} champion={plan["champion"][:12]} '
           f'candidate={plan["candidate"][:12]} roles={len({c["role"] for c in plan["cells"]})} '
           f'cells={len(plan["cells"])} plan={plan.get("plan_sha256", "-")}']
    out += [f'NEED {n}' for n in plan.get('needs', [])]
    out += [f'REFUSE {e}' for e in [*plan.get('errors', []), *extra]]
    for c in plan['cells']:
        if cell_state is not None:
            out.append(f'CELL {c["id"]} {cell_state.get(c["id"], "PENDING")}')
    return out


def read_cell_state(plan: dict) -> dict:
    root = Path(plan['result_root'] or '.')
    state = {}
    for c in plan['cells']:
        r = root / c['id'] / 'RESULT.json'
        if r.is_file():
            rc = json.loads(r.read_text()).get('rc')
            state[c['id']] = 'COMPLETE rc=0' if rc == 0 else f'FAILED rc={rc}'
    return state


def run(plan_path: Path, plan: dict) -> int:
    root = Path(plan['result_root'])
    for c in plan['cells']:
        out = root / c['id']
        if (out / 'RESULT.json').is_file():
            continue  # resumable; a failed cell is retained, never overwritten
        errs = verify(plan)
        if errs:
            print('\n'.join(f'REFUSE {e}' for e in errs))
            return 2
        out.mkdir(parents=True, exist_ok=False)
        argv = [a.format(plan=str(plan_path), cell=c['id'], out=str(out)) for a in c['entry']]
        child_env = {k: v for k, v in os.environ.items() if not k.startswith(HIDDEN_ENV_PREFIXES)}
        child_env.update(c['env'])
        with open(out / 'entry.log', 'wb') as log:
            rc = subprocess.call(argv, stdout=log, stderr=subprocess.STDOUT, env=child_env)
        (out / 'RESULT.json').write_text(json.dumps(
            {'cell': c['id'], 'rc': rc, 'argv': argv, 'plan_sha256': plan['plan_sha256']}, indent=2))
        print(f'CELL {c["id"]} {"COMPLETE rc=0" if rc == 0 else f"FAILED rc={rc}"}', flush=True)
        if rc != 0:
            return 1
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('bind')
    b.add_argument('--spec', type=Path, required=True)
    b.add_argument('--out', type=Path, required=True)
    for name in ('verify', 'status', 'run'):
        sub.add_parser(name).add_argument('--plan', type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'bind':
        plan = bind(json.loads(a.spec.read_text()))
        plan['plan_sha256'] = plan_digest(plan)
        a.out.mkdir(parents=True, exist_ok=True)
        target = a.out / 'FOLD-PLAN.json'
        if target.exists():
            print(f'REFUSE {target} exists; plans are write-once')
            return 2
        target.write_text(json.dumps(plan, indent=2, sort_keys=True))
        print('\n'.join(status_lines(plan)))
        return {'BOUND': 0, 'DESCRIPTIVE_ONLY': 3}.get(plan['status'], 2)
    plan = json.loads(a.plan.read_text())
    if a.cmd == 'status':
        print('\n'.join(status_lines(plan, cell_state=read_cell_state(plan))))
        return 0
    errs = verify(plan)
    if a.cmd == 'verify':
        print('\n'.join(status_lines(plan, errs)))
        return 2 if errs or plan['status'] == 'REFUSED' else 0
    if plan['status'] != 'BOUND':
        print('\n'.join(status_lines(plan, ['run requires status=BOUND'])))
        return 2
    return run(a.plan, plan)


if __name__ == '__main__':
    raise SystemExit(main())
