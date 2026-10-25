"""Synthetic boundary tests; imports no engine or live transport."""
import unittest
from kvu16b_predicate import bind_tasks, decoding_requests


def row(slot=0, task=43, proc=True, processed=60720, cached=0, decoded=1):
    return dict(id=slot, id_task=task, proc=proc, n_proc=processed,
                n_cache=cached, n_dec=decoded, n_tok=80000)


class AdmissionBoundaryTests(unittest.TestCase):
    def dec(self, rows, first=None, t=10):
        return decoding_requests(rows, [40, 41, 42, 43], [79836] * 4,
                                 first if first is not None else [None] * 4, t)

    def test_historical_stale_counter_never_admits_four(self):
        peers = [row(slot=i+1, task=40+i, processed=79836) for i in range(3)]
        self.assertEqual(set(self.dec(peers + [row()])), {0, 1, 2})

    def test_processed_boundary(self):
        self.assertEqual(self.dec([row(processed=79835)]), {})
        self.assertEqual(set(self.dec([row(processed=79836)])), {3})

    def test_cached_tokens_complete_prompt(self):
        self.assertEqual(self.dec([row(cached=19115)]), {})
        self.assertEqual(set(self.dec([row(cached=19116)])), {3})

    def test_first_token_causal_boundary(self):
        for first in (9, 10):
            self.assertEqual(set(self.dec([row()], [None, None, None, first])), {3})
        self.assertEqual(self.dec([row()], [None, None, None, 10.001]), {})

    def test_completion_event_is_not_token_proof(self):
        self.assertEqual(self.dec([row(decoded=100)]), {})

    def test_idle_or_unmapped_is_absent(self):
        self.assertEqual(self.dec([row(proc=False, processed=79836)]), {})
        self.assertEqual(self.dec([row(task=999, processed=79836)]), {})

    def test_request_keys_survive_slot_permutation(self):
        rows = [row(slot=0, task=43, processed=79836),
                row(slot=1, task=40, processed=79836)]
        dec = self.dec(rows)
        self.assertEqual(set(dec), {0, 3})
        self.assertEqual(dec[3]['id'], 0)
        self.assertEqual(dec[0]['id'], 1)

    def test_duplicate_task_fails_closed(self):
        with self.assertRaises(ValueError):
            self.dec([row(processed=79836), row(slot=1, processed=79836)])

    def test_baseline_task_never_claimed(self):
        self.assertEqual(bind_tasks([row()], {43}, [9], [None], 10), {})

    def test_new_task_maps_to_only_sent_request(self):
        self.assertEqual(bind_tasks([row(task=44)], {43}, [None, None, None, 9],
                                    [None] * 4, 10), {3: 44})

    def test_future_send_cannot_claim_prior_snapshot(self):
        with self.assertRaises(ValueError):
            bind_tasks([row(task=44)], {43}, [10.001], [None], 10)

    def test_ambiguous_request_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            bind_tasks([row(task=44)], {43}, [8, 9], [None, None], 10)

    def test_ambiguous_task_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            bind_tasks([row(task=44), row(slot=1, task=45)], {43}, [9], [None], 10)

    def test_sample_result_does_not_gain_future_first_tokens(self):
        first_at = [None] * 4
        history = dict(self.dec([row()], first_at, 10))
        first_at[3] = 11
        self.assertEqual(history, {})
        self.assertEqual(self.dec([row()], first_at, 10), {})
        self.assertEqual(set(self.dec([row()], first_at, 12)), {3})


if __name__ == '__main__':
    unittest.main()
