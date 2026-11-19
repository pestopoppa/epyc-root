"""Offline controls; optional retained-log replay reads evidence in place."""
import hashlib
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import job
from corpus_parser import parse_corpus

HEADER = '  FLASH_ATTN_EXT(n_shared=2048): '
DIAG = 'ggml_backend_cuda_graph_compute: CUDA graph warmup complete'
SUMMARY = '  25/25 tests passed\n  Backend ROCm0: OK\n1/1 backends passed\nOK\n'
GOOD = (HEADER + 'OK\n') * 25 + SUMMARY


class ParserTests(unittest.TestCase):
    def test_inline_and_standalone_diagnostics(self):
        data = GOOD.replace(HEADER + 'OK', HEADER + DIAG + '\n' + DIAG + '\nOK', 1)
        result = parse_corpus(data)
        self.assertEqual(result['shared_trunk'], 25)
        self.assertEqual(result['graph_diagnostics'], 2)

    def test_unsupported_preserved(self):
        data = '  FLASH_ATTN_EXT(n_shared=0): not supported [ROCm0] \n' + GOOD
        self.assertEqual(parse_corpus(data)['unsupported'], 1)

    def test_negative_controls(self):
        bad = {
            'bad_status': GOOD.replace(': OK', ': BROKEN', 1),
            'missing_inline_status': GOOD.replace(HEADER + 'OK\n', HEADER + DIAG + '\n', 1),
            'missing_final_status': (HEADER + 'OK\n') * 24 + HEADER + DIAG + '\n',
            'summary_as_status': (HEADER + 'OK\n') * 24 + HEADER + DIAG + '\n' + SUMMARY,
            'unknown_diagnostic': GOOD.replace(': OK', ': ' + DIAG + ' garbage\nOK', 1),
            'fail_after_diagnostic': GOOD.replace(': OK', ': ' + DIAG + '\nFAIL', 1),
            'missing_backend_summary': GOOD.replace('1/1 backends passed\n', ''),
            'missing_test_summary': GOOD.replace('  25/25 tests passed\n', ''),
            'duplicate_summary': GOOD.replace(SUMMARY, SUMMARY + SUMMARY),
            'zero_summary': GOOD.replace('25/25 tests passed', '0/0 tests passed'),
            'required_unsupported': GOOD.replace(': OK', ': not supported [ROCm0]', 1).replace('25/25', '24/24'),
            'missing_required': GOOD.replace(HEADER + 'OK\n', '', 1).replace('25/25', '24/24'),
            'orphan_status': 'FAIL\n' + GOOD,
            'truncated_final_marker': GOOD[:-3],
        }
        for name, data in bad.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                parse_corpus(data)

    def test_post_custody_even_on_parse_failure(self):
        for data in (GOOD, 'invalid'):
            result = {}
            with patch.object(job, 'check', return_value='checked') as check:
                try:
                    job.record_corpus(result, data)
                except ValueError:
                    self.assertEqual(data, 'invalid')
                check.assert_called_once_with()
                self.assertEqual(result['linkage_after'], 'checked')

    def test_post_custody_failure_propagates(self):
        with patch.object(job, 'check', side_effect=RuntimeError('drift')):
            with self.assertRaisesRegex(RuntimeError, 'drift'):
                job.record_corpus({}, GOOD)

    @unittest.skipUnless(os.environ.get('KPF41_RETAINED_LOG'), 'optional retained evidence path')
    def test_retained_corpus(self):
        raw = Path(os.environ['KPF41_RETAINED_LOG']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '00f32fda75481a50e864a3bb5abb1597378768a3143d5b97bfd46b440cc48537')
        result = parse_corpus(raw.decode())
        self.assertEqual({k: v for k, v in result.items() if k != 'cases'},
                         dict(selected=5207, supported=2978, unsupported=2229,
                              shared_trunk=25, graph_diagnostics=212))
        # Controls against the actual interleaved log as well as synthetic records.
        for bad in (raw.decode().replace('warmup complete', 'warmup BROKEN', 1),
                    raw.decode().replace('\x1b[1;32mOK\x1b[0m\n', '', 1)):
            with self.assertRaises(ValueError):
                parse_corpus(bad)


if __name__ == '__main__':
    unittest.main()
