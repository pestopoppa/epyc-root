import unittest
from types import SimpleNamespace
from unittest.mock import patch

import gate_hook


class FakeCapture:
    def __init__(self, target_pid, request_context):
        self.target_pid = target_pid
        self.request_context = request_context
        self.state = 'new'
        self.receipt = None
        self.aborted = False

    def attach_target(self, pid):
        if pid != self.target_pid:
            raise ValueError('wrong target')

    def begin(self):
        self.state = 'request'

    def end(self):
        self.state = 'finished'
        self.receipt = {'observer_id': 'ch26:' + str(len(self.request_context)) * 64}
        return self.receipt

    def abort(self):
        self.aborted = True
        self.state = 'failed'


class Gate:
    def install_measure_wrapper(self, serving, *args, **kwargs):
        return None


class Serving:
    _ch26_owner_patch = 'prototype-v2'

    def __init__(self, count=2):
        def measure(recipe, *args, ch26_capture_factory=None, **kwargs):
            for index in range(count):
                context = {'phase': 'warmup' if index == 0 else 'measurement',
                           'slot_index': 0, 'prompt_id': 'p', 'request_sha256': 'a' * 64,
                           'launch_ordinal': 1}
                capture = ch26_capture_factory(900, context)
                capture.attach_target(900)
                capture.begin()
                capture.end()
            return 1.0
        self._measure_once = measure


class GateHookTests(unittest.TestCase):
    def test_injects_one_owned_capture_per_request(self):
        captures = []
        def factory(pid, context):
            item = FakeCapture(pid, context)
            captures.append(item)
            return item
        gate = Gate(); serving = Serving()
        gate_hook.install_in_gate(gate, factory)
        with patch.object(gate_hook, 'RequestCapture', FakeCapture):
            gate.install_measure_wrapper(serving)
            value = serving._measure_once(SimpleNamespace(np=1))
        self.assertEqual(value, 1.0)
        self.assertEqual(len(captures), 2)
        self.assertTrue(all(c.state == 'finished' and not c.aborted for c in captures))

    def test_missing_request_capture_refuses_launch(self):
        captures = []
        def factory(pid, context):
            item = FakeCapture(pid, context)
            captures.append(item)
            return item
        gate = Gate(); serving = Serving(count=1)
        gate_hook.install_in_gate(gate, factory)
        with patch.object(gate_hook, 'RequestCapture', FakeCapture):
            gate.install_measure_wrapper(serving)
            with self.assertRaisesRegex(ValueError, 'capture count'):
                serving._measure_once(SimpleNamespace(np=1))
        self.assertEqual(captures[0].state, 'finished')

    def test_unpatched_serving_owner_is_rejected(self):
        gate = Gate(); serving = Serving()
        serving._ch26_owner_patch = 'prototype-v1'
        gate_hook.install_in_gate(gate, lambda pid, context: FakeCapture(pid, context))
        with patch.object(gate_hook, 'RequestCapture', FakeCapture):
            with self.assertRaisesRegex(ValueError, 'unbound'):
                gate.install_measure_wrapper(serving)


if __name__ == '__main__':
    unittest.main()
