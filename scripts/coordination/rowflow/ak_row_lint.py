#!/usr/bin/env python3
"""ak_row_lint.py - static lint of AK row dirs for the 2026-11-23 harness defects (see ak_row_harness.py).

Flags (one line each, exit 1 when any FAIL):
  QUIET-NO-BACKOFF   a quiet-host guard (readbw REF / sibling probe / contention retries) with no backoff wait and no
                     ak_row_harness import
  HARDCODED-PORT     launch.sh --port values (or job.py port literals) that are not ak_row_harness.expected_ports(id, n)
  ESTIMATE-UNMEASURED spec.json estimate_s with no estimate_basis (smoke measurement), or below the derived value
  DIFFERS-FIXED      a "differs" library proof with no touched_libs/libs_differ (fold_row_guard.py) derivation
Usage: ak_row_lint.py <row_dir> [<row_dir> ...]     (read-only; never touches a row)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ak_row_harness as H  # noqa: E402

GUARD_RX = re.compile(r"bench_readbw|read_sum|class\s+Probe|probe_p50|MAX_TRIES|contended", re.I)
BACKOFF_RX = re.compile(r"backoff|ak_row_harness|time\.sleep\(\s*(?:[2-9]\d|\d{3,})", re.I)
PORT_ARG_RX = re.compile(r"--port[ =]+([\d,]+)")
PORT_LIT_RX = re.compile(r"\bport\w*\s*[=:]\s*(\d{4,5})\b", re.I)
DIFFERS_RX = re.compile(r"differ", re.I)
LIB_RX = re.compile(r"lib[\w-]+\.so")
DERIVED_RX = re.compile(r"touched_libs|libs_differ|fold_row_guard")


def _read(p):
    try:
        with open(p, errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def lint_dir(d):
    out = []
    spec = {}
    try:
        spec = json.loads(_read(os.path.join(d, "spec.json")) or "{}")
    except ValueError:
        out.append(("FAIL", "SPEC", "spec.json is not JSON"))
    rid = spec.get("id") or os.path.basename(os.path.normpath(d))
    pys = sorted(f for f in os.listdir(d) if f.endswith(".py") and f != "ak_row_harness.py")
    code = {f: _read(os.path.join(d, f)) for f in pys}
    launch = _read(os.path.join(d, "launch.sh"))

    for f, t in code.items():
        if GUARD_RX.search(t) and not BACKOFF_RX.search(t):
            out.append(("FAIL", "QUIET-NO-BACKOFF", f"{f}: quiet-host guard retries with no backoff; use ak_row_harness.quiet_guard"))

    ports = [int(x) for m in PORT_ARG_RX.finditer(launch) for x in m.group(1).split(",") if x]
    if ports:
        exp = H.expected_ports(rid, len(ports))
        if sorted(ports) != sorted(exp):
            out.append(("FAIL", "HARDCODED-PORT", f"launch.sh --port {ports} != alloc_ports({rid!r}, {len(ports)}) = {exp}"))
    for f, t in code.items():
        lits = sorted({int(m.group(1)) for m in PORT_LIT_RX.finditer(t)} - set(ports))
        if lits and "alloc_ports" not in t and "FILLER_PORTS" not in t:
            out.append(("FAIL", "HARDCODED-PORT", f"{f}: port literal(s) {lits}; take them from FILLER_PORTS / alloc_ports"))

    if spec.get("estimate_s") is not None:
        try:
            _, w = H.check_spec_estimate(spec)
            for x in w:
                out.append(("FAIL", "ESTIMATE-UNMEASURED", x))
        except ValueError as e:
            out.append(("FAIL", "ESTIMATE-UNMEASURED", str(e)))

    for f, t in code.items():
        if DIFFERS_RX.search(t) and LIB_RX.search(t) and not DERIVED_RX.search(t):
            out.append(("FAIL", "DIFFERS-FIXED", f"{f}: library 'differs' proof over a fixed list; derive it with "
                                                 "fold_row_guard.touched_libs/libs_differ"))
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    bad = 0
    for d in argv:
        res = lint_dir(d)
        for lvl, code, msg in res:
            print(f"{lvl} {code} {d}: {msg}")
        bad += sum(1 for r in res if r[0] == "FAIL")
        if not res:
            print(f"OK {d}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
