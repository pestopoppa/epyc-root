"""The surviving status reader consumes exports, never deployment-source allowlists.

Historical controller records are deliberately not loop-status contracts. Additive
producer fields do survive a valid loop export, without recreating the old
29-module source-hash gate or silently treating an old controller as live.
"""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest

from dashboard import loop_status, server
from tests.autokernel_no_live_reads import NoLiveAutokernelReads

REPO = Path(__file__).resolve().parents[1]
DEPLOYMENTS = REPO / 'tests/fixtures/autokernel_producers/deployment-states'


def _recorded_states():
    return [(path.parent.name, json.loads(path.read_text()))
            for path in sorted(DEPLOYMENTS.glob('*/state.json'))]


class ControllerStateContractTests(NoLiveAutokernelReads, unittest.TestCase):
    def test_every_recorded_state_key_is_known_to_the_dashboard(self):
        states = _recorded_states()
        self.assertTrue(states)
        original = json.loads((REPO / 'tests/fixtures/autokernel_loop_status_sample.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, state in states:
                with self.subTest(deployment=name):
                    exported = {**state, **original}
                    (root / 'loop-status.json').write_text(json.dumps(exported))
                    payload, _ = loop_status.snapshot(root)
                    self.assertIsNotNone(payload['loop'])
                    for key in state.keys() - original.keys():
                        self.assertEqual(payload['loop'][key], state[key])
        self.assertFalse(hasattr(server, '_DISCOVERY_TERMINAL_STATE_KEYS'))

    def test_a_recorded_terminal_state_would_be_accepted(self):
        """Retired controller state is refused; no stale source is silently live."""
        states = _recorded_states()
        self.assertTrue(states)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, state in states:
                with self.subTest(deployment=name):
                    (root / 'loop-status.json').write_text(json.dumps(state))
                    payload, _ = loop_status.snapshot(root)
                    self.assertIsNone(payload['loop'])
                    self.assertEqual(payload['freshness_state'], loop_status.STATE_MALFORMED)
