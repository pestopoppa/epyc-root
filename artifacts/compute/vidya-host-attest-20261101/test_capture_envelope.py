"""Offline integrity/collector tests; never launches a model or samples the host."""
import copy
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import capture_envelope as probe

ROOT = Path(__file__).resolve().parent


class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT / 'native-host-observation.json').read_bytes()
        self.envelope = json.loads((ROOT / 'source-envelope.json').read_bytes())

    def test_retained_artifact_integrity(self):
        self.assertTrue(probe.validate(self.envelope, self.raw))
        self.assertEqual(self.envelope['research_source_commit'], probe.COMMIT)
        self.assertIn('benchmark launch', self.envelope['not_attested'])
        self.assertIn('measurement grade', self.envelope['not_attested'])

    def test_reject_integrity_and_warrant_mutations(self):
        for key, value in [('schema', 'other'), ('historical_warrant', True),
                           ('source_class', 'invented')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                item = copy.deepcopy(self.envelope)
                item[key] = value
                probe.validate(item, self.raw)
        with self.assertRaises(ValueError):
            probe.validate(self.envelope, self.raw + b' ')
        for field, value in [('path', '../elsewhere'), ('sha256', '0' * 64), ('bytes', 0)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                item = copy.deepcopy(self.envelope)
                item['native_artifact'][field] = value
                probe.validate(item, self.raw)

    def test_reject_source_and_projection_mutations(self):
        for key in ('collector_source', 'capture_source'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                item = copy.deepcopy(self.envelope)
                item[key]['sha256'] = '0' * 64
                probe.validate(item, self.raw)
        item = copy.deepcopy(self.envelope)
        item['native_record']['claim_mode'] = 'cpu_region_claim'
        with self.assertRaisesRegex(ValueError, 'projection'):
            probe.validate(item, self.raw)

    def test_reject_rebound_invalid_native_records(self):
        for key, value in [('claim_mode', 'cpu_region_claim'),
                           ('schema', 'invented'), ('source_sha256', '0' * 64),
                           ('capture_ended_monotonic_ns', 0)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                item = copy.deepcopy(self.envelope)
                item['native_record'][key] = value
                raw = probe.encode(item['native_record'])
                item['native_artifact'].update(bytes=len(raw), sha256=probe.sha(raw))
                probe.validate(item, raw)

    def test_capture_normalizes_unknown_uptime_without_host_calls(self):
        for uptime in (None, True, -1, math.nan, math.inf, 10**1000):
            with self.subTest(uptime=repr(uptime)), \
                 patch.object(probe.native, 'collect_attestation', return_value={'uptime_seconds': uptime}), \
                 patch.object(probe.native, 'host_health_warnings', return_value=['native warning']):
                record = probe.native.capture('explicit_unlocked_override')
                self.assertEqual(record['uptime_status'], 'unknown')
                self.assertIsNone(record['attestation']['uptime_seconds'])
                self.assertEqual(record['host_health_warnings'], ['native warning'])
                probe.encode(record)

    def test_native_exact_week_warning_boundary_is_preserved(self):
        native = probe.native.server_np_sweep
        base = {'numa_balancing': '0', 'existing_llama_processes': []}
        self.assertEqual(native.host_health_warnings(dict(base, uptime_seconds=604800)), [])
        self.assertTrue(native.host_health_warnings(dict(base, uptime_seconds=604801)))


if __name__ == '__main__':
    unittest.main()
