import unittest

from correlate_layers_v2 import classify_native_trace
from test_invocation_trace_v2 import BEGIN, END, DISPATCH, WORKER_DISPATCH


def binding(tensor='0x123', layer=4, invocation=12):
    return {'invocation': invocation, 'tensor': tensor, 'layer': layer, 'evidence': 'independent graph capture'}


def classify(lines, bindings=None, expected=(4,)):
    return classify_native_trace('\n'.join(lines), expected_layer_ids=expected,
                                 layer_bindings=[binding()] if bindings is None else bindings)


class CorrelateLayersTest(unittest.TestCase):
    def test_complete_vec_and_nonvec(self):
        for kernel, vec in [(100, True), (200, False)]:
            out = classify((BEGIN, DISPATCH.replace('kernel=100', f'kernel={kernel}'), END))
            self.assertEqual(out['status'], 'OBSERVED')
            self.assertIs(out['calls'][0]['vec_observed'], vec)

    def test_missing_duplicate_or_unmatched_bindings_are_unknown(self):
        for bindings in ([], [binding(), binding()], [binding(layer=5)],
                         [binding(), binding(tensor='0x124')]):
            with self.subTest(bindings=bindings):
                call = classify((BEGIN, DISPATCH, END), bindings)['calls'][0]
                self.assertEqual(call['status'], 'UNKNOWN')
                self.assertIsNone(call['vec_observed'])

    def test_uncorrelated_partial_duplicate_dispatch_and_null_tensor(self):
        for lines in ((BEGIN, DISPATCH, WORKER_DISPATCH, END), (BEGIN, DISPATCH),
                      (BEGIN, DISPATCH, DISPATCH, END),
                      (BEGIN, DISPATCH.replace('0x123', '0x0'), END)):
            with self.subTest(lines=lines):
                self.assertEqual(classify(lines)['status'], 'UNKNOWN')

    def test_sparse_layer_coverage(self):
        other = DISPATCH.replace('tensor=0x123', 'tensor=0x124').replace('kernel=100', 'kernel=200')
        out = classify((BEGIN, DISPATCH, other, END), [binding(), binding('0x124', 9)], (4, 9))
        self.assertEqual(out['status'], 'OBSERVED')
        self.assertTrue(out['calls'][0]['vec_observed'])
        self.assertEqual(classify((BEGIN, DISPATCH, other, END), [binding(), binding('0x124', 4)], (4, 9))['status'], 'UNKNOWN')

    def test_unsupported_and_invalid_evidence(self):
        for dispatch in (DISPATCH.replace('kernel=100', 'kernel=0'),
                         DISPATCH.replace('v_type=q8_0', 'v_type=q4_0')):
            self.assertEqual(classify((BEGIN, dispatch, END))['status'], 'UNKNOWN')
        for bad in ([binding(invocation=True)], [dict(binding(), evidence='')], [binding(tensor='0x0')]):
            with self.assertRaises(ValueError):
                classify((BEGIN, DISPATCH, END), bad)


if __name__ == '__main__':
    unittest.main()
