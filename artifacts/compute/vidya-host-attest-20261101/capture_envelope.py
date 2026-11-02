#!/usr/bin/env python3
"""Prospective standalone collector probe; never a benchmark attestation."""
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'source'))
import canonical_host_attestation as native
COMMIT = 'f311e004e2eaaf23bd87d2ab4a7530396c77830f'
def sha(data):
    return hashlib.sha256(data).hexdigest()
def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
def validate(envelope, raw):
    if envelope.get('schema') != 'epyc.vidya.canonical-host-source-envelope.probe.v1':
        raise ValueError('unexpected envelope schema')
    if envelope.get('historical_warrant') is not False or envelope.get('source_class') is not None:
        raise ValueError('standalone probe cannot assign warrant or source class')
    expected = json.loads((ROOT / 'source-manifest.json').read_text())
    for key, name in (('collector_source', 'server_np_sweep.py'),
                      ('capture_source', 'canonical_host_attestation.py')):
        source = envelope[key]
        if source['path'] != 'source/' + name or source['sha256'] != expected[name]:
            raise ValueError('source reference mismatch: ' + name)
        if sha((ROOT / 'source' / name).read_bytes()) != expected[name]:
            raise ValueError('source snapshot mismatch: ' + name)
    if envelope['native_artifact']['path'] != 'native-host-observation.json':
        raise ValueError('unexpected native artifact path')
    if envelope['native_artifact']['bytes'] != len(raw):
        raise ValueError('native artifact size mismatch')
    if sha(raw) != envelope['native_artifact']['sha256']:
        raise ValueError('native artifact digest mismatch')
    payload = json.loads(raw)
    if payload.get('schema') != 'canonical-host-attestation-v1':
        raise ValueError('unexpected native schema')
    if payload != envelope['native_record']:
        raise ValueError('native projection mismatch')
    if payload['source_sha256'] != envelope['collector_source']['sha256']:
        raise ValueError('collector source mismatch')
    for key in ('capture_started_at', 'capture_ended_at', 'claim_mode', 'capture_started_monotonic_ns', 'capture_ended_monotonic_ns', 'attestation', 'host_health_warnings'):
        if key not in payload:
            raise ValueError('missing native field: ' + key)
    if payload['capture_ended_monotonic_ns'] < payload['capture_started_monotonic_ns']:
        raise ValueError('reversed monotonic interval')
    if payload['claim_mode'] != 'explicit_unlocked_override':
        raise ValueError('standalone probe must remain explicitly unlocked')
    return True

def main():
    # Source bytes are checked before the collector executes; no read-side reconstruction.
    sources = {}
    expected = json.loads((ROOT / 'source-manifest.json').read_text())
    for name, digest in expected.items():
        data = (ROOT / 'source' / name).read_bytes()
        if sha(data) != digest:
            raise ValueError('source snapshot mismatch: ' + name)
        sources[name] = digest
    record = native.capture('explicit_unlocked_override')
    raw = encode(record)
    native_path = ROOT / 'native-host-observation.json'
    with native_path.open('xb') as stream:
        stream.write(raw)
    envelope = {
        'schema': 'epyc.vidya.canonical-host-source-envelope.probe.v1',
        'written_at': datetime.now(timezone.utc).isoformat(),
        'context': 'Fresh standalone read-only collector probe. No benchmark or CPU-region claim was run; native capture_scope is preserved verbatim but is not asserted as launch provenance.',
        'research_source_commit': COMMIT,
        'collector_source': {'path': 'source/server_np_sweep.py', 'sha256': sources['server_np_sweep.py']},
        'capture_source': {'path': 'source/canonical_host_attestation.py', 'sha256': sources['canonical_host_attestation.py']},
        'native_artifact': {'path': native_path.name, 'sha256': sha(raw), 'bytes': len(raw)},
        'native_record': record,
        'source_class': None,
        'source_class_status': 'Owner review pending; no registered adapter, grading or planning-context claim.',
        'not_attested': ['cache drop', 'NUMA re-warm', 'THP', 'benchmark launch', 'CPU region admission', 'compliance', 'measurement grade'],
        'historical_warrant': False,
    }
    validate(envelope, native_path.read_bytes())
    with (ROOT / 'source-envelope.json').open('xb') as stream:
        stream.write(encode(envelope))
if __name__ == '__main__':
    main()
