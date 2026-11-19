"""Offline regressions for qualification, case resume and input custody."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QualificationTest(unittest.TestCase):
    def test_complete_result_required_outside_smoke(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            native = root / 'native'
            native.mkdir()
            script = root / 'first_progress.py'
            script.write_text((HERE / 'first_progress.py').read_text().replace(
                '/mnt/raid0/llm/tmp/triattention-s8c-api-real-20261104/native', str(native)))
            env = dict(os.environ)
            env.pop('FILLER_SMOKE_T0', None)
            def run():
                return subprocess.run([sys.executable, str(script)], env=env, capture_output=True).returncode
            self.assertNotEqual(run(), 0)
            result = native / 'RESULT.json'
            result.write_text(json.dumps({'unit': 's8c-real-api', 'status': 'invalid'}))
            self.assertNotEqual(run(), 0)
            for status in ('pass', 'fail'):
                result.write_text(json.dumps({'unit': 's8c-real-api', 'status': status}))
                self.assertEqual(run(), 0)

    def test_smoke_requires_full_result_not_case_log(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            native = root / 'native'
            native.mkdir()
            script = root / 'first_progress.py'
            script.write_text((HERE / 'first_progress.py').read_text().replace(
                '/mnt/raid0/llm/tmp/triattention-s8c-api-real-20261104/native', str(native)))
            env = dict(os.environ, FILLER_SMOKE_T0=str(time.time() - 1))
            def run():
                return subprocess.run([sys.executable, str(script)], env=env, capture_output=True).returncode
            (native / 'cases.jsonl').write_text('{"case":"first_compaction","pass":true}\n')
            self.assertNotEqual(run(), 0)
            (native / 'RESULT.json').write_text(json.dumps({'unit':'s8c-real-api','status':'pass'}))
            self.assertEqual(run(), 0)


class ApiOutcomeTest(unittest.TestCase):
    def test_gapped_rejection_and_no_eviction_are_distinct(self):
        api = load_module('s8c_api_cases_test', HERE / 'api_cases.py')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); dsos = root / 'dsos.json'; dsos.write_text('{}')
            def run(name, responses):
                output = root / name
                argv = ['api_cases.py', '--port', '18214', '--server-pid', '123',
                        '--server-sha256', 'a' * 64, '--dso-hashes', str(dsos), '--output', str(output)]
                with mock.patch.object(sys, 'argv', argv), \
                     mock.patch.object(api, 'require_owned_listener', return_value={'start_ticks': 42}), \
                     mock.patch.object(api, 'start_ticks', return_value=42), \
                     mock.patch.object(api, 'populate'), mock.patch.object(api, 'request', side_effect=responses):
                    rc = api.main()
                return rc, json.loads(output.read_text())
            rc, data = run('pass.json', [(200, {'id_slot': 0, 'scorer': 'expected_attention', 'n_evicted': 1}, ''), (500, {'error': {'message': 'Expected Attention compression failed'}}, '')])
            self.assertEqual(rc, 0); self.assertEqual(data['status'], 'pass')
            rc, data = run('inconclusive.json', [(200, {'id_slot': 0, 'scorer': 'expected_attention', 'n_evicted': 0}, '')])
            self.assertNotEqual(rc, 0); self.assertEqual(data['status'], 'inconclusive')
            self.assertEqual(len(data['cases']), 1)


class PacketPinTest(unittest.TestCase):
    def test_tampered_plan_or_token_ids_are_rejected(self):
        pins = load_module('s8c_packet_pins_test', HERE / 'packet_pins.py')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = root / 'plan.json'
            tokens = root / 'token-ids.json'
            plan.write_text('{"model":"test"}\n')
            tokens.write_text('[1, 2, 3]\n')
            digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            pin = root / 'packet-pin.json'
            pin.write_text(json.dumps({'plan_sha256': digest(plan), 'files': {str(tokens): digest(tokens)}}))
            pins.verify_packet_pin(pin)
            tokens.write_text('[1, 2, 4]\n')
            with self.assertRaises((ValueError, AssertionError, OSError)):
                pins.verify_packet_pin(pin)
            tokens.write_text('[1, 2, 3]\n')
            plan.write_text('{"model":"changed"}\n')
            with self.assertRaises((ValueError, AssertionError, OSError)):
                pins.verify_packet_pin(pin)


if __name__ == '__main__':
    unittest.main()
