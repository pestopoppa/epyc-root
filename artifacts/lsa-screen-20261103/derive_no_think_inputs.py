#!/usr/bin/env python3
"""Derive v1 Qwen3.8 no-think inputs from the immutable frozen cohort."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

PREFIX = [248045, 846, 198]
SUFFIX = [248046, 198, 248045, 74455, 198, 248068, 271, 248069, 271]
RENDERER = 'qwen38-no-think-filler-prefix-v1'

def dump(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def derive(row, ids, cohort, encode, special):
    if len(ids) != row['prompt_n'] or len(ids) + row['max_output_tokens'] > 262144:
        raise ValueError('truncated or oversized source')
    if any(x in special for x in ids):
        raise ValueError('source contains special/control token')
    offsets = row['evidence_offsets']
    evidence = cohort['evidence'] if isinstance(cohort['evidence'], list) else [cohort['evidence']]
    if len(offsets) != len(evidence) or not offsets or min(offsets) <= 12:
        raise ValueError('invalid evidence offsets')
    filler = encode(f"\nArchive {cohort['id']}: unrelated record describing routine observations and revision notes.\n")
    if not filler or ids[:12] != (filler * (12 // len(filler) + 1))[:12]:
        raise ValueError('source does not start with known filler')
    question = encode('\nQuestion: ' + cohort['question'] + '\nAnswer:')
    if not question or ids[-len(question):] != question:
        raise ValueError('question provenance mismatch')
    last = 12
    for offset, item in zip(offsets, evidence):
        chunk = encode('\n' + item + '\n')
        if not chunk or offset < last or offset + len(chunk) > len(ids) - len(question) or ids[offset:offset+len(chunk)] != chunk:
            raise ValueError('evidence provenance/overlap mismatch')
        last = offset + len(chunk)
    derived = PREFIX + ids[12:] + SUFFIX
    assert len(derived) == len(ids)
    return derived, [x - 12 + len(PREFIX) for x in offsets]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for option in ('manifest', 'tokenizer', 'proof', 'smoke-manifest', 'output-dir'):
        p.add_argument('--' + option, type=Path, required=True)
    a = p.parse_args()
    from tokenizers import Tokenizer
    manifest_bytes = a.manifest.read_bytes(); m = json.loads(manifest_bytes)
    proof_bytes = a.proof.read_bytes(); proof = json.loads(proof_bytes)
    smoke_bytes = a.smoke_manifest.read_bytes(); smoke = json.loads(smoke_bytes)
    tokenizer_bytes = a.tokenizer.read_bytes()
    if (Path(m['model']).name != 'Qwen3.8-27B-Q8_0.gguf' or sha(tokenizer_bytes) != m['tokenizer_sha256'] or
        proof.get('schema') != 'lsa-candidate-tokenizer-parity-v1' or proof.get('passed') is not True or
        proof.get('probe_count') != 4 or len(proof.get('results', [])) != 4 or
        not all(x.get('equal') and x.get('expected') == x.get('observed') for x in proof['results']) or
        proof.get('tokenizer_sha256') != m['tokenizer_sha256'] or proof.get('model_sha256') != m['model_sha256'] or
        smoke.get('model_sha256') != m['model_sha256'] or len(smoke.get('rows', [])) != 1 or
        smoke['rows'][0].get('wrapper_prefix_ids') != PREFIX or smoke['rows'][0].get('wrapper_suffix_ids') != SUFFIX):
        raise ValueError('model, tokenizer or verified wrapper provenance mismatch')
    tok = Tokenizer.from_file(str(a.tokenizer))
    encode = lambda text: tok.encode(text, add_special_tokens=False).ids
    if encode('<|im_start|>user\n') != PREFIX or encode('<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n') != SUFFIX:
        raise ValueError('tokenizer control strings do not match wrapper')
    special = {v['id'] for v in json.loads(tokenizer_bytes).get('added_tokens', []) if v.get('special')}
    cohort_path = a.manifest.parent / 'cohort.jsonl'
    if sha(cohort_path.read_bytes()) != m['cohort_sha256']:
        raise ValueError('cohort digest mismatch')
    cohort = {r['id']: r for r in map(json.loads, cohort_path.read_text().splitlines())}
    if len(cohort) != len(cohort_path.read_text().splitlines()): raise ValueError('duplicate cohort IDs')
    keys = [(r['id'], r['nominal']) for r in m['rows']]
    if len(set(keys)) != len(keys) or {r['source_id'] for r in m['rows'] if r['split'] == 'dev'} & {r['source_id'] for r in m['rows'] if r['split'] == 'heldout'}:
        raise ValueError('duplicate rows or overlapping fitting/heldout sources')
    out = a.output_dir.resolve(); source = a.manifest.parent.resolve()
    if out == source or source in out.parents or out in source.parents:
        raise ValueError('output must be separate from source tree')
    out.mkdir(parents=True, exist_ok=False); (out / 'inputs').mkdir()
    (out / 'cohort.jsonl').write_bytes(cohort_path.read_bytes())
    rows = []
    for row in m['rows']:
        path = (source / row['token_ids']).resolve()
        if source not in path.parents: raise ValueError('source path escapes manifest directory')
        raw = gzip.decompress(path.read_bytes())
        if sha(raw) != row['token_ids_sha256']: raise ValueError('source row digest mismatch')
        c = cohort[row['id']]
        if any(row[k] != c[k] for k in ('id', 'split', 'group', 'source_id')) or row['expected'] != c['answer']:
            raise ValueError('cohort row mismatch')
        ids, offsets = derive(row, json.loads(raw), c, encode, special)
        payload = dump(ids); rel = 'inputs/' + row['id'] + '-' + str(row['nominal']) + '.json.gz'
        dest = out / rel
        with dest.open('xb') as f:
            with gzip.GzipFile(fileobj=f, mode='wb', mtime=0, filename='') as g: g.write(payload)
        rows.append(dict(row, token_ids=rel, token_ids_sha256=sha(payload), evidence_offsets=offsets,
                         original_row_sha256=sha(dump(row)), original_token_ids_sha256=row['token_ids_sha256']))
    m['rows'] = rows
    m['derivation'] = {'renderer': RENDERER, 'template': '<|im_start|>user\\n{raw minus 12 filler IDs}<|im_end|>\\n<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n',
        'prefix_ids': PREFIX, 'suffix_ids': SUFFIX, 'removed_filler_prefix_tokens': 12,
        'source_manifest_sha256': sha(manifest_bytes), 'tokenizer_sha256': sha(tokenizer_bytes),
        'parity_proof_sha256': sha(proof_bytes), 'smoke_manifest_sha256': sha(smoke_bytes),
        'renderer_sha256': sha(Path(__file__).read_bytes())}
    (out / 'manifest.json').write_bytes(dump(m) + b'\n')
    print('derived', len(rows), 'rows')

if __name__ == '__main__':
    main()
