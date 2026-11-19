"""Draft request-scoped shadow span accounting; no runtime or persistence hook.

The caller runs each retrieval arm, maps hits to content-bound character spans,
then constructs this object before exposing the selected arm. This is not a
belief writer or an online experiment implementation.
"""
from __future__ import annotations

import re
from copy import deepcopy

_SHA = re.compile(r"^[0-9a-f]{64}$")
_NAME = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-]{0,63}$")


def _name(value):
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise ValueError("invalid identifier")
    return value


def _span(value):
    if not isinstance(value, dict) or set(value) != {"content_sha256", "start", "end"}:
        raise ValueError("invalid span shape")
    digest, start, end = value["content_sha256"], value["start"], value["end"]
    if not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise ValueError("invalid content digest")
    if type(start) is not int or type(end) is not int or not 0 <= start < end:
        raise ValueError("invalid half-open span")
    return {"content_sha256": digest, "start": start, "end": end}


class ShadowSearchCapture:
    """Record all arm identities privately; expose only the selected arm's spans.

    A single instance represents one search in one request. Errors stay errors;
    unobserved follows stay unknown unless the request is explicitly complete.
    Overlap is a correlation, not evidence that a counterfactual arm was shown.
    """

    def __init__(self, *, request_id, query_sha256, selected_arm, arms, content_sizes):
        self.request_id = _name(request_id)
        if not isinstance(query_sha256, str) or not _SHA.fullmatch(query_sha256):
            raise ValueError("invalid query digest")
        self.query_sha256 = query_sha256
        self.selected_arm = _name(selected_arm)
        if not isinstance(arms, dict) or not arms or self.selected_arm not in arms:
            raise ValueError("missing arms or selected arm")
        if not isinstance(content_sizes, dict) or not content_sizes:
            raise ValueError("missing content sizes")
        self._content_sizes = {}
        for digest, size in content_sizes.items():
            if (not isinstance(digest, str) or not _SHA.fullmatch(digest)
                    or type(size) is not int or not 0 < size <= 10**12):
                raise ValueError("invalid content size")
            self._content_sizes[digest] = size
        self._arms = {}
        for name, result in arms.items():
            _name(name)
            if not isinstance(result, dict) or set(result) != {"status", "hits"}:
                raise ValueError("invalid arm result")
            status, hits = result["status"], result["hits"]
            if status not in ("ok", "error", "timeout") or not isinstance(hits, list):
                raise ValueError("invalid arm status or hits")
            if status != "ok" and hits:
                raise ValueError("failed arm cannot return hits")
            spans = [self._bounded_span(hit) for hit in hits]
            self._arms[name] = {"status": status, "hits": spans, "opened": [False] * len(spans)}
        if self._arms[self.selected_arm]["status"] != "ok":
            raise ValueError("selected arm must succeed")
        self._finished = False
        self._selected_returned = False

    def _bounded_span(self, value):
        span = _span(value)
        size = self._content_sizes.get(span["content_sha256"])
        if size is None or span["end"] > size:
            raise ValueError("span outside declared content")
        return span

    def selected_hits(self):
        if self._finished:
            raise ValueError("capture already finished")
        self._selected_returned = True
        return deepcopy(self._arms[self.selected_arm]["hits"])

    def record_open(self, span):
        if self._finished:
            raise ValueError("capture already finished")
        if not self._selected_returned:
            raise ValueError("selected hits have not been returned")
        opened = self._bounded_span(span)
        for arm in self._arms.values():
            for i, hit in enumerate(arm["hits"]):
                if (hit["content_sha256"] == opened["content_sha256"]
                    and hit["start"] < opened["end"] and opened["start"] < hit["end"]):
                    arm["opened"][i] = True

    def finish(self, *, complete):
        if self._finished or type(complete) is not bool:
            raise ValueError("invalid completion")
        if not self._selected_returned:
            raise ValueError("selected hits have not been returned")
        self._finished = True
        arms = {}
        for name, arm in self._arms.items():
            arms[name] = {"status": arm["status"], "hits": [
                {**hit, "opened": opened if opened or complete else None}
                for hit, opened in zip(arm["hits"], arm["opened"])
            ]}
        return {"schema": "epyc.repl.shadow_span_follow.draft.v1",
                "request_id": self.request_id, "query_sha256": self.query_sha256,
                "selected_arm": self.selected_arm, "complete": complete, "arms": arms}
