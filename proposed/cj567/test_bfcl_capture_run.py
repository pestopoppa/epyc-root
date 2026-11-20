"""Real released schemas and durable scripted capture; no model-quality evidence."""
import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from bfcl_capture_run import Journal, capture_case, encoded, released_catalog
from bfcl_residency import LocalNativeTransport
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
                            self.catalog, output, query, software_control=True, **kw)

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

    def single_response(self, row):
        language_args = {
            'java_0': {'controller': 'mapController', 'parent': 'mapArea'},
            'java_1': {'object': 'Customers', 'useShortName': 'true',
                       'params': 'new HashMap<String, Object>() {{put("limit", 50); put("schemaFilter", "public");}}'},
            'javascript_0': {'inputField': '"userInputField"', 'isComplete': 'true'},
            'javascript_1': {'listElement': 'listElement', 'attribute': '"data-active"', 'value': 'true'},
        }
        calls = []
        for entry in row['gold']['ground_truth']:
            for name, parameters in entry.items():
                args = language_args.get(row['case']['id'], {
                    key: values[0] for key, values in parameters.items() if values[0] != ""})
                calls.append({'type': 'function', 'function': {
                    'name': name.replace('.', '_'), 'arguments': json.dumps(args)}})
        return {'choices': [{'finish_reason': 'tool_calls', 'message': {'tool_calls': calls}}]}

    def test_fourteen_single_turn_cases_durable_positive_negative_and_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            for row in controls.OfficialControls.rows[:14]:
                response = self.single_response(row)
                wrong = copy.deepcopy(response)
                wrong['choices'][0]['message']['tool_calls'][0]['function']['name'] = 'wrong_function'
                for label, raw, expected in [('positive', response, True),
                                              ('negative', wrong, False),
                                              ('malformed', {'choices': []}, None)]:
                    output = Path(tmp) / (row['case']['id'] + label)
                    before = copy.deepcopy(row)
                    def query(payload):
                        self.assertEqual(self.read(output)[-1], {'kind': 'exposure', 'request': payload})
                        self.assertEqual(payload, self.bridge.request(row['case'], row['category'],
                                                                     'scripted-control')[0])
                        return raw
                    with self.subTest(case=row['case']['id'], response=label):
                        with patch.object(self.bridge, 'score', wraps=self.bridge.score) as score:
                            verdict = self.run_case(row, output, query)
                            score.assert_called_once()
                        self.assertIs(verdict['valid'], expected)
                        events = self.read(output)
                        self.assertEqual([e['kind'] for e in events],
                                         ['identity', 'exposure', 'response', 'capture_result', 'verdict'])
                        self.assertEqual(events[0]['instrument'], 'native-single-turn')
                        self.assertEqual(events[2]['response'], raw)
                        self.assertEqual(events[-1]['verdict'], verdict)
                        self.assertEqual(row, before)
                        with self.assertRaises(FileExistsError):
                            self.run_case(row, output, lambda p: self.fail('retry'))

    def test_single_turn_stop_transport_and_tamper_refuse_without_score(self):
        row = controls.OfficialControls.rows[0]
        with tempfile.TemporaryDirectory() as tmp, patch.object(self.bridge, 'score') as score:
            output = Path(tmp) / 'stopped'
            verdict = self.run_case(row, output, lambda p: self.fail('exposed'), should_stop=lambda: True)
            self.assertIsNone(verdict['valid'])
            self.assertEqual(verdict['status'], 'interrupted')
            score.assert_not_called()
            output = Path(tmp) / 'failed'
            query = Mock(side_effect=OSError('transport lost'))
            with self.assertRaises(OSError):
                self.run_case(row, output, query)
            query.assert_called_once()
            score.assert_not_called()
            self.assertEqual(self.read(output)[-1]['kind'], 'aborted')
            changed = copy.deepcopy(row); changed['case']['question'][0][0]['content'] += ' altered'
            with self.assertRaisesRegex(ValueError, 'content differs'):
                self.run_case(changed, Path(tmp) / 'tampered', lambda p: self.fail('exposed'))
            self.assertFalse((Path(tmp) / 'tampered').exists())

    def test_single_turn_disk_or_residency_loss_prevents_scoring(self):
        row = controls.OfficialControls.rows[0]
        with tempfile.TemporaryDirectory() as tmp, patch.object(self.bridge, 'score') as score:
            query = Mock(return_value=self.single_response(row))
            with patch('bfcl_capture_run.os.fsync', side_effect=OSError('disk failed')):
                with self.assertRaises(OSError):
                    self.run_case(row, Path(tmp) / 'disk', query)
            query.assert_not_called()
            score.assert_not_called()
            transport = Mock(spec=LocalNativeTransport, return_value=self.single_response(row))
            transport.identity = self.identity
            transport.probe.side_effect = [{}, {}, ValueError('residency lost')]
            output = Path(tmp) / 'lost-proof'
            with self.assertRaisesRegex(ValueError, 'residency lost'):
                capture_case(self.bridge, row, 'scripted-control', self.identity,
                    self.catalog, output, transport)
            transport.assert_called_once()
            score.assert_not_called()
            events = self.read(output)
            self.assertEqual([e['kind'] for e in events],
                             ['identity', 'residency', 'exposure', 'response', 'aborted'])

    def test_single_turn_live_residency_brackets_response_before_checker(self):
        row = controls.OfficialControls.rows[0]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'live'
            transport = Mock(spec=LocalNativeTransport, return_value=self.single_response(row))
            transport.identity = self.identity
            transport.probe.return_value = {'mock': 'residency software control'}
            original = self.bridge.score
            def score(*args):
                events = self.read(output)
                self.assertEqual([e['kind'] for e in events],
                    ['identity', 'residency', 'exposure', 'response', 'residency', 'capture_result'])
                return original(*args)
            with patch.object(self.bridge, 'score', side_effect=score):
                verdict = capture_case(self.bridge, row, 'scripted-control', self.identity,
                    self.catalog, output, transport)
            self.assertIs(verdict['valid'], True)
            self.assertEqual(transport.probe.call_count, 3)

    def test_official_catalog_all_ten_cases_through_durable_official_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            for row in self.rows:
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
                sources = events[0]['catalog']['sources']
                if 'TwitterAPI' in row['case']['involved_classes']:
                    self.assertEqual(sources['posting_api.json']['revision'],
                                     'f64916eb4092aef76fc8609bd53eb594b5e84bd0')
                self.assertEqual(events[0]['catalog']['simulator_compatibility']['checker_commit'],
                                 events[0]['upstream_commit'])
                with self.assertRaises(FileExistsError):
                    self.run_case(row, output, lambda p: self.fail('redrawn'))

    def test_official_twitter_catalog_matches_original_simulator_without_filtering(self):
        repo = os.environ['BFCL_CHECKOUT']
        functions, binding = released_catalog({'involved_classes': ['TwitterAPI']}, self.catalog)
        source = binding['sources']['posting_api.json']
        raw = subprocess.check_output(['git', '-C', repo, 'show',
                                       source['revision'] + ':' + source['path']])
        self.assertEqual(raw, Path(self.catalog, 'posting_api.json').read_bytes())
        self.assertEqual(functions, list(map(json.loads, raw.splitlines())))
        self.assertEqual(len(functions), 13)
        self.assertNotIn('posting_get_login_status', {f['name'] for f in functions})
        compat = binding['simulator_compatibility']
        for revision in (compat['checker_commit'], source['revision']):
            blob = subprocess.check_output(['git', '-C', repo, 'rev-parse',
                revision + ':' + compat['twitter_source_path']], text=True).strip()
            self.assertEqual(blob, compat['twitter_blob'])

    def test_later_twitter_catalog_refused_before_exposure(self):
        # Bind the exact historical catalog; do not silently strip an extra method.
        with tempfile.TemporaryDirectory() as catalog:
            raw = subprocess.check_output(['git', '-C', os.environ['BFCL_CHECKOUT'], 'show',
                '4c16dbb2cffb65a56c95f9c06053dd205f663142:'
                'berkeley-function-call-leaderboard/data/multi_turn_func_doc/posting_api.json'])
            self.assertIn('posting_get_login_status', {json.loads(line)['name']
                                                     for line in raw.splitlines()})
            Path(catalog, 'posting_api.json').write_bytes(raw)
            Path(catalog, 'gorilla_file_system.json').write_bytes(
                Path(self.catalog, 'gorilla_file_system.json').read_bytes())
            row = next(r for r in self.rows if 'TwitterAPI' in r['case']['involved_classes'])
            with tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'result'
                with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                    capture_case(self.bridge, row, 'scripted-control', self.identity,
                                 catalog, output, lambda p: self.fail('exposed'), software_control=True)
                self.assertFalse(output.exists())

    def test_unknown_method_still_refuses_before_transport(self):
        for row in self.rows:
            if 'TwitterAPI' not in row['case']['involved_classes']:
                continue
            functions, _ = released_catalog(row['case'], self.catalog)
            functions.append({'name': 'posting_get_login_status'})
            with self.assertRaisesRegex(ValueError, 'exact simulator method schemas'):
                self.bridge.capture_multi_turn(row['case'], row['category'], 'scripted-control',
                    functions, lambda p: self.fail('incompatible exposure'),
                    lambda e: self.fail('incompatible event'))

    def test_binding_refusals_before_exposure(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'result'
            for field in ['case', 'gold']:
                row = copy.deepcopy(self.rows[1]); row[field]['extra'] = 'tampered'
                with self.assertRaisesRegex(ValueError, 'content differs'):
                    self.run_case(row, output, lambda p: self.fail('exposed'))
            with self.assertRaisesRegex(ValueError, 'content identity'):
                capture_case(self.bridge, self.rows[1], 'scripted-control', {'model': 'scripted-control'},
                             self.catalog, output, lambda p: self.fail('exposed'), software_control=True)
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

    def test_live_proofs_bracket_exposure_and_raw_response_before_scoring(self):
        transport = object.__new__(LocalNativeTransport)
        transport.identity = self.identity.copy()
        transport.probe = Mock(return_value={'fixture': 'software proof control'})
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'live-control'
            with patch.object(LocalNativeTransport, '__call__', return_value={'choices': []}):
                verdict = capture_case(self.bridge, self.rows[1], 'scripted-control', self.identity,
                    self.catalog, output, transport)
            self.assertIsNone(verdict['valid'])
            self.assertEqual([e['kind'] for e in self.read(output)],
                ['identity', 'residency', 'exposure', 'response', 'residency', 'capture_result', 'verdict'])
            self.assertEqual(transport.probe.call_count, 3)
            transport.probe = Mock(side_effect=[{}, {}, ValueError('server changed')])
            output = Path(tmp) / 'lost-residency'
            with patch.object(LocalNativeTransport, '__call__', return_value={'choices': []}):
                with self.assertRaisesRegex(ValueError, 'server changed'):
                    capture_case(self.bridge, self.rows[1], 'scripted-control', self.identity,
                        self.catalog, output, transport)
            self.assertEqual([e['kind'] for e in self.read(output)],
                             ['identity', 'residency', 'exposure', 'response', 'aborted'])
            self.assertIsNone(self.read(output)[-1]['valid'])

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
