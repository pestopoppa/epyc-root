import unittest
from invocation_trace_v4 import classify_invocation_trace_v4
from test_invocation_trace_v3 import B,D,E

class TimedTraceTest(unittest.TestCase):
    def parse(self, lines):
        return classify_invocation_trace_v4('\n'.join(lines), expected_layer_ids=[3])
    def test_complete(self):
        out = self.parse([B+' time_ns=1000000000',D+' time_ns=2000000000',E+' time_ns=3000000000'])
        self.assertEqual(out['status'],'OBSERVED')
        self.assertEqual(out['candidates'][0]['native_timing'][0]['native_dispatch'],2)
    def test_bad_order_is_unknown(self):
        out = self.parse([B+' time_ns=2000000000',D+' time_ns=1000000000',E+' time_ns=3000000000'])
        self.assertEqual(out['status'],'UNKNOWN')
        self.assertIsNone(out['candidates'][0]['vec_observed'])
    def test_missing_and_duplicate_timestamps_rejected(self):
        for line in [D,D+' time_ns=2 time_ns=3',D+' time_ns=x',D+' time_ns=0']:
            with self.subTest(line=line), self.assertRaises(ValueError):
                self.parse([B+' time_ns=1',line,E+' time_ns=3'])

if __name__ == '__main__': unittest.main()
