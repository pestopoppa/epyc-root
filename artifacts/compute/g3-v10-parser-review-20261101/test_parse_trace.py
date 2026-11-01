#!/usr/bin/env python3
import unittest
from parse_trace import TraceError, parse_bytes, MAX_BYTES

BEGIN = 'G3_TRACE_V1 BEGIN epoch=1 slot=0 task=7 phase=verify draft=2 rows=3 off=0\n'
DISPATCH = 'G3_TRACE_V1 DISPATCH i=0 device=0 kernel=100 q0=128 q1=3 q2=32 q3=1 k0=128 k1=1024 k2=8 ktype=q8_0 vtype=q8_0\n'
END = 'G3_TRACE_V1 END epoch=1 rc=0\n'

class TraceFixtures(unittest.TestCase):
    def parse(self, s): return parse_bytes(s.encode())
    def bad(self, s):
        with self.assertRaises(TraceError): self.parse(s)
    def test_valid_verify_is_only_structural(self):
        r=self.parse(BEGIN+DISPATCH+END)
        self.assertEqual(r['verify_dispatch_counts'], {'VEC':1})
        self.assertFalse(r['correlation_proven']); self.assertFalse(r['runtime_identity_proven'])
    def test_unscoped_dispatch_is_unknown(self):
        r=self.parse(DISPATCH+BEGIN+END)
        self.assertEqual(len(r['unscoped_dispatches']), 1); self.assertEqual(r['verify_dispatch_counts'], {})
    def test_nonverify_never_counts(self):
        r=self.parse(BEGIN.replace('phase=verify draft=2','phase=other_or_unknown draft=0')+DISPATCH+END)
        self.assertEqual(r['verify_dispatch_counts'], {})
    def test_missing_nested_and_duplicate_epochs(self):
        for x in (BEGIN+DISPATCH, BEGIN+BEGIN+END, END, BEGIN+END+BEGIN+END): self.bad(x)
    def test_mismatched_end_and_decode_failure(self):
        self.bad(BEGIN+END.replace('epoch=1','epoch=2')); self.bad(BEGIN+END.replace('rc=0','rc=1'))
    def test_overflow_and_dispatch_gap(self):
        self.bad(BEGIN+'G3_TRACE_V1 OVERFLOW limit=20000\n'+END); self.bad(BEGIN+DISPATCH.replace('i=0','i=2')+END)
    def test_duplicate_malformed_or_interleaved_marker(self):
        self.bad(BEGIN.replace('slot=0','slot=0 slot=0')+END)
        self.bad('prefix '+BEGIN+END); self.bad(BEGIN+'G3_TRACE_V1 BAD\n'+END)
    def test_invalid_verify_and_device(self):
        self.bad(BEGIN.replace('draft=2','draft=0')+END)
        self.bad(BEGIN+DISPATCH.replace('kernel=100','kernel=999')+END)
        self.bad(BEGIN.replace('slot=0','slot=1')+END)
    def test_length_and_encoding(self):
        with self.assertRaises(TraceError): parse_bytes(b'x'*(MAX_BYTES+1))
        with self.assertRaises(TraceError): parse_bytes(b'\xff')
        self.bad('x'*4097+'\n'+BEGIN+END)
    def test_truncated_final_marker_refused(self):
        self.bad(BEGIN+DISPATCH+END.rstrip('\n'))
        # A complete marker followed by a truncated ordinary log line is not a trace truncation.
        self.assertEqual(self.parse(BEGIN+DISPATCH+END+'ordinary')['verify_epoch_count'], 1)
    def test_none_kernel_refused_and_empty_verify_visible(self):
        self.bad(BEGIN+DISPATCH.replace('kernel=100','kernel=0')+END)
        r=self.parse(BEGIN+END)
        self.assertEqual(r['verify_epochs_without_dispatch'], [1])
        self.assertEqual(r['unscoped_dispatch_count'], 0)
    def test_concurrent_reordered_indexes_fail_closed(self):
        self.bad(BEGIN+DISPATCH.replace('i=0','i=1')+DISPATCH+END)
    def test_two_epochs_sequential(self):
        b=BEGIN.replace('epoch=1','epoch=2'); e=END.replace('epoch=1','epoch=2')
        r=self.parse(BEGIN+DISPATCH+END+b+DISPATCH.replace('i=0','i=1').replace('kernel=100','kernel=200')+e)
        self.assertEqual(r['verify_dispatch_counts'], {'TILE':1,'VEC':1})

if __name__ == '__main__': unittest.main()
