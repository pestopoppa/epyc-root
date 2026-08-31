"""Hub-side reader for the rebuilt AutoKernel loop's own status contract.

WHY THIS IS A SEPARATE MODULE
-----------------------------
The operator had **zero visibility** into the rebuilt loop: the dashboard showed
only the superseded deployment ``gpu-discovery-champion-v37`` as STOPPED — which
was correct, it *was* stopped at 2026-08-28T14:23Z — while the new loop ran as a
process the dashboard knew nothing about. A loop nobody can see is a loop nobody
can trust.

It is NOT bolted onto the existing Kernel-R&D surface in ``server.py``. That
surface pins 29 source paths and 47 content digests of another repository's
modules and is slated for wholesale rewrite; adding to it would re-arm that
landmine and couple a brand-new contract to a dying one. This is a small, clean,
separate surface with its own page, its own registry row and its own data probe.

THE PRODUCER OWNS THE SCHEMA; THIS SIDE ONLY READS
--------------------------------------------------
Contract: ``epyc.autokernel.loop_status.v1``, written atomically by
``scripts/kernel_rnd/autokernel/loop/status.py`` in **epyc-inference-research**
into the loop's store root (in practice
``/mnt/raid0/llm/autokernel/loop-memory/loop-status.json``). Per the plane rule
in ``dashboard/README.md`` the data contract lives with the subsystem it
observes; the page, the nav row and the probe live here. The hub **never imports
that package** — exactly as it never imports ``autokernel.dashboard`` for the
``kernel`` panel — so this module re-reads the same file with the same
semantics rather than pinning a cross-repo module path or digest.

FOUR-VALUED FRESHNESS, AND THE FOURTH IS NOT A LUXURY
-----------------------------------------------------
``absent`` / ``malformed`` / ``stale`` / ``fresh``. Collapsing ``absent`` into
``stale`` is how a dead producer renders as a clean, empty, trusted page — the
same lesson ``server.py`` records in its ``[]``-vs-``null`` comment on
``_read_kernel_contract``: ``[]`` says "the producer reported and there is
nothing", ``null`` says "no producer reported". So ``payload()["loop"]`` is
``None``, never ``{}``, when nothing readable was found.

ONE DELIBERATE REFINEMENT over the producer's own helper: its ``read()`` returns
``None`` for a file that exists but cannot be parsed, and ``freshness(None)``
then says ``absent``. Here a corrupt, empty or half-written file reads
``malformed`` and carries ``reader_error``, because **broken is not the same
fact as never-exported** (``server.py``'s ``READER_ERROR_KEY``): one points the
investigation at the producer's writer, the other at the producer's existence.
The three states the contract requires stay distinct; a fourth is added, none
are merged.

NOTHING IS CACHED. Every call re-reads the file. A cached value can outlive the
freshness envelope that is the entire point of the envelope.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
from typing import Any, Mapping, Optional

from dashboard import panels

#: The producer's schema string. A body carrying anything else is not this
#: contract and is refused as malformed rather than rendered on a page whose
#: field names would then mean something else.
STATUS_SCHEMA = "epyc.autokernel.loop_status.v1"
STATUS_FILENAME = "loop-status.json"

#: Mirrors ``status.DEFAULT_STALE_AFTER_S``. Used only when a body omits its own
#: budget; the producer's declared ``stale_after_s`` always wins.
DEFAULT_STALE_AFTER_S = 1800.0

#: Narrowest budget the hub will honour from a producer-declared value. A tiny
#: budget would make every reading stale between two publishes.
MIN_STALE_AFTER_S = 60.0

#: Where the loop keeps its memory, and therefore its status file. Overridable
#: for tests and for a second store root; resolved PER CALL, never at import, so
#: a test can point one request somewhere else without reloading the hub.
STORE_ROOT_ENV = "AUTOKERNEL_LOOP_STORE_ROOT"
DEFAULT_STORE_ROOT = Path("/mnt/raid0/llm/autokernel/loop-memory")

STATE_FRESH = "fresh"
STATE_STALE = "stale"
STATE_ABSENT = "absent"
STATE_MALFORMED = "malformed"
#: The four are distinct on purpose. If any two collapse, a dead producer can
#: render as a live one.
STATES = (STATE_FRESH, STATE_STALE, STATE_ABSENT, STATE_MALFORMED)

#: What absence MEANS here, in one sentence, travelling with every absent
#: reading. A panel that renders nothing without saying what nothing means is
#: the panel an operator reads as "fine".
ABSENCE_MEANS = (
    "the rebuilt AutoKernel loop has never published a status in this store "
    "root. It is not 'quiet' and it is not 'between iterations' — no process "
    "has written the contract at all. The loop publishes at start, after every "
    "iteration and on exit (including on failure), so a running loop is never "
    "absent here.")

#: Dispositions that mean a candidate actually reached the instrument. Mirrors
#: the producer's ``measurements_reached`` fold; kept here only to split the
#: rest out as NEGATIVES for the page.
MEASURED_DISPOSITIONS = ("kept", "measured_null")

#: The producer's OWN names first, then the shorter spellings this reader also
#: accepts. Getting this list wrong is not a cosmetic fault: it was wrong from
#: the surface's first commit — the reader looked only for ``held_s``/``busy_s``
#: while ``autokernel/loop/run.py`` has always written ``claim_held_s`` and
#: ``device_seconds_under_load`` — so the one panel this surface was built for
#: rendered "the loop published no held/busy seconds" over a producer that was
#: publishing them every iteration. The synthetic fixture invented the short
#: names and agreed with the code, so 41 tests passed over a dark panel.
HELD_KEYS = ("claim_held_s", "held_s", "held_seconds", "held")
BUSY_KEYS = ("device_seconds_under_load", "busy_s", "busy_seconds", "busy")

# --------------------------------------------------------------------------- #
# THE RUN'S LIFECYCLE IS NOT ITS FRESHNESS
# --------------------------------------------------------------------------- #
#: What the producer writes in ``state``. ``run.py`` publishes exactly these four:
#: ``starting`` once, ``running`` at every beat, and then ``complete`` or
#: ``failed`` on the way out — including after a STOP sentinel, which is drained
#: at the next iteration boundary and exits through the normal ``complete`` path.
RUN_STARTING = "starting"
RUN_RUNNING = "running"
RUN_COMPLETE = "complete"
RUN_FAILED = "failed"
RUN_STATES = (RUN_STARTING, RUN_RUNNING, RUN_COMPLETE, RUN_FAILED)

#: The banner the page must draw, which is NOT the freshness state.
#:
#: A run that was stopped on purpose goes quiet by design: it publishes
#: ``complete`` and exits, and thirty minutes later its last report is outside
#: the envelope. Keyed on freshness alone that renders "STALE — the loop has
#: stopped reporting", which accuses a producer that did exactly what it was
#: told. The reverse hole is worse: a loop that DECLARED ``failed`` one minute
#: ago is perfectly fresh, so freshness alone draws no banner at all over a dead
#: run — ``loop_data_health`` already refuses to make that mistake (it raises
#: ``failed`` to degraded explicitly) and the page must not make it either.
#:
#: So lifecycle and freshness are folded into ONE banner key here, server-side,
#: where a test can execute it. The freshness badge keeps the four-valued
#: vocabulary untouched; this is a second, orthogonal axis, never a fifth
#: freshness state.
NOTICE_ABSENT = "absent"
NOTICE_MALFORMED = "malformed"
NOTICE_STALE = "stale"
NOTICE_FINISHED = "finished"
NOTICE_FAILED = "failed"
NOTICE_NONE = "none"
NOTICES = (NOTICE_ABSENT, NOTICE_MALFORMED, NOTICE_STALE, NOTICE_FINISHED,
           NOTICE_FAILED, NOTICE_NONE)


def store_root() -> Path:
    """The loop's store root, resolved at call time."""
    return Path(os.environ.get(STORE_ROOT_ENV) or DEFAULT_STORE_ROOT)


def status_path(root: Optional[Path] = None) -> Path:
    return (store_root() if root is None else Path(root)) / STATUS_FILENAME


def read(root: Optional[Path] = None) -> dict:
    """``{artifact_present, body, reader_error}`` for the status file.

    Three outcomes, never two: no file (``artifact_present=False``), a file the
    hub could not turn into this contract (``reader_error`` set, ``body`` None),
    and a readable body. Absence and corruption are different facts about
    different subsystems and must not share a rendering.
    """
    path = status_path(root)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"artifact_present": False, "body": None, "reader_error": None,
                "path": str(path)}
    except OSError as exc:
        return {"artifact_present": path.exists(), "body": None,
                "reader_error": f"loop status unreadable: {exc}", "path": str(path)}
    if not raw.strip():
        # An EMPTY file is not an absent one: something opened it. Most likely a
        # writer that died between create and rename, which is a producer bug.
        return {"artifact_present": True, "body": None,
                "reader_error": "loop status is empty (0 bytes of content) — a "
                                "writer created the file and never finished it",
                "path": str(path)}
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"artifact_present": True, "body": None,
                "reader_error": f"loop status is not valid JSON: {exc}",
                "path": str(path)}
    if not isinstance(body, dict):
        return {"artifact_present": True, "body": None,
                "reader_error": "loop status is not a JSON object", "path": str(path)}
    schema = body.get("schema")
    if schema != STATUS_SCHEMA:
        return {"artifact_present": True, "body": None,
                "reader_error": (f"loop status declares schema {schema!r}, not "
                                 f"{STATUS_SCHEMA!r} — the field names on this "
                                 "page would not mean what they say"),
                "path": str(path)}
    return {"artifact_present": True, "body": body, "reader_error": None,
            "path": str(path)}


def _stamp_epoch(value: Any) -> Optional[float]:
    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def _budget(body: Mapping[str, Any]) -> float:
    """The producer's declared staleness budget, clamped to something usable.

    Clamped for the same reason ``panels.MAX_STALE_S`` exists: a budget wider
    than any real cadence satisfies "declares a threshold" and monitors nothing,
    and a budget of zero makes every reading stale between two publishes. The
    producer still owns the number inside those bounds — a loop that declares a
    longer cadence must not read as stale.
    """
    raw = body.get("stale_after_s")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_STALE_AFTER_S
    if value != value or value in (float("inf"), float("-inf")):  # NaN/inf
        return DEFAULT_STALE_AFTER_S
    return max(MIN_STALE_AFTER_S, min(value, float(panels.MAX_STALE_S)))


def freshness(report: Mapping[str, Any], *, now: Optional[float] = None) -> dict:
    """Fold one :func:`read` result into the four-valued freshness verdict."""
    now = time.time() if now is None else float(now)
    body = report.get("body")
    if body is None:
        if not report.get("artifact_present"):
            return {"state": STATE_ABSENT, "age_s": None, "stale_after_s": None,
                    "generated_at": None, "detail": ABSENCE_MEANS}
        return {"state": STATE_MALFORMED, "age_s": None, "stale_after_s": None,
                "generated_at": None,
                "detail": (report.get("reader_error")
                           or "the loop status file exists but could not be read "
                              "as this contract")}
    stamped = body.get("generated_at")
    written = _stamp_epoch(stamped)
    if written is None:
        return {"state": STATE_MALFORMED, "age_s": None,
                "stale_after_s": _budget(body), "generated_at": stamped,
                "detail": (f"unparseable generated_at {stamped!r} — a report "
                           "nobody can date cannot be trusted to be current")}
    age = now - written
    budget = _budget(body)
    if age < 0:
        # A report dated in the FUTURE cannot age, so it would read fresh forever
        # however long the producer has been dead. Same rule as
        # ``panels.FUTURE_SKEW_TOLERANCE_S``, applied to this contract's own
        # verdict so the page and the fold agree.
        if -age > panels.FUTURE_SKEW_TOLERANCE_S:
            return {"state": STATE_MALFORMED, "age_s": None,
                    "stale_after_s": budget, "generated_at": stamped,
                    "detail": (f"the loop dated this report {-age:.0f}s IN THE "
                               "FUTURE; a future timestamp cannot age, so it is "
                               "treated as undated rather than as fresh")}
        age = 0.0
    fresh = age <= budget
    return {
        "state": STATE_FRESH if fresh else STATE_STALE,
        "age_s": round(age, 1),
        "stale_after_s": budget,
        "generated_at": stamped,
        "detail": ("current" if fresh else
                   f"last heard from the loop {age / 60:.1f} min ago, past its "
                   f"own {budget / 60:.0f} min envelope — the reading below is "
                   "the loop's LAST report, not its current state"),
    }


def notice(report: Mapping[str, Any], fresh: Mapping[str, Any]) -> dict:
    """Fold freshness AND the run's declared lifecycle into ONE banner verdict.

    Six outcomes, and the two that freshness alone cannot reach are the point:

      * ``finished`` — the run DECLARED ``complete``. Its silence afterwards is
        compliance, not an outage. A STOP sentinel lands here: the loop drains
        the current iteration and exits through the same path, so "the operator
        stopped it" and "it ran out of planned iterations" are the same
        producer-visible fact and neither is a fault.
      * ``failed``   — the run DECLARED ``failed``. It published on the way out,
        so this reading can be perfectly FRESH and the run perfectly dead.
        Freshness alone draws no banner here at all.

    Lifecycle wins over staleness because a declared end explains the silence;
    an undeclared silence does not explain itself. ``absent`` and ``malformed``
    win over both, because with no trustworthy body there is no declared state
    to believe.
    """
    state = fresh.get("state")
    if state == STATE_ABSENT:
        return {"kind": NOTICE_ABSENT, "run_state": None,
                "detail": fresh.get("detail")}
    if state == STATE_MALFORMED:
        return {"kind": NOTICE_MALFORMED, "run_state": None,
                "detail": fresh.get("detail")}
    body = report.get("body") or {}
    run_state = body.get("state")
    run_state = str(run_state) if run_state is not None else None
    if run_state == RUN_FAILED:
        return {"kind": NOTICE_FAILED, "run_state": run_state,
                "detail": ("the loop DECLARED state=failed and published on its "
                           "way out. This reading may be perfectly fresh; the "
                           "run is over and it ended badly.")}
    if run_state == RUN_COMPLETE:
        return {"kind": NOTICE_FINISHED, "run_state": run_state,
                "detail": ("the loop DECLARED state=complete: it finished the "
                           "iteration it was on and exited. Everything below is "
                           "its FINAL report — a finished run, not a lost "
                           "producer. A STOP sentinel ends a run this way too, "
                           "so this is also what an operator-stopped run looks "
                           "like.")}
    if state == STATE_STALE:
        return {"kind": NOTICE_STALE, "run_state": run_state,
                "detail": fresh.get("detail")}
    return {"kind": NOTICE_NONE, "run_state": run_state, "detail": None}


def _gpu(body: Mapping[str, Any]) -> dict:
    """Held seconds against busy seconds — or an honest "not reported".

    The loop held a device 95.4% idle for a month and nothing reported it,
    because the old surface reported iterations and receipts. But an EMPTY gpu
    map must not be folded into "0s busy, 100% idle": that would be a fabricated
    measurement, which is worse than the silence it replaces. Absent inputs
    yield ``reported: false`` and no numbers.
    """
    raw = body.get("gpu")
    raw = dict(raw) if isinstance(raw, Mapping) else {}

    def _num(*names):
        for name in names:
            value = raw.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if value != value:  # NaN
                continue
            return float(value)
        return None

    held = _num(*HELD_KEYS)
    busy = _num(*BUSY_KEYS)
    out = {"reported": held is not None and busy is not None,
           "held_s": held, "busy_s": busy, "idle_s": None, "busy_pct": None,
           "raw": raw, "unreported_reason": None}
    if not out["reported"]:
        # WHY nothing is reported is a different fact depending on who is at
        # fault, and a page that says "the loop published no held/busy seconds"
        # over a loop that published four of them is making a false claim about
        # the producer. Three cases, named apart:
        if not raw:
            out["unreported_reason"] = (
                "the loop published no gpu map at all")
        elif not any(key in raw for key in HELD_KEYS + BUSY_KEYS):
            out["unreported_reason"] = (
                "the loop published a gpu map, but this reader recognises none "
                f"of its keys ({', '.join(sorted(raw))}) as held or busy "
                "seconds — that is a READER defect, not a silent producer")
        else:
            missing = [name for name, value in (("held", held), ("busy", busy))
                       if value is None]
            out["unreported_reason"] = (
                f"the loop published a gpu map with no usable "
                f"{' and '.join(missing)} seconds (present keys: "
                f"{', '.join(sorted(raw))})")
    if out["reported"] and held > 0:
        out["idle_s"] = round(max(0.0, held - busy), 1)
        out["busy_pct"] = round(100.0 * min(busy, held) / held, 1)
    elif out["reported"]:
        # Held for zero seconds: nothing to be a percentage OF.
        out["idle_s"] = 0.0
    return out


def summarize(body: Mapping[str, Any]) -> dict:
    """Derived view fields — folds, never new claims."""
    dispositions = body.get("dispositions")
    dispositions = dict(dispositions) if isinstance(dispositions, Mapping) else {}
    counts = {key: int(value) for key, value in dispositions.items()
              if isinstance(value, (int, float)) and not isinstance(value, bool)}
    kept = counts.get("kept", 0)
    total = sum(counts.values())
    measured = sum(counts.get(key, 0) for key in MEASURED_DISPOSITIONS)
    planned = body.get("iterations_planned")
    done = body.get("iterations_done")
    remaining = None
    if isinstance(planned, int) and isinstance(done, int):
        remaining = max(0, planned - done)
    return {
        "kept": kept,
        # Everything that is NOT a keep. On the page beside the keeps, always:
        # a board that shows only wins is how 0 promotions looked like progress
        # for a month.
        "negatives": max(0, total - kept),
        "measured": measured,
        "never_measured": max(0, total - measured),
        "iterations_remaining": remaining,
        "gpu": _gpu(body),
    }


def observation(report: Mapping[str, Any], fresh: Mapping[str, Any]
                ) -> panels.Observation:
    """The panel-registry observation for this reading.

    ``silence_budget_s`` hands the PRODUCER'S declared cadence to the envelope,
    so the hub does not hold a second, drifting opinion about when this loop is
    late. The watermark is the loop's progress identity: a producer that keeps
    rewriting its status with fresh timestamps and an unmoving iteration count
    is alive enough to publish and dead enough to make no progress.
    """
    body = report.get("body")
    if body is None:
        if not report.get("artifact_present"):
            return panels.absent(panels.source("autokernel_loop"), ABSENCE_MEANS)
        return panels.Observation(
            artifact_present=True, timestamp=None, source=None,
            detail=fresh.get("detail"), evidence=report.get("path"))
    timestamp = _stamp_epoch(body.get("generated_at"))
    state = str(body.get("state") or "unknown")
    if timestamp is None:
        return panels.Observation(
            artifact_present=True, timestamp=None, source=state,
            detail=fresh.get("detail"), evidence=report.get("path"))
    return panels.Observation(
        artifact_present=True,
        timestamp=timestamp,
        source=state,
        populated=bool(body.get("iterations_done")),
        detail=fresh.get("detail"),
        evidence=report.get("path"),
        watermark=(f"{state}|{body.get('iterations_done')}|"
                   f"{body.get('measurements_reached')}|{body.get('champion_head')}"),
        # A loop that has DECLARED it finished is allowed to be silent. A loop
        # that declared it FAILED is not treated as idle here: its silence is
        # expected, but so is an operator being told about it, and the data
        # probe raises `failed` to degraded on its own (see server.loop_data_health).
        producer_idle=(state == "complete"),
        silence_budget_s=_budget(body),
    )


# --------------------------------------------------------------------------- #
# THE CHAMPION HEADLINE — one number, one named anchor, allowed to be absent
# --------------------------------------------------------------------------- #
# THE RULING (operator, 2026-08-30): "the champion headline number shown should
# JUST BE THE COLLECTIVE PERFORMANCE GAIN VS FROZEN PRODUCTION KERNEL", with the
# capabilities that tree enables listed beside it. One number. One anchor.
#
# WHY THIS NEEDED A RULING. The page carried a +48.9% in its largest type, from
# the operator-gated manual-research bundle, beside a loop whose own champion
# was worth roughly a tenth of that by its own A/B. Different producers,
# different anchors, different questions — displayed side by side with nothing
# saying so, and the operator reasonably asked why the champion said +48.9% when
# they had been told +9%. A percentage with no named anchor is not a small
# labelling fault; it is the whole defect.
#
# WHY THIS SLOT IS ALLOWED TO BE EMPTY, AND WHY THAT IS THE CORRECT SHAPE.
# Whenever no direct A/B exists for the current champion, nothing may stand in
# for it: the per-iteration effects are MARGINALS against an anchor that
# advances on every keep — different baselines, one per keep — and composing
# them arithmetically would manufacture a measurement no run ever took. This
# program already made that error once. So an unmeasured slot renders NOT
# MEASURED and names what would fill it. An empty slot that says why is worth
# more than a number nobody measured. (Whether a bundle exists is a fact read
# from the store per request, never asserted here.)

# --------------------------------------------------------------------------- #
# THE ANCHOR IS RESOLVED, NEVER REMEMBERED
# --------------------------------------------------------------------------- #
# The headline is DEFINED as the gain over the frozen production kernel — but
# WHICH kernel that is, is a fact about the canonical frozen tree, not about
# this module. The first version of this reader remembered it as a constant
# (the v9 sha), which was exactly right until the first promotion and then
# exactly wrong in BOTH directions: a bundle correctly baselined on the newly
# promoted production would have been refused as malformed, and a stale
# v9-baselined bundle would have kept rendering as the current standing.
# Operator ruling (2026-08-31, near-verbatim): "Once we promote a new frozen
# version in the future, the comparison should be against the newly promoted
# version, NOT stale v9."
#
# So the current production commit is resolved LIVE from the frozen tree —
# `git rev-parse HEAD` plus the branch contract `scripts/session/
# verify_llama_cpp.sh` enforces (`production-consolidated-*`) — once per
# snapshot, never per field, and NEVER cached across requests (the module's own
# no-cache doctrine: a cached anchor can outlive a promotion). A resolution
# failure is its own explicit state on the wire (`production.resolved=False`
# with the reason), never a silent fallback to a remembered sha and never a
# crash of the payload: the rest of the page must still render.

#: Where the frozen production tree lives. Overridable for tests — the resolver
#: must be injectable so no unit test depends on the real host tree — and
#: resolved PER CALL, like ``STORE_ROOT_ENV``.
FROZEN_TREE_ENV = "AUTOKERNEL_FROZEN_TREE"
DEFAULT_FROZEN_TREE = Path("/mnt/raid0/llm/llama.cpp")

#: The branch shape the freeze contract enforces. The PREFIX is the contract;
#: the suffix (v9, v10, …) is the part promotions advance, so it is never
#: pinned here. The displayed label ("production-consolidated-v9" today) is the
#: branch name itself — derived, not remembered.
PRODUCTION_BRANCH_PREFIX = "production-consolidated-"

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")

PRODUCTION_UNRESOLVED_MEANS = (
    "the hub could not resolve WHICH kernel is currently the frozen production "
    "kernel, so nothing on this panel can be checked against it. This is a "
    "fact about the frozen tree or this host, not about the champion or its "
    "measurement — and it renders as its own state rather than falling back "
    "to a remembered sha, because a remembered sha is stale the day after a "
    "promotion.")


def frozen_tree() -> Path:
    """The canonical frozen production tree, resolved at call time."""
    return Path(os.environ.get(FROZEN_TREE_ENV) or DEFAULT_FROZEN_TREE)


def _git_read(tree: Path, *args: str) -> str:
    """One READ-ONLY git query against ``tree``. Raises on any failure.

    Read-only by construction: only ``rev-parse``/``branch`` queries are ever
    passed, because the frozen tree must never be written, fetched or checked
    out by this hub.
    """
    proc = subprocess.run(["git", "-C", str(tree), *args],
                          capture_output=True, text=True, timeout=10)
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip()
        message = message.splitlines()[0] if message else (
            f"exit status {proc.returncode}")
        raise RuntimeError(f"git {' '.join(args)}: {message}")
    return proc.stdout.strip()


def resolve_production(tree: Optional[Path] = None) -> dict:
    """``{resolved, commit, branch, label, tree, error}`` for the frozen tree.

    ``resolved`` is True only when HEAD is a full commit AND the tree sits on a
    ``production-consolidated-*`` branch — the same contract
    ``verify_llama_cpp.sh`` enforces at session start. Any other outcome
    (missing tree, git error, detached HEAD, off-contract branch) carries the
    reason in ``error`` and resolves NOTHING: there is deliberately no
    hardcoded sha to fall back to.
    """
    tree = frozen_tree() if tree is None else Path(tree)
    out = {"resolved": False, "commit": None, "branch": None, "label": None,
           "tree": str(tree), "error": None}
    if not (tree / ".git").exists():
        out["error"] = (f"the frozen production tree is not a git repository "
                        f"at {tree} (no .git) — the canonical tree is missing "
                        "from this host or the hub is misconfigured")
        return out
    try:
        commit = _git_read(tree, "rev-parse", "HEAD")
        branch = _git_read(tree, "branch", "--show-current")
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        out["error"] = f"git could not read the frozen production tree: {exc}"
        return out
    if not _FULL_SHA.fullmatch(commit):
        out["error"] = (f"the frozen tree's HEAD resolved to {commit!r}, not a "
                        "full 40-hex commit")
        return out
    out["commit"] = commit
    out["branch"] = branch or None
    if not branch:
        out["error"] = (f"the frozen production tree at {tree} is on a "
                        f"DETACHED HEAD, not a {PRODUCTION_BRANCH_PREFIX}* "
                        "branch — off the freeze contract, so its HEAD cannot "
                        "be trusted to be the production kernel")
        return out
    if not branch.startswith(PRODUCTION_BRANCH_PREFIX):
        out["error"] = (f"the frozen production tree at {tree} is on branch "
                        f"{branch!r}, not a {PRODUCTION_BRANCH_PREFIX}* branch "
                        "— off the freeze contract, so its HEAD cannot be "
                        "trusted to be the production kernel")
        return out
    #: The label is the branch name — "production-consolidated-v9" today,
    #: "-v10" the day after a promotion, with no edit to this module.
    out["label"] = branch
    out["resolved"] = True
    return out

#: Where the champion BRANCH lives. The single-champion invariant (ratified
#: 2026-08-31, OPERATING_CONSTRAINTS.md: one champion per production kernel tree)
#: makes the BRANCH TIP the definition of "the current champion". The loop status
#: file's `champion_head` is one RUN's view and outlives the run: run 20's dying
#: status named its own (pre-reconciliation) branch tip while the merge moved the
#: champion, and this panel called a fresh measurement of the REAL champion
#: superseded. Branch-pattern check, not a pinned name: the canonical branch is
#: renamed at each production promotion (`ak/champion/<tree>-<anchor12>`).
CHAMPION_BRANCH_PREFIX = "ak/champion/"


CHAMPION_TREE_ENV = "AUTOKERNEL_CHAMPION_TREE"


def champion_tree() -> Path:
    return Path(os.environ.get(CHAMPION_TREE_ENV, "/mnt/raid0/llm/tmp/champ2"))


def resolve_champion(tree: Optional[Path] = None) -> dict:
    """``{resolved, commit, branch, error}`` for the champion branch tip.

    Same contract shape as :func:`resolve_production`, same refusal to fall
    back to a remembered sha. ``resolved`` requires an attached HEAD on an
    ``ak/champion/*`` branch.
    """
    tree = champion_tree() if tree is None else Path(tree)
    out = {"resolved": False, "commit": None, "branch": None,
           "tree": str(tree), "error": None}
    if not (tree / ".git").exists():
        out["error"] = f"no champion worktree at {tree} (no .git)"
        return out
    try:
        commit = _git_read(tree, "rev-parse", "HEAD")
        branch = _git_read(tree, "branch", "--show-current")
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        out["error"] = f"git could not read the champion tree: {exc}"
        return out
    if not _FULL_SHA.fullmatch(commit):
        out["error"] = f"champion HEAD resolved to {commit!r}, not a full sha"
        return out
    out["commit"] = commit
    out["branch"] = branch or None
    if not branch or not branch.startswith(CHAMPION_BRANCH_PREFIX):
        out["error"] = (f"the champion tree at {tree} is on "
                        f"{branch or 'a DETACHED HEAD'!s}, not an "
                        f"{CHAMPION_BRANCH_PREFIX}* branch — its HEAD cannot "
                        "be trusted to be the champion")
        return out
    out["resolved"] = True
    return out


#: The four relationship verdicts between a MEASURED commit and the CURRENT
#: champion tip. Distinct on purpose: "its work is in the champion" and "it is
#: a different tree" are opposite claims, and the line that renders them went
#: stale precisely because it was worded as a constant instead of computed.
REL_TIP = "tip"
REL_ANCESTOR = "ancestor"
REL_DIVERGENT = "divergent"
REL_UNRESOLVABLE = "unresolvable"
RELATIONS = (REL_TIP, REL_ANCESTOR, REL_DIVERGENT, REL_UNRESOLVABLE)


def champion_relationship(measured: Optional[str],
                          tree: Optional[Path] = None) -> dict:
    """How ``measured`` relates to the CURRENT champion — computed, never worded.

    THE SCAR THIS EXISTS FOR: the operator-gated card's scope line asserted
    "a different tree" as prose. It was written when the bundle's commit and the
    loop's champion_head disagreed, and it kept rendering after a reconciliation
    merge made the measured commit a PARENT of the champion — same lineage, the
    exact opposite of the claim. A relationship between two commits is a git
    fact (`merge-base --is-ancestor`, a read); a sentence typed at commit time
    is a memory of one reading of it.

    Four verdicts, each earned per call:

      * ``tip``          — ``measured`` IS the champion branch tip.
      * ``ancestor``     — ``measured`` is in the tip's history: its work is IN
                           the current champion.
      * ``divergent``    — the tree answered, and ``measured`` is NOT in the
                           tip's history: genuinely a different line of work.
      * ``unresolvable`` — no verdict could be computed (no measured commit, an
                           unresolvable champion tree, or a commit git cannot
                           find), with the reason. NEVER folded into
                           ``divergent``: "we cannot say" is not "it is
                           different".
    """
    tip = resolve_champion(tree)
    out = {"relation": REL_UNRESOLVABLE, "measured": measured,
           "current_champion": tip.get("commit"),
           "champion_branch": tip.get("branch"),
           "champion_source": "the champion branch tip",
           "detail": None}
    if not measured or not _FULL_SHA.fullmatch(str(measured)):
        out["detail"] = (f"the bundle names no full 40-hex measured commit "
                         f"(got {measured!r}), so its relationship to the "
                         "current champion cannot be established")
        return out
    if not tip.get("resolved"):
        out["detail"] = (f"the current champion cannot be resolved right now "
                         f"({tip.get('error')}), so the relationship cannot "
                         "be established")
        return out
    if measured == tip["commit"]:
        out["relation"] = REL_TIP
        out["detail"] = "the measured commit IS the current champion tip"
        return out
    # One READ-ONLY ancestry query against the champion tree. Exit 0 = ancestor,
    # exit 1 = not an ancestor — a real answer, not a failure — anything else
    # (e.g. a commit this tree has never seen) is no verdict at all.
    try:
        proc = subprocess.run(
            ["git", "-C", str(champion_tree() if tree is None else Path(tree)),
             "merge-base", "--is-ancestor", str(measured), tip["commit"]],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        out["detail"] = (f"git could not answer the ancestry query: {exc}")
        return out
    if proc.returncode == 0:
        out["relation"] = REL_ANCESTOR
        out["detail"] = ("the measured commit is an ancestor of the current "
                         "champion: its work is IN the current champion")
    elif proc.returncode == 1:
        out["relation"] = REL_DIVERGENT
        out["detail"] = ("the measured commit is NOT in the current champion's "
                         "history — a genuinely different line of work")
    else:
        message = (proc.stderr or proc.stdout or "").strip()
        out["detail"] = (f"git could not answer the ancestry query "
                         f"({message.splitlines()[0] if message else 'exit ' + str(proc.returncode)}), "
                         "so the relationship cannot be established")
    return out


CHAMPION_SCHEMA = "epyc.autokernel.champion_vs_production.v1"
CHAMPION_FILENAME = "champion-vs-production.json"
#: A cumulative A/B is a deliberate, expensive act, not a per-iteration beat, so
#: the envelope is days rather than minutes. The producer still owns the number
#: inside the same clamps every other contract on this page is held to.
CHAMPION_DEFAULT_STALE_AFTER_S = 14 * 86400.0

CHAMPION_ABSENCE_MEANS = (
    "no direct A/B of the champion tree against the frozen production kernel "
    "has ever been published here. This is NOT 'the champion has no gain' and "
    "NOT 'the gain is zero' — it is 'the measurement this headline names has "
    "not been taken for this commit'.")

CHAMPION_NOT_COMPOSABLE = (
    "The per-iteration effects on this page are MARGINALS against an anchor "
    "that advances on every keep, so each one has a different baseline. They "
    "must never be summed, multiplied or otherwise composed into a cumulative "
    "figure: a composed number would claim a measurement no run ever took. "
    "This headline can only ever come from one direct A/B.")


def _champion_would_populate(path: Path, production: Mapping[str, Any]) -> str:
    if production.get("resolved"):
        anchor = (f"the frozen production kernel "
                  f"{str(production.get('commit'))[:12]} "
                  f"({production.get('label')})")
    else:
        # No remembered sha stands in for a failed resolution — the sentence
        # says the anchor is currently unresolvable rather than naming a
        # kernel that may already be superseded.
        anchor = ("the CURRENT frozen production kernel (unresolvable right "
                  "now — see the resolution failure on this card)")
    return (f"one direct A/B — the champion commit built and benched against "
            f"{anchor} on the loop's own surface and pair "
            f"count, both arms measured in the same session — published as "
            f"{CHAMPION_SCHEMA} at {path}.")


#: Why the capability list cannot be sourced today, stated as what was CHECKED
#: rather than as a shrug — three candidate sources, each rejected for a reason
#: that survives being looked up:
#:
#:   * the loop's build recipe (``autokernel.controller.build_recipe``) declares
#:     four flags, all matching production by construction ("Matches production
#:     on every flag"), so a list derived from it would render EMPTY — and empty
#:     reads as "this tree enables nothing", which is a claim, and a false one;
#:   * a flag DIFF against production cannot be computed either: that module
#:     sets ``PRODUCTION_RECIPE_IS_VERIFIABLE = False`` and the frozen tree's
#:     build directory carries no ``CMakeCache.txt``, so production's own recipe
#:     is not recoverable from disk;
#:   * the anchor build's ``CMakeCache.txt`` names how ONE build was compiled and
#:     carries no commit attribution, so nothing ties it to a champion.
#:
#: Nothing anywhere under the campaign's store or surface records a feature list
#: for the champion tree — there is no FlashAttention2 record of any kind — so a
#: list typed here would be a memory wearing a measurement's clothes.
CHAMPION_CAPABILITIES_UNKNOWN = (
    "no producer attributes a capability list to a champion commit. The "
    "champion-vs-production contract carries an optional `capabilities` array "
    "and none has been published. Build flags are not a substitute: the loop's "
    "recipe declares zero divergences from production by construction, so a "
    "list derived from it would be empty — and empty would read as 'this tree "
    "enables nothing' rather than 'nobody has said' — and a flag DIFF is not "
    "computable either, because production's own recipe is not recoverable from "
    "disk (the recipe module declares it unverifiable and the frozen build "
    "directory has no CMakeCache).")

CHAMPION_CAPABILITIES_WOULD_POPULATE = (
    "a `capabilities` array in the champion-vs-production bundle: one entry per "
    "capability, each naming the evidence that establishes it (the commit, the "
    "gate, or the artifact). Typed here by hand it would be a memory, not a "
    "measurement.")


def champion_path(root: Optional[Path] = None) -> Path:
    return (store_root() if root is None else Path(root)) / CHAMPION_FILENAME


def read_champion(root: Optional[Path] = None) -> dict:
    """``{artifact_present, body, reader_error}`` for the champion A/B bundle.

    The same three-outcome shape as :func:`read`, for the same reason: a file
    nobody ever wrote and a file somebody wrote badly point at different
    subsystems and must not share a rendering.
    """
    path = champion_path(root)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"artifact_present": False, "body": None, "reader_error": None,
                "path": str(path)}
    except OSError as exc:
        return {"artifact_present": path.exists(), "body": None,
                "reader_error": f"champion bundle unreadable: {exc}",
                "path": str(path)}
    if not raw.strip():
        return {"artifact_present": True, "body": None,
                "reader_error": ("the champion bundle is empty (0 bytes of "
                                 "content) — a writer created it and never "
                                 "finished it"),
                "path": str(path)}
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"artifact_present": True, "body": None,
                "reader_error": f"the champion bundle is not valid JSON: {exc}",
                "path": str(path)}
    if not isinstance(body, dict):
        return {"artifact_present": True, "body": None,
                "reader_error": "the champion bundle is not a JSON object",
                "path": str(path)}
    schema = body.get("schema")
    if schema != CHAMPION_SCHEMA:
        return {"artifact_present": True, "body": None,
                "reader_error": (f"the champion bundle declares schema "
                                 f"{schema!r}, not {CHAMPION_SCHEMA!r} — its "
                                 "field names would not mean what this headline "
                                 "says they mean"),
                "path": str(path)}
    baseline = body.get("baseline")
    baseline = baseline if isinstance(baseline, Mapping) else {}
    measured_against = baseline.get("commit")
    if not isinstance(measured_against, str) \
            or not _FULL_SHA.fullmatch(measured_against):
        # MALFORMED, and deliberately narrower than the first version of this
        # check. A bundle that names NO full baseline commit is a percentage
        # whose anchor cannot be identified — it can be neither verified
        # current nor honestly marked superseded, so it is refused as the
        # emitter's fault. A bundle that names a full commit which is NOT the
        # current production is a DIFFERENT case: it is honest about what it
        # measured, and it renders downstream as SUPERSEDED-BASELINE rather
        # than being refused — refusing it is exactly how a hardcoded anchor
        # would have rejected the first correct post-promotion bundle.
        return {"artifact_present": True, "body": None,
                "reader_error": (
                    f"the champion bundle names no full 40-hex baseline "
                    f"commit (got {measured_against!r}) — a comparison whose "
                    f"anchor cannot be identified cannot be shown under this "
                    f"headline, verified current, or marked superseded"),
                "path": str(path)}
    return {"artifact_present": True, "body": body, "reader_error": None,
            "path": str(path)}


def _champion_budget(body: Mapping[str, Any]) -> float:
    raw = body.get("stale_after_s")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return CHAMPION_DEFAULT_STALE_AFTER_S
    if isinstance(raw, bool) or value != value or value in (
            float("inf"), float("-inf")) or value <= 0:
        return CHAMPION_DEFAULT_STALE_AFTER_S
    return max(MIN_STALE_AFTER_S, min(value, float(panels.MAX_STALE_S)))


def champion_freshness(report: Mapping[str, Any], *,
                       now: Optional[float] = None) -> dict:
    """The same four-valued verdict as the loop's, over the champion bundle.

    Same vocabulary on purpose — ``fresh``/``stale``/``absent``/``malformed``,
    the words the loop badge and the operator-gate badge already use. Three
    producers on one page saying "stale" three different ways is a page nobody
    can read at a glance.
    """
    now = time.time() if now is None else float(now)
    body = report.get("body")
    if body is None:
        if not report.get("artifact_present"):
            return {"state": STATE_ABSENT, "age_s": None, "stale_after_s": None,
                    "generated_at": None, "detail": CHAMPION_ABSENCE_MEANS}
        return {"state": STATE_MALFORMED, "age_s": None, "stale_after_s": None,
                "generated_at": None,
                "detail": (report.get("reader_error")
                           or "a champion bundle exists but could not be read "
                              "as this contract")}
    stamped = body.get("generated_at")
    written = _stamp_epoch(stamped)
    budget = _champion_budget(body)
    if written is None:
        return {"state": STATE_MALFORMED, "age_s": None, "stale_after_s": budget,
                "generated_at": stamped,
                "detail": (f"unparseable generated_at {stamped!r} — a "
                           "measurement nobody can date cannot be shown as the "
                           "current standing")}
    age = now - written
    if age < 0:
        if -age > panels.FUTURE_SKEW_TOLERANCE_S:
            return {"state": STATE_MALFORMED, "age_s": None,
                    "stale_after_s": budget, "generated_at": stamped,
                    "detail": (f"this measurement is dated {-age:.0f}s IN THE "
                               "FUTURE; a future timestamp cannot age, so it is "
                               "treated as undated rather than as fresh")}
        age = 0.0
    fresh = age <= budget
    return {
        "state": STATE_FRESH if fresh else STATE_STALE,
        "age_s": round(age, 1),
        "stale_after_s": budget,
        "generated_at": stamped,
        "detail": ("current" if fresh else
                   f"this A/B was measured {age / 86400:.1f} d ago, past its "
                   f"own {budget / 86400:.1f} d envelope — it is the LAST "
                   "champion-vs-production measurement, not a current one"),
    }


def _champion_capabilities(body: Optional[Mapping[str, Any]]) -> dict:
    """The capability list, or an honest "nobody has said" with the reason.

    Entries are the producer's, verbatim: ``{"name", "evidence"}``. Nothing is
    inferred and nothing is defaulted — a capability the page invents is worse
    than a capability nobody listed, because it cannot be traced back to a
    commit when someone asks how we know.
    """
    out = {"known": False, "source": None, "items": [],
           "unknown_reason": CHAMPION_CAPABILITIES_UNKNOWN,
           "would_populate": CHAMPION_CAPABILITIES_WOULD_POPULATE}
    raw = body.get("capabilities") if body is not None else None
    if not isinstance(raw, (list, tuple)):
        if body is not None and raw is not None:
            out["unknown_reason"] = (
                "the champion bundle carries a `capabilities` field that is not "
                "a list, so this reader cannot enumerate it; the emitter's "
                "writer is at fault, not the absence of evidence.")
        return out
    items = []
    for entry in raw:
        if isinstance(entry, Mapping):
            name = entry.get("name")
            evidence = entry.get("evidence")
        else:
            name, evidence = entry, None
        if name is None or not str(name).strip():
            continue
        items.append({"name": str(name),
                      "evidence": None if evidence is None else str(evidence)})
    out["items"] = items
    out["source"] = f"{CHAMPION_SCHEMA} `capabilities`"
    if not items:
        # DECLARED EMPTY is not UNKNOWN. The producer published the array and
        # put nothing in it; that is a statement, and it is a different one from
        # never having been asked.
        out["known"] = True
        out["unknown_reason"] = None
        out["would_populate"] = None
        return out
    out["known"] = True
    out["unknown_reason"] = None
    out["would_populate"] = None
    return out


def champion_snapshot(root: Optional[Path] = None, *,
                      now: Optional[float] = None,
                      champion_head: Optional[str] = None,
                      production: Optional[Mapping[str, Any]] = None,
                      champion: Optional[Mapping[str, Any]] = None) -> dict:
    """The wire block for the champion headline.

    ``champion_head`` is the loop's CURRENT champion, passed in rather than
    re-read, so the page can say whether the measurement it is showing is even
    about the tree the loop is running. A cumulative A/B is expensive and the
    champion advances on every keep, so "measured, but three keeps ago" is the
    normal case and must be visible — a number that silently re-anchors to
    whatever the champion is today is the same defect one level down.

    ``production`` is a pre-resolved :func:`resolve_production` block, for
    callers (and tests) that already hold one; by default it is resolved here,
    ONCE per snapshot — never per field, and never cached across requests.
    The same supersession logic then runs on the OTHER side of the comparison:
    a bundle whose baseline is no longer the current production kernel is
    honest about what it measured and renders as SUPERSEDED-BASELINE — dated,
    both commits named — not refused and not fresh.
    """
    prod = dict(production) if production is not None else resolve_production()
    tip = dict(champion) if champion is not None else resolve_champion()
    report = read_champion(root)
    fresh = champion_freshness(report, now=now)
    body = report.get("body")
    path = champion_path(root)

    effect = None
    if body is not None:
        raw = body.get("effect_fraction")
        if isinstance(raw, (int, float)) and not isinstance(raw, bool) \
                and raw == raw and raw not in (float("inf"), float("-inf")):
            effect = float(raw)

    measured_commit = None
    if body is not None:
        champ = body.get("champion")
        champ = champ if isinstance(champ, Mapping) else {}
        measured_commit = champ.get("commit")
        measured_commit = str(measured_commit) if measured_commit else None

    # WHO defines "the current champion": the BRANCH TIP when it resolves (the
    # single-champion invariant — the tip IS the champion), and only failing
    # that, the loop status file's champion_head, which is one run's view and
    # OUTLIVES the run. Deciding against the status file while a reconciliation
    # merge moved the branch made this panel call a fresh measurement of the
    # real champion "superseded" — inverted, with the truth one rev-parse away.
    supersession = None
    if tip.get("resolved"):
        current, current_src = tip["commit"], "the champion branch tip"
    else:
        current, current_src = champion_head, "the last loop run's status"
    if measured_commit and current and measured_commit != current:
        supersession = {
            "measured_for": measured_commit,
            "current_champion": current,
            "current_champion_source": current_src,
            "detail": (
                f"this A/B measured champion {measured_commit[:12]}; the "
                f"current champion per {current_src} is {str(current)[:12]}. "
                f"The number stands for the tree it measured and for no other. "
                f"The commits added since were screened as marginals against "
                f"an advancing anchor and cannot be added to it."),
        }

    # THE OTHER SIDE OF THE SAME COIN, and orthogonal to it on purpose: the
    # champion supersession above says the MEASURED arm has moved on; this one
    # says the ANCHOR has. A bundle can be champion-superseded,
    # baseline-superseded, both, or neither, and the page must be able to say
    # which. ``baseline_check`` is the server-side fold, so a test executes it
    # instead of re-deriving it from three fields:
    #   * ``current``      — the bundle's anchor IS the resolved production;
    #   * ``superseded``   — production has been promoted past the bundle's
    #                        anchor (or the bundle was never anchored on a
    #                        production kernel at all — either way the number
    #                        does not answer "gain over CURRENT production");
    #   * ``unverifiable`` — production did not resolve, so no comparison can
    #                        be made in either direction;
    #   * ``None``         — no readable bundle to check.
    bundle_baseline = {}
    if body is not None:
        raw_baseline = body.get("baseline")
        bundle_baseline = (dict(raw_baseline)
                           if isinstance(raw_baseline, Mapping) else {})
    measured_baseline = bundle_baseline.get("commit")

    baseline_check = None
    baseline_supersession = None
    if body is not None:
        if not prod.get("resolved"):
            baseline_check = "unverifiable"
        elif measured_baseline == prod.get("commit"):
            baseline_check = "current"
        else:
            baseline_check = "superseded"
            measured_label = bundle_baseline.get("label")
            baseline_supersession = {
                "measured_against": measured_baseline,
                "measured_label": measured_label,
                "current_production": prod.get("commit"),
                "current_label": prod.get("label"),
                "detail": (
                    f"this A/B was measured against production kernel "
                    f"{str(measured_baseline)[:12]}"
                    + (f" ({measured_label})" if measured_label else "")
                    + f", which has since been superseded by a promotion: the "
                    f"frozen production kernel is now "
                    f"{str(prod.get('commit'))[:12]} ({prod.get('label')}). "
                    f"The number stands for the comparison it made and for no "
                    f"other — only a new direct A/B against "
                    f"{prod.get('label')} can say what the champion is worth "
                    f"over CURRENT production."),
            }

    # The anchor printed beside the number. For a readable bundle it is the
    # bundle's OWN declared anchor — what was actually measured, even when that
    # anchor is superseded — because relabelling a measurement with today's
    # production would claim a comparison nobody ran. With no readable bundle
    # it is the resolved current production (the anchor a measurement WOULD be
    # against), and with no resolution either, it is honestly empty.
    if body is not None:
        shown_baseline = {"commit": measured_baseline,
                          "label": bundle_baseline.get("label"),
                          "kind": "frozen production kernel",
                          "source": "the bundle's own declared anchor"}
    elif prod.get("resolved"):
        shown_baseline = {"commit": prod.get("commit"),
                          "label": prod.get("label"),
                          "kind": "frozen production kernel",
                          "source": "resolved live from the frozen tree"}
    else:
        shown_baseline = {"commit": None, "label": None,
                          "kind": "frozen production kernel",
                          "source": None}

    return {
        "schema": CHAMPION_SCHEMA,
        "evidence": str(path),
        "artifact_present": bool(report.get("artifact_present")),
        "reader_error": report.get("reader_error"),
        # `measured` is the whole question this panel answers, and it is False
        # for absent AND for malformed: a bundle the hub refused is not a
        # measurement it may show.
        "measured": body is not None and effect is not None,
        "freshness": fresh,
        # The anchor is stated on EVERY reading, present or not. The headline is
        # a claim about a comparison; naming only one side of it is how a
        # percentage becomes unreadable.
        "baseline": shown_baseline,
        # The RESOLVED current production kernel — or the explicit reason it
        # could not be resolved. Never a remembered sha.
        "production": prod,
        "production_unresolved_means": (
            None if prod.get("resolved") else PRODUCTION_UNRESOLVED_MEANS),
        "baseline_check": baseline_check,
        "baseline_supersession": baseline_supersession,
        "champion": {"measured_commit": measured_commit,
                     "loop_champion_head": champion_head,
                     "branch_tip": tip.get("commit"),
                     "branch": tip.get("branch"),
                     "tip_error": tip.get("error")},
        "supersession": supersession,
        "effect_fraction": effect,
        "metric": (body or {}).get("metric"),
        "metric_direction": (body or {}).get("metric_direction"),
        "surface": (body or {}).get("surface"),
        "pairs": (body or {}).get("pairs"),
        "noise_floor_pct": (body or {}).get("noise_floor_pct"),
        "measurement_evidence": (body or {}).get("evidence"),
        "capabilities": _champion_capabilities(body),
        "absence_means": CHAMPION_ABSENCE_MEANS,
        "would_populate": _champion_would_populate(path, prod),
        "not_composable": CHAMPION_NOT_COMPOSABLE,
    }


# --------------------------------------------------------------------------- #
# THE LOOP'S ACCUMULATED KNOWLEDGE — the memory store, read as a FOURTH producer
# --------------------------------------------------------------------------- #
# The operator: "I still don't see a card tracking autokernel's generated
# actionable knowledge and hypotheses tested/confirmed/falsified." The loop's
# memory store (`experiments.db`, sqlite, written by the loop itself) is that
# record: every attempt ever, its mechanism, and its disposition. This reader
# opens it READ-ONLY (`mode=ro` URI — the hub must never be able to write a
# producer's store), computes folds only, and carries its own four-valued
# freshness envelope from the db's mtime. It is a fourth producer on the page:
# the loop status card answers "is the loop alive"; this answers "what does the
# program KNOW".

KNOWLEDGE_DB_FILENAME = "experiments.db"

#: The envelope for the MEMORY, not for liveness. The loop's own status card
#: owns "is the loop running" on a minutes-scale budget; the memory store only
#: advances when an attempt lands, and a store that has not grown for a day is
#: dated knowledge, not an outage. The stale wording says exactly that.
KNOWLEDGE_STALE_AFTER_S = 86400.0

#: How many of the most recent keeps are named on the card, with their effects.
KNOWLEDGE_RECENT_KEPT = 5

#: The dispositions the card names first-class. Everything ELSE in the store is
#: folded into a no-scientific-verdict bucket that ENUMERATES its members —
#: never dropped, never silently merged into a named one.
KNOWLEDGE_PRIMARY_DISPOSITIONS = ("kept", "measured_null",
                                  "refused_at_formation", "superseded")

KNOWLEDGE_ABSENCE_MEANS = (
    "no memory store exists at this path — the loop has never recorded an "
    "attempt here. A missing count is not a zero: this page can say nothing "
    "about what the program has tried, kept or ruled out.")


def knowledge_path(root: Optional[Path] = None) -> Path:
    return (store_root() if root is None else Path(root)) / KNOWLEDGE_DB_FILENAME


def read_knowledge(root: Optional[Path] = None) -> dict:
    """Folds over the memory store — ``{artifact_present, body, reader_error}``.

    The same three-outcome shape as :func:`read`: a store nobody ever wrote and
    a store somebody wrote badly point at different subsystems. ``body`` holds
    ONLY folds computed from the producer's own rows — counts, groupings and
    the most recent keeps — never a row this reader invented.
    """
    path = knowledge_path(root)
    if not path.exists():
        return {"artifact_present": False, "body": None, "reader_error": None,
                "path": str(path), "mtime": None}
    try:
        mtime = path.stat().st_mtime
        # mode=ro: a read-only URI open. The hub must be INCAPABLE of writing a
        # producer's store, not merely polite about it.
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5.0)
        try:
            cur = con.cursor()
            total = cur.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]
            by_status = dict(cur.execute(
                "SELECT status, COUNT(*) FROM experiments GROUP BY status"
            ).fetchall())
            mech_distinct = cur.execute(
                "SELECT COUNT(DISTINCT mechanism_id) FROM experiments "
                "WHERE mechanism_id IS NOT NULL AND mechanism_id != ''"
            ).fetchone()[0]
            mech_revisited = cur.execute(
                "SELECT COUNT(*) FROM (SELECT mechanism_id FROM experiments "
                "WHERE mechanism_id IS NOT NULL AND mechanism_id != '' "
                "GROUP BY mechanism_id HAVING COUNT(*) >= 2)"
            ).fetchone()[0]
            recent_kept = [
                {"mechanism_id": row[0], "effect_fraction": row[1],
                 "recorded_at": row[2]}
                for row in cur.execute(
                    "SELECT mechanism_id, effect_fraction, recorded_at "
                    "FROM experiments WHERE status = 'kept' "
                    "ORDER BY recorded_at DESC LIMIT ?",
                    (KNOWLEDGE_RECENT_KEPT,)).fetchall()]
            window = cur.execute(
                "SELECT MIN(recorded_at), MAX(recorded_at) FROM experiments"
            ).fetchone()
        finally:
            con.close()
    except (OSError, sqlite3.Error) as exc:
        # Exists-but-unreadable (a corrupt db, a foreign schema, a permissions
        # fault) is MALFORMED, never absent and never a page of zeros: a zero
        # here would be a fabricated claim that the program tried nothing.
        return {"artifact_present": True, "body": None,
                "reader_error": (f"the memory store exists but could not be "
                                 f"read: {exc}"),
                "path": str(path),
                "mtime": None}
    body = {
        "attempts": int(total),
        "dispositions": {str(k): int(v) for k, v in by_status.items()},
        "mechanisms": {"distinct": int(mech_distinct),
                       "revisited": int(mech_revisited)},
        "recent_kept": recent_kept,
        "recorded_window": {"first": window[0], "last": window[1]},
    }
    return {"artifact_present": True, "body": body, "reader_error": None,
            "path": str(path), "mtime": mtime}


def _knowledge_groups(dispositions: Mapping[str, int]) -> dict:
    """The card's disposition split — a fold, so a test can execute it.

    The four primary dispositions are counted even at zero (the store reported,
    and there are none — a statement, not an absence). Every OTHER status the
    producer ever wrote lands in ``no_verdict`` WITH its own name and count:
    an attempt that hit a planner outage or a lane error produced no scientific
    verdict, but hiding it would overstate how much of the record is science.
    """
    named = {key: int(dispositions.get(key, 0))
             for key in KNOWLEDGE_PRIMARY_DISPOSITIONS}
    rest = {key: int(value) for key, value in sorted(dispositions.items())
            if key not in KNOWLEDGE_PRIMARY_DISPOSITIONS}
    named["no_verdict"] = {"total": sum(rest.values()), "by_status": rest}
    return named


def knowledge_freshness(report: Mapping[str, Any], *,
                        now: Optional[float] = None) -> dict:
    """Four-valued verdict over the store, dated by the db file's mtime.

    Same vocabulary as every other envelope on the page. The store carries no
    ``generated_at`` of its own — the file IS the record and every insert
    touches it — so mtime is the producer's own last-write fact here, not the
    weaker stand-in it is for a JSON bundle.
    """
    now = time.time() if now is None else float(now)
    if not report.get("artifact_present"):
        return {"state": STATE_ABSENT, "age_s": None,
                "stale_after_s": None, "detail": KNOWLEDGE_ABSENCE_MEANS}
    if report.get("body") is None:
        return {"state": STATE_MALFORMED, "age_s": None,
                "stale_after_s": None,
                "detail": (report.get("reader_error")
                           or "the memory store exists but could not be read")}
    mtime = report.get("mtime")
    if not isinstance(mtime, (int, float)):
        return {"state": STATE_MALFORMED, "age_s": None,
                "stale_after_s": None,
                "detail": "the memory store could not be dated (no mtime)"}
    age = max(0.0, now - float(mtime))
    fresh = age <= KNOWLEDGE_STALE_AFTER_S
    return {
        "state": STATE_FRESH if fresh else STATE_STALE,
        "age_s": round(age, 1),
        "stale_after_s": KNOWLEDGE_STALE_AFTER_S,
        "detail": ("current" if fresh else
                   f"no attempt has been recorded for {age / 86400:.1f} d — "
                   "the knowledge below is complete as of the store's last "
                   "write, not necessarily today's frontier"),
    }


def knowledge_snapshot(root: Optional[Path] = None, *,
                       now: Optional[float] = None) -> dict:
    """The wire block for the accumulated-knowledge card.

    Every count is ``None`` — never 0 — when there is nothing readable to
    count: a missing count is not a zero (the standing rule on this page), and
    a zero here would claim the program has tried nothing.
    """
    report = read_knowledge(root)
    fresh = knowledge_freshness(report, now=now)
    body = report.get("body")
    return {
        "source": "the loop's own memory store (sqlite, read-only)",
        "evidence": report.get("path"),
        "artifact_present": bool(report.get("artifact_present")),
        "reader_error": report.get("reader_error"),
        "freshness": fresh,
        "attempts": body["attempts"] if body else None,
        "mechanisms": body["mechanisms"] if body else None,
        "dispositions": body["dispositions"] if body else None,
        "groups": _knowledge_groups(body["dispositions"]) if body else None,
        "recent_kept": body["recent_kept"] if body else None,
        "recorded_window": body["recorded_window"] if body else None,
        "absence_means": KNOWLEDGE_ABSENCE_MEANS,
    }


def payload(root: Optional[Path] = None, *, now: Optional[float] = None) -> dict:
    """The wire payload for ``/api/loop``, minus the panel envelope.

    ``loop`` is ``None`` — never ``{}`` — when nothing readable was found.
    """
    return snapshot(root, now=now)[0]


def snapshot(root: Optional[Path] = None, *, now: Optional[float] = None
             ) -> tuple:
    """``(payload, observation)`` from ONE read of the file.

    One read, so the body the page renders and the body the health probe judges
    cannot be two different files written a second apart.
    """
    report = read(root)
    fresh = freshness(report, now=now)
    body = report.get("body")
    wire = {
        "schema": STATUS_SCHEMA,
        "evidence": report.get("path"),
        "store_root": str(store_root() if root is None else Path(root)),
        "artifact_present": bool(report.get("artifact_present")),
        "reader_error": report.get("reader_error"),
        "freshness_state": fresh["state"],
        "age_s": fresh["age_s"],
        "stale_after_s": fresh["stale_after_s"],
        "generated_at": fresh["generated_at"],
        "detail": fresh["detail"],
        "absence_means": ABSENCE_MEANS,
        # Freshness answers "is this report current"; `notice` answers "what
        # should the operator be told", and a finished run is the case where
        # those two disagree. Folded here, not in the page, so a test can
        # EXECUTE it instead of grepping the markup for a branch.
        "notice": notice(report, fresh),
        "loop": dict(body) if body is not None else None,
        "derived": summarize(body) if body is not None else None,
        # A THIRD producer, and it dates neither of the other two. It is read
        # here rather than in `server.loop_payload` only so that the loop's own
        # champion head — which lives in the body read one line above — can be
        # handed to it without a second read of the status file.
        "champion_vs_production": champion_snapshot(
            root, now=now,
            champion_head=(body or {}).get("champion_head")),
        # A FOURTH producer: the loop's accumulated knowledge, from its own
        # memory store, on its own envelope. It dates none of the other three
        # and none of them dates it.
        "knowledge": knowledge_snapshot(root, now=now),
    }
    return wire, observation(report, fresh)


__all__ = ["ABSENCE_MEANS", "BUSY_KEYS", "CHAMPION_ABSENCE_MEANS",
           "CHAMPION_CAPABILITIES_UNKNOWN",
           "CHAMPION_CAPABILITIES_WOULD_POPULATE",
           "CHAMPION_DEFAULT_STALE_AFTER_S", "CHAMPION_FILENAME",
           "CHAMPION_NOT_COMPOSABLE", "CHAMPION_SCHEMA",
           "DEFAULT_STALE_AFTER_S",
           "DEFAULT_STORE_ROOT", "DEFAULT_FROZEN_TREE", "FROZEN_TREE_ENV",
           "HELD_KEYS",
           "KNOWLEDGE_ABSENCE_MEANS", "KNOWLEDGE_DB_FILENAME",
           "KNOWLEDGE_PRIMARY_DISPOSITIONS", "KNOWLEDGE_RECENT_KEPT",
           "KNOWLEDGE_STALE_AFTER_S",
           "RELATIONS", "REL_ANCESTOR", "REL_DIVERGENT", "REL_TIP",
           "REL_UNRESOLVABLE",
           "MEASURED_DISPOSITIONS", "MIN_STALE_AFTER_S",
           "NOTICES", "NOTICE_ABSENT", "NOTICE_FAILED", "NOTICE_FINISHED",
           "NOTICE_MALFORMED", "NOTICE_NONE", "NOTICE_STALE",
           "PRODUCTION_BRANCH_PREFIX", "PRODUCTION_UNRESOLVED_MEANS",
           "RUN_COMPLETE", "RUN_FAILED", "RUN_RUNNING", "RUN_STARTING",
           "RUN_STATES", "STATES",
           "STATE_ABSENT", "STATE_FRESH", "STATE_MALFORMED", "STATE_STALE",
           "STATUS_FILENAME", "STATUS_SCHEMA", "STORE_ROOT_ENV",
           "champion_freshness", "champion_path", "champion_relationship",
           "champion_snapshot",
           "freshness", "frozen_tree", "knowledge_freshness", "knowledge_path",
           "knowledge_snapshot", "notice",
           "observation", "payload", "read", "read_champion", "read_knowledge",
           "resolve_champion", "resolve_production", "snapshot",
           "status_path", "store_root", "summarize"]
