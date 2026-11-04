"""Experimental authenticated-owner, per-CPU trace capture lifecycle.

Works on caller-opened disabled perf Session objects. Source FD attributes, loss
semantics, request meaning and thread lineage remain independently unverified.
Returns raw ring snapshots; never grants measurement admission.
"""
import threading
from owner_marker import Receiver
from perf_mmap import Session
from target_identity import Target
from trace_open import validate_provenance
from same_fd_guard import SameFDGuard
from tracepoint_payload_guard import check as check_payload

EVENTS = frozenset(('sched_switch', 'irq_handler_entry', 'irq_handler_exit',
                    'softirq_entry', 'softirq_exit'))


class Capture:
    def __init__(self, receiver, target, sources, cpus, *, interval_s=0.05,
                 max_bytes=16 * 1024 * 1024):
        if not isinstance(receiver, Receiver) or receiver.failed or receiver.fd is None:
            raise ValueError('live authenticated owner receiver required')
        if not isinstance(target, Target): raise ValueError('pidfd target required')
        if not isinstance(cpus, (set, frozenset)) or not cpus or any(type(c) is not int or c < 0 for c in cpus):
            raise ValueError('invalid CPU inventory')
        if not 0.005 <= interval_s <= 1 or type(max_bytes) is not int or not 4096 <= max_bytes <= 256 * 1024 * 1024:
            raise ValueError('invalid capture bounds')
        if not isinstance(sources, list): raise ValueError('invalid sources')
        expected = {(c, e) for c in cpus for e in EVENTS}
        actual = []
        provenance = []
        for item in sources:
            if not isinstance(item, dict) or set(item) != {'name', 'session'} or not isinstance(item['session'], Session) or item['session'].state != 'new':
                raise ValueError('new owned perf session required')
            actual.append((item['session'].cpu, item['name']))
            provenance.append(validate_provenance(item['name'], item['session']))
        ids = [x['session'].event_id for x in sources]; fds = [x['session'].fd for x in sources]
        if len(actual) != len(expected) or set(actual) != expected or len(ids) != len(set(ids)) or len(fds) != len(set(fds)):
            raise ValueError('missing or duplicate event, FD or CPU')
        # Pin each open file description before any capture operation. A
        # partial acquisition closes all pins; source ownership remains with caller.
        guards = {}
        try:
            for item in sources:
                session = item['session']
                guards[id(session)] = SameFDGuard(session)
        except BaseException:
            for guard in guards.values():
                guard.close()
            raise
        self.guards = guards
        self.receiver, self.target, self.sources = receiver, target, sources
        self.provenance = provenance
        self.provenance_by_session = {id(item['session']): p for item, p in zip(sources, provenance)}
        self.interval_s, self.max_bytes = interval_s, max_bytes
        self.stop_event = threading.Event(); self.thread = None; self.started = []
        self.snapshots = []; self.results = []; self.errors = []; self.size = 0
        self.markers = []; self.observations = []; self.state = 'new'
        self.cleaned = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.abort()
        return False

    def abort(self):
        """Release owned sessions once; failed joins require worker process exit."""
        if self.cleaned:
            return
        self._cleanup()
        if self.state != 'finished':
            self.state = 'failed'

    def _retain(self, item, ring):
        snapshot = ring.get('snapshot')
        if not isinstance(snapshot, bytes) or not isinstance(ring.get('errors'), list):
            raise ValueError('ring snapshot missing')
        if ring['errors']: raise ValueError('ring reported loss or malformed record')
        session = item['session']
        source = self.provenance_by_session[id(session)]
        check_payload(ring, cpu=session.cpu, event_id=session.event_id, tracepoint_id=source['tracepoint_id'])
        if self.size + len(snapshot) > self.max_bytes: raise ValueError('capture byte bound exceeded')
        self.size += len(snapshot)
        self.snapshots.append({'name': item['name'], 'cpu': item['session'].cpu,
                               'event_id': item['session'].event_id, 'ring': ring})

    def _drain_loop(self):
        try:
            while not self.stop_event.is_set():
                for item in self.sources:
                    if self.stop_event.is_set(): break
                    session = item['session']
                    self._retain(item, self.guards[id(session)].call(session.drain))
                self.stop_event.wait(self.interval_s)
        except Exception as exc:
            self.errors.append(f'drain: {type(exc).__name__}: {exc}')
            self.stop_event.set()

    def _cleanup(self, window=None):
        if self.cleaned:
            return
        # Set before cleanup so signal unwinding cannot close the same FD twice.
        self.cleaned = True
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                self.errors.append('drain worker did not stop; perf FDs left owned by worker')
                return
        for item in self.started:
            s = item['session']
            if s.state == 'running':
                try:
                    result = self.guards[id(s)].call(lambda: s.stop(request_window=window), closes_fd=True)
                    self._retain(item, result['ring'])
                    self.results.append({'name': item['name'], **result})
                    self.errors.extend(result.get('errors', []))
                except Exception as exc: self.errors.append(f'stop: {type(exc).__name__}: {exc}')
        for item in self.sources:
            guard = self.guards[id(item['session'])]
            if guard.failed:
                self.errors.append('same-FD guard failed; original session left for worker process exit')
            else:
                try: item['session'].close()
                except Exception as exc: self.errors.append(f'close: {type(exc).__name__}: {exc}')
            try: guard.close()
            except Exception as exc: self.errors.append(f'guard close: {type(exc).__name__}: {exc}')
        try: self.target.close()
        except Exception as exc: self.errors.append(f'target: {type(exc).__name__}: {exc}')
        try: self.receiver.close()
        except Exception as exc: self.errors.append(f'owner: {type(exc).__name__}: {exc}')

    def start(self):
        if self.state != 'new': raise ValueError('wrong state')
        try:
            self.observations.append(self.target.snapshot())
            for item in self.sources:
                session = item['session']
                self.guards[id(session)].call(session.start); self.started.append(item)
            self.thread = threading.Thread(target=self._drain_loop, name='ch26-ring-drain', daemon=True)
            self.thread.start(); self.state = 'started'
        except BaseException:
            self.state = 'failed'; self._cleanup(); raise

    def begin(self):
        if self.state != 'started': raise ValueError('wrong state')
        try:
            marker = self.receiver.receive()
            if marker['kind'] != 'begin' or self.errors: raise ValueError('invalid begin or capture failed')
            self.observations.append(self.target.snapshot()); self.markers.append(marker); self.state = 'request'
        except BaseException:
            self.state = 'failed'; self._cleanup(); raise

    def finish(self):
        if self.state != 'request': raise ValueError('wrong state')
        try:
            marker = self.receiver.receive()
            if marker['kind'] != 'end': raise ValueError('invalid end marker')
            self.observations.append(self.target.snapshot()); self.markers.append(marker)
            if any(x != self.observations[0] for x in self.observations): raise ValueError('target identity changed')
            window = (self.markers[0]['timestamp_ns'], marker['timestamp_ns'])
            self._cleanup(window)
            if len(self.results) != len(self.sources): self.errors.append('missing final ring result')
            self.state = 'finished' if not self.errors else 'failed'
            return {'status': 'unproven', 'coverage': 'unknown', 'loss': 'unknown',
                    'measurement_admission': 'none', 'markers': self.markers,
                    'target_observations': self.observations, 'snapshots': self.snapshots,
                    'rings': self.results, 'source_provenance': self.provenance, 'errors': self.errors,
                    'limitations': ['FD attributes recorded at syscall lack independent kernel readback',
                                    'same-FD and raw common_type checks trust owner process and source receipt',
                                    'same-FD checks are non-atomic and trust exclusive process FD ownership',
                                    'kernel loss and coverage semantics not validated',
                                    'request meaning, task lineage and contention are not proven']}
        except BaseException:
            self.state = 'failed'; self._cleanup(); raise
