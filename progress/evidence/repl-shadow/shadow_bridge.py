"""Unapplied opt-in candidate for prospective bundle-search shadow attribution.

The caller must explicitly configure a bundle with a shown-arm identity, hidden
arm callables and an authorized sink. The sink receives hash/span records only.
Not a traffic collector or proof of model/runtime identity.
"""
from __future__ import annotations

import hashlib
import os
import threading
import uuid
from datetime import datetime, timezone

from scripts.vidya.producers.repl_shadow import ShadowAttribution, Span


def _digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _now():
    return datetime.now(timezone.utc)


def _span(bundle, hit):
    section = bundle._section(hit['section'])
    return Span(_digest(section.name), _digest(section.text), hit['start'], hit['end'], len(section.text))


class Bridge:
    def __init__(self, bundle, shown_arm, hidden_arms, sink):
        if not hidden_arms or shown_arm in hidden_arms or not callable(sink):
            raise ValueError('shown arm, hidden arms and sink required')
        if any(not callable(run) for run in hidden_arms.values()):
            raise ValueError('hidden arms must be callable')
        self.bundle, self.shown_arm, self.hidden_arms, self.sink = bundle, shown_arm, dict(hidden_arms), sink
        self.session = uuid.uuid4().hex[:16]
        self.pending = None
        self.lock = threading.Lock()

    def _emit(self):
        if self.pending is None:
            return
        row = self.pending.result()
        for arm, hits in row['arms'].items():
            for hit in hits:
                hit['interpretation'] = 'shown' if arm == self.shown_arm else 'counterfactual_span_match'
        self.pending = None
        self.sink(row)

    def search(self, query, k, section, shown_hits):
        with self.lock:
            # A superseded search never gains a negative follow outcome.
            self._emit()
            rankings = {self.shown_arm: [_span(self.bundle, h) for h in shown_hits]}
            for arm, run in self.hidden_arms.items():
                rankings[arm] = [_span(self.bundle, h) for h in run(query, k, section)]
            self.pending = ShadowAttribution(session=self.session, query_digest=_digest(query),
                searched_at=_now(), rankings=rankings, shown_arm=self.shown_arm)

    def opened(self, section, start, end):
        with self.lock:
            if self.pending is None or start >= end:
                return
            span = _span(self.bundle, {'section': section, 'start': start, 'end': end})
            self.pending.observe_open(session=self.session, opened_at=_now(), span=span)
            self._emit()

    def close(self):
        with self.lock:
            self._emit()


def configure(bundle, *, shown_arm, hidden_arms, sink):
    if os.environ.get('EPYC_REPL_SHADOW_CAPTURE') != '1':
        return False
    bundle._repl_shadow_bridge = Bridge(bundle, shown_arm, hidden_arms, sink)
    return True


def search(bundle, query, k, section, shown_hits):
    if os.environ.get('EPYC_REPL_SHADOW_CAPTURE') != '1':
        return
    bridge = getattr(bundle, '_repl_shadow_bridge', None)
    if bridge is not None:
        bridge.search(query, k, section, shown_hits)


def opened(bundle, section, start, end):
    if os.environ.get('EPYC_REPL_SHADOW_CAPTURE') != '1':
        return
    bridge = getattr(bundle, '_repl_shadow_bridge', None)
    if bridge is not None:
        bridge.opened(section, start, end)
