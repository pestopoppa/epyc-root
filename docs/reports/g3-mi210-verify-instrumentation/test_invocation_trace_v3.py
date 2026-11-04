import unittest
from invocation_trace_v3 import classify_invocation_trace_v3
from test_invocation_trace_v2 import BEGIN, END, DISPATCH, WORKER_DISPATCH

B = BEGIN.replace('_V2', '_V3').replace(' correlation=', ' indices=7,8 correlation=')
E = END.replace('_V2', '_V3')
D = DISPATCH.replace('_V2', '_V3').replace(' tensor=', ' layer=3 tensor=')
W = WORKER_DISPATCH.replace('_V2', '_V3').replace(' tensor=', ' layer=-1 tensor=')


def run(lines, layers=(3,)):
    return classify_invocation_trace_v3('\n'.join(lines), expected_layer_ids=layers)


class V3Test(unittest.TestCase):
    def test_positive_and_control(self):
        control = B.replace('invocation=12', 'invocation=13').replace('parallel_verify_candidate', 'unclassified').replace('indices=7,8', 'indices=none')
        control_end = E.replace('invocation=12', 'invocation=13')
        result = run((control, control_end, B, D, E))
        self.assertEqual(result['status'], 'OBSERVED')
        self.assertTrue(result['candidates'][0]['vec_observed'])
        self.assertEqual(len(result['unclassified_controls']), 1)
        self.assertEqual(len(result['raw_events']), 5)

    def test_unknown(self):
        for lines in ((B, D), (B, E), (B, D, W, E), (B, D.replace('layer=3', 'layer=-1'), E),
                      (B.replace('indices=7,8', 'indices=8,7'), D, E), (B, D, D, E),
                      (B, D, E.replace('rc=0', 'rc=1'))):
            with self.subTest(lines=lines):
                out = run(lines)
                self.assertEqual(out['status'], 'UNKNOWN')
                self.assertIsNone(out['candidates'][0]['vec_observed'])

    def test_bad_markers_and_payload_fail(self):
        for lines in ((B, D.replace('layer=3', 'layer=x'), E), (B, D.replace('invocation=12', 'invocation=99'), E),
                      (B.replace('indices=7,8', 'indices=7,x'), D, E)):
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                run(lines)

    def test_query_shape_must_cover_whole_verify_batch_at_every_layer(self):
        second = D.replace('tensor=0x123', 'tensor=0x124').replace('layer=3', 'layer=7')
        self.assertEqual(run((B, D, second, E), (3, 7))['status'], 'OBSERVED')
        for query_length in (1, 3):
            partial = second.replace('q=128,2,32,1', f'q=128,{query_length},32,1')
            result = run((B, D, partial, E), (3, 7))
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertIsNone(result['candidates'][0]['vec_observed'])
            self.assertIn('attention query length does not match complete verify batch',
                          result['candidates'][0]['reasons'])

    def test_candidate_token_count_must_equal_draft_length_plus_one(self):
        with self.assertRaises(ValueError):
            run((B.replace('drafts=1', 'drafts=2'), D, E))
