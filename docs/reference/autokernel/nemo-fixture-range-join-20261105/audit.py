#!/usr/bin/env python3
"""Offline SDK fixture trace join; no inference about server tokens or clocks."""
import argparse, csv, hashlib, importlib.util, json, pathlib, re, sys

SOURCE = pathlib.Path('/mnt/raid0/llm/tmp/akagg/filing-20261105/nemo-sdk-roctx-marker-compare-r2-20261105')
sys.path.insert(0, str(SOURCE / 'nemo-marker-csv-adapter-20261105'))
from marker_csv import normalize, ENVELOPE
spec = importlib.util.spec_from_file_location('clock_join', SOURCE / 'nemo-fixture-clock-join-20261105/fixture_clock_join.py')
clock = importlib.util.module_from_spec(spec); spec.loader.exec_module(clock)
NAMES = ('probe_marker_api_trace.csv', 'probe_hip_api_trace.csv', 'probe_kernel_trace.csv')
LABELS = ['launch--1', 'launch-0', 'launch-1', 'launch-2', 'launch-3', 'launch-4']

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''): h.update(chunk)
    return h.hexdigest()

def unique(pairs):
    out = {}
    for k, v in pairs:
        if k in out: raise ValueError('duplicate JSON key')
        out[k] = v
    return out

def audit(d):
    trace = d / 'fixture-trace'; marker = trace / NAMES[0]; log = d / 'fixture.log'
    clock_result = clock.validate_fixture_markers(log.read_text(), marker)
    # normalize enforces complete fixture-specific marker envelope, identity and cardinality.
    normalize(marker)
    ranges = []
    for line in marker.read_text().splitlines()[1:]:
        m = ENVELOPE.fullmatch(line)
        if not m: raise ValueError('invalid marker envelope')
        if not m[1].startswith('{'): continue
        obj = json.loads(m[1], object_pairs_hook=unique)
        ranges.append((int(m[5]), int(m[6]), int(m[2]), int(m[3]), obj))
    ranges.sort(key=lambda r: r[0])
    if [x[4]['launch_identity'] for x in ranges] != LABELS: raise ValueError('unexpected range order')
    log_launch = []
    for line in log.read_text().splitlines():
        if not line.startswith('{'): continue
        row = json.loads(line, object_pairs_hook=unique)
        if row.get('event') == 'launch': log_launch.append(row)
    if [r[4] for r in ranges] != log_launch: raise ValueError('range/log identity mismatch')
    with (trace / NAMES[1]).open(newline='') as f:
        graph = [r for r in csv.DictReader(f) if r['Function'] == 'hipGraphLaunch']
    graph.sort(key=lambda r: int(r['Start_Timestamp']))
    if len(graph) != 6 or len({r['Correlation_Id'] for r in graph}) != 6: raise ValueError('graph cardinality or identity')
    with (trace / NAMES[2]).open(newline='') as f: kernels = list(csv.DictReader(f))
    joins = []
    for i, (start, end, pid, tid, obj) in enumerate(ranges):
        g = graph[i]; gs = int(g['Start_Timestamp']); ge = int(g['End_Timestamp'])
        if (int(g['Process_Id']), int(g['Thread_Id'])) != (pid, tid) or not start <= gs <= ge <= end: raise ValueError('range/API mismatch')
        if i < 5 and gs >= ranges[i+1][0]: raise ValueError('ambiguous range/API ordering')
        k = [r for r in kernels if r['Correlation_Id'] == g['Correlation_Id']]
        if len(k) != 2 or sum('nemo_fixture_kernel_a' in r['Kernel_Name'] for r in k) != 1 or sum('nemo_fixture_kernel_b' in r['Kernel_Name'] for r in k) != 1: raise ValueError('kernel cardinality or identity')
        for row in k:
            if int(row['Start_Timestamp']) <= 0 or int(row['End_Timestamp']) < int(row['Start_Timestamp']): raise ValueError('invalid kernel timestamps')
        joins.append({'launch_identity': obj['launch_identity'], 'graph_correlation_id': g['Correlation_Id'], 'kernel_count': len(k)})
    return {'fixture_pid': ranges[0][2], 'clock_constraint': clock_result, 'joins': joins, 'input_sha256': {p.relative_to(d).as_posix(): digest(p) for p in [log] + [trace / n for n in NAMES]}}

def main():
    p = argparse.ArgumentParser(); p.add_argument('run_dir', type=pathlib.Path); p.add_argument('output', type=pathlib.Path); a = p.parse_args()
    dirs = sorted(a.run_dir.glob('*-sdk'), key=lambda x: int(x.name.split('-')[0]))
    if len(dirs) != 80 or [d.name for d in dirs] != [f'{i}-sdk' for i in range(80)]: raise SystemExit('refuse: expected SDK runs 0..79')
    receipt = SOURCE / 'RESULT.json'
    if digest(receipt) != '7d6db4dea6dfed738f1fc2f223a9d9333630e86d4ec4f2bb486da781971fff1e': raise SystemExit('refuse: original result digest mismatch')
    recorded = json.loads(receipt.read_text())
    if recorded.get('status') != 'COMPLETE' or recorded.get('unit_count') != 80 or len(recorded.get('rows', [])) != 80: raise SystemExit('refuse: invalid original receipt')
    results = {}
    for d in dirs:
        try:
            r = audit(d); pair = int(d.name.split('-')[0]); row = recorded['rows'][pair]
            arms = [x for x in row['arms'] if x['arm'] == 'sdk']
            if row['pair'] != pair or len(arms) != 1: raise ValueError('receipt pair mismatch')
            arm = arms[0]; files = arm['marker_files']
            if arm['status'] != 'PASS' or len(files) != 1 or files[0]['sha256'] != r['input_sha256']['fixture-trace/'+NAMES[0]]: raise ValueError('receipt marker mismatch')
            if arm['fixture_pids'] != [str(r['fixture_pid'])] or arm['graph_ids'] != [j['graph_correlation_id'] for j in r['joins']]: raise ValueError('receipt graph or PID mismatch')
            results[d.name] = r
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e: raise SystemExit(f'refuse {d.name}: {e}')
    out = {'schema': 'nemo.fixture.offline-join.v1', 'scope': 'SDK fixture traces only; no historical boundaries, server tokens, clock identity or GPU claim', 'run_count': len(results), 'source_result_sha256': digest(receipt), 'validator_sha256': digest(pathlib.Path(__file__)), 'dependencies_sha256': {str(x): digest(x) for x in [SOURCE/'nemo-marker-csv-adapter-20261105/marker_csv.py', SOURCE/'nemo-fixture-clock-join-20261105/fixture_clock_join.py']}, 'runs': results}
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True)+'\n')
if __name__ == '__main__': main()
