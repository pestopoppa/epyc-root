"""Fail closed on missing build-time custody before resuming a witness cell."""
import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    'ggml_custody', Path(__file__).resolve().parent.parent / 'kpf174d-ggml-custody/custody.py')
ggml = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ggml)


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
    return ggml.verify_maps(manifest, maps, bin_dir)
