"""Real pinned upstream checker plus local HTTP controls; no model runs."""
import copy
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import threading
import unittest

from bfcl_native import OfficialV3, capture

ROOT = Path(__file__).resolve().parents[2]


def completion(name, arguments):
    return {'choices': [{'finish_reason': 'tool_calls', 'message': {'tool_calls': [
        {'type': 'function', 'function': {'name': name, 'arguments': json.dumps(arguments)}}]}}]}


class OfficialControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = OfficialV3(os.environ['BFCL_CHECKOUT'])
        cls.rows = json.loads((ROOT / 'data/benchmarks/bfcl-v3-cj3d-prep-20261104/sample-manifest.json').read_text())['cases']

    def score(self, index, response):
        row = self.rows[index]
        return self.bridge.score(row['case'], row['category'], row['gold'], response, 'local-test-model')

    def test_official_positive_and_negative(self):
        for name, args, want in [
            ('calculate_triangle_area', {'base': 10, 'height': 5}, True),
            ('calculate_triangle_area', {'base': 10, 'height': 6}, False),
            ('wrong_function', {'base': 10, 'height': 5}, False),
            ('calculate_triangle_area', {'base': '10', 'height': 5}, False),
            ('calculate_triangle_area', {'base': 10}, False),
            ('calculate_triangle_area', {'base': 10, 'height': 5, 'extra': 1}, False),
        ]:
            with self.subTest(name=name, args=args):
                verdict = self.score(0, completion(name, args))
                self.assertEqual(verdict['status'], 'scored')
                self.assertIs(verdict['valid'], want)

    def test_all_ten_python_cases_and_parallel_order(self):
        for index, row in enumerate(self.rows[:10]):
            with self.subTest(case=row['case']['id']):
                calls = []
                for entry in row['gold']['ground_truth']:
                    for name, parameters in entry.items():
                        arguments = {key: values[0] for key, values in parameters.items()
                                     if values[0] != ""}
                        calls.append({'type': 'function', 'function': {
                            'name': name.replace('.', '_'), 'arguments': json.dumps(arguments)}})
                response = {'choices': [{'finish_reason': 'tool_calls', 'message': {'tool_calls': calls}}]}
                self.assertIs(self.score(index, response)['valid'], True)
                if len(calls) > 1:
                    calls.reverse()
                    self.assertIs(self.score(index, response)['valid'], True)
                    calls.pop()
                    self.assertIs(self.score(index, response)['valid'], False)

    def test_dotted_name_mapping_and_no_mutation(self):
        row = self.rows[1]; before = copy.deepcopy(row)
        payload, reverse = self.bridge.request(row['case'], 'simple', 'actual-local-model')
        self.assertEqual(payload['model'], 'actual-local-model')
        self.assertEqual(payload['tools'][0]['function']['name'], 'math_factorial')
        self.assertEqual(reverse, {'math_factorial': 'math.factorial'})
        self.assertIs(self.score(1, completion('math_factorial', {'number': 5}))['valid'], True)
        self.assertIs(self.score(1, completion('math_factorial', {'number': 6}))['valid'], False)
        self.assertEqual(row, before)

    def test_collision_refused(self):
        case = copy.deepcopy(self.rows[1]['case'])
        other = copy.deepcopy(case['function'][0]); other['name'] = 'math_factorial'
        case['function'].append(other)
        with self.assertRaisesRegex(ValueError, 'collision'):
            self.bridge.request(case, 'simple', 'test')

    def test_malformed_remains_unknown(self):
        response = completion('calculate_triangle_area', {})
        response['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = '{'
        for raw in (response, {'choices': []}, {'choices': [{}]}):
            verdict = self.score(0, raw)
            self.assertEqual(verdict['status'], 'parse_error')
            self.assertIsNone(verdict['valid'])

    def test_gold_mismatch_refused(self):
        row = self.rows[0]; gold = dict(row['gold'], id='simple_1')
        with self.assertRaisesRegex(ValueError, 'ID mismatch'):
            self.bridge.score(row['case'], 'simple', gold, {}, 'test')

    def test_execution_categories_refused(self):
        for row in self.rows:
            if row['category'] in {'simple', 'multiple', 'parallel', 'parallel_multiple'}:
                continue
            with self.subTest(category=row['category']), self.assertRaises(ValueError):
                self.bridge.request(row['case'], row['category'], 'test')

    def test_http_transport_to_official_checker(self):
        seen = []
        class Endpoint(BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append((self.path, json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                body = json.dumps(completion('math_factorial', {'number': 5})).encode()
                self.send_response(200); self.send_header('Content-Length', str(len(body)))
                self.end_headers(); self.wfile.write(body)
            def log_message(self, *args):
                pass
        # Handle exactly one request. No long-lived service or polling loop.
        with HTTPServer(('127.0.0.1', 0), Endpoint) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True); thread.start()
            row = self.rows[1]
            payload, _ = self.bridge.request(row['case'], 'simple', 'scripted-control')
            raw = capture(f'http://127.0.0.1:{server.server_port}/v1/chat/completions', payload, timeout=3)
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
        self.assertEqual(seen, [('/v1/chat/completions', payload)])
        self.assertEqual(set(payload), {'model', 'messages', 'tools', 'tool_choice', 'temperature', 'seed', 'max_tokens', 'stream'})
        self.assertNotIn('ground_truth', json.dumps(payload))
        self.assertIs(self.score(1, raw)['valid'], True)

    def test_wrong_source_refused(self):
        with self.assertRaisesRegex(ValueError, 'source commit mismatch'):
            OfficialV3(ROOT)


if __name__ == '__main__':
    unittest.main()
