"""Real released schemas and durable scripted capture; no model-quality evidence."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bfcl_capture_run import Journal, capture_case, encoded, released_catalog
import test_bfcl_native as controls


class CustodyControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        controls.OfficialControls.setUpClass()
        cls.bridge = controls.OfficialControls.bridge
        cls.rows = controls.OfficialControls.rows[16:]
        cls.catalog = os.environ['BFCL_CATALOG']
        cls.helpers = controls.OfficialControls()
        cls.identity = {'model': 'scripted-control', **{key: 'a' * 64 for key in (
            'model_sha256', 'server_binary_sha256', 'build_manifest_sha256',
            'runtime_manifest_sha256')}}

    def run_case(self, row, output, query, **kw):
        return capture_case(self.bridge, row, 'scripted-control', self.identity,
                            self.catalog, output, query, **kw)

    def read(self, output):
        records = [json.loads(line) for line in output.read_bytes().splitlines()]
        previous = None
        for index, row in enumerate(records):
            sha = row.pop('sha256')
            self.assertEqual(sha, hashlib.sha256(encoded(row)).hexdigest())
            self.assertEqual(row['sequence'], index)
            self.assertEqual(row['previous_sha256'], previous)
            previous = sha
        return [r['event'] for r in records]

    def test_released_catalog_five_filesystem_cases_through_durable_official_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            for row in self.rows:
                if 'TwitterAPI' in row['case']['involved_classes']:
                    continue
                output = Path(tmp) / row['case']['id']
                script = iter(self.helpers.script(self.helpers.native_turns(row)))
                def query(payload):
                    events = self.read(output)
                    self.assertEqual(events[-1]['kind'], 'exposure')
                    self.assertEqual(events[-1]['request'], payload)
                    self.assertFalse({'gold', 'initial_config', 'path'} & payload.keys())
                    return next(script)
                verdict = self.run_case(row, output, query)
                self.assertIs(verdict['valid'], True)
                events = self.read(output)
                self.assertEqual(events[0]['identity'], self.identity)
                self.assertEqual(events[-1]['kind'], 'verdict')
                self.assertEqual(events[-1]['verdict'], verdict)
                self.assertTrue(events[0]['catalog']['files'])
                with self.assertRaises(FileExistsError):
                    self.run_case(row, output, lambda p: self.fail('redrawn'))

    def test_five_twitter_cases_refuse_schema_simulator_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            for row in self.rows:
                if 'TwitterAPI' not in row['case']['involved_classes']:
                    continue
                output = Path(tmp) / row['case']['id']
                with self.assertRaisesRegex(ValueError, 'exact simulator method schemas'):
                    self.run_case(row, output, lambda p: self.fail('incompatible exposure'))
                events = self.read(output)
                self.assertEqual([e['kind'] for e in events], ['identity', 'aborted'])
                self.assertIsNone(events[-1]['valid'])

    def test_binding_refusals_before_exposure(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'result'
            for field in ['case', 'gold']:
                row = copy.deepcopy(self.rows[1]); row[field]['extra'] = 'tampered'
                with self.assertRaisesRegex(ValueError, 'content differs'):
                    self.run_case(row, output, lambda p: self.fail('exposed'))
            with self.assertRaisesRegex(ValueError, 'content identity'):
                capture_case(self.bridge, self.rows[1], 'scripted-control', {'model': 'scripted-control'},
                             self.catalog, output, lambda p: self.fail('exposed'))
            self.assertFalse(output.exists())
            Path(tmp, 'gorilla_file_system.json').write_text('{}')
            Path(tmp, 'posting_api.json').write_bytes(Path(self.catalog, 'posting_api.json').read_bytes())
            with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                released_catalog(self.rows[1]['case'], tmp)

    def test_transport_failure_records_abort_and_refuses_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'result'
            def query(payload):
                raise OSError('transport failed')
            with self.assertRaises(OSError):
                self.run_case(self.rows[1], output, query)
            events = self.read(output)
            self.assertEqual([e['kind'] for e in events], ['identity', 'exposure', 'aborted'])
            self.assertIsNone(events[-1]['valid'])
            with self.assertRaises(FileExistsError):
                self.run_case(self.rows[1], output, query)

    def test_parse_error_and_interruption_remain_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'malformed'
            verdict = self.run_case(self.rows[1], output, lambda p: {'choices': []})
            self.assertEqual(verdict['status'], 'parse_error')
            self.assertIsNone(verdict['valid'])
            self.assertEqual([e['kind'] for e in self.read(output)],
                             ['identity', 'exposure', 'response', 'capture_result', 'verdict'])
            verdict = self.run_case(self.rows[1], Path(tmp) / 'stopped',
                                    lambda p: self.fail('exposed'), should_stop=lambda: True)
            self.assertEqual(verdict['status'], 'interrupted')
            self.assertIsNone(verdict['valid'])

    def test_fsync_failure_prevents_query_and_poisoned_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('bfcl_capture_run.os.fsync', side_effect=OSError('disk')):
                with self.assertRaises(OSError):
                    self.run_case(self.rows[1], Path(tmp) / 'before-header', lambda p: self.fail('exposed'))
            real_fsync = os.fsync
            calls = []
            def fail_exposure(fd):
                calls.append(fd)
                if len(calls) == 3:
                    raise OSError('exposure flush failed')
                return real_fsync(fd)
            with patch('bfcl_capture_run.os.fsync', side_effect=fail_exposure):
                with self.assertRaisesRegex(OSError, 'exposure flush'):
                    self.run_case(self.rows[1], Path(tmp) / 'exposure', lambda p: self.fail('exposed'))
            journal = Journal(Path(tmp) / 'journal')
            try:
                with patch('bfcl_capture_run.os.fsync', side_effect=OSError('disk')):
                    with self.assertRaises(OSError): journal.append({'kind': 'exposure'})
                with self.assertRaises(RuntimeError): journal.append({'kind': 'response'})
            finally:
                journal.close()
