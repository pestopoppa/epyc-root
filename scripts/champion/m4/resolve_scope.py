#!/usr/bin/env python3
"""Resolve M4 scope to physical server configs; refuse stale/conflicting source inputs.

This is a source binding preflight, not a measurement or a launcher. It does not
establish that a server is running, a recipe is optimal, or binaries match source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(orch: Path, scope: dict, prior: dict, registry: dict) -> dict:
    errors: list[str] = []
    rows: list[dict] = []
    roots = orch.resolve()
    for name, pin in prior.get('source_artifacts', {}).items():
        try:
            path = (roots / pin['path']).resolve(strict=True)
            if not path.is_relative_to(roots) or sha(path) != pin['sha256']:
                errors.append(f'{name}: source pin mismatch or path escape')
        except (KeyError, OSError, TypeError):
            errors.append(f'{name}: source pin missing or unreadable')
    if not prior.get('source_artifacts'):
        errors.append('source artifacts missing')
    modes = registry.get('server_mode', {})
    roles = prior.get('roles', {})
    seen = set()
    for backend, entries in scope.items():
        if backend not in ('cpu', 'gpu') or not isinstance(entries, list) or not entries:
            errors.append(f'{backend}: invalid or empty scope')
            continue
        for item in entries:
            role = item.get('role')
            if not isinstance(role, str) or role in seen:
                errors.append(f'{role}: invalid or duplicate role')
                continue
            seen.add(role)
            try:
                serving = roles[role]['serving']
                launch = serving['launch']
                primaries = launch['primary_roles']
                if len(primaries) != 1:
                    raise ValueError('expected one physical primary')
                primary = primaries[0]
                physical = modes[primary]
                physical_model = physical.get('model_path') or physical.get('model')
                if isinstance(physical_model, dict):
                    physical_model = physical_model.get('path')
                # Some registry models are relative to the canonical model directory.
                target = Path(physical_model)
                if not target.is_absolute():
                    target = Path('/mnt/raid0/llm/models') / target
                if str(target) != item['model_path']:
                    raise ValueError('physical model conflicts with scope')
                if role != primary:
                    alias = modes.get(role, {})
                    if alias.get('alias_of') != primary and role not in physical.get('shared_with', []):
                        raise ValueError('alias not declared by physical server')
                runtime = launch['runtime']
                primary_serving = roles[primary]['serving']['launch']['runtime']
                # Alias-local flags may intentionally describe request policy; physical
                # process settings always come from the primary, never the alias.
                primary_model = roles[primary]['serving']['launch']['requirements']['model_path']
                if primary_model != item['model_path']:
                    raise ValueError('primary prior model conflicts with scope')
                if runtime.get('binary_family') != primary_serving.get('binary_family'):
                    raise ValueError('alias binary family differs from primary')
                rows.append({'backend': backend, 'role': role, 'primary': primary,
                    'model_path': str(target), 'primary_registry': physical,
                    'primary_runtime': primary_serving})
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(f'{role}: {exc}')
    return {'schema': 'epyc.m4.scope_binding_candidate.v1',
            'status': 'REFUSED' if errors else 'SOURCE_BOUND_ONLY',
            'errors': errors, 'roles': rows, 'admission_authorized': False,
            'limitations': ['No independent live runtime or best-recipe attestation',
                            'No model/image content seals or measurement authority']}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--orchestrator', type=Path, required=True)
    parser.add_argument('--cpu-scope', type=Path, required=True)
    parser.add_argument('--gpu-scope', type=Path, required=True)
    args = parser.parse_args()
    orch = args.orchestrator
    try:
        cpu = json.loads(args.cpu_scope.read_text())
        gpu = json.loads(args.gpu_scope.read_text())
        if set(cpu) != {'cpu'} or set(gpu) != {'gpu'}:
            raise ValueError('scope must have exactly its expected backend')
        p = orch / 'orchestration'
        result = resolve(orch, {**cpu, **gpu}, yaml.safe_load((p/'derived/stack_priors.yaml').read_text()),
                         yaml.safe_load((p/'model_registry.yaml').read_text()))
    except (OSError, ValueError, TypeError, yaml.YAMLError, json.JSONDecodeError) as exc:
        result = {'schema': 'epyc.m4.scope_binding_candidate.v1', 'status': 'REFUSED',
                  'errors': [str(exc)], 'roles': []}
    print(json.dumps(result, sort_keys=True, indent=2, default=str))
    # Source matching alone is not a reviewed recipe, runtime, or image attestation.
    # This preflight never authorizes a launcher, including the source-bound case.
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
