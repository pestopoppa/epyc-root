"""Shared llama-bench PROTOCOL precondition for every adapter that projects llama-bench rows (VB-LLAMA-BENCH-HARDEN-PROTOCOL).

Defect (found 2026-10-23, fix V11-103 / CH-28): builds from ``0492c2319`` through the champion
``49550eda5`` (v10 included) leave ``cmd_params::autokernel_harden`` uninitialised, so about half of the
processes started WITHOUT ``--autokernel-harden`` emit rows saying ``"autokernel_hardened": true``. The hardened
protocol (2 x reps contexts, a depth fill per context, hybrid ordinary/full-device-sync pairs) and the ordinary
one are different measurements, so ``autokernel_hardened`` is a PROTOCOL field, not a quality flag.

This module is a PROJECTION PRECONDITION. It holds no grading rule and writes no tuple field that changes a
measurement id: an adapter calls :func:`assess` before it builds a ``ClaimTuple`` and either gets back the
protocol identity (attach it to ``extra``) or a :class:`LlamaBenchProtocolRefusal` (a ``ProjectionError``, so the
existing report path counts it as ``refused`` with its reason, never as a silent drop). ``claim_tuple.grade()``
remains the only grader.

Rules (mirrors the research consumer guard LBH-3, ``LlamaBenchExpectation.check_row`` /
``BenchRow.hardened_state`` on research main ``5c3ad96c3``):

1. The ROW's state: ``hardened`` when ``autokernel_hardened`` is true or hardened-only receipt fields prove it;
   ``ordinary`` when the key is present and false; ``unknown`` when the key is missing (never read as false).
2. The REQUEST: ``--autokernel-harden`` in the producer's recorded argv. No argv -> ``None`` (unrecoverable).
3. Row state differs from the request -> REFUSE (``unrequested_hardened`` / ``requested_not_attested``).
4. A hardened row whose request is unrecoverable -> REFUSE for any build that is not known to carry V11-103.
5. An unknown row is NOT refused (``strict_unknown=False``, the LBH-3 default, so pre-fix archives stay
   loadable); its identity says ``unknown``. A consumer gating a NEW claim passes ``strict_unknown=True``.
"""
from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError  # noqa: E402

PROTOCOL_SCHEMA = "epyc.vidya.llama_bench_protocol.v1"
HARDEN_FLAG = "--autokernel-harden"

#: Builds that carry V11-103 (the fixed ``parse_cmd_params``). Prefix match, >= 7 hex chars. Extend when a
#: later champion/production kernel is cut: a build NOT listed is treated as inside the defect window.
FIXED_BUILD_PREFIXES: tuple[str, ...] = ("141e4bcf5",)

#: Fields only a hardened receipt carries; any of them proves the hardened protocol ran even if the flag is lost.
_HARDENED_ONLY = ("autokernel_input_hashes", "autokernel_output_hashes")
_HEX = re.compile(r"[0-9a-f]{7,40}")

REFUSAL_CODES = ("unrequested_hardened", "requested_not_attested", "hardened_request_unrecoverable",
                 "unknown_protocol_strict")


class LlamaBenchProtocolRefusal(ProjectionError):
    """A llama-bench row whose protocol does not match its request (or cannot be shown to)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"llama_bench_protocol:{code}: {message}")
        self.code = code


def _tokens(argv: Any) -> list[str] | None:
    if argv is None:
        return None
    if isinstance(argv, str):
        try:
            return shlex.split(argv)
        except ValueError:
            return argv.split()
    if isinstance(argv, Sequence) and not isinstance(argv, (bytes, bytearray)):
        return [str(item) for item in argv]
    return None


def requested_from_argv(argv: Any) -> bool | None:
    """True/False when the recorded argv exists (flag present / absent); None when there is no argv."""
    tokens = _tokens(argv)
    if not tokens:
        return None
    return any(tok == HARDEN_FLAG or tok.startswith(HARDEN_FLAG + "=") for tok in tokens)


def hardened_state(row: Mapping[str, Any] | None) -> str:
    """``hardened`` / ``ordinary`` / ``unknown`` -- what the ROW attests, not what argv asked."""
    if not isinstance(row, Mapping):
        return "unknown"
    flag = row.get("autokernel_hardened")
    if flag is True or str(flag).lower() == "true":
        return "hardened"
    for key in _HARDENED_ONLY:
        if row.get(key):
            return "hardened"
    size = row.get("autokernel_input_working_set_bytes")
    if isinstance(size, (int, float)) and not isinstance(size, bool) and size > 0:
        return "hardened"
    if row.get("autokernel_output_invariant") is True:
        return "hardened"
    if "autokernel_hardened" not in row:
        return "unknown"
    # A BenchRow.to_dict() serialisation writes autokernel_hardened=False even when the key was absent; it
    # then also carries autokernel_hardened_reported=False, which is the honest "unknown".
    if row.get("autokernel_hardened_reported") is False:
        return "unknown"
    return "ordinary"


def build_is_fixed(build_commit: Any) -> bool:
    if not isinstance(build_commit, str):
        return False
    head = build_commit.strip().split()[0].lower() if build_commit.strip() else ""
    if not _HEX.fullmatch(head):
        return False
    return any(head.startswith(p) or p.startswith(head) for p in FIXED_BUILD_PREFIXES)


def assess(*, row: Mapping[str, Any] | None, argv: Any = None, requested: bool | None = None,
           build_commit: Any = None, label: str = "llama-bench row",
           strict_unknown: bool = False, format_carries_flag: bool = True) -> dict:
    """Return the protocol identity for one llama-bench result, or raise :class:`LlamaBenchProtocolRefusal`.

    ``requested`` overrides ``argv`` when the producer recorded the request directly. ``build_commit`` defaults
    to the row's own ``build_commit``. ``format_carries_flag=False`` is for sources that CANNOT carry the field
    (llama-bench markdown tables): an unknown row is then expected, not a missing receipt, so a requested-hardened
    command is accepted on the strength of the request and the identity says ``unknown`` for the row.
    """
    state = hardened_state(row)
    if requested is None:
        requested = requested_from_argv(argv)
    if build_commit is None and isinstance(row, Mapping):
        build_commit = row.get("build_commit")
    fixed = build_is_fixed(build_commit)
    if requested is True:
        if state == "ordinary":
            raise LlamaBenchProtocolRefusal(
                "requested_not_attested",
                f"{label}: argv requested {HARDEN_FLAG} but the row says autokernel_hardened=false")
        if state == "unknown" and format_carries_flag:
            raise LlamaBenchProtocolRefusal(
                "requested_not_attested",
                f"{label}: argv requested {HARDEN_FLAG} but the row carries no hardened receipt")
    elif requested is False:
        if state == "hardened":
            raise LlamaBenchProtocolRefusal(
                "unrequested_hardened",
                f"{label}: argv did NOT request {HARDEN_FLAG} but the row attests the hardened protocol "
                f"(uninitialised autokernel_harden, V11-103); build {build_commit or 'unknown'}")
    else:  # request unrecoverable
        if state == "hardened" and not fixed:
            raise LlamaBenchProtocolRefusal(
                "hardened_request_unrecoverable",
                f"{label}: the row attests the hardened protocol, no argv is recorded to show it was "
                f"requested, and build {build_commit or 'unknown'} is not known to carry V11-103")
    if state == "unknown" and strict_unknown and format_carries_flag:
        raise LlamaBenchProtocolRefusal(
            "unknown_protocol_strict",
            f"{label}: the row does not record autokernel_hardened (strict_unknown)")
    return {
        "schema": PROTOCOL_SCHEMA,
        "autokernel_hardened": state,
        "autokernel_harden_requested": "unknown" if requested is None else requested,
        "build_commit": build_commit if isinstance(build_commit, str) else "",
        "build_carries_v11_103": fixed,
    }


class RefusalTally:
    """Counts refusals by code for an adapter's own report (the refusal is still raised, never swallowed)."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {code: 0 for code in REFUSAL_CODES}
        self.assessed = 0

    def assess(self, **kwargs: Any) -> dict:
        self.assessed += 1
        try:
            return assess(**kwargs)
        except LlamaBenchProtocolRefusal as exc:
            self.counts[exc.code] += 1
            raise

    def report(self) -> dict:
        return {"assessed": self.assessed, "refused_by_code": dict(self.counts),
                "refused": sum(self.counts.values())}


def refusal_code(message: str) -> str | None:
    """The code of a ``llama_bench_protocol:<code>:`` refusal message, else None (for report bucketing)."""
    m = re.match(r"llama_bench_protocol:([a-z_]+):", message or "")
    return m.group(1) if m else None


__all__ = ["PROTOCOL_SCHEMA", "HARDEN_FLAG", "FIXED_BUILD_PREFIXES", "REFUSAL_CODES",
           "LlamaBenchProtocolRefusal", "RefusalTally", "assess", "hardened_state",
           "requested_from_argv", "build_is_fixed", "refusal_code"]
