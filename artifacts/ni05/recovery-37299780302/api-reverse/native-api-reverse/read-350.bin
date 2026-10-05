#!/usr/bin/env python3
"""`expected_stack_services` may fail open — but never quietly.

Filed 2026-07-24 as the "scripts.server circular-import fail-open flake": the
NUMA-mode filter was wrapped in `except Exception -> unfiltered list`, logged at
**debug**, because a partially-initialized `scripts.server` import chain could
make the filter unavailable. The quiet level is what turned a fallback into a
MASK: a filter defect produced a silently unfiltered service list that looks
exactly like a correct one, so ports belonging to other NUMA modes render as
"expected" with nothing to indicate degradation.

Re-derived 2026-08-12 (`mainB`): **the import cycle no longer reproduces.** Three
bare imports and four package-order imports of `runtime_facts_manifest`,
`stack_paths`, `stack_manifest` and `orchestrator_stack` all import cleanly. So
the original justification is gone, and anything the handler catches now is a
REAL filter defect — precisely the case that must not be silent.

The fail-open itself is KEPT deliberately: for a dashboard panel, over-reporting
beats dropping the panel. What changed is that both degraded paths now log at
warning with what was substituted and why. These tests pin the loudness, because
the loudness is the entire fix — a fallback nobody can see is the defect.
"""

from __future__ import annotations

import logging

import pytest

from src.api.routes import dashboard_topology as dt


def test_filter_failure_falls_open_but_warns(monkeypatch, caplog):
    """A filter defect must produce a WARNING naming the substitution."""
    import scripts.server.stack_manifest as sm

    def _explode(_servers, _mode):
        raise RuntimeError("synthetic filter defect")

    monkeypatch.setattr(sm, "_filter_by_numa_mode", _explode, raising=True)
    monkeypatch.setattr(dt, "active_stack_numa_mode", lambda: "quarter", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)
    monkeypatch.setattr(dt, "read_runtime_stack_selected_servers", lambda: None, raising=True)

    with caplog.at_level(logging.WARNING, logger=dt.logger.name):
        services = dt.expected_stack_services()

    # Fail-open preserved: the panel still renders.
    assert services, "fail-open dropped the panel entirely — that is worse, not better"

    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "UNFILTERED" in text, f"degradation not announced: {text!r}"
    assert "synthetic filter defect" in text, "the cause was swallowed"
    assert "quarter" in text, "the mode in force was not reported"


def test_manifest_unavailable_warns_rather_than_reporting_an_empty_stack(
    monkeypatch, caplog
):
    """`return []` must not be mistakable for "no services expected".

    An empty list renders as a healthy empty stack. At debug level, a read
    failure and a genuinely empty topology were indistinguishable to anyone
    reading the panel.
    """
    import builtins

    real_import = builtins.__import__

    def _fail_stack_manifest(name, *a, **k):
        if name == "scripts.server.stack_manifest":
            raise ImportError("synthetic partially-initialized chain")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _fail_stack_manifest)
    monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)
    monkeypatch.setattr(dt, "read_runtime_stack_selected_servers", lambda: None, raising=True)

    with caplog.at_level(logging.WARNING, logger=dt.logger.name):
        services = dt.expected_stack_services()

    assert services == []
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "READ FAILURE" in text, f"empty result not distinguished from empty stack: {text!r}"


def test_healthy_path_stays_silent(monkeypatch, caplog):
    """Negative control: the compliant path must NOT warn.

    Without this, both assertions above would also pass if the function warned
    unconditionally — which would be its own defect (an alarm that always fires
    is not an alarm).
    """
    monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)
    monkeypatch.setattr(dt, "read_runtime_stack_selected_servers", lambda: None, raising=True)
    monkeypatch.setattr(dt, "active_stack_numa_mode", lambda: "both", raising=False)

    with caplog.at_level(logging.WARNING, logger=dt.logger.name):
        dt.expected_stack_services()

    noisy = [r.getMessage() for r in caplog.records if "UNFILTERED" in r.getMessage()
             or "READ FAILURE" in r.getMessage()]
    assert not noisy, f"healthy path emitted a degradation warning: {noisy}"


@pytest.mark.parametrize(
    "module",
    [
        "scripts.server.runtime_facts_manifest",
        "scripts.server.stack_paths",
        "scripts.server.stack_manifest",
    ],
)
def test_the_original_import_cycle_no_longer_reproduces(module):
    """Pins the re-derivation, so a regression re-files the row rather than the fix.

    If the cycle comes back this fails, which is the signal that the fail-open's
    original justification has returned and the warnings above will start firing
    for a reason that is NOT a filter defect.
    """
    __import__(module)
