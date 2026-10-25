"""Request-owned KVU-16b admission and causal polling; no live IO at import."""
from __future__ import annotations

import threading
import time

PREDICATE_VERSION = 'request-task-prompt-end-v1'


def bind_tasks(rows, baseline, sent_at, request_tasks, sample_started):
    known = baseline | {t for t in request_tasks if t is not None}
    fresh = {r['id_task'] for r in rows
             if r['proc'] and r['id_task'] is not None and r['id_task'] not in known}
    pending = [i for i, task in enumerate(request_tasks)
               if task is None and sent_at[i] is not None and sent_at[i] <= sample_started]
    if not fresh:
        return {}
    if len(fresh) != 1 or len(pending) != 1:
        raise ValueError('ambiguous task/request mapping')
    return {pending[0]: next(iter(fresh))}


def decoding_requests(rows, request_tasks, prompt_tokens, first_at, sample_started):
    by_task = {task: i for i, task in enumerate(request_tasks) if task is not None}
    out = {}
    for row in rows:
        i = by_task.get(row['id_task'])
        if not row['proc'] or i is None:
            continue
        first_seen = first_at[i] is not None and first_at[i] <= sample_started
        past_prompt = row['n_proc'] + row['n_cache'] >= prompt_tokens[i]
        if first_seen or past_prompt:
            if i in out:
                raise ValueError('duplicate task rows')
            out[i] = row
    return out


class RequestLedger:
    def __init__(self, prompt_tokens, baseline, clock=time.time):
        self.prompts = list(prompt_tokens)
        self.baseline = set(baseline)
        self.clock = clock
        self.lock = threading.Lock()
        self.sent_at = [None] * len(prompt_tokens)
        self.first_at = [None] * len(prompt_tokens)
        self.tasks = [None] * len(prompt_tokens)
        self.faults = []
        self.history = []
        self.mapped = [threading.Event() for _ in prompt_tokens]

    def sent(self, i):
        with self.lock:
            self.sent_at[i] = self.clock()

    def first(self, i):
        with self.lock:
            if self.first_at[i] is None:
                self.first_at[i] = self.clock()

    def observe(self, t_req, rows):
        with self.lock:
            try:
                # A response can include a task sent after the poll started. Such a
                # snapshot cannot attribute that task yet; wait for the next poll.
                eligible = [r for r in rows if r['id_task'] in self.baseline
                            or r['id_task'] in self.tasks]
                fresh = [r for r in rows if r['proc'] and r['id_task'] is not None
                         and r['id_task'] not in self.baseline and r['id_task'] not in self.tasks]
                after_send = any(t is not None and t <= t_req and self.tasks[i] is None
                                 for i, t in enumerate(self.sent_at))
                if after_send or not any(t is not None and t > t_req for t in self.sent_at):
                    eligible += fresh
                additions = bind_tasks(eligible, self.baseline, self.sent_at, self.tasks, t_req)
                for i, task in additions.items():
                    self.tasks[i] = task
                    self.mapped[i].set()
                dec = decoding_requests(rows, self.tasks, self.prompts, self.first_at, t_req)
            except ValueError as exc:
                self.faults.append({'t_req': t_req, 'error': str(exc)})
                return {}
            # Save only what was admissible DURING this poll. Never relabel history
            # later using the final first-token timestamps.
            if len(dec) == len(self.prompts):
                self.history.append((t_req, {i: r['n_dec'] for i, r in dec.items()}))
            return dec

    def rates(self):
        if len(self.history) < 2:
            return {}, []
        (ta, da), (tb, db) = self.history[0], self.history[-1]
        faults = [i for i in db if db[i] < da[i]]
        if faults or tb <= ta:
            return {}, [{'requests': faults, 'error': 'non-monotonic decode counter or sample time'}]
        return {i: round((db[i] - da[i]) / (tb - ta), 2) for i in db}, []


class CausalSlotsSampler(threading.Thread):
    """Runner-private sampler. Fetch errors and callback faults are distinct."""
    def __init__(self, fetch, interval, sink, on_sample, clock=time.time):
        super().__init__(daemon=True)
        self.fetch, self.interval, self.sink, self.on_sample = fetch, interval, sink, on_sample
        self.clock = clock
        self.stop_ev = threading.Event()
        self.samples = []
        self.missed_samples = 0
        self.errors = 0
        self.fault = None

    def sample_once(self):
        t_req = self.clock()
        try:
            rows = self.fetch()
        except Exception as exc:
            # urllib can wrap a socket timeout in URLError.reason.
            if isinstance(exc, TimeoutError) or isinstance(getattr(exc, 'reason', None), TimeoutError):
                self.missed_samples += 1
            else:
                self.errors += 1
            return
        t_resp = self.clock()
        try:
            self.samples.append((t_req, rows))
            if self.sink:
                self.sink.add({'t': t_req, 't_req': t_req, 't_resp': t_resp, 'slots': rows})
            self.on_sample(t_req, t_resp, rows)
        except Exception as exc:
            self.fault = repr(exc)
            self.stop_ev.set()

    def run(self):
        try:
            while not self.stop_ev.is_set():
                self.sample_once()
                self.stop_ev.wait(self.interval)
        except Exception as exc:
            self.fault = repr(exc)
            self.stop_ev.set()


def residency_sample(decoding, resident, n_requests, resident_threshold):
    return len(decoding) == n_requests and resident >= resident_threshold


def admission_ok(pass_t, bad, kfd_peak_gib, kfd_budget_gib, failed, mapping_faults, sampler_fault):
    return (pass_t is not None and all(v == 0 for v in bad.values())
            and kfd_peak_gib is not None and kfd_peak_gib <= kfd_budget_gib
            and not failed and not mapping_faults and not sampler_fault)
