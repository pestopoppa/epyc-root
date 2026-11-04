#!/usr/bin/env python3
"""Validate one complete request's native trace before scoring pruning or quality."""
import json
import pathlib
import sys

d = pathlib.Path(__file__).resolve().parent
plan = json.loads((d / 'plan.json').read_text())
manifest = dict(line.split('=', 1) for line in (d / 'native.manifest').read_text().splitlines())
trace = pathlib.Path(sys.argv[1]).read_bytes()
offset = int(sys.argv[2])
request = json.loads(pathlib.Path(sys.argv[3]).read_text())
assert 0 <= offset <= len(trace) and (not offset or trace[offset - 1:offset] == b'\n')
assert not trace or trace.endswith(b'\n'), 'partial trace'
before = [json.loads(line) for line in trace[:offset].splitlines()]
rows = [json.loads(line) for line in trace[offset:].splitlines()]
assert request.get('schema') == 'lsa-native-sentinel-request-v1'
assert type(request.get('request_start_monotonic_ns')) is int
assert type(request.get('request_end_monotonic_ns')) is int
assert request['request_start_monotonic_ns'] < request['request_end_monotonic_ns']
assert all(row.get('schema') == 'lsa-native-graph-v1' for row in before + rows)
admitted = [row for row in before + rows if row.get('event') == 'admitted']
assert len(admitted) == 1
assert admitted[0].get('model_sha256') == manifest['model_sha256']
assert admitted[0].get('map_sha256') == manifest['map_sha256']
assert not any(row.get('event') == 'admission_refused' for row in before + rows)
assert all(row.get('event') == 'layer_complete' for row in rows) and rows

layers = set(range(3, 64, 4))
identities = set()
groups = {}
pruned = set()
for row in rows:
    layer = row.get('layer')
    assert layer in layers and row.get('backend') == 'hip'
    assert row.get('model_sha256') == manifest['model_sha256']
    assert row.get('map_sha256') == manifest['map_sha256']
    assert row.get('native_success') == 1
    assert row.get('original_flash_fallback_count') == 0
    assert not any(key in row for key in ('failure_stage', 'failure_reason', 'failure_detail'))
    sequence, slot, epoch, first, count = (row.get(key) for key in ('sequence', 'slot', 'epoch', 'first', 'count'))
    assert all(type(value) is int for value in (sequence, slot, epoch, first, count))
    assert sequence >= 0 and slot == 0 and epoch > 0 and first >= 0 and 0 < count <= int(manifest['max_new_tokens'])
    assert first + count <= plan['prompt_n'] + plan['request']['n_predict']
    identities.add((sequence, slot, epoch))
    groups.setdefault((first, count), []).append(layer)
    key, value, dense = (row.get(name) for name in ('selected_key_rows', 'selected_value_rows', 'dense_visible_rows'))
    assert all(type(number) is int and number > 0 for number in (key, value, dense))
    assert key <= dense and value <= dense
    if key < dense and value < dense:
        pruned.add(layer)
assert len(identities) == 1, f'multiple request identities: {identities}'
for group, seen in groups.items():
    assert len(seen) == 16 and set(seen) == layers, f'incomplete or duplicate layers for {group}'
cursor = 0
for first, count in sorted(groups):
    assert first == cursor, f'noncontiguous request coverage at {cursor}, found {first}'
    cursor = first + count
assert cursor >= plan['prompt_n'], f'incomplete prompt coverage {cursor}/{plan["prompt_n"]}'
mechanism = 'pruned' if pruned == layers else 'unpruned'
print(json.dumps({'valid': True, 'schema': 'lsa-native-trace-validation-v1',
                  'mechanism': mechanism, 'identity': list(next(iter(identities))),
                  'layers_pruned': sorted(pruned), 'events': len(rows),
                  'covered_tokens': cursor,
                  'scope': 'one request; no model-quality or speedup generalization'}))
