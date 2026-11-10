#!/usr/bin/env python3
"""Tests for REG-ENF-1: scripts/governance/rule_registry.py.

The live registry must validate against the live tree, and each class of defect the
validator exists for must be caught by a mutation of a copy.

Run: python3 -m pytest -q scripts/governance/tests/test_rule_registry.py
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "governance"))
import rule_registry as rr  # noqa: E402


class Live(unittest.TestCase):
    def test_live_registry_checks_clean(self):
        self.assertEqual(rr.main(["--check", "--root", str(ROOT)]), 0)

    def test_region_claim_hook_is_registered_hard(self):
        reg = rr.load(ROOT)
        row = next(r for r in reg["rules"] if r["id"] == "INF-REGION-CLAIM")
        self.assertEqual(row["enforcement_class"], "hard")
        self.assertIn("scripts/hooks/check_inference_region_claim.sh",
                      [p["path"] for p in row["enforcement_points"]])

    def test_every_class_present(self):
        classes = {r["enforcement_class"] for r in rr.load(ROOT)["rules"]}
        self.assertEqual(classes, {"hard", "soft", "prose"})


class Mutations(unittest.TestCase):
    """Each mutation runs validate() on a temp root carrying copies of the inputs."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for rel in (rr.REGISTRY, ".claude/settings.json", "CLAUDE.md",
                    "agents/shared/OPERATING_CONSTRAINTS.md", "agents/shared/INVARIANTS.md",
                    "opencode.json"):
            (self.tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, self.tmp / rel)
        shutil.copytree(ROOT / "scripts/hooks", self.tmp / "scripts/hooks",
                        ignore=shutil.ignore_patterns("tests", "__pycache__"))
        for rel in ("scripts/coordination/rowflow/grant_ok_launcher.py", "scripts/session/verify_llama_cpp.sh"):
            (self.tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, self.tmp / rel)
        self.reg = rr.load(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def errs(self, reg=None):
        return rr.validate(reg or self.reg, self.tmp)

    def test_baseline_clean(self):
        self.assertEqual(self.errs(), [])

    def test_duplicate_id(self):
        reg = copy.deepcopy(self.reg)
        reg["rules"].append(copy.deepcopy(reg["rules"][0]))
        self.assertTrue(any("duplicate id" in e for e in self.errs(reg)))

    def test_bad_class(self):
        reg = copy.deepcopy(self.reg)
        reg["rules"][0]["enforcement_class"] = "maybe"
        self.assertTrue(any("enforcement_class" in e for e in self.errs(reg)))

    def test_anchor_drift(self):
        reg = copy.deepcopy(self.reg)
        reg["rules"][0]["source"]["anchor"] = "this text is not in any governance file 7f3a"
        self.assertTrue(any("anchor not found" in e for e in self.errs(reg)))

    def test_hard_without_block_point(self):
        reg = copy.deepcopy(self.reg)
        r = next(r for r in reg["rules"] if r["enforcement_class"] == "hard")
        for p in r["enforcement_points"]:
            p["mode"] = "warn"
        self.assertTrue(any("hard rule needs a blocking" in e for e in self.errs(reg)))

    def test_prose_with_points(self):
        reg = copy.deepcopy(self.reg)
        r = next(r for r in reg["rules"] if r["enforcement_class"] == "prose")
        r["enforcement_points"] = [{"kind": "validator", "path": "CLAUDE.md", "mode": "warn"}]
        self.assertTrue(any("prose rule must have no" in e for e in self.errs(reg)))

    def test_unwired_hook_point(self):
        reg = copy.deepcopy(self.reg)
        r = next(r for r in reg["rules"] if r["id"] == "INF-REGION-CLAIM")
        r["enforcement_points"][0]["matcher"] = "Write|Edit"
        self.assertTrue(any("not wired" in e for e in self.errs(reg)))

    def test_unregistered_hook_in_settings(self):
        reg = copy.deepcopy(self.reg)
        reg["rules"] = [r for r in reg["rules"] if r["id"] != "INF-REGION-CLAIM"]
        self.assertTrue(any("unregistered hook" in e and "check_inference_region_claim" in e
                            for e in self.errs(reg)))

    def test_missing_point_path(self):
        reg = copy.deepcopy(self.reg)
        reg["rules"][0]["enforcement_points"][0]["path"] = "scripts/hooks/nope.sh"
        self.assertTrue(any("missing on disk" in e for e in self.errs(reg)))

    def test_stale_prose_surface(self):
        prose = self.tmp / "docs/reference/governance/RULE_REGISTRY.md"
        prose.write_text(rr.render(self.reg), encoding="utf-8")
        self.assertEqual(rr.main(["--check", "--root", str(self.tmp)]), 0)
        reg = copy.deepcopy(self.reg)
        reg["rules"][0]["rule"] += " (edited)"
        (self.tmp / rr.REGISTRY).write_text(json.dumps(reg), encoding="utf-8")
        self.assertEqual(rr.main(["--check", "--root", str(self.tmp)]), 1)


if __name__ == "__main__":
    unittest.main()
