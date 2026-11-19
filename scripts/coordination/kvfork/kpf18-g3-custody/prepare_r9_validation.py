#!/usr/bin/env python3
"""Check retained R9 validation custody independently; never dispatch runtime."""
import hashlib
import json
from pathlib import Path
import re
import sys

from rebind_manifest import LINE, read_regular, rebind
from verify_manifest import verify

R9 = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-format-r9')
PINS = {
    'q0/SOURCES.sha256': '3c32bf352e1f72426647c394d70a4b7c90399c9108ad9cbd503d34b2f25e6921',
    'q0/NATIVE-SOURCES.sha256': 'b3086e9fd26777da741cbb43bde4982d9443073b675e30cecab46d106034c2c2',
    'data/SHA256SUMS': '4433e7b63dd90669de27b15d689f76267ec8bd8d2dff6f0a40099e7b927017f0',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def absolute_inventory(raw, root):
    """Translate a pinned relative inventory without changing any digest."""
    result = []
    paths = set()
    for line in raw.decode('utf-8').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if not match:
            raise ValueError('malformed relative inventory')
        checksum, name = match.groups()
        path = Path(name)
        if path.is_absolute() or any(part in ('', '.', '..') for part in name.split('/')):
            raise ValueError('noncanonical relative inventory path')
        full = str(root / path)
        if full in paths:
            raise ValueError('duplicate inventory path')
        paths.add(full)
        result.append(f'{checksum}  {full}')
    if not result:
        raise ValueError('empty inventory')
    return ('\n'.join(result) + '\n').encode()


def prepare_r9(output, mapping_file, root=R9, pins=None):
    """Retain pinned originals and independently verify each manifest closure."""
    pins = PINS if pins is None else pins
    if set(pins) != set(PINS):
        raise ValueError('unexpected original manifest inventory')
    root, output = Path(root), Path(output)
    originals = {name: read_regular(root / name) for name in pins}
    for name, raw in originals.items():
        if digest(raw) != pins[name]:
            raise ValueError('original manifest pin mismatch: ' + name)
    mapping_raw = read_regular(mapping_file)
    mapping = json.loads(mapping_raw)
    if not isinstance(mapping, dict):
        raise ValueError('mapping must be an object')
    # Only the independent native inventory may use historical byte-equal paths.
    native_paths = []
    for line in originals['q0/NATIVE-SOURCES.sha256'].decode().splitlines():
        match = LINE.fullmatch(line)
        if not match:
            raise ValueError('malformed native inventory')
        native_paths.append(match.group(2))
    if set(mapping) - set(native_paths):
        raise ValueError('unbound mapping key')
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in mapping.items()):
        raise ValueError('mapping must contain string paths')
    # Refuse before reading any inventory member, even with alternate API pins.
    absolute = {name: absolute_inventory(originals[name], (root / name).parent)
                for name in ('q0/SOURCES.sha256', 'data/SHA256SUMS')}
    selected_paths = [mapping.get(path, path) for path in native_paths]
    for raw in absolute.values():
        selected_paths.extend(LINE.fullmatch(line).group(2) for line in raw.decode().splitlines())
    for path in [*native_paths, *selected_paths]:
        if Path(path).suffix.lower() == '.gguf' or Path(path).name.upper() == 'FULL-MODEL.SHA256':
            raise ValueError('model input forbidden in custody-only preparation: ' + path)
    if not output.is_absolute():
        raise ValueError('output must be absolute')
    output.mkdir(exist_ok=False)
    (output / 'INCOMPLETE').write_text('Custody incomplete; runtime disabled.\n')
    for name, raw in originals.items():
        (output / ('original--' + name.replace('/', '--'))).write_bytes(raw)
    checks = []
    for name in ('q0/SOURCES.sha256', 'data/SHA256SUMS', 'q0/NATIVE-SOURCES.sha256'):
        raw = originals[name]
        label = name.replace('/', '--')
        if name == 'q0/NATIVE-SOURCES.sha256':
            target = output / ('rebound--' + label)
            rebind(root / name, mapping, target, pins[name])
            expected = [mapping.get(path, path) for path in native_paths]
        else:
            target = output / ('absolute--' + label)
            target.write_bytes(absolute[name])
            expected = [LINE.fullmatch(line).group(2) for line in target.read_text().splitlines()]
        count = verify(target, expected, digest(read_regular(target)))
        checks.append(dict(original=str(root / name), original_sha256=pins[name],
                           manifest=str(target), manifest_sha256=digest(read_regular(target)),
                           expected_paths=expected, verified_entries=count))
        (output / 'VERIFIED-CLOSURES.json').write_text(json.dumps(checks, indent=2) + '\n')
    (output / 'rebinding.json').write_text(json.dumps(mapping, indent=2) + '\n')
    receipt = dict(status='INDEPENDENT_R9_CUSTODY_ONLY', runtime_dispatch=False,
                   checks=checks, model_files_read=False,
                   limits=['No R9 tests rerun or inference performed',
                           'Historical helper bytes do not establish current lock semantics',
                           'No changes applied to NI packet or its guard',
                           'Live cancellation, output supervision and GPU qualification remain open'])
    (output / 'RESULT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (output / 'INCOMPLETE').unlink()
    return receipt


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_r9_validation.py NEW-absolute-output mapping.json')
    try:
        print(json.dumps(prepare_r9(*sys.argv[1:]), indent=2))
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise SystemExit('REFUSED: ' + str(exc))
