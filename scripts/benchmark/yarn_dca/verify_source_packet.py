#!/usr/bin/env python3
"""Check prepared DCA source custody, without building or claiming binary provenance."""
import hashlib
import json
from pathlib import Path

BASE = 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
DCA = '9264f8095e4272f84e3b375e73b57ec380ecb328'
FA = '0c480112766f59eeb9f4587b952c1d5e29b0df81'
TREE = '47e8f54c5c06a3983442fc692fd65d26392d9636'
REVIEWED = {'common/arg.cpp', 'common/common.cpp', 'common/common.h', 'include/llama.h', 'tests/CMakeLists.txt'}

class CustodyError(ValueError):
    pass

def verify(source, audit, review, archive):
    if source.get('status') != 'NOT_BUILT_NOT_QUALIFIED':
        raise CustodyError('unexpected source state')
    if (source.get('production_base'), source.get('dca_tip'), source.get('fa_tip'), source.get('prospective_tree')) != (BASE, DCA, FA, TREE):
        raise CustodyError('source identities changed')
    if (audit.get('base'), audit.get('dca'), audit.get('fa'), audit.get('prospective_tree')) != (BASE, DCA, FA, TREE):
        raise CustodyError('audit identities differ')
    if audit.get('violations') != []:
        raise CustodyError('source audit has violations')
    pending = audit.get('both_changed_require_semantic_review')
    if not isinstance(pending, list) or {x.get('path') for x in pending} != REVIEWED or len(pending) != len(REVIEWED):
        raise CustodyError('shared-path review set differs')
    if review.get('base') != BASE or review.get('candidate_tree') != TREE or set(review.get('files', [])) != REVIEWED:
        raise CustodyError('review identities or scope differ')
    checks = review.get('checks', {})
    if set(checks) != {'fa', 'dca'} or any(checks[x].get('reverse_and_roundtrip') != 'PASS' for x in checks):
        raise CustodyError('parent roundtrip review incomplete')
    # This verifies exact archive bytes only. It does not establish a build or
    # prove the archive independently represents a git tree.
    h = hashlib.sha256()
    p = Path(archive)
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    if p.stat().st_size != source.get('archive_size') or h.hexdigest() != source.get('archive_sha256'):
        raise CustodyError('source archive bytes changed')
    return {'state':'SOURCE_PACKET_ONLY', 'tree':TREE, 'archive_sha256':h.hexdigest(),
            'limits':['no merge commit or build attestation','textual source review only',
                      'no runtime, memory, residency or qualification evidence']}

def main():
    import argparse
    p = argparse.ArgumentParser()
    for flag in ('source', 'audit', 'review', 'archive'):
        p.add_argument('--'+flag, required=True)
    a = p.parse_args()
    inputs = [json.loads(Path(getattr(a, key)).read_text()) for key in ('source', 'audit', 'review')]
    print(json.dumps(verify(*inputs, a.archive), indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
