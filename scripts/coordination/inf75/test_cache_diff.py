import unittest
from cache_diff import compare_caches, parse_cache


class CacheDiffTests(unittest.TestCase):
    def test_reports_additions_deletions_type_and_values_including_internal(self):
        base = 'A:BOOL=ON\nB:STRING=one\nC:INTERNAL=/old\n'
        candidate = 'A:BOOL=OFF\nB:FILEPATH=one\nD:INTERNAL=/new\n'
        result = compare_caches(base, candidate)
        self.assertEqual(result['status'], 'UNVERIFIED_COMPARISON')
        self.assertEqual([x['key'] for x in result['differences']], ['A', 'B', 'C', 'D'])
        self.assertIsNone(result['differences'][2]['candidate'])
        self.assertIsNone(result['differences'][3]['base'])

    def test_duplicate_malformed_or_empty_refuse(self):
        for data in ('', 'A:BOOL=ON\nA:BOOL=OFF\n', 'A=ON\n', ':BOOL=ON\n'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_cache(data)

    def test_equal_and_values_with_equals(self):
        data = '//comment\n# header\nF:STRING=-DKEY=a=b\n'
        self.assertEqual(compare_caches(data, data)['differences'], [])


if __name__ == '__main__':
    unittest.main()
