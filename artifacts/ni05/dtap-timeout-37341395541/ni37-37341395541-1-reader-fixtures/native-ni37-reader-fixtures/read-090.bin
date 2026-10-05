"""Exception-reporting guard for the verbatim-transcribed DTAP judges (CJ-12).

WHY THIS FILE EXISTS
--------------------
Each `judges/<case_id>/judge.py` is a VERBATIM upstream transcription carried
under a per-file byte-identity attestation in `manifest.json`
(`upstream_judge_sha256` + `transcribed_judge_sha256`). Upstream's judges
swallow exceptions at 33 verdict-affecting `except` handlers, so a judge that
CRASHED returns the same `(False, metadata)` shape as a judge that deliberately
judged "no". The harness boundary already owns the right vocabulary
(`outcomes.JudgeFailure` / `OutcomeType.JUDGE`) but never sees the exception.

CJ-12 was ruled by the operator (2026-09-07, option 1): amend the transcription
contract to permit an exception-reporting WRAPPER while the judgment logic stays
byte-identical. The binding constraint is that upstream's bytes remain
SEPARATELY attestable, so this guard is a strictly EXTERNAL layer:

    judges/<case>/judge.py   upstream bytes, UNMODIFIED, still hashed on its own
    harness/judge_guard.py   ours, hashed on its own, never inlined into a judge

Nothing here edits, rewrites, patches, or re-emits judge source. The guard reads
each judge's AST (read-only) and observes its execution through `sys.settrace`.

HOW A SWALLOWED CRASH IS TOLD FROM A JUDGMENT
---------------------------------------------
Not every caught exception is a crash: upstream also uses `except` for genuine
control flow. The guard classifies every handler in the judge file STATICALLY,
from the untouched source, into exactly three kinds:

  NARROW      `except (ValueError, TypeError):` — upstream named the exception
              it expects. Typed control flow inside the judgment. NOT a crash.
  SUPPRESSING `except Exception: pass` (body is only pass/continue/break) —
              upstream explicitly chose to ignore the whole failure and record
              nothing from it. A deliberate suppression. NOT a crash.
  ESCALATING  any other broad handler (`except Exception:` / bare `except:`)
              whose body RETURNS a verdict, records an error message, or defaults
              a value the verdict is computed from. This is exactly the shape
              where a crash becomes a verdict. IS a crash.

At run time the guard watches only frames belonging to the judge file. When an
exception is raised in (or propagates into) such a frame, the guard resolves the
INNERMOST enclosing `try` in that frame whose handlers match the exception type
— i.e. the handler Python itself will run. If that handler is ESCALATING, the
guard records it and, once the judge method returns, raises `JudgeFailure`
instead of letting the swallowed verdict stand.

Escalation is DEFERRED to the call boundary on purpose: the trace function never
alters the judge's own control flow, so the upstream judgment executes exactly as
upstream wrote it. The guard only decides whether its RESULT is admissible.

VOCABULARY
----------
The typed outcome is the harness's existing `JudgeFailure` / `OutcomeType.JUDGE`
(`harness/outcomes.py`); no parallel vocabulary is introduced. For a downstream
gate fold, the failure detail carries `cause: "checker_error"` — the registered
CJ-8 cause ("the checker raised — the instrument is defective") from
`scripts/benchmark/gate_verdict_vocab.py`. A judge crash is never a "no" verdict
and never a pass.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .outcomes import HarnessFailure, JudgeFailure, RunFailure

#: The CJ-8 cause code carried on every guard-raised JudgeFailure.
GUARD_CAUSE = "checker_error"

#: Contract version recorded in manifest.json meta.
CONTRACT = "verbatim-judgment-plus-external-guard-v1"

KIND_NARROW = "narrow"
KIND_SUPPRESSING = "suppressing"
KIND_ESCALATING = "escalating"

#: Handler type names that catch anything a judge can plausibly raise.
_BROAD_NAMES = frozenset({"Exception", "BaseException"})


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Handler:
    """One `except` clause of the judge, classified from the untouched source."""

    lineno: int
    kind: str
    exc_names: Tuple[str, ...]  # () for a bare `except:`


@dataclass(frozen=True)
class _TryRegion:
    """A `try` body's line span plus its handlers, in source order."""

    start: int
    end: int
    handlers: Tuple[Handler, ...]

    def matching(self, exc_type: type) -> Optional[Handler]:
        mro = {c.__name__ for c in exc_type.__mro__}
        for h in self.handlers:
            if not h.exc_names:  # bare except: catches everything
                return h
            if any(n in mro for n in h.exc_names):
                return h
        return None


def _exc_names(node: Optional[ast.expr]) -> Tuple[str, ...]:
    """Simple names of an except clause's type expression ( () == bare except)."""
    if node is None:
        return ()
    items = node.elts if isinstance(node, ast.Tuple) else [node]
    out: List[str] = []
    for it in items:
        if isinstance(it, ast.Name):
            out.append(it.id)
        elif isinstance(it, ast.Attribute):
            out.append(it.attr)
        else:  # dynamic expression: treat as broad, we cannot prove it narrow
            out.append("Exception")
    return tuple(out)


def _classify(handler: ast.ExceptHandler, names: Tuple[str, ...]) -> str:
    broad = not names or any(n in _BROAD_NAMES for n in names)
    if not broad:
        return KIND_NARROW
    pure_suppression = all(
        isinstance(stmt, (ast.Pass, ast.Continue, ast.Break)) for stmt in handler.body
    )
    return KIND_SUPPRESSING if pure_suppression else KIND_ESCALATING


class JudgeGuard:
    """The wrapper layer for ONE judge file. Holds no upstream bytes."""

    def __init__(self, path: Path, source: str):
        self.path = Path(path)
        self.filename = str(self.path.resolve())
        self.source_sha256 = sha256_bytes(source.encode())
        tree = ast.parse(source, filename=self.filename)
        regions: List[_TryRegion] = []
        handlers: List[Handler] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            hs: List[Handler] = []
            for h in node.handlers:
                names = _exc_names(h.type)
                hs.append(Handler(lineno=h.lineno, kind=_classify(h, names), exc_names=names))
            handlers.extend(hs)
            # Only the `try:` BODY is protected by these handlers. An exception
            # raised in an except/else/finally block is not caught by them.
            start = min(s.lineno for s in node.body)
            end = max((s.end_lineno or s.lineno) for s in node.body)
            regions.append(_TryRegion(start=start, end=end, handlers=tuple(hs)))
        # Innermost first: the smallest containing span wins, which is what
        # Python's own handler resolution does within a single frame.
        self.regions: Tuple[_TryRegion, ...] = tuple(
            sorted(regions, key=lambda r: (r.end - r.start, r.start))
        )
        self.handlers: Tuple[Handler, ...] = tuple(sorted(handlers, key=lambda h: h.lineno))

    # ---------------------------------------------------------------- manifest

    def handler_map(self) -> Dict[str, Any]:
        """The guard's per-case identity: which handlers it escalates on.

        Recorded in manifest.json ALONGSIDE (never mixed into) the upstream
        digest, so a reader can see exactly what the wrapper does to this judge
        without that changing a single upstream byte.
        """
        by_kind: Dict[str, List[int]] = {KIND_ESCALATING: [], KIND_SUPPRESSING: [], KIND_NARROW: []}
        for h in self.handlers:
            by_kind[h.kind].append(h.lineno)
        return {
            "escalating_handler_lines": sorted(by_kind[KIND_ESCALATING]),
            "suppressing_handler_lines": sorted(by_kind[KIND_SUPPRESSING]),
            "narrow_handler_lines": sorted(by_kind[KIND_NARROW]),
        }

    def handler_map_sha256(self) -> str:
        return sha256_bytes(json.dumps(self.handler_map(), sort_keys=True).encode())

    # ----------------------------------------------------------------- runtime

    def _resolve(self, lineno: int, exc_type: type) -> Optional[Handler]:
        for region in self.regions:
            if region.start <= lineno <= region.end:
                h = region.matching(exc_type)
                if h is not None:
                    return h
        return None

    def call(self, fn: Callable, *args: Any, label: str = "", **kwargs: Any) -> Any:
        """Run `fn` under the guard. Returns its value, or raises JudgeFailure.

        The judge's own control flow is untouched: the exception is observed,
        never injected. Escalation happens after `fn` returns.
        """
        swallowed: List[Dict[str, Any]] = []
        seen: set = set()
        guard_bug: List[BaseException] = []
        filename = self.filename

        def _local(frame, event, arg):
            if event == "exception":
                try:
                    exc_type, exc, _tb = arg
                    key = id(exc)
                    if key not in seen:
                        handler = self._resolve(frame.f_lineno, exc_type)
                        if handler is not None and handler.kind == KIND_ESCALATING:
                            seen.add(key)
                            swallowed.append(
                                {
                                    "exception": exc_type.__name__,
                                    "message": str(exc)[:400],
                                    "raised_at_line": frame.f_lineno,
                                    "function": frame.f_code.co_name,
                                    "swallowed_by_handler_line": handler.lineno,
                                }
                            )
                except BaseException as bug:  # a guard bug is a HARNESS bug
                    guard_bug.append(bug)
            return _local

        def _global(frame, event, arg):
            if frame.f_code.co_filename != filename:
                # DELEGATE, never return None. Returning None here would blind any
                # tracer already installed -- coverage.py above all -- for every frame
                # executed during the judge call, for as long as the guard is installed.
                # The verdict would stay correct and the coverage number would quietly
                # drop, which is the exact defect class CJ-8 exists to remove: an
                # instrument reporting less than the truth without saying so.
                return previous(frame, event, arg) if previous is not None else None
            return _local

        previous = sys.gettrace()
        sys.settrace(_global)
        try:
            result = fn(*args, **kwargs)
        except RunFailure:
            raise
        except BaseException as exc:
            # Escaped the judge entirely: still a judge failure, not a verdict.
            raise JudgeFailure(
                f"judge {label or self.path.parent.name} raised out of "
                f"{getattr(fn, '__name__', 'call')}: {exc!r}",
                detail={
                    "cause": GUARD_CAUSE,
                    "judge": str(self.path),
                    "escaped": True,
                    "exception": type(exc).__name__,
                    "message": str(exc)[:400],
                },
            ) from exc
        finally:
            sys.settrace(previous)

        if guard_bug:
            raise HarnessFailure(
                f"judge guard failed while observing {self.path}: {guard_bug[0]!r}"
            ) from guard_bug[0]
        if swallowed:
            first = swallowed[0]
            raise JudgeFailure(
                f"judge {label or self.path.parent.name} crashed and swallowed it: "
                f"{first['exception']}: {first['message']} "
                f"(raised at line {first['raised_at_line']}, swallowed by the handler "
                f"at line {first['swallowed_by_handler_line']}). The verdict it "
                f"returned is NOT a judgment.",
                detail={
                    "cause": GUARD_CAUSE,
                    "judge": str(self.path),
                    "escaped": False,
                    "swallowed": swallowed,
                },
            )
        return result


_CACHE: Dict[str, JudgeGuard] = {}
_CACHE_LOCK = threading.Lock()


def scan_judge(path: Path) -> JudgeGuard:
    """Build (and memoize by content) the guard for one judge file."""
    p = Path(path)
    source = p.read_text()
    key = f"{p.resolve()}:{sha256_bytes(source.encode())}"
    with _CACHE_LOCK:
        guard = _CACHE.get(key)
        if guard is None:
            guard = JudgeGuard(p, source)
            _CACHE[key] = guard
    return guard


def guard_identity() -> Dict[str, str]:
    """This module's OWN identity, for manifest.json. Never mixed with a judge's."""
    return {
        "module": "harness/judge_guard.py",
        "sha256": sha256_bytes(Path(__file__).resolve().read_bytes()),
        "contract": CONTRACT,
        "cause_code": GUARD_CAUSE,
    }
