#!/usr/bin/env python3
"""PROPOSED replacement: explicit normalized row and native metadata under owner lease."""
import fcntl
import os
from pathlib import Path
import sys
import tempfile
import registration_gate as gate
import validate_fillers as vf

# FLAGS override is for private fixtures; owner cutover pins the production directory.
flags = Path(os.environ.get('CTCQD_FLAGS', '/mnt/raid0/llm/tmp/compute-flags'))
try:
    args = sys.argv[1:]
    if len(args) == 7: args += ['cpu', '', '']
    rid, src, pid, win, gib, regs, metadata, lane, minimum, regex = args
    raw = gate.sweep.read_regular(src).decode('utf-8')
    col, parsed, _ = vf.parse_table(raw)
    matches = [cells for _, cells in parsed if cells[0] == rid]
    gate.sweep.require(len(matches) == 1, 'exactly one candidate required')
    fd = os.open(flags / '.publication.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        with tempfile.NamedTemporaryFile(dir=flags, prefix='.candidate-', delete=False) as f:
            name = f.name; f.write(gate.table(col, matches[0]))
        try: result = gate.register(flags, Path(name), Path(metadata), pid, win, gib, regs, lane, minimum, regex)
        finally: os.unlink(name)
        print(gate.json.dumps(result, sort_keys=True))
    finally: os.close(fd)
except (ValueError, OSError, gate.sweep.Invalid, gate.dryrun.Refused, vf.Malformed, KeyError, TypeError) as e:
    print('refuse: ' + str(e), file=sys.stderr); sys.exit(2)
