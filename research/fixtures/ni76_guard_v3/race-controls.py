"""Hosted-only real-filesystem FIFO replacement between lstat and open."""
import importlib.util
import os
from pathlib import Path
import sys

assert os.environ.get('GITHUB_ACTIONS') == 'true'
source = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('ni76_actual_guard', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original_open = os.open
path = Path('/mnt/raid0/llm/tmp/cpu_region.build.q0.lock')
saved = path.with_name('race-held-original')
injected = False


def replacing_open(name, flags, mode=0o777, *, dir_fd=None):
    global injected
    if name == path.name and dir_fd is not None and not flags & os.O_DIRECTORY and not injected:
        path.rename(saved)
        os.mkfifo(path, 0o600)
        injected = True
    return original_open(name, flags, mode, dir_fd=dir_fd)


os.open = replacing_open
try:
    try:
        module.admit()
    except module.Refusal as exc:
        assert injected, 'replacement injection did not land'
        assert 'opened lock is not regular' in str(exc), str(exc)
        print('real FIFO replacement refused without blocking; actual live ancestor flocks remained on original inode')
        result = 64
    else:
        raise AssertionError('FIFO replacement admitted')
finally:
    os.open = original_open
    if injected:
        path.unlink()
        saved.rename(path)
raise SystemExit(result)
