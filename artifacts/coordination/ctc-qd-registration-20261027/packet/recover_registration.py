#!/usr/bin/env python3
"""Owner only: replay the recorded registration generation under the publication lease."""
import fcntl
import os
from pathlib import Path
import sys
import registration_gate as gate
flags = Path(sys.argv[1])
if len(sys.argv) > 2 and sys.argv[2:] != ['--abort']:
    raise SystemExit('usage: recover_registration.py FLAGS [--abort]')
fd = os.open(flags / '.publication.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
try:
    fcntl.flock(fd, fcntl.LOCK_EX)
    print(gate.json.dumps(gate.abort(flags) if sys.argv[2:] else gate.recover(flags), sort_keys=True))
except (gate.sweep.Invalid, gate.sweep.vf.Malformed, KeyError, TypeError, OSError, ValueError) as e:
    print('refuse: ' + str(e), file=sys.stderr); sys.exit(2)
finally: os.close(fd)
