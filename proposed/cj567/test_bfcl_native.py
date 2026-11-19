"""Real pinned upstream checker plus local HTTP controls; no model runs."""
import ast
import inspect
import importlib
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
            if row['category'] in {'simple', 'multiple', 'parallel', 'parallel_multiple', 'java', 'javascript'}:
                continue
            with self.subTest(category=row['category']), self.assertRaises(ValueError):
                self.bridge.request(row['case'], row['category'], 'test')

    def test_java_javascript_selected_controls(self):
        controls = [
            (10, {'controller': 'mapController', 'parent': 'mapArea'}),
            (11, {'object': 'Customers', 'useShortName': 'true',
                  'params': 'new HashMap<String, Object>() {{put("limit", 50); put("schemaFilter", "public");}}'}),
            (12, {'inputField': '"userInputField"', 'isComplete': 'true'}),
            (13, {'listElement': 'listElement', 'attribute': '"data-active"', 'value': 'true'}),
        ]
        for index, args in controls:
            row = self.rows[index]
            with self.subTest(case=row['case']['id']):
                before = copy.deepcopy(row)
                payload, reverse = self.bridge.request(row['case'], row['category'], 'test')
                wire_name = next(iter(reverse))
                self.assertEqual(len(reverse), 1)
                self.assertEqual(payload['tools'][0]['function']['name'], wire_name)
                self.assertEqual(reverse[wire_name], row['case']['function'][0]['name'])
                properties = payload['tools'][0]['function']['parameters']['properties']
                self.assertTrue(all(p['type'] == 'string' for p in properties.values()))
                self.assertIn('syntax', payload['tools'][0]['function']['description'])
                self.assertNotIn('ground_truth', json.dumps(payload))
                self.assertIs(self.score(index, completion(wire_name, args))['valid'], True)
                # Function name, required parameter and value errors stay failures.
                self.assertIs(self.score(index, completion('wrong_function', args))['valid'], False)
                self.assertIs(self.score(index, completion(wire_name, {}))['valid'], False)
                wrong = dict(args)
                required = row['case']['function'][0]['parameters']['required'][0]
                wrong[required] = 'wrong_value'
                self.assertIs(self.score(index, completion(wire_name, wrong))['valid'], False)
                self.bridge.request(row['case'], row['category'], 'test')
                self.assertEqual(row, before)

    def test_language_boolean_types_are_not_coerced(self):
        for index, name, args in [
            (11, 'SQLCompletionAnalyzer_makeProposalsFromObject',
             {'object': 'Customers', 'useShortName': True,
              'params': 'new HashMap<String, Object>() {{put("limit", 50); put("schemaFilter", "public");}}'}),
            (12, 'validateUserInput', {'inputField': 'userInputField', 'isComplete': True}),
        ]:
            with self.subTest(case=self.rows[index]['case']['id']):
                verdict = self.score(index, completion(name, args))
                self.assertIs(verdict['valid'], False)
                self.assertIn('type_error:', verdict['official']['error_type'])

    def test_language_category_mismatch_refused(self):
        with self.assertRaises(ValueError):
            self.bridge.request(self.rows[10]['case'], 'javascript', 'test')

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

    def native_turns(self, row):
        turns = []
        for gold_turn in row['gold']['ground_truth']:
            steps = []
            for source in gold_turn:
                call = ast.parse(source, mode='eval').body
                args = {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords}
                if call.args:
                    for class_name in row['case']['involved_classes']:
                        module = importlib.import_module(self.bridge.execution.CLASS_FILE_PATH_MAPPING[class_name])
                        method = getattr(getattr(module, class_name), call.func.id, None)
                        if method:
                            names = list(inspect.signature(method).parameters)[1:]
                            args.update(zip(names, map(ast.literal_eval, call.args)))
                            break
                steps.append(completion(call.func.id, args))
            turns.append(steps)
        return turns

    def multi_score(self, row, turns):
        return self.bridge.score_multi_turn(row['case'], row['category'], row['gold'], turns)

    def test_multi_turn_all_ten_gold_controls_and_isolation(self):
        for row in self.rows[16:]:
            with self.subTest(case=row['case']['id']):
                before = copy.deepcopy(row)
                turns = self.native_turns(row)
                globals_before = set(vars(self.bridge.execution))
                for _ in range(2):
                    self.assertIs(self.multi_score(row, turns)['valid'], True)
                    self.assertEqual(set(vars(self.bridge.execution)), globals_before)
                self.assertEqual(row, before)

    def test_multi_turn_missing_state_and_turn_count(self):
        row = self.rows[16]
        turns = self.native_turns(row)
        turns[0] = []
        verdict = self.multi_score(row, turns)
        self.assertIs(verdict['valid'], False)
        self.assertEqual(verdict['official']['state']['error_type'], 'multi_turn:empty_turn_model_response')
        turns = self.native_turns(row)
        turns[0] = [completion('ls', {})]
        self.assertIs(self.multi_score(row, turns)['valid'], False)
        verdict = self.multi_score(row, turns[:-1])
        self.assertEqual(verdict['status'], 'parse_error')
        self.assertIsNone(verdict['valid'])

    def test_multi_turn_irrelevance_and_text_finish(self):
        for row in self.rows[22:]:
            with self.subTest(case=row['case']['id']):
                turns = self.native_turns(row)
                index = next(i for i, calls in enumerate(row['gold']['ground_truth']) if not calls)
                turns[index] = [{'choices': [{'finish_reason': 'stop', 'message': {'content': 'Please clarify'}}]}]
                self.assertIs(self.multi_score(row, turns)['valid'], True)
                turns[index] = [completion('ls', {})]
                verdict = self.multi_score(row, turns)
                # Pinned upstream treats nested execution strings as empty.
                # Preserve and disclose this blind spot rather than fixing scoring.
                self.assertIs(verdict['valid'], True)
                self.assertIs(verdict['official']['irrelevance']['valid'], True)

    def test_multi_turn_malformed_and_code_injection_refused(self):
        row = self.rows[16]
        for name, args in [('__import__', {'name': 'os'}), ('ls', {'x);bad(': 1}), ('xargs', {'command': 'sh', 'file_name': 'log.txt'})]:
            turns = self.native_turns(row)
            turns[0] = [completion(name, args)]
            verdict = self.multi_score(row, turns)
            self.assertEqual(verdict['status'], 'parse_error')
            self.assertIsNone(verdict['valid'])
        turns[0] = [{'choices': [{}]}]
        self.assertEqual(self.multi_score(row, turns)['status'], 'parse_error')

    def test_wrong_source_refused(self):
        with self.assertRaisesRegex(ValueError, 'source commit mismatch'):
            OfficialV3(ROOT)


if __name__ == '__main__':
    unittest.main()
