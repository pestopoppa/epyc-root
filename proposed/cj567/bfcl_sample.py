"""Offline, ID-only stratified sampling from immutable official BFCL V3 blobs.

This does not select by answers, certify full-BFCL representativeness, or score.
Existing coverage launchers deliberately do not consume this manifest yet.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from bfcl_native import CATEGORIES, PACKAGE, UPSTREAM


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def select(frame, per_category, seed):
    if type(per_category) is not int or per_category < 1:
        raise ValueError('positive integer per-category size required')
    if type(seed) is not int or seed < 0:
        raise ValueError('nonnegative integer seed required')
    if set(frame) != CATEGORIES:
        raise ValueError('exactly the six supported categories required')
    strata = {}
    for category in sorted(CATEGORIES):
        ids = frame[category]
        if (not isinstance(ids, list) or any(not isinstance(i, str) or
                not i.startswith(category + '_') or not i[len(category) + 1:].isdigit()
                for i in ids) or len(set(ids)) != len(ids)):
            raise ValueError('invalid or duplicate frame ID')
        if len(ids) < per_category:
            raise ValueError('sample exceeds a category population')
        def priority(qid):
            return digest(json.dumps([seed, category, qid], separators=(',', ':')).encode()), qid
        chosen = sorted(ids, key=priority)[:per_category]
        strata[category] = {'population_n': len(ids), 'sample_n': len(chosen),
                            'ids': chosen}
    return {'schema': 'epyc.bfcl-supported-sample.v1', 'upstream_commit': UPSTREAM,
            'method': 'lowest SHA-256 of compact JSON [seed,category,id]; without replacement',
            'seed': seed, 'per_category': per_category, 'strata': strata,
            'population_n': sum(len(v) for v in frame.values()),
            'sample_n': per_category * len(CATEGORIES),
            'scope': 'six supported single-turn AST categories only; not full BFCL V3',
            'aggregation': 'report each stratum separately; unweighted pooled score is not a population estimate',
            'score': None}


def prepare(checkout, per_category, seed):
    if os.environ.get('FILLER_ID') or os.environ.get('FILLER_DRYRUN'):
        raise ValueError('sample preparation must precede a grant')
    checkout = str(Path(checkout).resolve(strict=True))
    frame, bindings = {}, {}
    for category in sorted(CATEGORIES):
        records = []
        for folder in ('', 'possible_answer/'):
            path = f'{PACKAGE}/data/{folder}BFCL_v3_{category}.json'
            obj = f'{UPSTREAM}:{path}'
            raw = subprocess.check_output(['git', '-C', checkout, 'show', obj])
            blob = subprocess.check_output(['git', '-C', checkout, 'rev-parse', obj], text=True).strip()
            rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
            ids = [r['id'] for r in rows]
            if len(ids) != len(set(ids)):
                raise ValueError('duplicate source IDs')
            if folder:
                if any('ground_truth' not in r for r in rows):
                    raise ValueError('missing gold')
            elif any(not isinstance(r.get('question'), list) or len(r['question']) != 1
                     or not isinstance(r.get('function'), list) or not r['function'] for r in rows):
                raise ValueError('unsupported case shape')
            records.append(ids)
            bindings[path] = {'blob': blob, 'sha256': digest(raw), 'rows': len(rows)}
        if set(records[0]) != set(records[1]):
            raise ValueError('case/gold population mismatch')
        frame[category] = records[0]
    result = select(frame, per_category, seed)
    result['sources'] = bindings
    result['frame_sha256'] = digest(json.dumps({k: sorted(v) for k, v in frame.items()},
                                              sort_keys=True, separators=(',', ':')).encode())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', required=True)
    parser.add_argument('--per-category', required=True, type=int)
    parser.add_argument('--seed', required=True, type=int)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.checkout, args.per_category, args.seed)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')


if __name__ == '__main__':
    main()
