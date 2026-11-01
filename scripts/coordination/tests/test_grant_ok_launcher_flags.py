#!/usr/bin/env python3
"""Drift guard: every CLI flag accepted by the filler engine (filler_run15.sh) must be known to the grant gate
(grant_ok_launcher.py VALUE_FLAGS / BOOL_FLAGS), else the gate fails to parse a live poller's argv and every grant is
skipped (incident 2026-11-01 21:11Z, --qual-interpreter). Stdlib only; the gate files are parsed with ast, not imported."""
import ast
import os
import re
import unittest

_COORD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(_COORD, "rowflow", "filler_run15.sh")
GATES = {
    "rowflow": os.path.join(_COORD, "rowflow", "grant_ok_launcher.py"),
    "churn/legacy": os.path.join(_COORD, "churn", "legacy", "grant_ok_launcher.py"),
}
# Flags a gate may carry that the engine does not accept (documented exceptions). Currently none.
KNOWN_EXTRA = {}

ARM_RE = re.compile(r"(--[a-z][a-z0-9-]*(?:\s*\|\s*--[a-z][a-z0-9-]*)*)\)(.*?)(?:;;|$)")


def engine_flags():
    with open(ENGINE) as f:
        text = f.read()
    m = re.search(r"while \[ \$# -gt 0 \]; do\s*\n\s*case \$1 in\n(.*?)\n\s*esac", text, re.S)
    assert m, "engine case block not found"
    value, boolean = set(), set()
    for arm in ARM_RE.finditer(m.group(1)):
        names = {n.strip() for n in arm.group(1).split("|")}
        body = arm.group(2)
        if "shift 2" in body:
            value |= names
        elif re.search(r"\bshift\s*$", body.strip()) or re.search(r"\bshift\s*;", body):
            boolean |= names
    return value, boolean


def gate_sets(path):
    with open(path) as f:
        tree = ast.parse(f.read())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and getattr(node.targets[0], "id", "") in (
                "VALUE_FLAGS", "BOOL_FLAGS"):
            out[node.targets[0].id] = set(ast.literal_eval(node.value))
    return out["VALUE_FLAGS"], out["BOOL_FLAGS"]


class GrantOkLauncherFlagParity(unittest.TestCase):
    def test_engine_parse_not_vacuous(self):
        v, b = engine_flags()
        self.assertGreaterEqual(len(v | b), 15, f"only found {sorted(v | b)}")
        self.assertFalse(v & b)
        self.assertIn("--id", v)
        self.assertIn("--self-claim", b)

    def test_gates_cover_engine(self):
        ev, eb = engine_flags()
        for name, path in GATES.items():
            with self.subTest(gate=name):
                gv, gb = gate_sets(path)
                self.assertFalse(ev - gv, f"{name}: engine value flags missing from VALUE_FLAGS: {sorted(ev - gv)}")
                self.assertFalse(eb - gb, f"{name}: engine bool flags missing from BOOL_FLAGS: {sorted(eb - gb)}")

    def test_gates_have_no_stale_flags(self):
        ev, eb = engine_flags()
        for name, path in GATES.items():
            with self.subTest(gate=name):
                gv, gb = gate_sets(path)
                extra_v = gv - ev - KNOWN_EXTRA.get(name, set())
                extra_b = gb - eb - KNOWN_EXTRA.get(name, set())
                self.assertFalse(extra_v, f"{name}: VALUE_FLAGS not accepted by engine: {sorted(extra_v)}")
                self.assertFalse(extra_b, f"{name}: BOOL_FLAGS not accepted by engine: {sorted(extra_b)}")


if __name__ == "__main__":
    unittest.main()
