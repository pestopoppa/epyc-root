"""In-container entrypoint: apply orchestrator exec containment before exec."""
import os
import shutil
import sys

sys.path.insert(0, '/opt/p5_sandbox')
from src.repl_environment import exec_sandbox

try:
    if sys.argv[1] == '--git':
        git = shutil.which('git')
        if not git:
            raise RuntimeError('git is not installed')
        # The image's checkout may be owned by a different UID. Trust exactly
        # this isolated checkout, never all directories or image git config.
        os.environ.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
                          GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='safe.directory',
                          GIT_CONFIG_VALUE_0='/testbed', GIT_PAGER='cat')
        command = [git, *sys.argv[2:]]
    else:
        command = ['/bin/bash', '-c', sys.argv[1]]
    argv, extra = exec_sandbox.wrap(command, policy=exec_sandbox.Policy())
    os.execvpe(argv[0], argv, {**os.environ, **extra})
except Exception as exc:
    print('P5 containment refused:', str(exc), file=sys.stderr)
    sys.exit(126)
