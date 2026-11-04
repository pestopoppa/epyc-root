import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import p3_kvu_probe as p


class LifecycleTests(unittest.TestCase):
    def test_busy_evidence_requires_measurement_slot(self):
        poll = p.SlotPoller('fixture')
        poll.samples = [dict(sum=100, busy=[1], per_slot={0: 20, 1: 80})]
        self.assertEqual(poll.summary()['n_during_busy'], 0)
        poll.samples.append(dict(sum=100, busy=[0], per_slot={0: 20, 1: 80}))
        self.assertEqual(poll.summary()['busy_per_slot_min'][1], 80)

    def test_failed_stop_retains_handle_and_checks_port(self):
        with patch.object(p, 'server_argv', return_value=(['server'], [])):
            server = p.Server('fixture', 18192, False, False)
        server.proc = object()
        with patch.object(p.C, 'stop_own', return_value={'verified_dead': False}), \
             patch.object(p, 'log_scan', return_value={}), \
             patch.object(p.subprocess, 'run') as check:
            check.return_value.returncode = 0
            check.return_value.stdout = ''
            with self.assertRaises(RuntimeError):
                server.stop()
        self.assertIsNotNone(server.proc)
        self.assertTrue(server.rec['port_free_after'])

    def test_port_probe_error_is_not_free(self):
        with patch.object(p, 'server_argv', return_value=(['server'], [])):
            server = p.Server('fixture', 18192, False, False)
        with patch.object(p, 'log_scan', return_value={}), patch.object(p.subprocess, 'run') as check:
            check.return_value.returncode = 1
            check.return_value.stdout = ''
            with self.assertRaises(RuntimeError):
                server.stop()
            self.assertFalse(server.rec['port_free_after'])

    def test_variants_require_matched_occupancy_and_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            seen = []
            mismatch = [False]
            def run(_):
                seen.append((p.ACTIVE_VARIANT, p.SHARED_NONCE))
                rows = []
                for level in ('L0_base', 'L1_158k', 'L2_258k', 'L3_358k', 'L0_after'):
                    for rep in (1, 2):
                        n = 100 if not (mismatch[0] and p.ACTIVE_VARIANT == 'nodraft') else 70
                        rows.append({'level': level, 'rep': rep, 'variant': p.ACTIVE_VARIANT,
                                     'kv_resident': {'busy_per_slot_min': {str(k): n for k in range(int(level[1])+1)}}})
                p.C.write_json(p.P3/'a1.json', {'status': 'ok', 'rows': rows, 'server': {
                    'pid': 1 if p.ACTIVE_VARIANT == 'drafted' else 2,
                    'hip_dlopen_proof': {'ok': True}, 'vram': {'nonzero_samples': 2},
                    'teardown': {'verified_dead': True}, 'port_free_after': True}})
                return 0
            with patch.object(p, 'P3', root), patch.object(p, 'phase_a1_single', run):
                self.assertEqual(p.phase_a1(None), 0)
                self.assertEqual(seen[0][1], seen[1][1])
                self.assertEqual(len(json.loads((root/'a1.json').read_text())['rows']), 20)
                mismatch[0] = True
                self.assertEqual(p.phase_a1(None), 1)
                self.assertEqual(json.loads((root/'a1.json').read_text())['status'], 'failed')

    def test_chat_rejects_before_transport(self):
        p.SERVER_ARGV['http://fixture'] = ['llama-server', '-md', 'draft']
        with patch.object(p.SB, 'stream_chat') as transport:
            with self.assertRaises(ValueError):
                p.chat('http://fixture', 'x', 0, 1, p.NODRAFT)
            transport.assert_not_called()

if __name__ == '__main__':
    unittest.main()
