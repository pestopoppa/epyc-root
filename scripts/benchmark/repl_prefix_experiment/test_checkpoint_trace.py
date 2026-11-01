import unittest
from checkpoint_trace import match_checkpoint


class MatchTests(unittest.TestCase):
    def test_matches_only_exact_context_checkpoint(self):
        line = ('slot create_check: id  3 | task 42 | created context checkpoint 1 of 4 '
                '(pos_min = 0, pos_max = 98, n_tokens = 99, size = 2.500 MiB)')
        self.assertEqual(match_checkpoint(line, 3, 42, 99), [1])
        for slot, task, boundary in [(4, 42, 99), (3, 43, 99), (3, 42, 100)]:
            self.assertEqual(match_checkpoint(line, slot, task, boundary), [])
        self.assertEqual(match_checkpoint(line.replace('context', 'speculative'), 3, 42, 99), [])
        self.assertEqual(match_checkpoint('', 3, 42, 99), [])

    def test_rejects_invalid_inputs(self):
        for args in [(-1, 42, 99), (3, -1, 99), (3, 42, 0)]:
            with self.assertRaises(ValueError):
                match_checkpoint('', *args)


if __name__ == '__main__':
    unittest.main()
