#!/usr/bin/env python3
"""Recognize native progress separately from the final scientific verdict."""
import json
import os
from pathlib import Path
import sys

D = Path(__file__).resolve().parent
SOURCE = Path('/mnt/raid0/llm/views/epyc-root-main/docs/reports/g3-mi210-verify-instrumentation')
sys.path.insert(0, str(SOURCE))
from native_protocol import capture_ok, negative_control, verify_inputs
from diagnostic_runner import resolve_build_binding


def precondition():
    base = json.loads((D / 'base.json').read_text())
    verify_inputs(base)
    resolve_build_binding(base)
    s = Path(base['model']).stat()
    actual = dict(dev=s.st_dev, ino=s.st_ino, size=s.st_size,
                  mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns)
    assert actual == json.loads(Path(base['model_preflight']).read_text())['model']['stat']


def progress():
    t0 = float(os.environ['FILLER_SMOKE_T0'])
    base = json.loads((D / 'base.json').read_text())
    layers = json.loads(Path(base['layer_manifest']).read_text())['verify_attention_layer_ids']
    for p in (D / 'runs').glob('attempt-*/capture/endpoint.json'):
        if p.stat().st_mtime < t0:
            continue
        cell = json.loads(p.read_text())['cells'].get('q8_0-mtp-off', {})
        native = cell.get('result', {})
        if cell.get('rc') != 0 or not capture_ok(native, len(base['requests'])):
            continue
        trace = (p.parent / 'q8_0-mtp-off/server.log').read_text()
        if negative_control(trace, native, layers, len(base['requests']), 'q8_0')['status'] == 'PASS':
            return
    raise ValueError('no new drained native MTP-off control')


def complete():
    if os.environ.get('FILLER_DRYRUN') == '1':
        raise ValueError('smoke is not full completion')
    data = json.loads((D / 'RESULT.json').read_text())
    expected = {'q8_0-mtp-off', 'q4_0-mtp-off', 'q8_0-d1', 'q8_0-d4', 'q4_0-d1', 'q4_0-d4'}
    assert set(data['cells']) == expected
    for cell in data['cells'].values():
        assert cell['rc'] == 0 and capture_ok(cell['result'], cell['request_count'])


if __name__ == '__main__':
    try:
        {'precondition': precondition, 'progress': progress, 'complete': complete}[sys.argv[1]]()
    except (OSError, ValueError, KeyError, AssertionError, TypeError):
        sys.exit(1)
