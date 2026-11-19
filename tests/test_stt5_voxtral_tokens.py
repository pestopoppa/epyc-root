import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('voxtral_tokens', Path(__file__).parents[1] /
                                             'scripts/speech/stt5_voxtral_tokens.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def witness(ids):
    return '\n'.join([f'CS8_VOXTRAL_TOKENS {len(ids)}'] +
                     [f'CS8_VOXTRAL_TOKEN {i} {v}' for i, v in enumerate(ids)] +
                     ['CS8_VOXTRAL_TOKENS_END'])


class VoxtralTokensTest(unittest.TestCase):
    def test_preserves_control_tokens_and_ignores_diagnostics(self):
        self.assertEqual(module.parse_voxtral_tokens('load model\n' + witness([32, 0, 1046, 32]) +
                                                    '\ntranscribed'), [32, 0, 1046, 32])

    def test_rejects_broken_witnesses(self):
        valid = witness([32, 100])
        bad = ['', witness([]), valid + '\n' + valid,
               valid.replace('TOKEN 1', 'TOKEN 0'),
               valid.replace('TOKEN 1', 'TOKEN 2'),
               valid.replace('TOKENS 2', 'TOKENS 3'),
               valid.replace('TOKENS 2', 'TOKENS 1'),
               valid.replace('TOKENS_END', 'TOKENS_EN'),
               valid.replace('TOKEN 1 100', 'TOKEN 1 -1'),
               valid.replace('TOKEN 1 100', 'TOKEN 1 100 garbage'),
               valid.replace('CS8_VOXTRAL_TOKENS_END', ''),
               'CS8_VOXTRAL_TOKEN 0 32\n' + valid,
               valid + '\nCS8_VOXTRAL_TOKEN 2 32',
               valid + '\nCS8_VOXTRAL_UNKNOWN 1']
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.parse_voxtral_tokens(value)

    def test_exact_agreement(self):
        result = module.compare(witness([32, 1, 32]), witness([32, 1, 32]))
        self.assertEqual(result['verdict'], 'PASS')
        self.assertIsNone(result['first_difference'])

    def test_control_and_length_differences_fail_without_alignment(self):
        for actual, expected, first in [([32, 1], [1], 0), ([1], [1, 32], 1),
                                        ([1, 32], [1], 1), ([1, 2], [1, 3], 1)]:
            with self.subTest(actual=actual, expected=expected):
                result = module.compare(witness(actual), witness(expected))
                self.assertEqual(result['verdict'], 'FAIL')
                self.assertEqual(result['first_difference'], first)
                self.assertEqual(result['candidate_ids'], actual)
                self.assertEqual(result['reference_ids'], expected)


if __name__ == '__main__':
    unittest.main()
