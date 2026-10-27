import socket
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import server_evidence_full as evidence
import server_probe_full as probe


def graph(decode, tokens, width, ctx='target', seq='0'):
    return {'model': 'model', 'ctx': ctx, 'decode_id': decode,
            'api_batch': {'tokens': tokens, 'tokens_per_seq': {seq: tokens}},
            'dense_matmul_ne11': [width]}


class Controls(unittest.TestCase):
    def test_split_and_identity(self):
        shape = SimpleNamespace(phase='prefill', n_tokens=2048, n_seq=1)
        def observed(rows): return evidence.tensor_shape_observed(shape, {'graphs': rows})
        def split(rows): return evidence.split_prefill_description(shape, {'graphs': rows})['observed_split_prefill']
        self.assertFalse(observed([graph(1, 4, 4), graph(3, 2044, 2044)]))
        self.assertFalse(split([graph(1, 4, 4), graph(3, 2044, 2044)]))
        self.assertTrue(split([graph(1, 4, 4), graph(2, 4, 4, 'draft'), graph(3, 2044, 2044)]))
        self.assertFalse(split([graph(1, 4, 4), graph(2, 2, 99), graph(3, 2044, 2044)]))
        self.assertFalse(observed([graph(1, 4, 4), graph(3, 2044, 2044, 'draft')]))
        self.assertFalse(observed([graph(1, 4, 4), graph(3, 2044, 2048)]))
        self.assertFalse(observed([graph(1, 4, 4), graph(3, 2044, 2044, seq='1')]))
        self.assertFalse(observed([graph(1, 4, 4), graph(2, 2, 99), graph(3, 2044, 2044)]))
        self.assertTrue(observed([graph(1, 2048, 2048)]))

    def test_slot_timeout_is_recorded_but_process_sampling_survives(self):
        with patch.object(probe, 'request', side_effect=socket.timeout('timed out')):
            sample = probe.own_sample(__import__('os').getpid(), gpu=False,
                                      phase='requests', port=1)
        self.assertEqual(sample['slots'], [])
        self.assertIn('TimeoutError', sample['slots_error'])
        self.assertTrue(sample['task_affinity'])

    def test_non_timeout_error_is_not_swallowed(self):
        with patch.object(probe, 'request', side_effect=ValueError('bad response')):
            with self.assertRaises(ValueError):
                probe.own_sample(__import__('os').getpid(), gpu=False,
                                 phase='requests', port=1)

    def test_bounded_response_parser(self):
        class Response:
            def __init__(self, data): self.data = data
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit):
                self.limit = limit
                return self.data[:limit]
        good = Response(b'{"stop":true}')
        with patch.object(probe.urllib.request, 'urlopen', return_value=good):
            self.assertTrue(probe.request(1, 'completion', {'stream': False})['stop'])
        self.assertEqual(good.limit, (16 << 20) + 1)
        for content, expected in [(b'data: {}\n\n', ValueError), (b'x' * ((16 << 20) + 1), ValueError)]:
            with patch.object(probe.urllib.request, 'urlopen', return_value=Response(content)):
                with self.assertRaises(expected):
                    probe.request(1, 'completion', {'stream': False})


if __name__ == '__main__': unittest.main()
