"""Offline attempt lifecycle: interrupted work resumes; terminal markers never get reused."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from attempt_state import AttemptRefusal, begin_finalization, prepare_attempt
from verdict_inputs import VERDICT_INPUTS

PINS = ('src', 'manifest', 'pre', 'amend')

def test_interrupted_attempt_resumes_same_identity_but_terminal_artifacts_refuse():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'attempt'
        first = prepare_attempt(out, 'row-x', *PINS)
        resumed = prepare_attempt(out, 'row-x', *PINS)
        assert resumed['run_id'] == first['run_id']
        input_path = out / 'run' / 'pb_qcost_1.jsonl'; input_path.parent.mkdir()
        for rel in VERDICT_INPUTS:
            target = out / rel; target.parent.mkdir(parents=True, exist_ok=True); target.write_text('fixture')
        begin_finalization(out / 'ATTEMPT.json', input_path, 12.5)
        # Simulate a crash after the verdict write and before RESULT/COMPLETE.
        (out / 'VERDICT.json').write_text(json.dumps({'run_id': first['run_id']}))
        resumed_finalizing = prepare_attempt(out, 'row-x', *PINS)
        assert resumed_finalizing['state'] == 'FINALIZING'
        (out / 'RESULT.json').write_text(json.dumps({'run_id':'stale-other-attempt'}))
        # Simulate a crash after RESULT write; recovery may re-derive, never trusts this mixed pair.
        resumed_after_result = prepare_attempt(out, 'row-x', *PINS)
        assert resumed_after_result['run_id'] == first['run_id']
        state = json.loads((out / 'ATTEMPT.json').read_text())
        state['state'] = 'ACTIVE'
        (out / 'ATTEMPT.json').write_text(json.dumps(state))
        try:
            prepare_attempt(out, 'row-x', *PINS)
        except AttemptRefusal as exc:
            assert 'without FINALIZING' in str(exc)
        else:
            raise AssertionError('stale terminal artifact was accepted without a durable finalization record')

def test_identity_or_source_drift_refuses_resume():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'attempt'
        prepare_attempt(out, 'row-x', *PINS)
        try:
            prepare_attempt(out, 'row-x', 'changed', *PINS[1:])
        except AttemptRefusal as exc:
            assert 'pins differ' in str(exc)
        else:
            raise AssertionError('source drift was accepted')
