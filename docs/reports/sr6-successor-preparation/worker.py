#!/usr/bin/env python3
"""SR-6 four-arm capture planner; NOT a runnable inference worker.

This model-free component validates the pre-exposure packet and constructs a
counterbalanced capture schedule. It intentionally cannot launch a server or
emit observations. Qualification must integrate actual admission, separate
server lifetimes, native response/placement capture, STOP and drain, and a
predeclared uncertainty rule before a row can be published.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ARMS = ('composed3', 'composed4', 'mtp3', 'mtp4', 'mtp4_repeat')
HEX = re.compile(r'^[0-9a-f]{64}$')


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def repetition(tokens):
    """Return counts of repeated 5-gram occurrences, not distinct 5-grams."""
    if not isinstance(tokens, list) or not all(type(x) is int and x >= 0 for x in tokens):
        raise ValueError('rendered tokens must be nonnegative integer IDs')
    seen = set()
    repeats = 0
    for i in range(max(0, len(tokens) - 4)):
        gram = tuple(tokens[i:i + 5])
        repeats += gram in seen
        seen.add(gram)
    total = max(0, len(tokens) - 4)
    return {'numerator': repeats, 'denominator': total, 'fraction': repeats / total if total else None}


def build_schedule(packet):
    """Validate all three planned windows before producing any arm schedule.

    Repetition counts are over provided tokenizer IDs; identity/provenance of
    the rendering and tokenization remains an external preflight responsibility.
    """
    if not isinstance(packet, dict) or packet.get('schema') != 'sr6.capture-plan.v1':
        raise ValueError('invalid packet schema')
    seals = packet.get('seals')
    required = ('model', 'binary', 'libraries', 'launch', 'template', 'sampler',
                'tokenizer', 'prior_prompt_hashes', 'decision_rule')
    if not isinstance(seals, dict) or any(not isinstance(seals.get(k), str) or not HEX.fullmatch(seals[k]) for k in required):
        raise ValueError('missing preflight identity seal')
    sampler = packet.get('sampler')
    if not isinstance(sampler, dict) or not sampler or digest_bytes(canonical(sampler)) != seals['sampler']:
        raise ValueError('sampler and seal mismatch')
    if set(sampler) & {'prompt', 'seed', 'cache_prompt', 'return_tokens'}:
        raise ValueError('sampler may not override matching fields')
    prior = packet.get('prior_prompt_hashes')
    if (not isinstance(prior, list) or any(not isinstance(x, str) or not HEX.fullmatch(x) for x in prior)
            or digest_bytes(canonical(prior)) != seals['prior_prompt_hashes']):
        raise ValueError('invalid prior prompt inventory or seal')
    windows = packet.get('windows')
    if not isinstance(windows, list) or len(windows) != 3:
        raise ValueError('exactly three predeclared windows required')
    ids, seeds, rendered_hashes, raw_hashes, window_ids = set(), set(), set(), set(), set()
    schedule = []
    for wi, window in enumerate(windows):
        wid = window.get('id') if isinstance(window, dict) else None
        if not isinstance(wid, str) or not wid or wid in window_ids:
            raise ValueError('invalid or duplicate window')
        window_ids.add(wid)
        blocks = window.get('blocks')
        if not isinstance(blocks, list) or len(blocks) < 4:
            raise ValueError('at least four blocks per window needed for rotated arm order')
        for bi, block in enumerate(blocks):
            prompts = block.get('prompts') if isinstance(block, dict) else None
            if not isinstance(prompts, list) or not prompts:
                raise ValueError('empty block')
            prepared = []
            for p in prompts:
                if not isinstance(p, dict):
                    raise ValueError('invalid prompt')
                ident, seed, category = p.get('id'), p.get('seed'), p.get('class')
                raw, rendered, tokens = p.get('prompt'), p.get('rendered'), p.get('rendered_tokens')
                if not isinstance(ident, str) or not ident or ident in ids:
                    raise ValueError('missing or duplicate prompt id')
                if type(seed) is not int or seed < 0 or seed in seeds:
                    raise ValueError('missing or duplicate prompt seed')
                if category not in ('code', 'rag', 'prose') or not isinstance(raw, str) or not raw or not isinstance(rendered, str) or not rendered:
                    raise ValueError('invalid prompt or class')
                raw_sha = digest_bytes(raw.encode('utf-8'))
                rendered_sha = digest_bytes(rendered.encode('utf-8'))
                if ({raw_sha, rendered_sha} & (raw_hashes | rendered_hashes | set(prior))):
                    raise ValueError('duplicate or previously exposed prompt')
                metric = repetition(tokens)
                if metric['denominator'] == 0:
                    raise ValueError('rendered prompt too short for repetition metric')
                ids.add(ident); seeds.add(seed); raw_hashes.add(raw_sha); rendered_hashes.add(rendered_sha)
                prepared.append({'id': ident, 'class': category, 'seed': seed, 'prompt_sha256': raw_sha,
                                 'rendered_sha256': rendered_sha, 'rendered_tokens_sha256': digest_bytes(canonical(tokens)),
                                 'repeated_5gram': metric, 'rendered': rendered})
            # Repeat arm is independently served too. Rotation across five
            # positions prevents repeatedly privileging one arm's position.
            offset = (wi * len(blocks) + bi) % len(ARMS)
            order = ARMS[offset:] + ARMS[:offset]
            schedule.append({'window': wid, 'block': bi, 'arm_order': order, 'prompts': prepared})
    classes = {p['class'] for b in schedule for p in b['prompts']}
    if classes != {'code', 'rag', 'prose'}:
        raise ValueError('code, rag and prose classes all required')
    return {'schema': 'sr6.capture-schedule.v1', 'state': 'NOT_RUN', 'verdict': None,
            'sampler_sha256': seals['sampler'], 'blocks': schedule,
            'limitations': ['plan only; no grant, runtime, residency, exposure or response evidence',
                            'rendering, tokenization, prior inventory and seals require independent provenance verification']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        packet = json.loads(args.packet.read_text(encoding='utf-8'))
        schedule = build_schedule(packet)
        # Exclusive output prevents accidental overwrite of an existing plan.
        with args.output.open('x', encoding='utf-8') as out:
            json.dump(schedule, out, sort_keys=True, ensure_ascii=False, indent=2)
            out.write('\n')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f'NOT_RUN: {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
