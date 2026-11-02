"""In-container entrypoint: apply orchestrator exec containment before exec."""
import os
import sys

sys.path.insert(0, '/opt/p5_sandbox')
from src.repl_environment import exec_sandbox

try:
    argv, extra = exec_sandbox.wrap(['/bin/bash', '-c', sys.argv[1]], policy=exec_sandbox.Policy())
    os.execvpe(argv[0], argv, {**os.environ, **extra})
except Exception as exc:
    print('P5 containment refused:', str(exc), file=sys.stderr)
    sys.exit(126)
