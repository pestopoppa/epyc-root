import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

spec = importlib.util.spec_from_file_location('hs9_live', Path(__file__).resolve().parents[1] / 'scripts/harness/hs9_live.py')
live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)


class LiveTests(unittest.TestCase):
    def run_case(self, transport, directory, **kwargs):
        return live.run_live('HS9-01', policy='policy', task='inspect', model='test-only',
                             transport=transport, output_dir=directory, **kwargs)

    def test_feedback_and_durable_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'trial'
            requests = []
            def transport(request):
                requests.append(request)
                self.assertTrue((out / f'{len(requests)-1:03d}-request.json').exists())
                if len(requests) == 1:
                    request['messages'].clear()  # Cannot mutate runner context.
                    return json.dumps({'tool': 'inspect', 'args': {}})
                observation = json.loads(request['messages'][-1]['content'])
                self.assertEqual(observation['observation']['result'], {'value': 42})
                return json.dumps({'report': {'value': 42}})
            trace = self.run_case(transport, out)
            self.assertTrue(trace['capture_complete'])
            self.assertEqual(len(trace['events']), 1)
            self.assertEqual(json.loads((out / 'trace.json').read_text()), trace)
            self.assertEqual(len(requests[1]['messages']), 4)
            with self.assertRaises(FileExistsError):
                self.run_case(transport, out)

    def test_failure_after_real_event_preserves_partial_capture(self):
        for error, reason in [(TimeoutError(), 'timeout'), (OSError(), 'transport_error')]:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as tmp:
                transport = MagicMock(side_effect=[json.dumps({'tool': 'inspect', 'args': {}}), error])
                trace = self.run_case(transport, Path(tmp) / 'trial')
                self.assertFalse(trace['capture_complete'])
                self.assertEqual(trace['termination'], reason)
                self.assertEqual(trace['events'][0]['result']['value'], 42)

    def test_unsafe_calls_spoofing_and_limits(self):
        cases = [({'tool': 'shell', 'args': {}}, {}, 'invalid_tool_call'),
                 ({'report': {}, 'events': []}, {}, 'invalid_tool_call'),
                 ({'tool': 'inspect', 'args': {}}, {'max_turns': 1}, 'turn_limit'),
                 ({'report': {}}, {'max_bytes': 1}, 'byte_limit')]
        for response, kwargs, reason in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as tmp:
                trace = self.run_case(lambda _: json.dumps(response), Path(tmp) / 'trial', **kwargs)
                self.assertFalse(trace['capture_complete'])
                self.assertEqual(trace['termination'], reason)

    def test_http_response_limits_and_text_validation(self):
        for body in [b'x' * 101, b'{', b'{"choices":[{"message":{"content":null}}]}']:
            with self.subTest(body=body), patch.object(live.urllib.request, 'urlopen') as opened:
                opened.return_value.__enter__.return_value.read.return_value = body
                with self.assertRaises((ValueError, KeyError)):
                    live.ChatTransport('http://localhost/v1/chat/completions', max_response_bytes=100)({})
                self.assertEqual(opened.call_args.kwargs['timeout'], 60)
                opened.return_value.__enter__.return_value.read.assert_called_once_with(101)


if __name__ == '__main__':
    unittest.main()
