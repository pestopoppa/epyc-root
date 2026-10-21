"""Session-wide carrier invariants for the loop-belief redesign (P1-A).

Two properties must hold for EVERY tuple any registered projection produces, not only for the
handful a single test file builds:

  (a) byte identity -- a tuple with no `observation` emits exactly the frames the pre-P1-A
      `to_frames` emitted (`_legacy_frames.legacy_to_frames`, frozen verbatim), so no existing
      frame id moves;
  (b) grade invariance -- grade(t) == grade(replace(t, observation={})): the observation is
      inert to the ladder.

Every adapter test already drives its projection over its own fixtures, so the complete corpus is
"every ClaimTuple constructed during the session". This plugin records them (a class-level wrap of
`ClaimTuple.__post_init__`, after validation succeeds) and checks both properties once, at session
end; a violation fails the run with the offending measurement ids. `test_claim_tuple.py` carries
explicit, non-session-dependent tests of the same two properties over the P1 fixtures.

Tuples built through the packaged import path (`scripts.vidya.claim_tuple`) are a different class
object and are not recorded; that path has its own dependency-graph test.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for entry in (str(ROOT / "scripts" / "vidya"), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

_SEEN: list = []
_MAX_RECORDED = 50_000
_STATE = {"recording": True, "failures": [], "checked": 0, "kinds": 0}


def pytest_configure(config):
    import claim_tuple as ct

    original = ct.ClaimTuple.__post_init__
    if getattr(original, "__p1a_recorder__", False):
        return

    def recording(self):
        original(self)
        if _STATE["recording"] and len(_SEEN) < _MAX_RECORDED:
            _SEEN.append(self)

    recording.__p1a_recorder__ = True
    ct.ClaimTuple.__post_init__ = recording


def _check() -> None:
    from dataclasses import replace

    import claim_tuple as ct
    from _legacy_frames import legacy_to_frames, outcome

    _STATE["recording"] = False
    kinds = set()
    for tup in _SEEN:
        kinds.add(tup.source_kind)
        kw = {"as_of": "2026-10-21T00:00:00Z", "adapter_id": "p1a.recorder/v1"}
        if tup.observation:
            try:
                bare = replace(tup, observation={})
            except Exception as exc:  # noqa: BLE001
                _STATE["failures"].append((tup.measurement_id, f"replace failed: {exc}"))
                continue
            if ct.grade(tup) != ct.grade(bare):
                _STATE["failures"].append((tup.measurement_id, "grade moved with observation"))
        elif outcome(ct.to_frames, tup, **kw) != outcome(legacy_to_frames, tup, **kw):
            _STATE["failures"].append((tup.measurement_id, "frames differ from pre-P1-A bytes"))
        _STATE["checked"] += 1
    _STATE["kinds"] = len(kinds)


def pytest_sessionfinish(session, exitstatus):
    if not _SEEN:
        return
    _check()
    if _STATE["failures"]:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not _STATE["checked"]:
        return
    terminalreporter.write_line(
        f"P1-A carrier invariants: {_STATE['checked']} tuples from {_STATE['kinds']} source "
        f"kinds checked (byte identity / grade invariance), "
        f"{len(_STATE['failures'])} violation(s)")
    for ident, why in _STATE["failures"][:20]:
        terminalreporter.write_line(f"  P1-A VIOLATION {ident}: {why}", red=True)
