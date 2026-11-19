"""Disabled outer supervisor; callable tests confer no execution admission."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def verify():
    if (HERE / 'INCOMPLETE').exists():
        raise ValueError('incomplete supervisor')
    seal = json.loads((HERE / 'manifest.json').read_text())
    if seal['runtime_dispatch'] is not False:
        raise ValueError('disabled supervisor required')
    for name, expected in seal['sources'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise ValueError('supervisor source drift: ' + name)
    return seal


def run(entry):
    seal = verify()
    # /proc covers native threads as well as Python threading.Thread instances.
    if len(list(Path('/proc', str(os.getpid()), 'task').iterdir())) != 1:
        raise RuntimeError('single-threaded isolated supervisor required')
    spec = importlib.util.spec_from_file_location('_owned_cleanup', seal['helper'])
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    if helper.children():
        raise RuntimeError('preexisting children refused')
    helper.enable()
    try:
        return entry()
    finally:
        # Runs after entry's own server-stop and partial-run finalizers, even
        # when entry raises SystemExit/KeyboardInterrupt or an ordinary error.
        helper.drain()
        if helper.children():
            raise RuntimeError('owned cleanup returned with children')


def refuse_preloaded_dependencies(seal):
    """Source hashes cannot attest objects already present in sys.modules.

    Binding modules deliberately import peers under stable public names. Refuse
    those names before executing any binding code, including dotted aliases.
    The supervisor is an isolated entry, so even a matching origin is refused:
    its module globals could have changed since the file was verified.
    """
    names = {Path(name).stem for name in seal['sources']
             if Path(name).suffix == '.py'} - {'__init__'}
    names.update({'composition', '_supervised_driver'})
    conflicts = sorted(name for name in sys.modules
                       if name.rsplit('.', 1)[-1] in names)
    if conflicts:
        raise ValueError('preloaded driver binding or dependency: ' + ', '.join(conflicts))


def run_driver():
    def entry():
        seal = verify()
        driver_path = Path(seal['driver'])
        refuse_preloaded_dependencies(seal)
        sys.path.insert(0, str(driver_path.parent))
        spec = importlib.util.spec_from_file_location('_supervised_driver', driver_path)
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        return driver.main()
    return run(entry)


if __name__ == '__main__':
    raise SystemExit(78)
