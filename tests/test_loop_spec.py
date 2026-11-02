"""JEV-5 phase A: the churn loop spec is valid AND still equals the code.

The diagram on /loop-spec is only worth reading if it cannot drift. Every
threshold whose ``source`` is ``<file>:<CONSTANT>`` is evaluated from the code
(``ast.literal_eval`` of the module-level assignment, ``256 << 20`` included)
and compared; every ``<file>:<function>`` code anchor must exist.
"""
import ast
import json
import unittest
from pathlib import Path

from dashboard import loop_spec, panels, server

REPO = Path(__file__).resolve().parents[1]
CHURN = REPO / "docs" / "reference" / "loop-specs" / "churn.loop.json"


def _const(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return eval(compile(ast.Expression(node.value), str(path), "eval"), {"__builtins__": {}})  # noqa: S307 (literal arithmetic only)
    raise AssertionError(f"{name} not assigned at module level in {path}")


class LoopSpecTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(CHURN.read_text(encoding="utf-8"))

    def test_schema_file_parses_and_names_the_id(self):
        schema = json.loads((CHURN.parent / "loop-spec.schema.json").read_text())
        self.assertEqual(schema["$id"], loop_spec.SCHEMA_ID)
        self.assertEqual(set(schema["properties"]["machines"]["items"]["properties"]["states"]["items"]
                             ["properties"]["kind"]["enum"]), set(loop_spec.STATE_KINDS))
        self.assertEqual(set(schema["properties"]["stop_reasons"]["items"]["properties"]["kind"]["enum"]),
                         set(loop_spec.REASON_KINDS))

    def test_churn_spec_is_valid(self):
        self.assertEqual(loop_spec.validate(self.spec), [])

    def test_validator_catches_dangling_references(self):
        bad = json.loads(json.dumps(self.spec))
        bad["machines"][0]["transitions"].append({"from": "nowhere", "to": "done", "on": "x", "reason": "NOPE"})
        errs = loop_spec.validate(bad)
        self.assertTrue(any("nowhere" in e for e in errs))
        self.assertTrue(any("NOPE" in e for e in errs))

    def test_thresholds_equal_the_code(self):
        checked = 0
        for t in self.spec["thresholds"]:
            src = t["source"]
            if not src.startswith("scripts/") or ":" not in src:
                continue
            file, name = src.rsplit(":", 1)
            value = _const(REPO / file, name)
            if isinstance(value, tuple):
                value = ",".join(str(v) for v in value)
            self.assertEqual(value, t["value"], f"{t['id']} drifted from {src}")
            checked += 1
        self.assertGreaterEqual(checked, 15)

    def test_code_anchors_exist(self):
        for m in self.spec["machines"]:
            for anchor in m["code"]:
                file, _, sym = anchor.partition(":")
                path = REPO / file
                self.assertTrue(path.exists(), anchor)
                if sym:
                    self.assertIn(f"def {sym}(", path.read_text(encoding="utf-8"), anchor)

    def test_row_states_match_rowflow_status(self):
        text = (REPO / "scripts/coordination/rowflow/rowflow.py").read_text(encoding="utf-8")
        row = next(m for m in self.spec["machines"] if m["id"] == "row")
        for s in row["states"]:
            self.assertIn(f'state="{s["id"]}"', text, s["id"])

    def test_payload_draws_every_machine(self):
        data = server.loop_spec_payload()
        self.assertEqual(data["problems"], [])
        spec = next(s for s in data["specs"] if s["loop_id"] == "churn")
        for m in spec["machines"]:
            self.assertTrue(m["mermaid"].startswith("stateDiagram-v2"))
        self.assertIn("staleness_class", data["_freshness"])
        status, body = server.loop_spec_health()
        self.assertIn(status, (200, 503))
        self.assertEqual(body["panel"], "loop_spec")

    def test_panels_registered(self):
        self.assertEqual({k: v for k, v in panels.registry_gaps(server).items() if v}, {})


if __name__ == "__main__":
    unittest.main()
