"""Fail-closed, pre-execution binding for the M4 CPU native successor.

An independently reviewed plan and a separately enrolled reader are required.
This code does not create a canary, source enrollment, or measurement verdict.
"""
from __future__ import annotations

import hashlib
import json
import planning_canary
from pathlib import Path

CHAMPION = 'c72ec82f5417bb2937310326120f149b665e8400'
CANDIDATE = 'bc441f1a261766d11bfeff21668a1031c4dbf8cd'


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def checked_file(path: str, expected: str) -> Path:
    if not isinstance(path, str) or not Path(path).is_absolute() or '..' in Path(path).parts:
        raise ValueError('input path must be absolute and traversal-free')
    p = Path(path).resolve(strict=True)
    if not p.is_file() or not isinstance(expected, str) or len(expected) != 64 or sha(p) != expected:
        raise ValueError(f'input content mismatch: {path}')
    return p


def verify(plan: dict, *, current_champion: str, enrolled: bool) -> dict:
    if not enrolled:
        raise ValueError('reviewed source reader not enrolled')
    if current_champion != CHAMPION or plan.get('baseline_commit') != CHAMPION or plan.get('candidate_commit') != CANDIDATE:
        raise ValueError('champion or candidate changed; recut required')
    role = plan.get('role')
    if not isinstance(role, str) or not role or Path(role).name != role:
        raise ValueError('one exact role required')
    scope = checked_file(plan['scope'],plan['scope_sha256'])
    native_plan = checked_file(plan['native_plan'],plan['native_plan_sha256'])
    binding = checked_file(plan['binding'],plan['binding_sha256'])
    binding_doc = json.loads(binding.read_bytes())
    if binding_doc.get('status') != 'SOURCE_BOUND_ONLY' or binding_doc.get('errors') != []:
        raise ValueError('scope resolver has not bound source')
    scopes = json.loads(scope.read_bytes()).get('cpu')
    entries = json.loads(native_plan.read_bytes()).get('models')
    if not isinstance(scopes, list) or not isinstance(entries, list) or not scopes:
        raise ValueError('scope or recipe plan missing')
    scoped = [(x.get('role'), x.get('model_path')) for x in scopes]
    bound = [(x.get('role'), x.get('model_path')) for x in binding_doc.get('roles', []) if x.get('backend') == 'cpu']
    models = [(x.get('role'), x.get('model_path')) for x in entries]
    if len(scoped) != len(set(scoped)) or set(scoped) != set(bound) or set(scoped) != set(models):
        raise ValueError('scope, source binding and recipe roles differ')
    selected = [e for e in entries if e.get('role') == role]
    if len(selected) != 1:
        raise ValueError('role not uniquely selected')
    for entry in entries:
        checked_file(entry['model_path'], entry['model_sha256'])
        for item in entry.get('additional_model_inputs', []):
            checked_file(item['path'],item['sha256'])
        for arm in ('baseline', 'candidate'):
            recipe = entry[arm]
            checked_file(recipe['best_evidence'],recipe['best_evidence_sha256'])
            scenario = recipe.get('scenario_config')
            if not isinstance(scenario, dict):
                raise ValueError('explicit native scenario required')
            draft = scenario.get('draft_model')
            if draft:
                checked_file(draft, recipe['draft_model_sha256'])
            elif recipe.get('draft_model_sha256'):
                raise ValueError('draft identity differs')
    images = {}
    for arm in ('baseline','candidate'):
        image = plan['images'][arm]
        raw_root = Path(image['root'])
        if not raw_root.is_absolute() or '..' in raw_root.parts:
            raise ValueError('image root must be absolute')
        root = raw_root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError('image root missing')
        seals = image['files']
        manifest = checked_file(image['build_manifest'], image['build_manifest_sha256'])
        manifest_doc = json.loads(manifest.read_bytes())
        expected_commit = CHAMPION if arm == 'baseline' else CANDIDATE
        if manifest_doc.get('source_commit') != expected_commit or manifest_doc.get('files') != seals:
            raise ValueError('image build manifest does not bind source and files')
        if not isinstance(seals, dict) or 'bin/llama-server' not in seals:
            raise ValueError('image binary seal missing')
        libs = {str(p.relative_to(root)) for p in (root/'bin').glob('libggml*.so*') if p.is_file()}
        if not libs or not libs.issubset(seals):
            raise ValueError('image ggml library seals incomplete')
        for rel, digest in seals.items():
            p = Path(rel)
            if p.is_absolute() or '..' in p.parts:
                raise ValueError('image path escape')
            target = (root/p).resolve(strict=True)
            if not target.is_relative_to(root) or sha(target) != digest:
                raise ValueError('image content changed')
        images[arm] = root
    receipt = _verify_planning_canary()
    return {'scope':scope,'native_plan':native_plan,'role':role,'images':images,'canary_receipt':receipt}


def _verify_planning_canary() -> dict:
    # Execute the canonical native replay; no plan-supplied summary or strings
    # can serve as a receipt. Unknown/crash/FAIL all refuse before inference.
    return planning_canary.run()
