#!/usr/bin/env python3
"""Validate the fixed G8 matrix before a future launcher; not admission proof."""

class PlanError(ValueError):
    pass


def verify_plan(plan):
    if not isinstance(plan, dict):
        raise PlanError('plan must be a mapping')
    if plan.get('greedy') is not True or plan.get('single_slot') is not True or plan.get('single_drafter') is not True:
        raise PlanError('must be greedy, single-slot and single-drafter')
    if plan.get('target_k') != 'f16' or plan.get('target_v') != 'f16' or plan.get('draft_v') != 'f16':
        raise PlanError('target K/V and draft V must be f16')
    target = plan.get('target_model')
    if not isinstance(target, str) or not target or plan.get('draft_model') != target:
        raise PlanError('target and draft model must be the identical sealed model path')
    expected = {(k, n) for k in ('q4_0', 'q8_0') for n in (4, 8, 16)}
    cells = plan.get('cells')
    if not isinstance(cells, list) or len(cells) != len(expected):
        raise PlanError('matrix must have exactly six cells')
    got = []
    for cell in cells:
        if (not isinstance(cell, dict) or type(cell.get('width')) is not int or
                type(cell.get('draft_k')) is not str):
            raise PlanError('invalid cell')
        got.append((cell['draft_k'], cell['width']))
    if set(got) != expected or len(got) != len(set(got)):
        raise PlanError('incorrect or duplicated matrix cell')
    if plan.get('control') != 'fresh-trace-off-and-on-token-identical':
        raise PlanError('missing trace identity control')
    if plan.get('metric') != 'teacher-forced-match-and-prefix-acceptance':
        raise PlanError('incorrect metric')
    preflight = plan.get('model_preflight')
    digest = preflight.get('sha256') if isinstance(preflight, dict) else None
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise PlanError('missing or malformed external model preflight identity')
    for key in ('server_sha256', 'backend_sha256', 'patch_sha256', 'prompt_manifest_sha256'):
        v = plan.get(key)
        if not isinstance(v, str) or len(v) != 64 or any(c not in '0123456789abcdef' for c in v):
            raise PlanError('missing or malformed ' + key)
    return {'status': 'PLAN_VALID', 'cells': len(got), 'model': target,
            'scope': 'configuration only; no admission, process identity, residency, or runtime evidence'}
