#!/usr/bin/env python3
"""Pin IFBench inputs for existing --questions-in generation and official scoring.

This module never imports IFBench or generates a response. Canonical runner
scores for ifbench_external are out of coverage: only the pinned official
run_eval.py strict/loose outputs are IFBench observations, never routing priors.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

COMMIT = '1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d'
CORPUS_SHA256 = 'd2ada7da94a38cfe406351614c4e686846ed2da6d1b339db95fa5ead19554a4a'
SUITE = 'ifbench_candidate'
BENCHMARK_KEY = 'ifbench_prompt_loose'
NLTK_RESOURCES = ('tokenizers/punkt', 'tokenizers/punkt_tab', 'corpora/stopwords',
                  'taggers/averaged_perceptron_tagger_eng')


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_corpus(path: Path) -> list[dict]:
    raw = path.read_bytes()
    if digest(raw) != CORPUS_SHA256:
        raise ValueError('IFBench corpus bytes differ from pinned official commit')
    rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    validate_corpus(rows)
    return rows


def validate_corpus(rows: list[dict]) -> None:
    if len(rows) != 300 or len({r['prompt'] for r in rows}) != 300:
        raise ValueError('full unique 300-prompt corpus required')
    if len({r['key'] for r in rows}) != 300:
        raise ValueError('duplicate corpus key')
    if sum(len(r['instruction_id_list']) for r in rows) != 344:
        raise ValueError('344 constraint instances required')
    if len({i for r in rows for i in r['instruction_id_list']}) != 58:
        raise ValueError('58 constraint IDs required')
    for row in rows:
        if not isinstance(row['prompt'], str) or not row['prompt']:
            raise ValueError('nonempty exact prompt required')
        if len(row['kwargs']) != len(row['instruction_id_list']):
            raise ValueError('kwargs/constraint length mismatch')


def exact_response_join(corpus: list[dict], responses: list[dict]) -> list[dict]:
    """Refuse missing/extra/duplicate/normalized prompts before official scoring."""
    expected = {r['prompt'] for r in corpus}
    prompts = [r['prompt'] for r in responses]
    if len(prompts) != len(set(prompts)) or set(prompts) != expected:
        raise ValueError('response prompt set must equal corpus exactly, once each')
    by_prompt = {r['prompt']: r for r in responses}
    if any(not isinstance(r.get('response'), str) for r in responses):
        raise ValueError('response must be a string; empty responses remain incorrect')
    return [{'prompt': row['prompt'], 'response': by_prompt[row['prompt']]['response']}
            for row in corpus]


def export_runner_responses(corpus: list[dict], results: dict) -> list[dict]:
    expected = {str(row['key']) for row in corpus}
    if set(results) != expected:
        raise ValueError('runner IDs must match all pinned corpus keys')
    rows = [{'prompt': row['prompt'], 'response': results[str(row['key'])]['response']}
            for row in corpus]
    return exact_response_join(corpus, rows)


def manifest(corpus: list[dict]) -> dict:
    validate_corpus(corpus)
    counts = Counter(i for r in corpus for i in r['instruction_id_list'])
    return {
        'suites': {SUITE: [
            {'id': str(row['key']), 'prompt': row['prompt'], 'expected': '',
             'scoring_method': 'ifbench_external', 'scoring_config': {},
             'source': 'allenai/IFBench@' + COMMIT} for row in corpus]},
        'sample': {'suite': SUITE, 'full_population': True, 'n': 300,
                   'population_sha256': CORPUS_SHA256, 'commit': COMMIT},
        'preregistered': {
            'benchmark_key': BENCHMARK_KEY,
            'secondary_benchmark_key': 'ifbench_prompt_strict',
            'oracle': 'pinned official run_eval.py; no alternative predicate',
            'constraint_counts': dict(sorted(counts.items())),
            'prompt_sha256_by_key': {str(r['key']): digest(r['prompt'].encode())
                                    for r in corpus},
            'denominator': 300, 'pairing': 'same exact 300 prompts',
            'noise_floor_pp': {'one_item': 100 / 300, 'single_arm_95_approx': 5.6,
                               'unpaired_difference_95_approx': 8.0},
            'comparison': 'existing scripts/autopilot/paired_stats.py McNemar',
            'generation_only_runner_scores': 'out-of-coverage',
            'routing_or_adoption': False,
        },
    }


def nltk_seed_manifest(path: Path) -> dict:
    """Freeze a preseeded resource tree without importing NLTK or downloading."""
    for resource in NLTK_RESOURCES:
        if not (path / resource).is_dir():
            raise ValueError('preseed missing: ' + resource)
    files = {}
    for child in sorted(path.rglob('*')):
        if child.is_symlink():
            raise ValueError('NLTK seed must not contain symlinks')
        if child.is_file():
            raw = child.read_bytes()
            files[str(child.relative_to(path))] = {'sha256': digest(raw), 'bytes': len(raw)}
    return {'resources': list(NLTK_RESOURCES), 'files': files,
            'network_during_scoring': 'must be denied in offhost execution recipe'}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--responses', type=Path)
    p.add_argument('--nltk-seed', type=Path)
    a = p.parse_args(argv)
    rows = load_corpus(a.corpus)
    doc = manifest(rows)
    if a.responses:
        responses = [json.loads(x) for x in a.responses.read_text().splitlines() if x.strip()]
        doc['official_prompt_response_join'] = exact_response_join(rows, responses)
    if a.nltk_seed:
        doc['nltk_seed'] = nltk_seed_manifest(a.nltk_seed)
    a.out.write_text(json.dumps(doc, sort_keys=True, indent=2) + '\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
