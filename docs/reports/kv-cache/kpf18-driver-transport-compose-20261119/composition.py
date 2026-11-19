"""Import-only binding for a disabled driver, not rowflow runtime authority."""
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def verify():
    if (HERE / 'INCOMPLETE').exists():
        raise ValueError('incomplete composition')
    seal = json.loads((HERE / 'manifest.json').read_text())
    if seal['runtime_dispatch'] is not False:
        raise ValueError('disabled composition required')
    for name, expected in seal['sources'].items():
        path = Path(name)
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
        if h.hexdigest() != expected:
            raise ValueError('composition source drift: ' + name)
    return seal


def bind():
    seal = verify()
    # A clean interpreter is required: no silent replacement of consumers that
    # already captured the old class, nor reuse of a foreign dependency cache.
    inherited = Path(seal['predecessor']) / 'candidate'
    names = {p.stem for p in inherited.rglob('*.py')}
    names.update(('slots_transport', 'composition_driver'))
    conflicts = names.intersection(sys.modules) - {'composition'}
    if conflicts:
        raise ValueError('preloaded candidate modules: ' + ','.join(sorted(conflicts)))
    transport = Path(seal['transport'])
    transport_seal = json.loads((transport / 'manifest.json').read_text())
    dependencies = Path(transport_seal['dependency_path'])
    sys.path[:0] = [str(transport), str(dependencies), str(inherited),
                   '/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-normalization-r13/data']
    # The receipt-backed predecessor predates the cancel-order repair. Import
    # all six pinned dependencies now, before driver.py prepends its vendor
    # directory; otherwise its older native_task_log silently wins resolution.
    for name in ('physical_trace', 'socket_deadline', 'cancel_seed_stream',
                 'native_task_log', 'cancel_seed_admission', 'native_block'):
        module = importlib.import_module(name)
        if Path(module.__file__).resolve() != (dependencies / (name + '.py')).resolve():
            raise ValueError('wrong transport dependency: ' + name)
    for name in ('slots_transport', 'cancel_seed_transport'):
        spec = importlib.util.spec_from_file_location(name, transport / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise


def output_root():
    root = Path(os.environ.get('KPF_COMPOSITION_OUTPUT', ''))
    scratch = Path('/mnt/raid0/llm/tmp/kvu')
    if (not root.is_absolute() or not root.resolve().is_relative_to(scratch)
            or root.is_symlink() or not root.is_dir()):
        raise ValueError('existing private scratch output required')
    return root
