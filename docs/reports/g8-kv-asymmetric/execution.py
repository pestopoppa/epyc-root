#!/usr/bin/env python3
"""G8 paired-cell sequencing seam. Not an authorized inference launcher.

A future adapter must prove grant/lock ownership, model identity, actual child
and descendant drain, STOP interruption, backend mappings and residency. This
module injects those adapters and deliberately provides none that launches.
"""
from analyze_trace import analyze_pair
from build_binding import bind_receipt
from plan_guard import verify_plan


class ExecutionError(RuntimeError):
    pass


def execute(*, plan, receipt, admission, run_arm, record):
    verify_plan(plan)
    bound = bind_receipt(receipt)
    if (plan['server_sha256'] != bound['artifacts']['server']['sha256'] or
            plan['backend_sha256'] != bound['artifacts']['hip']['sha256'] or
            plan['patch_sha256'] != bound['patch_sha256']):
        raise ExecutionError('plan disagrees with build receipt')
    if not all(callable(x) for x in (admission, run_arm, record)):
        raise ExecutionError('missing adapters')
    results = []
    for cell in plan['cells']:
        if admission() is not True:
            raise ExecutionError('admission or STOP failed before control')
        control = run_arm(cell, False, bound)
        # One retained partial control is never promoted to an analysis.
        record({'cell': cell, 'arm': 'control', 'native': control, 'status': 'PARTIAL'})
        if admission() is not True:
            raise ExecutionError('admission or STOP failed before trace')
        traced = run_arm(cell, True, bound)
        record({'cell': cell, 'arm': 'trace', 'native': traced, 'status': 'PARTIAL'})
        for arm in (control, traced):
            if (not isinstance(arm, dict) or arm.get('native_complete') is not True or
                    arm.get('fresh_server') is not True or arm.get('child_tree_drained') is not True or
                    arm.get('gpu_residency_verified') is not True or arm.get('backend_identity_verified') is not True):
                raise ExecutionError('unverified native arm')
        metrics = analyze_pair({'greedy': plan['greedy'], 'single_slot': plan['single_slot'],
                                'single_drafter': plan['single_drafter'],
                                'control_request': control['request'], 'traced_request': traced['request'],
                                'control_response': control['response'], 'traced_response': traced['response'],
                                'trace': traced['trace']})
        result = {'cell': cell, 'status': 'VALID', 'metrics': metrics}
        record(result)
        results.append(result)
    return results
