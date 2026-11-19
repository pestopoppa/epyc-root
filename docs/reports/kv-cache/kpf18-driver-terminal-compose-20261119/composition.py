"""Import-only terminal/transport binding. This grants no native authority."""
import hashlib
import importlib.util
import json
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
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise ValueError('composition source drift: ' + name)
    return seal


def load(name, path):
    if name in sys.modules:
        raise ValueError('preloaded composition module: ' + name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def bind():
    seal = verify()
    if {'adapter', 'driver_boundary'}.intersection(sys.modules):
        raise ValueError('preloaded terminal dependency')
    previous = load('_kpf_transport_binding', Path(seal['predecessor']) / 'composition.py')
    previous.bind()
    boundary = Path(seal['boundary_path'])
    load('adapter', boundary / 'adapter.py')
    load('driver_boundary', boundary / 'driver_boundary.py')


def output_root():
    return sys.modules['_kpf_transport_binding'].output_root()
