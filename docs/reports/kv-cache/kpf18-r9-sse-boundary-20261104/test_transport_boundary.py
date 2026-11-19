"""Model-free composition check: rowflow STOP interrupts real R9 SSE capture."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from driver_boundary import EntryRefused, RowflowContext
from cancel_seed_stream import capture


class FakeGuard:
    def __init__(self):
        self.checks = 0
    def check_boundary(self):
        self.checks += 1


class FakeTransport:
    def __init__(self):
        self.close_count = 0
    def close(self):
        self.close_count += 1


class TransportBoundaryTest(unittest.TestCase):
    def test_stop_between_native_sse_events_closes_without_acceptance(self):
        with tempfile.TemporaryDirectory(prefix='kpf18-boundary-') as temp:
            root = Path(temp)
            stop = root / 'STOP'
            env = {'FILLER_END': '2000', 'FILLER_DEADLINE': '1900',
                   'FILLER_STOPFILE': str(stop)}
            original = FakeGuard()
            wrapped = RowflowContext(original, env, lambda: 1000.0)
            first = b'data: ' + json.dumps({'id_slot': -1, 'prompt_progress':
                   {'processed': 100, 'total': 32512}}).encode() + b'\n\n'
            second = b'data: ' + json.dumps({'id_slot': -1, 'prompt_progress':
                    {'processed': 31744, 'total': 32512}}).encode() + b'\n\n'
            transport = FakeTransport()
            raw = []
            identities = []
            def lines():
                yield first
                stop.touch()
                yield second
            def write_raw(line):
                raw.append(line)
            def identify(event):
                wrapped.check_boundary()
                identities.append(17)
                return 17
            with self.assertRaises(EntryRefused):
                capture(lines=lines(), close_transport=transport.close,
                        capture_task_identity=identify, write_raw=write_raw,
                        deadline_check=wrapped.check_boundary, slot_id=1,
                        trigger_processed=31744, delay_s=0,
                        sleep=lambda _delay: None, clock=lambda: 1.0)
            self.assertEqual(raw, [first])
            self.assertEqual(identities, [17])
            self.assertEqual(transport.close_count, 1)
            self.assertEqual(original.checks, 2)
            self.assertFalse(any(b'31744' in item for item in raw))
            self.assertFalse(hasattr(transport, 'native_cancel_accepted'))

    def test_allowed_capture_keeps_transport_request_only(self):
        with tempfile.TemporaryDirectory(prefix='kpf18-allowed-') as temp:
            original = FakeGuard()
            env = {'FILLER_END': '2000', 'FILLER_DEADLINE': '1900',
                   'FILLER_STOPFILE': str(Path(temp) / 'STOP')}
            wrapped = RowflowContext(original, env, lambda: 1000.0)
            event = b'data: ' + json.dumps({'id_slot': -1, 'prompt_progress':
                    {'processed': 31744, 'total': 32512}}).encode() + b'\n\n'
            transport = FakeTransport()
            raw = []
            result = capture(lines=iter([event]), close_transport=transport.close,
                             capture_task_identity=lambda _event: 17,
                             write_raw=raw.append, deadline_check=wrapped.check_boundary,
                             slot_id=1, trigger_processed=31744, delay_s=0,
                             sleep=lambda _delay: None, clock=lambda: 1.0)
            self.assertEqual(result['seed_task_id'], 17)
            self.assertTrue(result['transport_closed'])
            self.assertFalse(result['native_cancel_accepted'])
            self.assertEqual(transport.close_count, 1)
            self.assertGreaterEqual(original.checks, 3)


if __name__ == '__main__':
    unittest.main()
