"""Q38-T7 A/B payloads and scorer for the isolated-arm successor.

This module is not a launcher. Prefixes and native token counts are inputs
frozen before launch, not generated from observed outputs. Independently
warming both arms changes historical phase B; never merge those timings.
"""

from __future__ import annotations

import collections
import hashlib
import json
import math
import re
from dataclasses import dataclass

import degeneracy as detector
import lib_gpublock as lib
import q38_t7 as original
from q38_t7_isolated import Pair


@dataclass(frozen=True)
class FrozenContext:
    target: int
    nominal_tokens: int
    prefixes: tuple[str, ...]
    min_cached_tokens: int


@dataclass(frozen=True)
class Plan:
    pairs: tuple[Pair, ...]
    metadata: dict
    tokenizer_sha256: str
    sha256: str


def _plan_hash(pairs: tuple[Pair, ...], metadata: dict, tokenizer_sha256: str) -> str:
    items = [{'key': p.key, 'body': p.body, 'warm_body': p.warm_body,
              'min_cached_tokens': p.min_cached_tokens, 'arms': p.arms,
              'nodraft_body': p.nodraft_body} for p in pairs]
    payload = json.dumps({'pairs': items, 'metadata': metadata, 'tokenizer_sha256': tokenizer_sha256}, sort_keys=True,
                         separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def build_plan(prompts: list[dict], contexts: list[FrozenContext], *, gen: int = 1500,
               gen_nodraft: int = 500, tokenizer_sha256: str) -> Plan:
    """Build original A and B bodies with separately warmed B arms.

    Each target's final B repetition has the original no-draft generation cap;
    earlier repetitions are drafted-only. Needle bodies remain greedy/64 tokens.
    The transport must aggregate streaming responses with exact token IDs.
    """
    if (not prompts or not contexts or type(gen) is not int or gen <= 0
            or type(gen_nodraft) is not int or gen_nodraft <= 0):
        raise ValueError('nonempty workload and positive generation limits required')
    if not isinstance(tokenizer_sha256, str) or re.fullmatch(r'[0-9a-f]{64}', tokenizer_sha256) is None:
        raise ValueError('pinned tokenizer SHA-256 required')
    pairs, metadata, ids = [], {}, set()
    for prompt in prompts:
        if (not isinstance(prompt, dict) or not isinstance(prompt.get('id'), str)
                or not prompt['id'] or prompt['id'] in ids
                or not isinstance(prompt.get('prompt'), str) or not prompt['prompt']
                or not isinstance(prompt.get('suite'), str)):
            raise ValueError('invalid or duplicate production prompt')
        ids.add(prompt['id'])
        key = f"A/{prompt['id']}"
        body = original.chat_body(prompt['prompt'], max_tokens=200, temperature=0.0,
                                  cache_prompt=False, chat_template_kwargs={'enable_thinking': False})
        pairs.append(Pair(key, body))
        metadata[key] = {'phase': 'A', 'id': prompt['id'], 'suite': prompt['suite']}
    targets = set()
    for context in contexts:
        if (type(context.target) is not int or context.target <= 0 or context.target in targets
                or type(context.nominal_tokens) is not int or context.nominal_tokens <= 0
                or type(context.min_cached_tokens) is not int or context.min_cached_tokens <= 0
                or not context.prefixes or any(not isinstance(p, str) for p in context.prefixes)
                or len(set(context.prefixes)) != len(context.prefixes)):
            raise ValueError('invalid or duplicate frozen context')
        targets.add(context.target)
        _, _, facts = original.needles(context.target)
        for index, prefix in enumerate(context.prefixes, 1):
            if not isinstance(prefix, str) or not prefix or not all(fact in prefix for fact in facts):
                raise ValueError('each frozen prefix must contain both target needle facts')
            key = f'B/{context.target}/decode/{index}'
            warm = original.chat_body(prefix, max_tokens=1, cache_prompt=True)
            body = original.chat_body(prefix + original.TASK, max_tokens=gen, stream=True)
            last = index == len(context.prefixes)
            nodraft = original.chat_body(prefix + original.TASK, max_tokens=gen_nodraft, stream=True) if last else None
            pairs.append(Pair(key, body, warm, context.min_cached_tokens,
                              ('drafted', 'nodraft') if last else ('drafted',), nodraft))
            metadata[key] = {'phase': 'B', 'type': 'decode', 'target': context.target,
                             'rep': index, 'nominal_tokens': context.nominal_tokens}
        prefix = context.prefixes[-1]
        key = f'B/{context.target}/needle'
        warm = original.chat_body(prefix, max_tokens=1, cache_prompt=True)
        body = original.chat_body(prefix + original.QUESTION, max_tokens=64, temperature=0.0,
                                  chat_template_kwargs={'enable_thinking': False})
        pairs.append(Pair(key, body, warm, context.min_cached_tokens))
        metadata[key] = {'phase': 'B', 'type': 'needle', 'target': context.target,
                         'expected': facts}
    frozen = tuple(pairs)
    return Plan(frozen, metadata, tokenizer_sha256, _plan_hash(frozen, metadata, tokenizer_sha256))


def _body_hash(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _result(response: dict, *, stream: bool, tokenizer_sha256: str,
            require_tokens: bool) -> tuple[str, str, str | None, list[int]]:
    if not isinstance(response, dict) or response.get('http_status') != 200 or response.get('error'):
        raise ValueError('missing or failed native response')
    if stream:
        content, reasoning, finish = response.get('content'), response.get('reasoning'), response.get('finish')
    else:
        payload = response.get('body')
        choices = payload.get('choices') if isinstance(payload, dict) else None
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise ValueError('missing native chat choice')
        message = choices[0].get('message')
        if not isinstance(message, dict):
            raise ValueError('missing native message')
        content, reasoning, finish = message.get('content'), '', choices[0].get('finish_reason')
    tokens = response.get('token_ids', [] if not require_tokens else None)
    if (not isinstance(content, str) or not isinstance(reasoning, str)
            or not isinstance(tokens, list) or any(type(token) is not int for token in tokens)):
        raise ValueError('missing text, reasoning or tokenizer evidence')
    if require_tokens and (content or reasoning) and not tokens:
        raise ValueError('nonempty text has no tokenizer evidence')
    if require_tokens:
        proof = response.get('tokenizer_provenance')
        text = reasoning + '\n' + content if stream else content
        text_digest = hashlib.sha256(text.encode()).hexdigest()
        if (not isinstance(proof, dict) or proof.get('method') != 'retokenized_text'
                or proof.get('text_sha256') != text_digest
                or proof.get('tokenizer_sha256') != tokenizer_sha256):
            raise ValueError('tokenizer provenance missing or mismatched')
        if stream and (response.get('stream_complete') is not True
                       or not isinstance(response.get('raw_stream_sha256'), str)
                       or re.fullmatch(r'[0-9a-f]{64}', response['raw_stream_sha256']) is None):
            raise ValueError('stream custody incomplete')
    if finish is not None and not isinstance(finish, str):
        raise ValueError('invalid finish reason')
    return content, reasoning, finish, tokens


def score(plan: Plan, run: dict, ground_truth: dict[str, dict]) -> dict:
    """Score complete A/B pairs with the original classifier and paired verdict.

    The response envelope is required to contain raw body/stream fields, native
    timings and exact token IDs. Incomplete custody or inputs return UNKNOWN;
    no missing row can be converted into a passing original verdict.
    """
    unknown = lambda why: {'status': 'UNKNOWN', 'reason': why, 'protocol': 'independent-warm-v1'}
    try:
        if _plan_hash(plan.pairs, plan.metadata, plan.tokenizer_sha256) != plan.sha256:
            return unknown('frozen plan was modified')
    except (TypeError, ValueError):
        return unknown('invalid frozen plan')
    if run.get('partial') or run.get('cleanup') != {'drafted': True, 'nodraft': True}:
        return unknown('incomplete run or unverified cleanup')
    by = {}
    for record in run.get('records', []):
        key = (record.get('arm'), record.get('key'), record.get('kind'))
        if key in by:
            return unknown('duplicate record')
        by[key] = record
    expected = {(arm, pair.key, kind) for pair in plan.pairs for arm in pair.arms
                for kind in (('warm', 'measure') if pair.warm_body is not None else ('measure',))}
    if set(by) != expected:
        return unknown('missing or unexpected record')
    rows_a, rows_b, texts = [], [], {}
    try:
        for pair in plan.pairs:
            meta = plan.metadata[pair.key]
            for arm in pair.arms:
                record = by[(arm, pair.key, 'measure')]
                body = pair.nodraft_body if arm == 'nodraft' and pair.nodraft_body is not None else pair.body
                if record.get('body_sha256') != _body_hash(body):
                    raise ValueError('measured body hash mismatch')
                response = record['response']
                content, reasoning, finish, toks = _result(
                    response, stream=meta.get('type') == 'decode', tokenizer_sha256=plan.tokenizer_sha256,
                    require_tokens=meta.get('type') != 'needle')
                timings = response.get('timings')
                if not isinstance(timings, dict):
                    raise ValueError('native timings missing')
                if pair.warm_body is not None:
                    warm = by[(arm, pair.key, 'warm')]
                    if warm.get('body_sha256') != _body_hash(pair.warm_body):
                        raise ValueError('warm body hash mismatch')
                    if not isinstance(warm.get('response'), dict) or warm['response'].get('http_status') != 200:
                        raise ValueError('warm response missing or failed')
                    cache = timings.get('cache_n')
                    if type(cache) is not int or cache < pair.min_cached_tokens:
                        raise ValueError('missing or insufficient cached-token witness')
                common = {'http': 200, 'busy_before': response.get('busy_before'),
                          'wall_s': response.get('wall_s'), 'ttft_s': response.get('ttft_s'),
                          **lib.timing_summary(timings)}
                if meta['phase'] == 'A':
                    label = 'dflash2' if arm == 'drafted' else 'nodraft'
                    expected_item = ground_truth.get(meta['id'])
                    row = {'phase': 'A', 'id': meta['id'], 'suite': meta['suite'], 'arm': label,
                           **common, 'degeneracy': detector.classify(content, toks, finish, True),
                           'answer': original.grade(content, expected_item),
                           'expected': (expected_item or {}).get('expected'), 'text': content, 'token_ids': toks}
                    rows_a.append(row); texts[(meta['id'], label)] = content
                elif meta['type'] == 'decode':
                    label = 'drafted' if arm == 'drafted' else 'no-draft (isolated, cached)'
                    rows_b.append({'phase': 'B', 'target': meta['target'], 'nominal_tokens': meta['nominal_tokens'],
                                   'variant': label, 'rep': meta['rep'], **common, 'error': response.get('error'),
                                   'degeneracy': detector.classify(reasoning + '\n' + content, toks, finish, True),
                                   'finish': finish, 'reasoning': reasoning, 'content': content, 'token_ids': toks})
                else:
                    norm = lambda value: ''.join(value.lower().split())
                    facts = meta['expected']
                    rows_b.append({'phase': 'B', 'target': meta['target'],
                                   'variant': 'needle' if arm == 'drafted' else 'needle (no-draft)', **common,
                                   'answer': content, 'expected': facts,
                                   'correct': all(norm(fact) in norm(content) for fact in facts),
                                   'abstained': original.abstained(content)})
    except (KeyError, TypeError, ValueError) as exc:
        return unknown(str(exc))
    ids = [value['id'] for value in plan.metadata.values() if value['phase'] == 'A']
    a = {'rows': rows_a, 'n_prompts': len(ids),
         'greedy_identical': sum(texts[(pid, 'dflash2')] == texts[(pid, 'nodraft')] for pid in ids),
         'paired': original.pair_a(rows_a, texts, ids)}
    for arm in ('dflash2', 'nodraft'):
        rs = [row for row in rows_a if row['arm'] == arm]
        big = [row for row in rs if (row.get('predicted_n') or 0) >= 16 and row.get('decode_tps')]
        tokens = sum(row['predicted_n'] for row in big)
        seconds = sum(row['predicted_n'] / row['decode_tps'] for row in big)
        dn, da = sum(row.get('draft_n') or 0 for row in rs), sum(row.get('draft_n_accepted') or 0 for row in rs)
        a[arm] = {'token_weighted_decode_tps': round(tokens / seconds, 2) if seconds else None,
                  'classes': dict(collections.Counter(row['degeneracy']['cls'] for row in rs)),
                  'v1_classes': dict(collections.Counter(row['degeneracy'].get('v1_cls') for row in rs)),
                  'answers': dict(collections.Counter(str(row['answer']) for row in rs)),
                  'draft_acceptance': round(da / dn, 4) if dn else None}
    b = {'rows': rows_b}
    verdict = original.verdict({'A': a, 'B': b})
    decode_rows = rows_a + [row for row in rows_b if not row['variant'].startswith('needle')]
    missing_speed = [f"{row['phase']}:{row.get('id', row.get('target'))}:{row.get('arm', row.get('variant'))}"
                     for row in decode_rows
                     if type(row.get('predicted_n')) is not int or row['predicted_n'] <= 0
                     or type(row.get('decode_tps')) not in (int, float) or row['decode_tps'] <= 0]
    if missing_speed:
        verdict['speed_valid'] = False
    verdict['speed_missing'] = missing_speed
    return {'status': 'COMPLETE', 'protocol': 'independent-warm-v1', 'plan_sha256': plan.sha256, 'A': a, 'B': b,
            'verdict': verdict,
            'historical_timing_comparable': False}


def render_markdown(report: dict) -> str:
    """Report original A/B observables without claiming the old cache protocol."""
    if report.get('status') != 'COMPLETE':
        return f"# Q38-T7 isolated A/B\n\nUNKNOWN: {report.get('reason', 'incomplete')}\n"
    verdict = report['verdict']
    lines = ['# Q38-T7 isolated A/B', '',
             'Protocol: independent-warm-v1; historical timing is not directly comparable.', '',
             f"Correctness: {verdict['correctness']}; speed "
             f"{'VALID' if verdict['speed_valid'] else 'INVALID'} under the original paired rule.",
             f"Classifier: {verdict['classifier']}; {verdict['semantic']}"]
    lines += [f'- {reason}' for reason in verdict['reasons']]
    if verdict['speed_missing']:
        lines.append(f"- Speed evidence missing: {verdict['speed_missing']}")
    lines += [f'- Model behavior: {note}' for note in verdict['model_behaviour']]
    lines += ['', '## A — paired production prompts', '',
              '| arm | decode tok/s | draft acceptance | v2 classes | v1 classes | answers |',
              '|---|---:|---:|---|---|---|']
    for arm in ('dflash2', 'nodraft'):
        row = report['A'][arm]
        lines.append(f"| {arm} | {row['token_weighted_decode_tps']} | {row['draft_acceptance']} | "
                     f"{row['classes']} | {row['v1_classes']} | {row['answers']} |")
    a = report['A']
    lines += ['', f"Greedy identity: {a['greedy_identical']}/{a['n_prompts']}; "
              f"paired results: {a['paired']}", '', '## B — independently warmed context probes', '',
              '| target | variant | rep | prompt | cache | prefill tok/s | TTFT s | decode tok/s | '
              'generated | draft acceptance | class / needle | busy before |',
              '|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for row in report['B']['rows']:
        if 'degeneracy' in row:
            label = row['degeneracy']['cls']
        else:
            label = 'correct' if row['correct'] else ('ABSTAINED' if row['abstained'] else 'WRONG')
        lines.append(f"| {row['target']} | {row['variant']} | {row.get('rep', '-')} | "
                     f"{row.get('prompt_n')} | {row.get('cache_n')} | {row.get('prefill_tps')} | "
                     f"{row.get('ttft_s')} | {row.get('decode_tps')} | {row.get('predicted_n')} | "
                     f"{row.get('draft_acc')} | {label} | {row.get('busy_before')} |")
    lines += ['', f"Eyeball review: {verdict['eyeball_required']}",
              'Original pre-KVU MTP and phase C are not measured by this successor.']
    return '\n'.join(lines) + '\n'
