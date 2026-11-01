"""Offline-testable mode, exposure and event controls; never launches inference."""
import json, os
from pathlib import Path

def mode_check(mode, dryrun):
    if mode not in ('qualification', 'full') or (dryrun == '1') != (mode == 'qualification'):
        raise RuntimeError('qualification mode mismatch')
    return mode

def target_allowed(mode):
    return mode == 'full'

def exposure_seen(output_dir):
    return any(Path(output_dir).glob('*.exposure.json'))

def stopped(stop_file, engine_stop_file, now, deadline):
    return Path(stop_file).exists() or bool(engine_stop_file and Path(engine_stop_file).exists()) or now >= deadline

def emit(path, event):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        data = (json.dumps(event, sort_keys=True) + '\n').encode()
        if os.write(fd, data) != len(data):
            raise OSError('short event write')
        os.fsync(fd)
    finally:
        os.close(fd)
