"""Fail closed on missing build-time custody before resuming a witness cell."""
import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    'ggml_custody', Path(__file__).resolve().parent.parent / 'kpf174d-ggml-custody/custody.py')
ggml = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ggml)


def validate_custody(packet, bin_dir, proof):
    packet, bin_dir = Path(packet), Path(bin_dir)
    receipt_path = packet / 'BUILD-RECEIPT.json'
    manifest_path = packet / 'GGML-CUSTODY.json'
    helper = packet / 'verify_ggml_linkage.sh'
    receipt = json.loads(receipt_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    expected = ggml.create_manifest(bin_dir, receipt_path)
    if manifest != expected:
        raise ValueError('custody manifest differs from build receipt')
    receipt_sha, manifest_sha = ggml.digest(receipt_path), ggml.digest(manifest_path)
    if (proof.get('build_receipt_sha256') != receipt_sha
            or proof.get('ggml_custody_sha256') != manifest_sha):
        raise ValueError('build proof custody pin mismatch')
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
    return {'build_receipt_sha256': receipt_sha, 'ggml_custody_sha256': manifest_sha,
            'linkage_verifier_sha256': helper_sha}


def verify_mappings(packet, bin_dir, maps):
    manifest = json.loads((Path(packet) / 'GGML-CUSTODY.json').read_text())
    return ggml.verify_maps(manifest, maps, bin_dir)
