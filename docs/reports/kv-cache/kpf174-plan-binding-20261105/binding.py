"""Prospective plan binding before calling the unchanged KPF-17.4 judge.

The caller must supply trusted, predeclared plan and guard digests. This module
is not connected to any live launcher and does not revise historical results.
"""
import copy
import hashlib
import json


class InvalidPlan(ValueError):
    pass


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidPlan('duplicate JSON key')
        result[key] = value
    return result


def invoke_bound(plan_bytes, expected_plan_sha256, guard_bytes, expected_guard_sha256, cells, judge):
    if not isinstance(plan_bytes, bytes) or hashlib.sha256(plan_bytes).hexdigest() != expected_plan_sha256:
        raise InvalidPlan('plan digest mismatch')
    if not isinstance(guard_bytes, bytes) or hashlib.sha256(guard_bytes).hexdigest() != expected_guard_sha256:
        raise InvalidPlan('guard digest mismatch')
    try:
        plan = json.loads(plan_bytes, object_pairs_hook=_object)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, RecursionError) as exc:
        raise InvalidPlan('invalid plan JSON') from exc
    if not isinstance(plan, dict) or set(plan) != {'schema', 'role', 'length', 'swa_cells', 'cells'} or plan['schema'] != 'kpf174-plan/v1':
        raise InvalidPlan('invalid plan schema')
    if plan['role'] not in ('honest', 'flag_on', 'mut_no_transfer', 'mut_partial_noop'):
        raise InvalidPlan('invalid role')
    entries = plan['cells']
    if not isinstance(entries, list) or not entries:
        raise InvalidPlan('empty cell plan')
    by_id = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {'id', 'group', 'c'}:
            raise InvalidPlan('invalid planned cell')
        cell_id, group, c = entry['id'], entry['group'], entry['c']
        if not isinstance(cell_id, str) or not cell_id or cell_id in by_id or type(group) is not int or group < 0 or type(c) is not int:
            raise InvalidPlan('invalid or duplicate planned identity')
        by_id[cell_id] = (group, c)
    if len(set(by_id.values())) != len(by_id):
        raise InvalidPlan('duplicate planned group and junction')
    if not isinstance(cells, dict) or set(cells) != set(by_id):
        raise InvalidPlan('cell set does not match plan')
    snapshot = copy.deepcopy(cells)
    for cell_id, (group, c) in by_id.items():
        cell = snapshot[cell_id]
        if not isinstance(cell, dict) or type(cell.get('group')) is not int or type(cell.get('c')) is not int or (cell['group'], cell['c']) != (group, c):
            raise InvalidPlan('cell geometry does not match plan')
    namespace = {}
    exec(compile(guard_bytes, '<pinned-kpf174-guard>', 'exec'), namespace)
    problems = namespace['validate_launch'](snapshot, list(by_id), length=plan['length'], swa_cells=plan['swa_cells'], mutant_partial=plan['role'] == 'mut_partial_noop')
    if problems:
        raise InvalidPlan('; '.join(problems))
    return judge(snapshot)
