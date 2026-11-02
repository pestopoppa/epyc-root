import unittest
from fractions import Fraction
from acceptance_decomposition import decompose_acceptance


def counts(ga, aa, gb, ab):
    return {'a': {'generated_tokens': ga, 'accepted_tokens': aa},
            'b': {'generated_tokens': gb, 'accepted_tokens': ab}}


class TestDecomposition(unittest.TestCase):
    def test_mix_only_and_reverse(self):
        a, b = counts(80, 64, 20, 4), counts(20, 16, 80, 16)
        r = decompose_acceptance(a, b)
        self.assertEqual((r['delta'], r['mix'], r['rate']), (Fraction(-9, 25), Fraction(-9, 25), 0))
        reverse = decompose_acceptance(b, a)
        self.assertEqual(reverse['delta'], -r['delta'])
        self.assertEqual(reverse['mix'], -r['mix'])

    def test_rate_only_and_mixed(self):
        a, b = counts(50, 40, 50, 10), counts(50, 45, 50, 15)
        r = decompose_acceptance(a, b)
        self.assertEqual((r['delta'], r['mix'], r['rate']), (Fraction(1, 10), 0, Fraction(1, 10)))
        r = decompose_acceptance(a, counts(75, 45, 25, 5))
        self.assertEqual(r['mix'] + r['rate'], r['delta'])
        self.assertNotEqual(r['mix'], 0)
        self.assertNotEqual(r['rate'], 0)

    def test_refuses_undefined_and_bad_counts(self):
        valid = counts(1, 1, 1, 0)
        for invalid in ({}, {'a': {'generated_tokens': 1, 'accepted_tokens': 1}},
                        counts(0, 0, 1, 0), counts(1, 2, 1, 0), counts(True, 1, 1, 0)):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                decompose_acceptance(valid, invalid)


if __name__ == '__main__':
    unittest.main()
