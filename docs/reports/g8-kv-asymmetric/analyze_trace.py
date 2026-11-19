#!/usr/bin/env python3
"""Fail-closed G8 greedy teacher-forced trace accounting; no throughput claim."""
import json
import re
import sys

BEGIN = re.compile(r'^G8_COMPARE_BEGIN rows=(\d+)$')
ROW = re.compile(r'^G8_COMPARE_ROW pos=(\d+) batch=(-?\d+) draft=(-?\d+) target=(-?\d+) match=([01])$')
END = re.compile(r'^G8_COMPARE_END rows=(\d+)$')


def analyze_trace(trace, response):
    groups, current, expected = [], None, None
    for line in trace.splitlines():
        if 'G8_COMPARE_' not in line:
            continue
        # Server logging can prefix lines, but a partial marker must never be ignored.
        marker = line[line.index('G8_COMPARE_'):].strip()
        begin, row, end = BEGIN.fullmatch(marker), ROW.fullmatch(marker), END.fullmatch(marker)
        if begin:
            if current is not None:
                raise ValueError('nested group')
            expected, current = int(begin.group(1)), []
            if expected < 1:
                raise ValueError('empty group')
        elif row:
            if current is None:
                raise ValueError('row outside group')
            pos, batch, draft, target, match = map(int, row.groups())
            if pos != len(current) or batch < 0 or draft < 0 or target < 0 or match != int(draft == target):
                raise ValueError('invalid row')
            current.append(match)
        elif end:
            if current is None or int(end.group(1)) != expected or len(current) != expected:
                raise ValueError('incomplete group')
            groups.append(current)
            current, expected = None, None
        else:
            raise ValueError('malformed marker')
    if current is not None or not groups:
        raise ValueError('missing or truncated trace')
    proposals = sum(map(len, groups))
    prefix_accepted = sum(next((i for i, x in enumerate(g) if not x), len(g)) for g in groups)
    timing = response.get('timings', {})
    if not isinstance(timing, dict):
        raise ValueError('missing timings')
    if type(timing.get('draft_n')) is not int or timing['draft_n'] != proposals:
        raise ValueError('draft count mismatch')
    if type(timing.get('draft_n_accepted')) is not int or timing['draft_n_accepted'] != prefix_accepted:
        raise ValueError('accepted count mismatch')
    positions = []
    for i in range(max(map(len, groups))):
        x = [g[i] for g in groups if len(g) > i]
        positions.append({'position': i, 'matches': sum(x), 'observed_proposals': len(x), 'agreement': sum(x) / len(x)})
    return {'rounds_with_proposals': len(groups), 'drafted': proposals,
            'accepted': prefix_accepted, 'mean_accepted_per_proposing_round': prefix_accepted / len(groups),
            'positions': positions,
            'scope': 'greedy teacher-forced draft prefixes, conditioned on an observed proposal; not throughput'}


def analyze_pair(packet):
    if packet.get('greedy') is not True or packet.get('single_slot') is not True or packet.get('single_drafter') is not True:
        raise ValueError('unqualified settings')
    a, b = packet['control_response'], packet['traced_response']
    control_request, traced_request = packet.get('control_request'), packet.get('traced_request')
    if (not isinstance(control_request, dict) or control_request != traced_request or
            control_request.get('temperature') != 0 or control_request.get('cache_prompt') is not False or
            control_request.get('return_tokens') is not True or control_request.get('stream') is not False or
            type(control_request.get('n_predict')) is not int or control_request['n_predict'] <= 0):
        raise ValueError('unmatched or invalid fresh greedy requests')
    if not isinstance(a.get('tokens'), list) or not a['tokens'] or a['tokens'] != b.get('tokens'):
        raise ValueError('output token identity missing or failed')
    if any(type(t) is not int for t in a['tokens']):
        raise ValueError('non-integer token identity')
    for key in ('draft_n', 'draft_n_accepted'):
        if (not isinstance(a.get('timings'), dict) or not isinstance(b.get('timings'), dict) or
                type(a['timings'].get(key)) is not int or a['timings'][key] != b['timings'].get(key)):
            raise ValueError('control counter mismatch')
    return analyze_trace(packet['trace'], b)


def main():
    try:
        with open(sys.argv[1], encoding='utf-8') as f:
            packet = json.load(f)
        result = {'status': 'VALID', 'analysis': analyze_pair(packet)}
    except (ValueError, TypeError, KeyError, IndexError, OSError, json.JSONDecodeError) as e:
        print(json.dumps({'status': 'UNKNOWN', 'reason': str(e)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
