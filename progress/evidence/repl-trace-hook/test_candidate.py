import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def invoke(tmp_path, enabled, pin_ok=True):
    source = tmp_path / 'trace_capture.py'
    # Apply the review patch to the pinned source without changing the APP tree.
    base = subprocess.check_output(['git', '-C', '/mnt/raid0/llm/epyc-orchestrator',
        'show', '488b31c96c6c148768508b3dcaefcb6c4c297664:src/repl_environment/trace_capture.py'])
    source.write_bytes(base)
    subprocess.run(['patch', '-s', str(source), str(HERE / 'app-hook.patch')], check=True)
    pin = hashlib.sha256(source.read_bytes()).hexdigest() if pin_ok else '0' * 64
    run = '''
import importlib.util, sys, types
from types import SimpleNamespace
src = types.ModuleType('src'); src.__path__ = []
repl = types.ModuleType('src.repl_environment'); repl.__path__ = []
sys.modules['src'] = src; sys.modules['src.repl_environment'] = repl
spec = importlib.util.spec_from_file_location('src.repl_environment.trace_belief', sys.argv[1])
bridge = importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)
sys.modules[spec.name] = bridge; repl.trace_belief = bridge
ns = {'__file__': sys.argv[2], '__name__': 'native_trace'}
exec(compile(open(sys.argv[2]).read(), sys.argv[2], 'exec'), ns)
env = SimpleNamespace(); path = sys.argv[3] + '/spill'; text = 'first target second'
ns['register_spill'](env, path, text)
ns['record_spill_search'](env, path, text, 'target', 1, [{'start': 6, 'end': 12}])
ns['record_spill_open'](env, path, text, 6, 12)
'''
    env = dict(os.environ, PYTHONPATH=str(ROOT), EPYC_REPL_TRACE_CAPTURE='1',
               EPYC_REPL_TRACE_DIR=str(tmp_path / 'native'),
               EPYC_REPL_TRACE_BELIEF_CAPTURE='1' if enabled else '0',
               EPYC_REPL_TRACE_BELIEF_DIR=str(tmp_path / 'belief'),
               EPYC_REPL_TRACE_BELIEF_SOURCE_SHA256=pin)
    subprocess.run([sys.executable, '-c', run, str(HERE / 'trace_belief.py'), str(source), str(tmp_path)],
                   env=env, check=True, capture_output=True, text=True)
    return list((tmp_path / 'belief').glob('*.belief_measurements.jsonl'))


def test_opted_in_native_events_finalize_valid_sidecar(tmp_path):
    from scripts.vidya.producers.repl_trace_capture import validate
    sidecars = invoke(tmp_path, True)
    assert len(sidecars) == 1
    row = json.loads(sidecars[0].read_text())
    assert row['value'] == 2 and validate(row) == []
    assert len(list((tmp_path / 'native').glob('*.jsonl'))) == 1


def test_flag_off_keeps_native_capture_without_belief_files(tmp_path):
    assert invoke(tmp_path, False) == []
    assert len(list((tmp_path / 'native').glob('*.jsonl'))) == 1


def test_bad_source_pin_fails_closed_but_native_capture_remains(tmp_path):
    assert invoke(tmp_path, True, False) == []
    assert len(list((tmp_path / 'native').glob('*.jsonl'))) == 1
