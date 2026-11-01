import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tokenizer import capture_strategy_prompt_tokens


class StrategyTokenizerTests(unittest.TestCase):
    def test_three_arms_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            arms = {}
            for arm in ('baseline', 'strategy_short', 'strategy_long'):
                data = arm.encode()
                (root / (arm + '.txt')).write_bytes(data)
                arms[arm] = {'file': arm + '.txt', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            (root / 'manifest.json').write_text(json.dumps({'schema': 'epyc.strategy_prompt_ablation.preparation.v1', 'arms': arms}))
            witness = lambda: {'pid': 1, 'birth': 2, 'port': 3, 'listener_inodes': ['4']}
            identity = {'binary_sha256': 'a', 'model_sha256': 'b', 'template_sha256': 'c'}
            calls = []
            def tokenize(prompt, **flags):
                calls.append(flags)
                return [1, 2, 3]
            def call(**kw):
                args = {'tokenize': tokenize, 'check_window': lambda: True, 'witness': witness, 'identity': identity}
                args.update(kw)
                return capture_strategy_prompt_tokens(root, **args)
            result = call()
            self.assertEqual([result['counts'][a]['tokens'] for a in arms], [3, 3, 3])
            self.assertEqual(calls[0], {'add_special': False, 'parse_special': True})
            with self.assertRaises(RuntimeError):
                call(check_window=lambda: False)
            with self.assertRaises(ValueError):
                call(tokenize=lambda *a, **k: [True])
            (root / 'baseline.txt').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                call()


if __name__ == '__main__':
    unittest.main()
