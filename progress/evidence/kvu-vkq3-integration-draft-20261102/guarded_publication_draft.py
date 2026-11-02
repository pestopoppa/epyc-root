"""Guard-to-receipt-to-rowflow publication integration; not a launcher.

Parent-death containment, signal routing, source/model/runtime binding, and
engine/chroot testing are not implemented here. Do not schedule this draft.
"""
import os
from pathlib import Path

from completion_draft import complete_diagnostic
from grant_bridge_draft import run_guarded_attempt


def publish_unit(mode, attempt_id, directory, output):
    """Publish one result only after its durable completion marker exists."""
    output = Path(output)
    if not output.is_absolute():
        raise ValueError('result path must be absolute')
    if not complete_diagnostic(mode, attempt_id, directory):
        raise ValueError('attempt is not a valid complete unit')
    data = (Path(directory) / 'unit.jsonl').read_bytes()
    temp = output.parent / ('.' + output.name + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        # The unique result path must never be replaced or reset on retry.
        os.link(temp, output, follow_symlinks=False)
        os.unlink(temp)
        parent_fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except BaseException:
        # Keep a partial file as evidence without making a result visible.
        raise


def run_and_publish(*, env, full_result_path, **guarded_args):
    """Use the engine's private dry-run result path in qualification mode."""
    raw_mode = env.get('FILLER_DRYRUN', '0')
    if raw_mode not in ('0', '1'):
        raise ValueError('invalid engine mode')
    mode = 'qualification' if raw_mode == '1' else 'full'
    selected = env.get('FILLER_DRYRUN_RESULT_PATH') if mode == 'qualification' else full_result_path
    if not selected or not Path(selected).is_absolute():
        raise ValueError('missing absolute result path')
    if mode == 'qualification' and Path(selected) == Path(full_result_path):
        raise ValueError('qualification cannot use full result path')
    output = Path(selected)
    if os.path.lexists(output) or os.path.lexists(output.parent / ('.' + output.name + '.tmp')):
        raise FileExistsError('result or partial result already exists')
    attempt_id = guarded_args['attempt_id']
    directory = run_guarded_attempt(env=env, **guarded_args)
    publish_unit(mode, attempt_id, directory, output)
    return output
