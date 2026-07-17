#!/usr/bin/env python3
"""C2 — code cross-check of a batch entry's ``preconditions.autopilot`` against the
live autopilot signal.

The inference-batch schema lets an entry declare the autopilot state it requires
at execution time (``preconditions.autopilot`` ∈ ``{stopped, running, any}`` —
inference_batch.schema.json). Nothing, however, cross-checked that declaration
against what ``inference_load_check.classify_load()`` actually observes, so a
``stopped``-required entry could be dispatched while autopilot was live (or vice
versa) with no guard catching the mismatch.

This module is that guard: a PURE function

    check_autopilot_precondition(entry_dict, load_signals) -> (ok, reason)

It takes the already-collected load-signal dict as input — it performs NO live
probing, loads NO model, and touches NO serving-path module. Fail-safe: when the
observed autopilot state is unconfirmed (``running=None``), a ``stopped`` or
``running`` requirement is NOT satisfied (we cannot prove it), while ``any`` (or
an absent requirement) is always satisfied.

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

#: Legal values for ``preconditions.autopilot`` (mirrors the batch schema enum).
VALID_PRECONDITIONS = ("stopped", "running", "any")


def _running_signal(load_signals: dict[str, Any]) -> bool | None:
    """Extract ``autopilot.running`` (True/False/None) from a load-signal dict.

    Accepts either the raw signal dict (``collect_signals()`` output, keyed
    ``autopilot`` at top level) OR a full ``classify_load()`` result (which nests
    the signals under a ``signals`` key). Missing/malformed → ``None``
    (unconfirmed).
    """
    if not isinstance(load_signals, dict):
        return None
    ap = load_signals.get("autopilot")
    if ap is None and isinstance(load_signals.get("signals"), dict):
        ap = load_signals["signals"].get("autopilot")
    if not isinstance(ap, dict):
        return None
    return ap.get("running")


def _required_autopilot(entry_dict: dict[str, Any]) -> str:
    """The entry's required autopilot precondition; ``any`` when unspecified."""
    pre = (entry_dict or {}).get("preconditions") or {}
    value = pre.get("autopilot")
    return str(value) if value is not None else "any"


def check_autopilot_precondition(
    entry_dict: dict[str, Any], load_signals: dict[str, Any]
) -> tuple[bool, str]:
    """Assert an entry's ``preconditions.autopilot`` is consistent with the live signal.

    Returns ``(ok, reason)``:
      * ``any`` (or an absent requirement) → always ``ok`` (no constraint).
      * ``running`` → ``ok`` iff the observed ``autopilot.running`` is ``True``.
      * ``stopped`` → ``ok`` iff the observed ``autopilot.running`` is ``False``.
      * an unconfirmed signal (``running is None``) fails ``running``/``stopped``
        (conservative — the requirement cannot be proven).
      * an out-of-enum requirement → ``not ok`` with an explanatory reason.

    Pure: no live probing, no serving-path, no model. ``load_signals`` is the
    signal dict (or full ``classify_load()`` result) supplied by the caller.
    """
    required = _required_autopilot(entry_dict)
    running = _running_signal(load_signals)
    observed = (
        "running" if running is True else ("stopped" if running is False else "unconfirmed")
    )

    if required == "any":
        return True, f"precondition 'any' imposes no autopilot constraint (observed: {observed})"
    if required not in VALID_PRECONDITIONS:
        return False, (
            f"precondition.autopilot={required!r} is not one of {VALID_PRECONDITIONS} "
            f"(observed: {observed})"
        )
    if required == "running":
        if running is True:
            return True, "requires autopilot running; observed running"
        return False, f"requires autopilot running; observed {observed}"
    # required == "stopped"
    if running is False:
        return True, "requires autopilot stopped; observed stopped"
    return False, f"requires autopilot stopped; observed {observed}"


# --------------------------------------------------------------------------- #
# CLI (optional convenience; no live probing unless --live is passed)
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="C2 autopilot-precondition consistency gate (pure).")
    ap.add_argument("--entry", required=True, help="Path to a batch-entry JSON file.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--signals", help="Path to a load-signal JSON file (collect_signals/classify_load).")
    src.add_argument(
        "--live", action="store_true",
        help="Collect the live signal via inference_load_check.classify_load() (read-only).",
    )
    args = ap.parse_args(argv)

    with open(args.entry, "r", encoding="utf-8") as fh:
        entry = json.load(fh)
    if args.signals:
        with open(args.signals, "r", encoding="utf-8") as fh:
            signals = json.load(fh)
    else:  # --live: lazy import so the pure helper never pulls in the probe module.
        import inference_load_check as ic  # noqa: PLC0415

        signals = ic.classify_load()

    ok, reason = check_autopilot_precondition(entry, signals)
    print(json.dumps({"ok": ok, "reason": reason}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
