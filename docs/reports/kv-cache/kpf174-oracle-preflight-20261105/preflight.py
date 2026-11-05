#!/usr/bin/env python3
"""Prospective structure preflight for the declared KPF-17.4 v1 cell protocol.

This is an input guard, not a replacement judge. Historical verdicts are immutable.
The caller must bind expected cell IDs to a predeclared plan before invoking it.
"""


def validate_launch(cells, expected_ids, *, length, swa_cells, mutant_partial=False):
    errors = []
    if not isinstance(cells, dict) or not isinstance(expected_ids, (list, tuple)):
        return ['invalid cells or plan']
    if not expected_ids or any(not isinstance(x, str) or not x for x in expected_ids):
        return ['plan must contain nonempty string cell IDs']
    if len(set(expected_ids)) != len(expected_ids) or set(cells) != set(expected_ids):
        errors.append('cell set does not match plan')
    if type(length) is not int or type(swa_cells) is not int or length <= 0 or swa_cells <= 0:
        return errors + ['invalid geometry']
    for cell_id in expected_ids:
        cell = cells.get(cell_id)
        if not isinstance(cell, dict):
            errors.append(f'{cell_id}: missing cell')
            continue
        c = cell.get('c')
        if type(c) is not int or not 0 < c < length:
            errors.append(f'{cell_id}: invalid junction')
            continue
        if mutant_partial and (type(cell.get('pruned')) is not bool or cell['pruned'] != (c < length - swa_cells)):
            errors.append(f'{cell_id}: missing or inconsistent pruning scope')
        controls, arms = cell.get('controls'), cell.get('arms')
        if not isinstance(controls, list) or len(controls) < 3 or any(not isinstance(x, dict) for x in controls):
            errors.append(f'{cell_id}: expected at least three controls')
        if not isinstance(arms, list) or len(arms) != 2 or any(not isinstance(x, dict) for x in arms):
            errors.append(f'{cell_id}: expected exactly two arms')
        elif any(type(arm.get('fork_src_slot')) is not int or arm['fork_src_slot'] != 0 for arm in arms):
            errors.append(f'{cell_id}: fork source must be slot 0')
    return errors
