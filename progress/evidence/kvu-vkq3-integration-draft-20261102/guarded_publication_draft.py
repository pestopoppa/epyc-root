"""Guard-to-receipt-to-rowflow publication integration; not a launcher.

Parent-death containment, signal routing, source/model/runtime binding, and
engine/chroot testing are not implemented here. Do not schedule this draft.
"""
import os
from pathlib import Path

from completion_draft import publish_unit
from grant_bridge_draft import run_guarded_attempt


def run_and_publish(*, env, full_result_path, **guarded_args):
    """Use the engine's private dry-run result path in qualification mode."""
    raw_mode = env.get('FILLER_DRYRUN', '0')
    if raw_mode not in ('0', '1'):
        raise ValueError('invalid engine mode')
    mode = 'qualification' if raw_mode == '1' else 'full'
    selected = env.get('FILLER_DRYRUN_RESULT_PATH') if mode == 'qualification' else full_result_path
    if not selected or not Path(selected).is_absolute():
        raise ValueError('missing absolute result path')
    if mode == 'qualification' and os.path.realpath(selected) == os.path.realpath(full_result_path):
        raise ValueError('qualification cannot use full result path')
    output = Path(selected)
    if os.path.lexists(output) or os.path.lexists(output.parent / ('.' + output.name + '.tmp')):
        raise FileExistsError('result or partial result already exists')
    attempt_id = guarded_args['attempt_id']
    directory = run_guarded_attempt(env=env, **guarded_args)
    publish_unit(mode, attempt_id, directory, output)
    return output
