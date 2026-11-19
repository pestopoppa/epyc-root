"""Verify the complete research import chain before executing any of it."""
import hashlib
import importlib.util
from pathlib import Path

SOURCE_COMMIT = '1157adc2f007d1b0c45ddc6daf91eafc45358df7'
ROOT = Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174d/research')
PINS = {
    'scripts/benchmark/kpf174/kpf174c_bisect.py': 'b6b20eff44be06e46f63e132634227d7038032fce980570426ed0a7e73808084',
    'scripts/benchmark/kpf174/kpf174_swa_drafter.py': 'd008fc6bd0e2541b92f1cc7ef1acb72931332d59743c3d11615a3cf8c3d85725',
    'scripts/benchmark/kpf13/kpf13_restore_ab.py': '2683c46d8cb46ebd0d35d66c40c6cf970e6a181a6b8704f41ab1af6f3debba98',
    'scripts/benchmark/kpf13/argv.gpu-27b-dflash2.txt': 'acc297a1078a78e25bcd2715cb7105a2eabb35770332a506eac9e12a45a28702',
}


def verify_sources(root=ROOT):
    root = Path(root).resolve()
    for name, expected in PINS.items():
        path = root / name
        if not path.resolve().is_relative_to(root):
            raise ValueError('research source escapes root: ' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('research source pin mismatch: ' + name)
    return {'source_commit': SOURCE_COMMIT, 'files': dict(PINS)}


def load_harness(root=ROOT):
    verify_sources(root)
    path = Path(root) / 'scripts/benchmark/kpf174/kpf174c_bisect.py'
    spec = importlib.util.spec_from_file_location('kpf174c_pinned', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module.k13
