"""Model-free tests of the actual C++ reducer and its Python trace consumer."""
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('precision_native_worker', HERE / 'worker.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


@pytest.fixture(scope='module')
def reducer(tmp_path_factory):
    directory = tmp_path_factory.mktemp('native-reducer')
    source = directory / 'reduce.cpp'
    source.write_text(r'''
#include "native_witness.h"
#include <iostream>
#include <iomanip>
#include <limits>
#include <vector>
int main(int argc, char ** argv) {
    if (argc == 2) {
        float bad = std::numeric_limits<float>::quiet_NaN();
        try { precision_compare(&bad, &bad, argv[1][0] == '0' ? 0 : 1); }
        catch (const std::exception &) { return 0; }
        return 1;
    }
    std::size_t n; std::cin >> n;
    std::vector<float> a(n), b(n);
    for (auto & x : a) std::cin >> x;
    for (auto & x : b) std::cin >> x;
    auto w = precision_compare(a.data(), b.data(), n);
    std::cout << std::setprecision(17) << w.count << ' ' << w.verify_argmax
              << ' ' << w.max_abs << ' ' << w.sum_squared;
}
''')
    exe = directory / 'reduce'
    subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(HERE),
                    str(source), '-o', str(exe)], check=True, capture_output=True)
    return exe


@pytest.mark.parametrize('left,right', [([0, 2, 1], [0, 1.5, 1]),
                                      ([3, 3, 1], [3, 3, 1]),
                                      ([-3, -2, -2], [-3, 0, -2]),
                                      ([1e30, -1e30], [-1e30, 1e30])])
def test_cpp_full_vocabulary_moments(reducer, left, right):
    import struct
    f32 = lambda x: struct.unpack('f', struct.pack('f', x))[0]
    left, right = list(map(f32, left)), list(map(f32, right))
    data = ' '.join(map(str, [len(left), *left, *right]))
    out = subprocess.run([str(reducer)], input=data, text=True, capture_output=True, check=True).stdout.split()
    assert int(out[0]) == len(left)
    assert int(out[1]) == max(range(len(left)), key=left.__getitem__)
    assert float(out[2]) == max(abs(a - b) for a, b in zip(left, right))
    assert float(out[3]) == pytest.approx(math.fsum((a - b)**2 for a, b in zip(left, right)))


@pytest.mark.parametrize('arg', ['0', 'nan'])
def test_cpp_rejects_empty_and_nonfinite(reducer, arg):
    subprocess.run([str(reducer), arg], check=True)


def test_cpp_large_vocabulary_sum_accuracy(reducer):
    import struct
    n = 200000
    data = str(n) + ' ' + '0.1 ' * n + '0 ' * n
    result = subprocess.run([str(reducer)], input=data, text=True, capture_output=True, check=True).stdout.split()
    f32 = struct.unpack('f', struct.pack('f', .1))[0]
    assert float(result[3]) == pytest.approx(n * f32**2, rel=1e-14)


def compact():
    request = {'settings': {'sampling': {'temperature': 0, 'top_k': 1}}}
    rows = []
    for prefix, peak in [([2], .5), ([2, 1], 0), ([2, 1, 1], 0)]:
        rows.append({'verify_prefix': prefix, 'serial_prefix': prefix,
                     'witness': {'count': 3, 'verify_argmax': 1 if len(prefix) == 1 else 0,
                                 'max_abs': peak, 'sum_squared': peak**2}})
    return {'request': request, 'status': 'ok', 'spec_type': 'draft-dflash',
            'numerical_encoding': 'full-vocabulary-moments-v1',
            'blocks': [{'block': 0, 'draft_tokens': [1, 1], 'accepted': 1, 'logits': rows}]}, request


def test_compact_exact_denominators_and_rms():
    trace, request = compact()
    result = worker.reduce_trace(trace, request)
    assert result['accepted'] == 1 and result['drafted'] == 2
    assert result['numerical_divergence'] == {'max_abs': .5, 'rms': pytest.approx(1/6)}


@pytest.mark.parametrize('change', [
    lambda t: t.update(numerical_encoding='top-k'),
    lambda t: t['blocks'][0]['logits'][0]['witness'].update(count=True),
    lambda t: t['blocks'][0]['logits'][0]['witness'].update(count=0),
    lambda t: t['blocks'][0]['logits'][0]['witness'].update(count=1000001),
    lambda t: t['blocks'][0]['logits'][0]['witness'].update(verify_argmax=3),
    lambda t: t['blocks'][0]['logits'][0]['witness'].update(verify_argmax=0),
    lambda t: t['blocks'][0]['logits'][0]['witness'].update(max_abs=float('nan')),
    lambda t: t['blocks'][0]['logits'][0]['witness'].update(sum_squared=-1),
    lambda t: t['blocks'][0]['logits'][0]['witness'].update(sum_squared=.1),
    lambda t: t['blocks'][0]['logits'][0]['witness'].update(sum_squared=1),
    lambda t: t['blocks'][0]['logits'][0]['witness'].update(extra=1),
    lambda t: t['blocks'][0]['logits'][1]['witness'].update(count=4),
    lambda t: t['blocks'][0]['logits'][0].update(verify=[0, 2, 1]),
    lambda t: t['blocks'][0]['logits'][1].update(serial_prefix=[9]),
])
def test_compact_rejects_false_or_inconsistent_witness(change):
    trace, request = compact()
    request = copy.deepcopy(request)
    change(trace)
    with pytest.raises(ValueError):
        worker.reduce_trace(trace, request)


def test_compact_bound_for_large_vocabulary():
    trace, request = compact()
    for row in trace['blocks'][0]['logits']:
        row['witness']['count'] = 248320
    assert len(json.dumps(trace)) < 2000
    assert worker.reduce_trace(trace, request)['numerical_divergence']['rms'] == pytest.approx(math.sqrt(.25/(3*248320)))


def test_compact_variable_width_continuation():
    trace, request = compact()
    block = copy.deepcopy(trace['blocks'][0])
    block.update(block=1, draft_tokens=[1], accepted=1)
    block['logits'] = block['logits'][:2]
    for i, row in enumerate(block['logits']):
        row['verify_prefix'] = row['serial_prefix'] = [2, 1, 0] + [1] * i
    trace['blocks'].append(block)
    result = worker.reduce_trace(trace, request)
    assert result['accepted'] == 2 and result['drafted'] == 3
    assert result['positions'] == [dict(position=0, accepted=2, drafted=2),
                                  dict(position=1, accepted=0, drafted=1)]
    block['logits'][0]['verify_prefix'] = block['logits'][0]['serial_prefix'] = [9]
    with pytest.raises(ValueError, match='accepted continuation'):
        worker.reduce_trace(trace, request)


def test_compact_aggregate_overflow_refused():
    trace, request = compact()
    for row in trace['blocks'][0]['logits']:
        row['witness'].update(max_abs=1e154, sum_squared=1e308)
    with pytest.raises(ValueError, match='aggregate divergence overflow'):
        worker.reduce_trace(trace, request)


def test_cpp_api_against_fresh_production_source():
    source = os.environ.get('EPYC_PRECISION_SOURCE')
    if not source:
        pytest.skip('set EPYC_PRECISION_SOURCE to a fresh experimental source checkout')
    source = Path(source)
    command = ['g++', '-std=c++17', '-fsyntax-only', '-Wall', '-Wextra', '-Werror']
    for path in ('common', 'include', 'ggml/include', 'vendor/nlohmann'):
        command += ['-I', str(source / path)]
    subprocess.run(command + [str(HERE / 'native.cpp')], check=True, capture_output=True)


@pytest.mark.parametrize('change,expected', [
    (lambda r: r['settings']['verification'].update(extra=1), 'unsupported setting'),
    (lambda r: r['settings']['verification'].update(replay='live-rollback'), 'unsupported replay mode'),
    (lambda r: r['settings']['verification'].update(draft_max=17), 'setting outside diagnostic bound'),
    (lambda r: r['settings']['verification'].update(ubatch=4), 'verify block must fit one ubatch'),
    (lambda r: r['settings']['verification'].update(threads=True), 'expected integer setting'),
    (lambda r: r['settings']['verification'].update(kv_type='q8_0'), 'only explicit f16 KV supported'),
    (lambda r: r['settings']['sampling'].update(temperature=1), 'only greedy sampling supported'),
    (lambda r: r['settings']['sampling'].update(top_k=True), 'expected integer setting'),
    (lambda r: r['case'].update(seed=-1), 'seed outside uint32'),
    (lambda r: r['case'].update(seed=2**32), 'seed outside uint32'),
])
def test_actual_executable_rejects_unsupported_request_before_model_loading(tmp_path, change, expected):
    exe = os.environ.get('EPYC_PRECISION_EXECUTABLE')
    libs = os.environ.get('EPYC_PRECISION_LIBRARIES')
    if not exe or not libs:
        pytest.skip('set executable and its explicit kernel-store library directory')
    request = {'schema': worker.SCHEMA,
               'trace_semantics': 'greedy_prefix_acceptance_and_same_prefix_verify_vs_serial_logits',
               'case': {'seed': 42}, 'settings': {
                   'sampling': {'temperature': 0, 'top_k': 1},
                   'verification': {'mode': 'block', 'replay': 'fresh-block-serial-v1',
                                    'kv_type': 'f16', 'context': 128, 'batch': 32, 'ubatch': 32,
                                    'draft_max': 7, 'blocks': 2, 'threads': 4, 'flash_attention': 'on'}}}
    change(request)
    path, out = tmp_path / 'request.json', tmp_path / 'trace.json'
    path.write_text(json.dumps(request))
    # Deliberately no runtime/model paths: every case must refuse before the
    # loader boundary, in the real linked C++ executable, without model compute.
    subprocess.run([exe, '--request', str(path), '--output', str(out)],
                   env={'LD_LIBRARY_PATH': libs}, check=True, capture_output=True, timeout=20)
    trace = json.loads(out.read_text())
    assert trace['status'] == 'failed' and trace['request'] == request
    assert trace['error'] == expected
    second = subprocess.run([exe, '--request', str(path), '--output', str(out)],
                            env={'LD_LIBRARY_PATH': libs}, capture_output=True, timeout=20)
    assert second.returncode == 4  # originals cannot be overwritten
