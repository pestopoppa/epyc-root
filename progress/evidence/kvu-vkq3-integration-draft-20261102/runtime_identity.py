"""Pre-publication identity check against the prior VKQ3 runtime catalog.

This is not a source-build attestation or a runtime loader proof. Model weights
are deliberately excluded; prepare them separately, never inside a grant.
"""
import hashlib
import hmac
import os
import stat
from pathlib import Path

# artifacts/compute/kvu-vkq3-calibration-20261101/RUNTIME-INPUTS.sha256,
# committed on origin/main; explicit values avoid trusting a mutable catalog.
BIN = Path('/mnt/raid0/llm/kernels/builds/cpu-20261004-9a3f1392a/bin')
PINS = {
    'llama-tokenize': 'f1ec402de7d941f7ae43235f75e49b0e30d4d78337f7dcbb5737a23af794b62a',
    'libggml-cpu.so.0.16.0': 'd3b7cbda675a4eb5a684b77547cf3a1fefcab1a005edd73a5fe81c51fe55a471',
    'libggml-base.so.0.16.0': '22a2abb49aa904e07ceed81edbb39f84518ad66f99cc182ed03beafefff81a96',
    'libggml.so.0.16.0': 'd82ae95a59225e836061601cd715398284da3bdeddf2e4a2c4cb68ccab53aebe',
    'libllama-common.so.0.0.10325': 'dfc9ced0db5e9b6e7cd4f7728bb57a0ab92f8ed0ea203c864be802d428a64513',
    'libllama.so.0.0.10325': '6f732ca9174bf0b4bccb9ba8eab50dcc1ba9aa9685a944bc908f1506b8388f57',
}


def verify_runtime(directory=BIN, pins=None):
    """Hash canonical regular files once, raising on missing or changed content."""
    pins = PINS if pins is None else pins
    directory = Path(directory)
    for name, expected in pins.items():
        if Path(name).name != name or not name:
            raise ValueError('invalid filename')
        fd = os.open(directory / name, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError('runtime entry is not a regular file: ' + name)
            digest = hashlib.sha256()
            while chunk := os.read(fd, 1024 * 1024):
                digest.update(chunk)
            if not hmac.compare_digest(digest.hexdigest(), expected):
                raise ValueError('runtime digest mismatch: ' + name)
        finally:
            os.close(fd)
    return dict(pins)


if __name__ == '__main__':
    import json
    print(json.dumps(verify_runtime(), sort_keys=True))
