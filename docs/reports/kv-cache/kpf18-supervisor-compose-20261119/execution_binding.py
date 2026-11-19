"""Opt-in current guard bindings. Does not replace native boundary checks."""
import os
import sys
from pathlib import Path

REVISION = 'current-guard-v3'
SCRATCH = Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency')


def prepare(seal, admission, captured):
    if seal.get('guard_revision') != REVISION or seal.get('binding_revision') != 'retained-bindings-v2':
        raise ValueError('explicit current guard revision required')
    admission.recheck(seal, captured)
    config = seal['execution']
    if config.get('mode', 'official') == 'publisher-smoke':
        grant = captured[2]
        if not isinstance(grant, tuple) or len(grant) != 2:
            raise ValueError('captured publisher result required')
        root = Path(grant[1]).parent
    else:
        root = Path(config.get('output_root', ''))
        if not root.is_absolute() or not root.is_relative_to(SCRATCH) or root == SCRATCH:
            raise ValueError('sealed private output root required')
    # Contract already binds the publisher path. Check all components again at
    # every access, including for official output, without creating anything.
    def output_root():
        admission.recheck(seal, captured)
        if not root.is_absolute():
            raise ValueError('absolute output required')
        for part in (root, *root.parents):
            if part.is_symlink() or not part.is_dir():
                raise ValueError('unsafe current output root')
        for alias in ('KPF_COMPOSITION_OUTPUT', 'KPF_OUTPUT_ROOT'):
            if alias in os.environ and os.environ[alias] != str(root):
                raise ValueError('redirected current output alias')
        return root

    output_root()
    def bind(driver):
        argv = sys.argv[1:]
        if (argv.count('--out') != 1 or any(arg.startswith('--out=') for arg in argv)
                or argv.index('--out') + 1 >= len(argv)
                or argv[argv.index('--out') + 1] != str(output_root())):
            raise ValueError('driver argv must name admitted output')
        guard = driver.guard
        origin = str(Path(guard.__file__).resolve())
        if origin not in seal['sources']:
            raise ValueError('unsealed retained guard')
        if getattr(guard, '_current_guard_bound', False):
            raise ValueError('current guard already bound')
        if driver.OUT != output_root():
            raise ValueError('driver output differs from admitted output')
        def sources():
            admission.recheck(seal, captured)
        # The executing server is now the explicitly sealed artifact. Other
        # historical checks remain intact and can still refuse native entry.
        guard.BIN = Path(config['artifacts']['server'])
        guard.sources = sources
        guard.attempt_root = output_root
        guard._current_guard_bound = True
    return output_root, bind
