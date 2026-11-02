#!/usr/bin/env python3
"""Offline-tested grant envelope validation for the unpublished Jet-Long job.

This is not a launcher. It validates the keeper's exported values, but does not
replace the engine's grant or resource claim and never grants work itself.
"""
import math
from pathlib import Path


class AdmissionError(ValueError):
    pass


def validate(env, *, now, minimum_cell_s, startup_s, cleanup_s, result_path):
    try:
        end = int(env['FILLER_END'])
        deadline = int(env['FILLER_DEADLINE'])
        cpus = env['FILLER_CPUS']
        stop = Path(env['FILLER_STOPFILE'])
    except (KeyError, TypeError, ValueError) as exc:
        raise AdmissionError('missing or invalid keeper envelope') from exc
    if not cpus or not all(c in '0123456789,-' for c in cpus):
        raise AdmissionError('invalid CPU allocation')
    if not stop.is_absolute() or stop.exists():
        raise AdmissionError('missing absolute stop path or already stopped')
    limits = (now, minimum_cell_s, startup_s, cleanup_s)
    if any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in limits):
        raise AdmissionError('invalid timing value')
    if min(minimum_cell_s, startup_s, cleanup_s) <= 0:
        raise AdmissionError('non-positive reservation')
    if deadline > end or end <= now or deadline <= now:
        raise AdmissionError('expired or inconsistent keeper deadline')
    # lifecycle budget includes its own startup and cleanup. FILLER_DEADLINE is
    # the no-new-work boundary; never use its reserved hard-end cleanup margin.
    budget_s = deadline - now
    if budget_s < minimum_cell_s + startup_s + cleanup_s:
        raise AdmissionError('insufficient time for a complete cell and cleanup')
    dry = env.get('FILLER_DRYRUN') == '1'
    selected = env.get('FILLER_DRYRUN_RESULT_PATH') if dry else result_path
    if not selected or not Path(selected).is_absolute():
        raise AdmissionError('missing absolute result path')
    if dry:
        dry_dir = env.get('FILLER_DRYRUN_DIR')
        if not dry_dir or not Path(dry_dir).is_absolute():
            raise AdmissionError('dry-run directory missing')
        # A dry run may only write within its own dry-run directory. Do not let
        # an ordinary result satisfy keeper's first-unit check.
        if not Path(selected).resolve().is_relative_to(Path(dry_dir).resolve()):
            raise AdmissionError('dry-run result escapes dry-run directory')
    return {'budget_s': budget_s, 'cpus': cpus, 'stop_file': str(stop),
            'result_path': selected, 'dry_run': dry}
