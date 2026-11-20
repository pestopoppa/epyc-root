"""Offline materialization and content-pinned native capture of supported samples."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

from bfcl_native import PACKAGE, UPSTREAM
from bfcl_sample import prepare


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode()


def materialize(checkout, manifest):
    # prepare refuses grants and independently reconstructs the entire frame.
    if prepare(checkout, manifest['per_category'], manifest['seed']) != manifest:
        raise ValueError('sample manifest differs from immutable source reconstruction')
    rows = []
    for category, stratum in manifest['strata'].items():
        records = []
        for prefix in ('', 'possible_answer/'):
            path = f'{PACKAGE}/data/{prefix}BFCL_v3_{category}.json'
            raw = subprocess.check_output(['git', '-C', str(checkout), 'show', f'{UPSTREAM}:{path}'])
            if hashlib.sha256(raw).hexdigest() != manifest['sources'][path]['sha256']:
                raise ValueError('source changed during materialization')
            records.append({r['id']: r for r in map(json.loads, raw.splitlines())})
        for qid in stratum['ids']:
            rows.append({'category': category, 'case': records[0][qid], 'gold': records[1][qid]})
    return {'schema': 'epyc.bfcl-supported-capture.v1', 'sample': copy.deepcopy(manifest), 'cases': rows}


class BoundSample:
    """Private frozen copy; expected digest must be prepared in launcher config."""
    def __init__(self, path, expected_sha256):
        raw = Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError('prepared sample digest mismatch')
        bundle = json.loads(raw)
        if bundle['schema'] != 'epyc.bfcl-supported-capture.v1' or bundle['sample']['upstream_commit'] != UPSTREAM:
            raise ValueError('sample schema/checker mismatch')
        self._bundle = bundle
        self.sha256 = expected_sha256
        expected = [(c, qid) for c, s in bundle['sample']['strata'].items() for qid in s['ids']]
        actual = [(r['category'], r['case']['id']) for r in bundle['cases']]
        if actual != expected or len(set(actual)) != len(actual):
            raise ValueError('prepared sample order/IDs mismatch')
        self._records = {r['case']['id']: encoded(r) for r in bundle['cases']}
        for row in bundle['cases']:
            self.validate(row)

    def rows(self):
        return copy.deepcopy(self._bundle['cases'])

    def validate(self, row):
        if (row['case']['id'] != row['gold']['id'] or
                self._records.get(row['case']['id']) != encoded(row)):
            raise ValueError('case/gold differs from prepared sample')
        category = row['category']
        sources = self._bundle['sample']['sources']
        # Separate scope: legacy coverage lock contains released HF corpus bytes.
        lock = json.loads(Path(__file__).with_name('bfcl-supported-frame-lock.json').read_bytes())
        sample = self._bundle['sample']
        if any(sample[key] != lock[key] for key in ('upstream_commit', 'sources', 'frame_sha256')):
            raise ValueError('sample source differs from pinned corpus')
        return {'prepared_sample_sha256': self.sha256, 'sample': copy.deepcopy(sample)}



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', required=True)
    parser.add_argument('--selection', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    bundle = materialize(args.checkout, json.loads(args.selection.read_bytes()))
    with args.output.open('xb') as stream:
        stream.write(encoded(bundle) + b'\n')
