#!/usr/bin/env python3
"""Prospective six-process G3 capture. Run only under a scheduled GPU row.

Two independent FA-on, MTP-off controls precede the retained four MTP cells.
This module qualifies dispatch evidence only. Ownership must be established by
an independent grant verifier before a final endpoint can be reported.
"""
import argparse
import copy
import json
import math
import re
from pathlib import Path
import subprocess
import sys

from invocation_trace_v5 import classify_invocation_trace_v5

CELLS = tuple((kv, width) for kv in ('q8_0', 'q4_0') for width in (1, 4))


def configs(base, root):
    """Accept the canonical R5 argument spelling; reject ambiguous overrides."""
    options = ('--flash-attn', '-ctk', '-ctv', '--spec-type', '--spec-draft-n-max')
    args = base['server_args']
    # Alternate spellings/equals syntax could silently override the controls.
    forbidden = ('-fa', '--cache-type-k', '--cache-type-v', '--draft-max')
    if any(a in forbidden or any(a.startswith(o + '=') for o in options + forbidden)
           for a in args):
        raise ValueError('use canonical R5 option spellings')
    for option in options:
        if args.count(option) != 1 or args.index(option) + 1 >= len(args):
            raise ValueError('one explicit value required for ' + option)
    if args[args.index('--spec-type') + 1] != 'draft-mtp':
        raise ValueError('base must select draft-mtp')
    result = []
    for kv, width in [(k, 0) for k in ('q8_0', 'q4_0')] + list(CELLS):
        c = copy.deepcopy(base)
        ident = f'{kv}-' + (f'd{width}' if width else 'mtp-off')
        values = {'--flash-attn': 'on', '-ctk': kv, '-ctv': kv,
                  '--spec-type': 'draft-mtp' if width else 'none',
                  '--spec-draft-n-max': str(width or 1)}
        for option, value in values.items():
            c['server_args'][args.index(option) + 1] = value
        c['output'] = str(Path(root) / ident)
        result.append((ident, c))
    return result


def capture_ok(result, count):
    return (result.get('status') == 'complete' and result.get('process_group_drained') is True
            and len(result.get('requests', [])) == count
            and count > 0 and all(type(r.get('tokens_predicted')) is int and r['tokens_predicted'] > 0
                                  for r in result['requests']))


def negative_control(trace, result, layers, count, kv):
    """No candidate is allowed, including an UNKNOWN candidate.

    A real FA dispatch must occur during each completed request. Startup/prefill
    from the MTP-on cells cannot stand in for this separate server execution.
    Residency here is request-scoped; it does not attribute these dispatches.
    """
    try:
        if not capture_ok(result, count):
            raise ValueError('incomplete output or unverified drain')
        parsed = classify_invocation_trace_v5(trace, expected_layer_ids=layers)
        if parsed['candidates']:
            raise ValueError('MTP-off control contains verify candidates')
        windows = result['request_windows']
        residency = result['residency']
        if len(windows) != count or len(residency) != count or any(r['status'] != 'PASS' for r in residency):
            raise ValueError('missing in-request residency')
        events = [dict(e['fields']) for e in parsed['raw_events'] if e['kind'] == 'G3_FATTN_DISPATCH_V3']
        stamps = [int(re.search(r' time_ns=([0-9]+)$', line).group(1))
                  for line in trace.splitlines() if 'G3_FATTN_DISPATCH_V3' in line]
        if len(events) != len(stamps):
            raise ValueError('dispatch timestamp count mismatch')
        for event, stamp in zip(events, stamps):
            event['time_ns'] = stamp
        for start, end in windows:
            if (any(type(v) not in (int, float) or not math.isfinite(v) for v in (start, end))
                    or start >= end):
                raise ValueError('invalid request window')
            if not any(start <= int(e['time_ns']) / 1e9 <= end
                       and e['k_type'].lower() == kv and e['v_type'].lower() == kv
                       and int(e['kernel']) in (100, 200, 300, 400) for e in events):
                raise ValueError('no native FA dispatch during control request')
        return {'status': 'PASS', 'scope': 'independent MTP-off FA dispatch excluded from verify candidates'}
    except (ValueError, KeyError, TypeError, OverflowError, AttributeError) as exc:
        return {'status': 'UNKNOWN', 'reason': str(exc)}


def _assess(records):
    """Fold all six captures; no partial existential result bypasses a control.

    Final endpoint remains UNKNOWN here: this runner deliberately has no
    authority to certify GPU grant ownership or GPU operating-clock stability.
    """
    reasons, controls, observed = [], {}, []
    expected = {f'{kv}-mtp-off' for kv in ('q8_0', 'q4_0')} | {f'{kv}-d{w}' for kv, w in CELLS}
    if set(records) != expected:
        reasons.append('missing or extra protocol cells')
    for kv in ('q8_0', 'q4_0'):
        control = records.get(f'{kv}-mtp-off', {}).get('control', {})
        controls[kv] = control
        if control.get('status') != 'PASS' or records.get(f'{kv}-mtp-off', {}).get('rc') != 0:
            reasons.append(kv + ' independent negative control missing or failed')
    for kv, width in CELLS:
        cell = records.get(f'{kv}-d{width}', {})
        result = cell.get('result', {})
        timed = result.get('timed_analysis', {})
        coverage = timed.get('coverage') or {}
        expected_count = coverage.get('expected_dispatches')
        valid_coverage = (type(expected_count) is int and expected_count > 0
                          and coverage.get('bounded_dispatches') == expected_count
                          and coverage.get('unknown_dispatches') == 0 and coverage.get('complete') is True)
        if (cell.get('rc') != 0 or not capture_ok(result, cell.get('request_count', 0))
                or timed.get('status') != 'SCOPED_DISPATCH_OBSERVED' or not valid_coverage):
            reasons.append(f'{kv}-d{width} incomplete dispatch evidence')
            continue
        candidates = (timed.get('trace') or {}).get('candidates', [])
        # Requested n_max is not evidence that either verify shape occurred.
        lengths = [c['draft_length'] for c in candidates]
        if (not lengths or any(type(n) is not int or not 1 <= n <= width for n in lengths)
                or not any(n == 1 if width == 1 else n >= 2 for n in lengths)):
            reasons.append(f'{kv}-d{width} missing declared draft-length stratum')
        events = timed.get('observed', [])
        if (len(events) != expected_count or any(e.get('kernel') not in (100, 200, 300, 400) for e in events)
                or any(d.get('k_type', '').lower() != kv or d.get('v_type', '').lower() != kv
                       for c in candidates for d in c['dispatches'])):
            reasons.append(f'{kv}-d{width} inconsistent observations')
        observed.extend(events)
    protocol_pass = not reasons
    return {'status': 'UNKNOWN', 'dispatch_protocol': 'PASS' if protocol_pass else 'UNKNOWN',
            'vec_observed': any(e['kernel'] == 100 for e in observed) if protocol_pass else None,
            'controls': controls, 'reasons': reasons + ['independent GPU grant ownership and operating-clock assessment required'],
            'scope': 'Observed dispatches only; no bandwidth or throughput conclusion'}


def assess(records):
    try:
        return _assess(records)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return {'status': 'UNKNOWN', 'dispatch_protocol': 'UNKNOWN',
                'vec_observed': None, 'reasons': ['malformed protocol capture: ' + str(exc)]}


def execute(base, root, runner=None):
    """Each cell invokes the native runner in a fresh process; stop on failure."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    planned = configs(base, root)
    (root / 'protocol.json').write_text(json.dumps(planned, indent=2) + '\n')
    runner = runner or Path(__file__).with_name('diagnostic_runner.py')
    layers = json.loads(Path(base['layer_manifest']).read_text())['verify_attention_layer_ids']
    records = {}
    for ident, config in planned:
        path = root / (ident + '.json')
        path.write_text(json.dumps(config, indent=2) + '\n')
        rc = subprocess.run([sys.executable, str(runner), str(path)], check=False).returncode
        cell = {'rc': rc, 'request_count': len(config['requests'])}
        try:
            out = Path(config['output'])
            cell['result'] = json.loads((out / 'result.json').read_text())
            if ident.endswith('mtp-off'):
                cell['control'] = negative_control((out / 'server.log').read_text(), cell['result'], layers,
                                                   cell['request_count'], ident.split('-')[0])
                if rc != 0:
                    cell['control'] = {'status': 'UNKNOWN', 'reason': 'native runner failed'}
        except (OSError, ValueError) as exc:
            cell['error'] = str(exc)
        records[ident] = cell
        verdict = assess(records)
        (root / 'endpoint.json').write_text(json.dumps({'cells': records, 'assessment': verdict}, indent=2) + '\n')
        if rc != 0 or (ident.endswith('mtp-off') and cell.get('control', {}).get('status') != 'PASS'):
            break
    return verdict


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('base_config', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    execute(json.loads(a.base_config.read_text()), a.output)
