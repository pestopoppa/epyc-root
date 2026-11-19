import unittest
from replay import Replay, FakeTokenizer, replay, historical_report

class CursorReplayTests(unittest.TestCase):
    def test_fake_tokenizer_adaptive_doc_and_trim_are_explicit(self):
        r=Replay('x'*1000, FakeTokenizer(scripted=[105, 95]))
        r.doc(100, 4.0, 'doc')
        # Adaptive retries change the requested slice, then an over-budget response
        # triggers returned-text trimming without cursor rollback.
        self.assertGreaterEqual(r.tok.calls, 2)
        self.assertTrue(any(x.get('label','').startswith('doc:adapt') for x in r.rows))
        self.assertTrue(any('cursor_rollback' in x for x in r.rows))

    def test_take_records_wrap_and_cursor_advance(self):
        r=Replay('abcdefghij', FakeTokenizer())
        r.take(8,'a'); r.take(5,'b')
        self.assertEqual(r.rows[1]['start'],0)
        self.assertTrue(r.rows[1]['wrapped'])
        self.assertEqual(r.rows[1]['advanced_end'],5)

    def test_supplied_transcript_is_exact_and_deterministic(self):
        ops=[{'kind':'doc','ntok':20,'ratio':4,'label':'d'}, {'kind':'take','nchars':4,'label':'suffix'}]
        a=replay('z'*1000,ops,4); b=replay('z'*1000,ops,4)
        self.assertEqual(a,b)
        self.assertEqual(a['status'],'EXACT_FOR_SUPPLIED_TRANSCRIPT')
        self.assertEqual(a['final_cursor'],84)

    def test_exact_replay_requires_complete_tokenizer_counts(self):
        ops=[{'kind':'doc','ntok':20,'ratio':4,'label':'doc'}]
        with self.assertRaisesRegex(ValueError, 'exhausted'):
            replay('z'*1000,ops,scripted=[],strict=True)
        with self.assertRaisesRegex(ValueError, 'unused tokenizer_counts'):
            replay('z'*1000,[{'kind':'take','nchars':4}],scripted=[1],strict=True)
        # Exactness accepts a fully consumed captured response sequence.
        result=replay('z'*1000,ops,scripted=[20],strict=True)
        self.assertEqual(result['status'],'EXACT_FOR_SUPPLIED_TRANSCRIPT')

    def test_missing_transcript_is_not_reconstructed_from_tokens(self):
        # This models the audit boundary: request counts alone cannot make offsets exact.
        report=historical_report({'exact_logical_units': {}, 'corpus_sha256':'x', 'corpus_chars':0})
        self.assertEqual(report['status'],'UNKNOWN_CURSOR_INTERVALS')

    def test_historical_report_preserves_scalar_and_dict_exposure_values(self):
        report=historical_report({
            'exact_logical_units': {
                'start_anchor': {'completed': [[0, 0]], 'unused_detail': 'drop'},
                'warmup': 'Fixed non-corpus warm-up per launch.',
            },
            'corpus_sha256':'abc', 'corpus_chars':12,
        })
        self.assertEqual(report['status'], 'UNKNOWN_CURSOR_INTERVALS')
        self.assertEqual(report['exact_logical_units'], {
            'start_anchor': {'completed': [[0, 0]]},
            'warmup': 'Fixed non-corpus warm-up per launch.',
        })
        self.assertIsNone(report['exact_char_or_byte_ranges'])

if __name__=='__main__': unittest.main()
