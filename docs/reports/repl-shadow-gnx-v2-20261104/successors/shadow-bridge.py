"""Scratch-only prospective adapter; caller supplies live search and open events.

No orchestrator hooks, arm models, or runtime wiring are installed by this file.
"""
import hashlib
from threading import RLock
from scripts.vidya.producers.repl_shadow import Span
from scripts.vidya.producers.repl_shadow_sink import ShadowSink


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class ShadowBridge:
    def __init__(self, directory, *, run_id, session, source_sha256, arm_identities, arm_modes, sections):
        if not sections or any(not isinstance(k, str) or not isinstance(v, str) for k, v in sections.items()):
            raise ValueError('section snapshot must contain named strings')
        if set(arm_modes) != set(arm_identities) or any(not isinstance(v, str) or not v for v in arm_modes.values()):
            raise ValueError("each arm requires an expected execution mode")
        self.arm_modes = dict(arm_modes)
        self.sections = dict(sections)
        self.sink = ShadowSink(directory, run_id=run_id, session=session,
                               source_sha256=source_sha256, arm_identities=arm_identities)
        self.arms = set(arm_identities)
        self.lock = RLock()

    def _span(self, section, start, end):
        text = self.sections[section]
        return Span(digest(section), digest(text), start, end, len(text))

    def search(self, query, *, shown_arm, run_arm):
        """Run every arm once; only return the selected arm's real pointer list.

        run_arm(arm, query) -> (pointers, mode); caller must implement real,
        bounded and isolated search and call this before displaying results.
        Fallback/error or unknown mode must raise; no silent substitute arm.
        """
        if not isinstance(query, str) or not query.strip() or shown_arm not in self.arms:
            raise ValueError('invalid query or shown arm')
        with self.lock:
            pointers, rankings = {}, {}
            for arm in sorted(self.arms):
                hits, mode = run_arm(arm, query)
                if mode != self.arm_modes[arm]:
                    raise ValueError('arm did not execute as declared')
                if not isinstance(hits, list):
                    raise ValueError('invalid pointers')
                rankings[arm] = [self._span(h['section'], h['start'], h['end']) for h in hits]
                pointers[arm] = hits
            self.sink.search(query_digest=digest(query), rankings=rankings, shown_arm=shown_arm)
            return pointers[shown_arm]

    def opened(self, section, start, end, *, current_text):
        """At actual open, require same immutable section version as search."""
        with self.lock:
            if self.sections[section] != current_text:
                raise ValueError('section changed; cannot attribute span')
            return self.sink.opened(span=self._span(section, start, end))

    def close(self):
        with self.lock:
            self.sink.close()
