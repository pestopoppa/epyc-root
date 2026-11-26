#!/usr/bin/env python3
"""Summarize completed taskflow units without writing into the source rows.

Quartiles use linear interpolation at (n-1)*p. Comparisons are descriptive,
unpaired differences of group medians (or pass rates), not causal estimates.
"""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time

METRICS = {
    'decode_tok_s': ('perf', 'decode_tok_s_median'),
    'prefill_tok_s': ('perf', 'prefill_tok_s_median'),
    'ttft_s': ('perf', 'ttft_s_median'),
    'draft_acceptance': ('perf', 'draft_acceptance'),
    'draft_acceptance_per_request': ('perf', 'draft_acceptance_per_request_median'),
    'prefix_hit': ('perf', 'prefix_hit'),
    'aggregate_decode_tok_s': ('perf', 'aggregate_decode_tok_s'),
    'decode_only_aggregate_tok_s': ('perf', 'decode_only_aggregate_tok_s'),
    'output_tokens': ('tokens', 'output'),
    'wall_s': (None, 'wall_s'),
    'worker_wall_s': (None, 'worker_wall_s'),
}
COUNTS = ('degenerate_aborts', 'server_error_retries', 'bad_tool_args_seen', 'requests')


def source_path(row):
    row = Path(row).resolve()
    if (row / 'results.jsonl').is_file():
        return row / 'results.jsonl'
    return row / 'out' / 'results.jsonl'


def read_units(path):
    # A writer may be midway through the last line. Only newline-terminated
    # records are committed; malformed complete lines are errors, not omissions.
    data = path.read_bytes()
    lines = data.split(b'\n')[:-1]
    units = []
    for number, line in enumerate(lines, 1):
        if line.strip():
            try:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError('expected an object')
                units.append(value)
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError(f'{path}:{number}: {exc}') from exc
    return units, bool(data and not data.endswith(b'\n'))


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def distribution(values):
    values = sorted(v for v in values if number(v))
    if not values:
        return {'n': 0, 'median': None, 'q1': None, 'q3': None, 'iqr': None}
    def quantile(p):
        pos = (len(values) - 1) * p
        lo, hi = math.floor(pos), math.ceil(pos)
        return values[lo] + (values[hi] - values[lo]) * (pos - lo)
    q1, q3 = quantile(.25), quantile(.75)
    return {'n': len(values), 'median': statistics.median(values),
            'q1': q1, 'q3': q3, 'iqr': q3 - q1}


def summarize(units):
    verdicts = Counter(str(u.get('verdict') or 'unknown') for u in units)
    passed = verdicts['verified'] + verdicts['accepted']
    rejected = verdicts['rejected']
    # Unknown verdicts are visible and excluded from the decided denominator.
    decided = passed + rejected
    failures = Counter(str(u.get('failure_class') or 'unknown') for u in units if u.get('verdict') == 'rejected')
    metrics = {}
    for name, (section, key) in METRICS.items():
        metrics[name] = distribution((u.get(section) or {}).get(key) if section else u.get(key) for u in units)
    totals = {}
    for key in COUNTS:
        vals = [(u.get('perf') or {}).get(key) for u in units]
        vals = [v for v in vals if number(v)]
        totals[key] = {'total': sum(vals), 'n': len(vals)}
    return {'n': len(units), 'verdicts': dict(sorted(verdicts.items())),
            'passed': passed, 'rejected': rejected, 'decided': decided,
            'pass_rate': passed / decided if decided else None,
            'rejected_by_failure_class': dict(sorted(failures.items())),
            'metrics': metrics, 'totals': totals}


def device_for(path):
    matches = set(re.findall(r'(?i)(?:^|[^a-z0-9])(cpu|gpu)(?=$|[^a-z0-9])', str(path)))
    matches = {x.upper() for x in matches}
    return next(iter(matches)) if len(matches) == 1 else 'unknown'


def family(arm):
    match = re.match(r'^([RF])(?:-|$)', arm, re.I)
    return match.group(1).upper() if match else None


def compare(kind, a, b):
    # b minus a; counts for every metric expose missing-value denominators.
    changes = {}
    for name in METRICS:
        x, y = a['summary']['metrics'][name], b['summary']['metrics'][name]
        changes[name] = {'delta': y['median'] - x['median'] if x['median'] is not None and y['median'] is not None else None,
                         'n_a': x['n'], 'n_b': y['n']}
    x, y = a['summary']['pass_rate'], b['summary']['pass_rate']
    return {'kind': kind, 'a': a['id'], 'b': b['id'], 'n_a': a['summary']['n'], 'n_b': b['summary']['n'],
            'pass_rate_delta': y - x if x is not None and y is not None else None,
            'pass_rate_n_a': a['summary']['decided'], 'pass_rate_n_b': b['summary']['decided'], 'metrics': changes}


def build(rows, overrides):
    groups, sources = [], []
    for row in rows:
        path = source_path(row)
        units, pending = read_units(path)
        device = overrides.get(str(Path(row).resolve()), device_for(row))
        sources.append({'row': str(Path(row).resolve()), 'results': str(path), 'device': device, 'pending_partial_line': pending, 'n': len(units)})
        buckets = defaultdict(list)
        for unit in units:
            buckets[(str(unit.get('arm') or 'unknown'), str(unit.get('model') or 'unknown'),
                     str(unit.get('np') if unit.get('np') is not None else 'unknown'),
                     unit.get('thinking') if isinstance(unit.get('thinking'), bool) else None)].append(unit)
        for (arm, model, np, thinking), members in sorted(buckets.items(), key=lambda item: str(item[0])):
            groups.append({'id': f'{Path(row).resolve()} | {arm} | model={model} np={np} thinking={thinking}',
                           'row': str(Path(row).resolve()), 'device': device, 'arm': arm, 'family': family(arm),
                           'model': model, 'np': np, 'thinking': thinking, 'summary': summarize(members)})
    comparisons = []
    for i, a in enumerate(groups):
        for b in groups[i + 1:]:
            if (a['model'], a['np']) != (b['model'], b['np']):
                continue
            if a['row'] != b['row'] and {a['device'], b['device']} == {'CPU', 'GPU'} and a['arm'] == b['arm'] and a['thinking'] == b['thinking']:
                cpu, gpu = (a, b) if a['device'] == 'CPU' else (b, a)
                comparisons.append(compare('GPU - CPU', cpu, gpu))
            if a['row'] == b['row'] and {a['family'], b['family']} == {'R', 'F'} and a['thinking'] == b['thinking']:
                r, f = (a, b) if a['family'] == 'R' else (b, a)
                comparisons.append(compare('F - R', r, f))
            if a['row'] == b['row'] and a['family'] and a['family'] == b['family'] and {a['thinking'], b['thinking']} == {True, False}:
                no, yes = (a, b) if a['thinking'] is False else (b, a)
                comparisons.append(compare('think - nothink', no, yes))
    return {'sources': sources, 'groups': groups, 'comparisons': comparisons}


def fmt(value):
    return 'NA' if value is None else f'{value:.3f}'


def markdown(report):
    lines = ['# Performance summary', '', 'Completed newline-terminated units only. Quartiles use linear interpolation; comparisons are unpaired differences of medians, not causal estimates. Pass rate excludes unknown verdicts.', '']
    for source in report['sources']:
        lines.append(f"Source: `{source['results']}`; device={source['device']}; n={source['n']}; partial line pending={source['pending_partial_line']}")
    for group in report['groups']:
        s = group['summary']
        lines += ['', f"## {group['id']}", '', f"Device: {group['device']}; units: {s['n']}; pass: {s['passed']}/{s['decided']} ({fmt(s['pass_rate'])}); rejected: {s['rejected']}; verdicts: {s['verdicts']}; rejected by failure class: {s['rejected_by_failure_class']}", '', '| Metric | n | Median | Q1 | Q3 | IQR |', '| --- | ---: | ---: | ---: | ---: | ---: |']
        for name, v in s['metrics'].items():
            lines.append(f"| {name} | {v['n']} | {fmt(v['median'])} | {fmt(v['q1'])} | {fmt(v['q3'])} | {fmt(v['iqr'])} |")
        lines += ['', 'Totals (with available-unit counts): ' + ', '.join(f"{k}={v['total']} (n={v['n']})" for k, v in s['totals'].items())]
    lines += ['', '## Comparisons', '']
    if not report['comparisons']:
        lines.append('No comparable groups available.')
    for c in report['comparisons']:
        lines += [f"### {c['kind']}", '', f"A: {c['a']} (n={c['n_a']})  ", f"B: {c['b']} (n={c['n_b']})", '', f"Pass rate difference: {fmt(c['pass_rate_delta'])} (decided n={c['pass_rate_n_a']}, {c['pass_rate_n_b']})", '', '| Metric | B − A | n A | n B |', '| --- | ---: | ---: | ---: |']
        for name, v in c['metrics'].items():
            lines.append(f"| {name} | {fmt(v['delta'])} | {v['n_a']} | {v['n_b']} |")
        lines.append('')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rows', nargs='+', help='row directories, or their output directories')
    parser.add_argument('--output-dir', default='.', help='destination outside all input rows (default: current directory)')
    parser.add_argument('--device', action='append', default=[], metavar='ROW=CPU|GPU', help='override path-based device detection')
    parser.add_argument('--watch', type=float, metavar='SECONDS', help='poll for input changes at this interval')
    args = parser.parse_args(argv)
    if args.watch is not None and (not math.isfinite(args.watch) or args.watch <= 0):
        parser.error('--watch must be positive and finite')
    overrides = {}
    for spec in args.device:
        row, sep, device = spec.rpartition('=')
        if not sep or device.upper() not in ('CPU', 'GPU') or str(Path(row).resolve()) not in {str(Path(r).resolve()) for r in args.rows}:
            parser.error('--device must be ROW=CPU or ROW=GPU for an input row')
        overrides[str(Path(row).resolve())] = device.upper()
    out = Path(args.output_dir).resolve()
    paths = [source_path(row) for row in args.rows]
    for row, path in zip(args.rows, paths):
        # Protect both an explicitly supplied output directory and its parent row.
        root = Path(row).resolve()
        if root == path.parent and (root.name == 'out' or root.name.startswith('out.')):
            root = root.parent
        if out == root or root in out.parents:
            parser.error('output directory must be outside input rows')
    out.mkdir(parents=True, exist_ok=True)
    previous = None
    try:
        while True:
            signature = [(p.stat().st_size, p.stat().st_mtime_ns) for p in paths]
            if signature != previous:
                report = build(args.rows, overrides)
                text = markdown(report)
                for name, content in [('canary-perf-summary.json', json.dumps(report, indent=2, allow_nan=False) + '\n'), ('canary-perf-summary.md', text)]:
                    target = out / name
                    temp = target.with_suffix(target.suffix + '.tmp')
                    temp.write_text(content, encoding='utf-8')
                    temp.replace(target)
                print(text, flush=True)
                previous = signature
            if args.watch is None:
                break
            time.sleep(args.watch)
    except (OSError, ValueError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
