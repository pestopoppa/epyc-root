import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/coordination/taskflow/canary_perf_summary.py'
FIXTURE = Path(__file__).parent / 'fixtures/canary_perf.jsonl'
spec = importlib.util.spec_from_file_location('canary_perf_summary', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_summary_and_comparisons(tmp_path, capsys):
    cpu = tmp_path / 'run-cpu' / 'out'
    gpu = tmp_path / 'run-gpu' / 'out'
    cpu.mkdir(parents=True)
    gpu.mkdir(parents=True)
    data = FIXTURE.read_bytes()
    (cpu / 'results.jsonl').write_bytes(data + b'{"unfinished":')
    (gpu / 'results.jsonl').write_bytes(data)
    out = tmp_path / 'summary'
    assert module.main([str(cpu.parent), str(gpu), '--output-dir', str(out)]) == 0
    report = json.loads((out / 'canary-perf-summary.json').read_text())
    assert report['sources'][0]['pending_partial_line']
    r = next(g for g in report['groups'] if g['device'] == 'CPU' and g['arm'] == 'R-canary-nothink')['summary']
    assert (r['n'], r['pass_rate'], r['rejected_by_failure_class']) == (2, .5, {'harness': 1})
    assert r['metrics']['decode_tok_s'] == {'n': 2, 'median': 15, 'q1': 12.5, 'q3': 17.5, 'iqr': 5}
    assert r['totals']['bad_tool_args_seen'] == {'total': 2, 'n': 2}
    assert {c['kind'] for c in report['comparisons']} == {'GPU - CPU', 'F - R', 'think - nothink'}
    comparison = next(c for c in report['comparisons'] if c['kind'] == 'F - R')
    assert comparison['metrics']['decode_tok_s'] == {'delta': 15, 'n_a': 2, 'n_b': 1}
    assert 'Performance summary' in capsys.readouterr().out
    assert (out / 'canary-perf-summary.md').exists()
    assert (cpu / 'results.jsonl').read_bytes() == data + b'{"unfinished":'


def test_pending_missing_and_corrupt(tmp_path):
    path = tmp_path / 'results.jsonl'
    path.write_bytes(b'{"arm":')
    assert module.read_units(path) == ([], True)
    assert module.distribution([None, float('nan')])['n'] == 0
    path.write_bytes(b'{broken}\n')
    with pytest.raises(ValueError, match=':1:'):
        module.read_units(path)


def test_watch_rewrites_on_growth(tmp_path, monkeypatch, capsys):
    row = tmp_path / 'row'
    row.mkdir()
    source = row / 'results.jsonl'
    source.write_bytes(FIXTURE.read_bytes().splitlines(keepends=True)[0])
    out = tmp_path / 'summary'
    calls = []
    def sleep(_):
        calls.append(1)
        if len(calls) == 1:
            with source.open('ab') as f:
                f.write(FIXTURE.read_bytes().splitlines(keepends=True)[1])
        else:
            raise KeyboardInterrupt
    monkeypatch.setattr(module.time, 'sleep', sleep)
    assert module.main([str(row), '--output-dir', str(out), '--watch', '1']) == 0
    assert json.loads((out / 'canary-perf-summary.json').read_text())['sources'][0]['n'] == 2
    assert capsys.readouterr().out.count('# Performance summary') == 2


def test_output_inside_row_rejected(tmp_path):
    row = tmp_path / 'row'
    (row / 'out').mkdir(parents=True)
    (row / 'out/results.jsonl').write_bytes(b'')
    with pytest.raises(SystemExit):
        module.main([str(row), '--output-dir', str(row / 'summary')])
