import json
import unittest
from pathlib import Path
from verifier import verify

TASKS = json.loads((Path(__file__).parent / 'corpus.json').read_text())
def envelope(files):
    return '\n'.join(f'<<<FILE: {name}>>>\n{body.rstrip()}\n<<<END>>>' for name, body in files.items())

class VerifierTests(unittest.TestCase):
    def test_reference_and_negative_controls(self):
        self.assertEqual(len(TASKS), 5)
        for task in TASKS:
            with self.subTest(task=task['id']):
                ref = dict(task['reference_files'])
                self.assertEqual(verify(task, envelope(ref))['status'], 'PASS')
                self.assertNotEqual(verify(task, envelope(task['files']))['status'], 'PASS')
                mutated = {name: body.replace('return ', 'return 1 + ', 1) for name,body in ref.items()}
                self.assertNotEqual(verify(task, envelope(mutated))['status'], 'PASS')
                missing = dict(ref); missing.pop(next(iter(missing)))
                self.assertEqual(verify(task, envelope(missing))['status'], 'FAIL')
    def test_unsupported_code_is_not_executed(self):
        task = TASKS[0]; files = dict(task['reference_files'])
        key = next(iter(files)); files[key] = 'import os\nos.system("touch /tmp/sr8-verifier-escape")\n'
        self.assertEqual(verify(task, envelope(files))['status'], 'UNKNOWN')
    def test_rejects_prose_and_duplicate(self):
        task = TASKS[0]; text = envelope(task['reference_files'])
        self.assertEqual(verify(task, 'explanation\n' + text)['status'], 'FAIL')
        self.assertEqual(verify(task, text + '\n' + text)['status'], 'FAIL')

if __name__ == '__main__': unittest.main()
