"""Fail closed on missing build-time custody before resuming a witness cell."""
import importlib.util
import json
import os
import re
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    'ggml_custody', Path(__file__).resolve().parent.parent / 'kpf174d-ggml-custody/custody.py')
ggml = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ggml)
APPLICATION = ('libllama.so', 'libllama-common.so', 'libllama-server-impl.so')


def serving_artifacts(bin_dir, receipt):
    """Reopen every serving artifact against its original receipt entry."""
    root = Path(bin_dir).resolve(strict=True)
    libraries = receipt.get('libraries', {})
    if set(libraries) != set(ggml.REQUIRED) | set(APPLICATION):
        raise ValueError('incomplete serving library receipt')
    # The receipt remains immutable when its original build is relocated.
    origin = Path(receipt['run_dir']) / 'build/bin' if 'run_dir' in receipt else root
    paths = {}
    for name in (*ggml.REQUIRED, *APPLICATION, 'llama-server'):
        p = (root / name).resolve(strict=True)
        expected = receipt.get('binary_sha256') if name == 'llama-server' else libraries[name]
        if (p.parent != root or not p.is_file()
                or receipt.get('files', {}).get(str(origin / p.name)) != expected
                or ggml.digest(p) != expected):
            raise ValueError('serving artifact not attested: ' + name)
        paths[name] = p
    if len(set(paths.values())) != len(paths):
        raise ValueError('distinct serving artifacts required')
    return paths


def relocated_manifest(bin_dir, receipt_path, receipt, original_bin):
    """Reopen retained bytes against the immutable receipt's original paths.

    Relocation changes paths and inodes, never the receipt or its attestations.
    All seven serving libraries and the executable must still be attested.
    """
    root = Path(bin_dir).resolve(strict=True)
    origin = Path(original_bin)
    if (not origin.is_absolute() or '..' in origin.parts
            or origin != Path(receipt.get('run_dir', '')) / 'build/bin'):
        raise ValueError('relocation origin differs from receipt run directory')
    if (receipt.get('schema') != 'epyc.kpf174d.build.v1'
            or receipt.get('status') != 'built'
            or receipt.get('source_commit') != ggml.SOURCE
            or receipt.get('parent_source') != ggml.PARENT):
        raise ValueError('invalid relocated build receipt')
    libraries = receipt.get('libraries', {})
    required = {*ggml.REQUIRED, 'libllama.so', 'libllama-common.so',
                'libllama-server-impl.so'}
    if set(libraries) != required:
        raise ValueError('incomplete relocated library receipt')
    entries = {}
    for name in sorted(required | {'llama-server'}):
        local = (root / name).resolve(strict=True)
        if local.parent != root or not local.is_file():
            raise ValueError('relocated artifact escapes bin: ' + name)
        expected = receipt['binary_sha256'] if name == 'llama-server' else libraries[name]
        if (receipt.get('files', {}).get(str(origin / local.name)) != expected
                or ggml.digest(local) != expected):
            raise ValueError('relocated artifact not attested: ' + name)
        if name in ggml.REQUIRED:
            entries[name] = {'filename': local.name, 'sha256': expected}
    if len({v['filename'] for v in entries.values()}) != len(ggml.REQUIRED):
        raise ValueError('distinct relocated ggml libraries required')
    return {'schema': 'kpf174d.ggml-custody.v1', 'source_commit': ggml.SOURCE,
            'parent_source': ggml.PARENT,
            'build_receipt_sha256': ggml.digest(receipt_path), 'libraries': entries}


def validate_custody(packet, bin_dir, proof):
    packet, bin_dir = Path(packet), Path(bin_dir)
    receipt_path = packet / 'BUILD-RECEIPT.json'
    manifest_path = packet / 'GGML-CUSTODY.json'
    helper = packet / 'verify_ggml_linkage.sh'
    receipt = json.loads(receipt_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    receipt_sha, manifest_sha = ggml.digest(receipt_path), ggml.digest(manifest_path)
    if (proof.get('build_receipt_sha256') != receipt_sha
            or proof.get('ggml_custody_sha256') != manifest_sha):
        raise ValueError('build proof custody pin mismatch')
    if 'relocated_from_bin' in proof:
        expected = relocated_manifest(bin_dir, receipt_path, receipt, proof['relocated_from_bin'])
    else:
        expected = ggml.create_manifest(bin_dir, receipt_path)
    if manifest != expected:
        raise ValueError('custody manifest differs from build receipt')
    serving_artifacts(bin_dir, receipt)
    if (proof.get('source_commit') != ggml.SOURCE
            or proof.get('parent_source') != ggml.PARENT
            or proof.get('binary_sha256') != receipt.get('binary_sha256')
            or ggml.digest(bin_dir / 'llama-server') != receipt.get('binary_sha256')
            or receipt.get('linkage_pass') is not True):
        raise ValueError('build proof identity mismatch')
    helper_sha = ggml.digest(helper)
    if (helper_sha != receipt.get('linkage_verifier_sha256')
            or helper_sha != proof.get('linkage_verifier_sha256')):
        raise ValueError('linkage helper pin mismatch')
    for name, entry in manifest['libraries'].items():
        if proof.get('libraries', {}).get(name) != entry['sha256']:
            raise ValueError('proof library differs from receipt: ' + name)
    result = {'build_receipt_sha256': receipt_sha, 'ggml_custody_sha256': manifest_sha,
              'linkage_verifier_sha256': helper_sha}
    if 'relocated_from_bin' in proof:
        result.update(relocated_from_bin=proof['relocated_from_bin'],
                      retained_bin=str(bin_dir.resolve(strict=True)))
    return result


def verify_mappings(packet, bin_dir, maps):
    manifest = json.loads((Path(packet) / 'GGML-CUSTODY.json').read_text())
    receipt_path = Path(packet) / 'BUILD-RECEIPT.json'
    if ggml.digest(receipt_path) != manifest.get('build_receipt_sha256'):
        raise ValueError('mapping receipt pin mismatch')
    paths = serving_artifacts(bin_dir, json.loads(receipt_path.read_text()))
    result = ggml.verify_maps(manifest, maps, bin_dir)
    expected = {}
    for name in APPLICATION:
        p = paths[name]
        st = p.stat()
        expected[str(p)] = (os.major(st.st_dev), os.minor(st.st_dev), st.st_ino)
    seen = set()
    for line in maps.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6 or not re.search(r'/libllama(?:[-.]|\.so)', parts[5]):
            continue
        name = parts[5]
        if name.endswith(' (deleted)'):
            raise ValueError('mapped deleted application library')
        try:
            major, minor = (int(x, 16) for x in parts[3].split(':'))
            inode = int(parts[4])
            path = str(Path(name).resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise ValueError('invalid application mapping') from exc
        if expected.get(path) != (major, minor, inode):
            raise ValueError('unexpected or replaced mapped application library: ' + name)
        seen.add(path)
    if seen != set(expected):
        raise ValueError('not all attested application libraries are mapped')
    return dict(result, mapped=sorted(set(result['mapped']) | seen))
