#!/usr/bin/env python3
"""Exercise prospective bank admission with synthetic native-shaped responses only."""
import base64
import copy
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import capture
import quality_parity as parity
from complete_predicate import complete
from pair import CAP_KEY


class Controls(unittest.TestCase):
    def setUp(self):
        self.plan = parity._parse((capture.D / 'plan.json').read_bytes())
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.filler = patch.dict(os.environ, {
            'FILLER_ID': 'offline-control', 'FILLER_DEADLINE': str(int(time.time()) + 10),
            'FILLER_STOPFILE': str(self.root / 'STOP'), 'FILLER_GRANTS_DIR': str(self.root),
            'FILLER_NEEDGPU': '0',
        })
        self.filler.start()
        self.addCleanup(self.filler.stop)
        (self.root / 'offline-control.grant').write_bytes(b'synthetic grant')
        self.runtime = self.plan['arms']['production']
        self.recipe = self.plan['recipes']['cpu_slice']
        self.cpus = list(range(24))

    def response(self, item, *, wrong_type=False, wrong_finish=False):
        cap = item['request_body'][CAP_KEY]
        expected = item['validator']['expected']
        if item['output_format'] == 'json':
            if wrong_type:
                expected = {**expected, 'count': '2'}
            content = json.dumps(expected)
        else:
            content = str(expected)
        length = item['expected_finish'] == 'length' or wrong_finish
        count = item['request_body']['n_predict'] if length else 20
        timings = {'predicted_n': count, 'prompt_n': 50, 'cache_n': 0}
        if cap:
            timings.update({'draft_n': 12, 'draft_n_accepted': 7})
        return {
            'content': content, 'tokens': list(range(count)), 'tokens_predicted': count,
            'stop_type': 'limit' if length else 'word', 'timings': timings,
            'tokens_evaluated': 50, 'truncated': False,
            'generation_settings': {CAP_KEY: cap, 'speculative.types': 'draft-dflash'},
        }

    def fixture(self, out, *, wrong_type=False, wrong_finish=False):
        production = out / 'production'
        production.mkdir()
        server = {'pid': 100, 'cpus': self.cpus, 'mapped_libraries': {'fixture-dso': {'inode': 1}},
                  'recipe': self.recipe, 'image': self.runtime}
        cleanup = {'pid': server['pid'], 'dead': True, 'port_closed': True}
        capture.write_json(production / 'server.json', server)
        capture.write_json(production / 'cleanup.json', cleanup)
        rows = []
        for item in self.plan['items']:
            name = item['id']
            body = item['request_body']
            wire = capture.canonical(body)
            response = self.response(
                item, wrong_type=wrong_type and name == 'dflash2-json-cap0',
                wrong_finish=wrong_finish and name == 'dflash2-json-cap7',
            )
            raw = capture.canonical(response)
            capture.write(production / f'{name}.request.json', wire)
            capture.write(production / f'{name}.response.json', raw)
            custody = {key: server[key] for key in ('pid', 'cpus', 'mapped_libraries')}
            custody['phase'] = 'after-request-send-before-response-read'
            rows.append({
                'id': name, 'request_sha256': capture.sha(wire), 'response_sha256': capture.sha(raw),
                'response_b64': base64.b64encode(raw).decode(), 'dflash_pair': item['dflash_pair'],
                'draft_counters': capture.verify_response(response, item, self.recipe),
                'server_instance': 'offline-control:production:100', 'parallel_slots': 1,
                'effective_n_max': body[CAP_KEY], 'request_custody_sha256': capture.write_json(
                    production / f'{name}.request-custody.json', custody),
            })
        return production, rows, server, cleanup

    def run_stub(self, **changes):
        requests = capture.validate_plan(self.plan)
        result = self.root / 'out/RESULT.json'

        def arm(name, runtime, recipe, items, wires, out, *rest):
            self.assertEqual((name, runtime, recipe, items, wires), (
                'production', self.runtime, self.recipe, self.plan['items'], requests,
            ))
            return self.fixture(out, **changes)[1]

        plan_pin = capture.file_sha(capture.D / 'plan.json')
        with patch.object(capture, 'capture_arm', side_effect=arm) as mocked:
            with patch.object(capture.os, 'sched_getaffinity', return_value=set(self.cpus)):
                rc = capture.run(self.plan, plan_pin, requests, result, False)
            mocked.assert_called_once()
        self.assertFalse((result.parent / 'native/candidate').exists())
        return rc, result

    def test_packet_pins(self):
        capture.validate_plan(self.plan)
        self.assertEqual(set(self.plan['arms']), {'production'})
        audit = json.loads((capture.D / 'dflash-original-admission.json').read_bytes())
        self.assertEqual(audit['status'], 'custody_slice_only_no_prospective_admission')
        for item in self.plan['items']:
            prior = audit['items'][item['id']]
            self.assertEqual(item['validator'], prior['proposed_validator'])
            self.assertEqual(item['expected_finish'], prior['proposed_finish'])
            new_pin = self.plan['request_files'][item['id']]['sha256']
            if item['output_format'] in ('code', 'prose'):
                self.assertEqual(new_pin, prior['request_sha256'])
            else:
                self.assertNotEqual(new_pin, prior['request_sha256'])
        changed = copy.deepcopy(self.plan)
        changed['arms']['candidate'] = self.runtime
        with self.assertRaisesRegex(ValueError, 'only the production'):
            capture.validate_plan(changed)

    def test_admission_and_success_predicate(self):
        rc, result = self.run_stub()
        self.assertEqual(rc, 0)
        self.assertTrue(complete(result, False))
        self.assertFalse(complete(result, True))
        bank = result.parent / 'native/banked-capture.json'
        with bank.open('ab') as stream:
            stream.write(b' ')
        self.assertFalse(complete(result, False))

    def test_typed_json_and_finish_refusal(self):
        rc, result = self.run_stub(wrong_type=True, wrong_finish=True)
        self.assertEqual(rc, 1)
        self.assertFalse(complete(result, False))
        summary = parity._parse(result.read_bytes())
        self.assertEqual(summary['status'], 'inadmissible_bank')
        self.assertEqual(summary['checks']['dflash2-json-cap0']['problems'], ['semantic_validation_failed'])
        self.assertEqual(summary['checks']['dflash2-json-cap7']['problems'], ['finish_mismatch'])
        self.assertTrue((result.parent / 'native/inadmissible-capture.json').exists())
        self.assertFalse((result.parent / 'native/banked-capture.json').exists())

    def test_raw_byte_tampering(self):
        production, rows, server, cleanup = self.fixture(self.root)
        row = rows[0]
        (production / f"{row['id']}.response.json").write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'original request, response, or pair'):
            capture.validate_bank(self.plan, rows, production, server, cleanup)

    def test_telemetry_and_cleanup_refusal(self):
        production, rows, server, cleanup = self.fixture(self.root)
        rows[1]['draft_counters']['draft_n'] = 0
        with self.assertRaisesRegex(ValueError, 'native draft or output token'):
            capture.validate_bank(self.plan, rows, production, server, cleanup)
        cleanup['port_closed'] = False
        with self.assertRaisesRegex(ValueError, 'PID or listener is not clean'):
            capture.validate_bank(self.plan, rows, production, server, cleanup)

    def test_stop_prevents_capture(self):
        (self.root / 'STOP').touch()
        with patch.object(capture, 'capture_arm') as arm:
            with self.assertRaises(InterruptedError):
                capture.run(self.plan, 'unused', {}, self.root / 'RESULT.json', False)
            arm.assert_not_called()
        self.assertFalse((self.root / 'RESULT.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
