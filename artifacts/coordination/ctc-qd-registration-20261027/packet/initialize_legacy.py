#!/usr/bin/env python3
"""Owner cutover only: snapshot current exact rows under the publication lease."""
import fcntl
import os
from pathlib import Path
import sys
import registration_gate as gate
flags = Path(sys.argv[1])
fd = os.open(flags / '.publication.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
try:
    fcntl.flock(fd, fcntl.LOCK_EX)
    print(gate.json.dumps(gate.cutover(flags), sort_keys=True))
finally: os.close(fd)
