"""Fake transports exercise the real worker and private sampler without live IO."""
import importlib.util
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import patch
from urllib.error import URLError

from kvu16b_predicate import CausalSlotsSampler, RequestLedger, admission_ok, residency_sample
from test_kvu16b_predicate import row


class Clock:
    def __init__(self, value=1):
        self.value = value

    def __call__(self):
        return self.value


class Sink:
    def __init__(self):
        self.rows = []

    def add(self, record):
        self.rows.append(record)


def load_runner(fake):
    path = Path(__file__).with_name('kvu16b_residency.py')
    spec = importlib.util.spec_from_file_location('fake_kvu16b_runner', path)
    runner = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'lib_gpublock': fake}):
        spec.loader.exec_module(runner)
    return runner


class WorkerSamplerTests(unittest.TestCase):
    def test_four_workers_are_causal_and_history_is_not_relabelled(self):
        clock = Clock()
        ledger = RequestLedger([79836] * 4, {5}, clock)
        started = [threading.Event() for _ in range(4)]
        release_token = [threading.Event() for _ in range(4)]
        finish = threading.Event()
        self.addCleanup(finish.set)
        for ev in release_token:
            self.addCleanup(ev.set)
        def stream(url, body, timeout, on_first_token, stop):
            i = int(body['prompt'])
            started[i].set()
            if not release_token[i].wait(2):
                raise RuntimeError('test failed to release first token')
            on_first_token()
            if not finish.wait(2):
                raise RuntimeError('test failed to finish worker')
            return {'http_status': 200}
        runner = load_runner(types.SimpleNamespace(stream_request=stream, timing_summary=lambda _: {}))
        sink, results = Sink(), [{} for _ in range(4)]
        firsts = [threading.Event() for _ in range(4)]
        slots, observations = [], []
        def observe(t_req, t_resp, rows):
            observations.append(ledger.observe(t_req, rows))
        sampler = CausalSlotsSampler(lambda: [dict(r) for r in slots], 0, sink, observe, clock)
        threads = []
        try:
            for i in range(4):
                clock.value = 10 * i + 1
                th = threading.Thread(target=runner.run_request,
                                      args=(i, (str(i), 79836), 2048, 'FAKE', 10,
                                            ledger, firsts[i], finish, results, sink))
                th.start()
                threads.append(th)
                self.assertTrue(started[i].wait(1))
                # Task is ours, but stale n_dec must not make it a decoder.
                slots.append(row(slot=(i + 1) % 4, task=100+i))
                clock.value += 1
                sampler.sample_once()
                self.assertTrue(ledger.mapped[i].is_set())
                self.assertNotIn(i, observations[-1])
                self.assertEqual(len(ledger.history), 0)
                clock.value += 1
                release_token[i].set()
                self.assertTrue(firsts[i].wait(1))
                sampler.sample_once()
                self.assertEqual(set(observations[-1]), set(range(i+1)))
            self.assertEqual(len(ledger.history), 1)
            self.assertEqual(set(ledger.history[0][1]), {0, 1, 2, 3})
            self.assertEqual(observations[-1][3]['id'], 0)
            clock.value += 2
            for r in slots:
                r['n_dec'] += 4
            sampler.sample_once()
            self.assertEqual(ledger.rates(), ({0: 2., 1: 2., 2: 2., 3: 2.}, []))
            self.assertEqual(len(ledger.history), 2)  # earlier stale snapshots remain absent
            self.assertEqual(ledger.faults, [])
        finally:
            finish.set()
            for ev in release_token:
                ev.set()
            for th in threads:
                th.join(2)
        self.assertTrue(all(not th.is_alive() for th in threads))
        self.assertTrue(all(r.get('http_status') == 200 for r in results))

    def test_token_during_fetch_does_not_backdate_to_poll_start(self):
        clock = Clock(1)
        ledger = RequestLedger([79836], set(), clock)
        ledger.sent(0)
        ledger.observe(2, [row()])  # bind while still prefilling
        sink, seen = Sink(), []
        def fetch():
            clock.value = 10
            ledger.first(0)  # token arrives while GET is in flight
            clock.value = 11
            return [row()]
        clock.value = 9
        sampler = CausalSlotsSampler(fetch, 0, sink,
                                    lambda a, b, rows: seen.append(ledger.observe(a, rows)), clock)
        sampler.sample_once()
        self.assertEqual(seen, [{}])
        self.assertEqual(ledger.history, [])
        self.assertEqual((sink.rows[0]['t_req'], sink.rows[0]['t_resp']), (9, 11))
        sampler.sample_once()
        self.assertEqual(set(seen[-1]), {0})

    def test_timeout_is_missed_poll_and_callback_fault_reaches_verdict(self):
        clock = Clock()
        responses = iter([TimeoutError('busy iteration'), URLError(TimeoutError('connect timeout')),
                          OSError('transport'), [row()]])
        def fetch():
            value = next(responses)
            if isinstance(value, Exception):
                raise value
            return value
        def broken_callback(*args):
            raise RuntimeError('callback fault')
        sampler = CausalSlotsSampler(fetch, 0, Sink(), broken_callback, clock)
        sampler.start()
        sampler.join(1)
        self.assertFalse(sampler.is_alive())
        self.assertEqual((sampler.missed_samples, sampler.errors), (2, 1))
        self.assertIn('callback fault', sampler.fault)
        self.assertFalse(admission_ok(1, {}, 62, 62, [], [], sampler.fault))

    def test_worker_fault_cannot_disappear_and_completion_is_not_first_token(self):
        def fail(*args, **kwargs):
            raise RuntimeError('synthetic stream failure')
        runner = load_runner(types.SimpleNamespace(stream_request=fail, timing_summary=lambda _: {}))
        ledger = RequestLedger([100], set(), Clock())
        event, results = threading.Event(), [{}]
        th = threading.Thread(target=runner.run_request,
                              args=(0, ('0', 100), 5, 'FAKE', 10, ledger, event,
                                    threading.Event(), results, Sink()))
        th.start()
        th.join(1)
        self.assertFalse(th.is_alive())
        self.assertTrue(event.is_set())
        self.assertEqual(ledger.first_at, [None])
        self.assertTrue(results[0]['worker_fault'])
        self.assertFalse(admission_ok(1, {}, 62, 62, [0], [], None))

    def test_concurrent_unmapped_tasks_record_fault_and_refuse_admission(self):
        ledger = RequestLedger([100] * 4, set(), Clock())
        ledger.sent(0)
        seen = ledger.observe(2, [row(task=43), row(slot=1, task=44)])
        self.assertEqual(seen, {})
        self.assertEqual(ledger.tasks, [None] * 4)
        self.assertIn('ambiguous', ledger.faults[0]['error'])
        self.assertFalse(admission_ok(1, {}, 62, 62, [], ledger.faults, None))

    def test_poll_started_before_send_defers_binding_until_next_poll(self):
        ledger = RequestLedger([100], set(), Clock(10))
        ledger.sent(0)
        self.assertEqual(ledger.observe(9, [row(processed=100)]), {})
        self.assertEqual(ledger.faults, [])
        self.assertEqual(set(ledger.observe(11, [row(processed=100)])), {0})

    def test_actual_residency_and_budget_gates_are_unchanged(self):
        def pass_t(decoders, resident):
            return 1 if residency_sample(dict.fromkeys(range(decoders)), resident, 4, 300000) else None
        def ok(n=4, resident=300000, kfd=62, bad=None, failed=None):
            return admission_ok(pass_t(n, resident), bad or {}, kfd, 62, failed or [], [], None)
        self.assertTrue(ok())
        self.assertFalse(ok(n=3))
        self.assertFalse(ok(resident=299999))
        self.assertFalse(ok(kfd=62.001))
        self.assertFalse(ok(kfd=None))
        self.assertFalse(ok(bad={'memory_slot': 1}))
        self.assertFalse(ok(failed=[3]))

    def test_negative_counter_delta_is_invalid_rate_not_clamped(self):
        ledger = RequestLedger([100], set())
        ledger.history = [(1, {0: 10}), (2, {0: 1})]
        rates, faults = ledger.rates()
        self.assertEqual(rates, {})
        self.assertEqual(faults[0]['requests'], [0])


if __name__ == '__main__':
    unittest.main()
