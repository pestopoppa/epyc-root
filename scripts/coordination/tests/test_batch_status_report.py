#!/usr/bin/env python3
"""Tests for B9 batch_status_report — rendering + op-bundle formatting.

Renders from in-memory manifest+ledger dicts (no yaml needed) and also tests the
.json loader path. Stdlib unittest.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

_COORD = Path(__file__).resolve().parents[1]
if str(_COORD) not in sys.path:
    sys.path.insert(0, str(_COORD))

import batch_status_report as bsr  # noqa: E402


def entry(
    task_id,
    phase,
    priority="P1",
    depends_on=None,
    driver="clean_window_entry",
    retry_on=None,
):
    execution = {"driver": driver, "concurrency_mode": "serial_noninference"}
    if retry_on:
        execution["retry_policy"] = {"max_attempts": 2, "retry_on": list(retry_on)}
    return {
        "task_id": task_id,
        "title": f"{task_id} title",
        "phase": phase,
        "priority": priority,
        "preconditions": {"depends_on": depends_on or []},
        "execution": execution,
        "outcomes": {"gate_table": []},
    }


MANIFEST = {
    "version": "inference_batch.v2",
    "entries": [
        entry("A1", 0),
        entry("A2", 0, depends_on=["A1"], retry_on=["INFRA_BLOCKED"]),
        entry("B1", 1),
        entry("B2", 1, depends_on=["B1"]),
        entry("C1", 2, depends_on=["A2"]),
    ],
}

LEDGER = [
    {"task_id": "A1", "status": "RUNNING"},
    {"task_id": "A1", "status": "DONE_PASS"},          # latest-row-wins
    {"task_id": "A2", "status": "INFRA_BLOCKED", "reasons": ["run timed out"]},
    {
        "task_id": "B1",
        "status": "HELD_OP_GATE",
        "reasons": ["auto-revert requires file edit"],
        "op_bundle_row": {
            "task_id": "B1",
            "title": "B1 title",
            "gate": "Did quality improve?",
            "evidence": "safety_gate=reject | sequential=confirmed",
            "options": ["Revert manually", "Accept override"],
        },
    },
    # B2 has no ledger row -> UNSTARTED; blocked by B1 (held) so not eligible.
    # C1 depends on A2 (infra-blocked) -> not eligible.
]


class TestReportModel(unittest.TestCase):
    def setUp(self):
        self.report = bsr.build_report(MANIFEST, LEDGER, generated_at="2026-07-17T00:00:00+00:00")

    def test_latest_row_wins(self):
        latest = bsr.latest_by_task(LEDGER)
        self.assertEqual(latest["A1"]["status"], "DONE_PASS")

    def test_status_counts(self):
        by = self.report["summary"]["by_status"]
        self.assertEqual(by.get("DONE_PASS"), 1)
        self.assertEqual(by.get("INFRA_BLOCKED"), 1)
        self.assertEqual(by.get("HELD_OP_GATE"), 1)
        self.assertEqual(by.get(bsr.UNSTARTED), 2)  # B2, C1

    def test_per_phase(self):
        pp = self.report["per_phase"]
        self.assertIn(0, pp)
        self.assertIn(1, pp)
        self.assertEqual(pp[0].get("DONE_PASS"), 1)

    def test_eligible_next(self):
        elig = {e["task_id"] for e in self.report["eligible"]}
        # A2 is INFRA_BLOCKED with dep A1 satisfied -> re-eligible.
        self.assertIn("A2", elig)
        # B1 is held -> not eligible; B2 depends on unsatisfied B1 -> not eligible.
        self.assertNotIn("B1", elig)
        self.assertNotIn("B2", elig)
        # C1 depends on A2 (not terminal-success) -> not eligible.
        self.assertNotIn("C1", elig)

    def test_infra_blocked_without_retry_policy_is_not_eligible(self):
        manifest = {
            "entries": [
                entry("A1", 0),
                entry("A2", 0, depends_on=["A1"]),
            ]
        }
        ledger = [
            {"task_id": "A1", "status": "DONE_PASS"},
            {"task_id": "A2", "status": "INFRA_BLOCKED"},
        ]
        report = bsr.build_report(manifest, ledger)
        self.assertNotIn("A2", {e["task_id"] for e in report["eligible"]})

    def test_eligible_entry_warns_on_entry_hash_drift(self):
        manifest = {
            "entries": [
                {**entry("A1", 0), "entry_hash": "sha256:current"},
            ]
        }
        ledger = [
            {
                "task_id": "A1",
                "status": "INFRA_BLOCKED",
                "entry_hash": "sha256:old",
            },
        ]
        manifest["entries"][0]["execution"]["retry_policy"] = {
            "max_attempts": 2,
            "retry_on": ["INFRA_BLOCKED"],
        }

        report = bsr.build_report(manifest, ledger)
        self.assertEqual(report["summary"]["warnings"], 1)
        self.assertEqual(report["warnings"][0]["type"], "entry_hash_drift")
        eligible = report["eligible"][0]
        self.assertTrue(eligible["entry_hash_drift"])
        self.assertEqual(eligible["ledger_entry_hash"], "sha256:old")
        self.assertEqual(eligible["current_entry_hash"], "sha256:current")

        markdown = bsr.render_markdown(report)
        self.assertIn("## Warnings", markdown)
        self.assertIn("entry_hash_drift", markdown)

    def test_blocked_breakdown(self):
        ids = {b["task_id"] for b in self.report["blocked_breakdown"]}
        self.assertIn("A2", ids)

    def test_held_breakdown(self):
        ids = {h["task_id"] for h in self.report["held_breakdown"]}
        self.assertIn("B1", ids)

    def test_op_bundle_accumulated(self):
        self.assertEqual(len(self.report["op_bundle_rows"]), 1)
        self.assertEqual(self.report["op_bundle_rows"][0]["task_id"], "B1")

    def test_render_markdown(self):
        md = bsr.render_markdown(self.report)
        self.assertIn("# Inference-Batch Status Report", md)
        self.assertIn("## Next-runnable entries", md)
        self.assertIn("A2", md)
        self.assertIn("## Structurally eligible but operator-gated", md)
        self.assertIn("## Accumulated operator-bundle rows", md)
        self.assertIn("### B1 — B1 title", md)

    def test_operator_gate_registry_filters_runnable_entries(self):
        manifest = {
            "entries": [
                {
                    **entry("A1", 0),
                    "preconditions": {"depends_on": [], "operator_gates": ["OP-A"]},
                },
                {
                    **entry("A2", 0),
                    "preconditions": {"depends_on": [], "operator_gates": ["OP-B"]},
                },
                {
                    **entry("A3", 0),
                    "preconditions": {"depends_on": [], "operator_gates": ["OP-MISSING"]},
                },
            ]
        }
        registry = {
            "OP-A": {"granted": True},
            "OP-B": {"granted": False},
        }

        report = bsr.build_report(manifest, [], operator_gate_registry=registry)
        self.assertEqual(report["summary"]["structurally_eligible"], 3)
        self.assertEqual(report["summary"]["eligible_now"], 1)
        self.assertEqual(report["summary"]["operator_gate_blocked"], 2)
        self.assertEqual([e["task_id"] for e in report["eligible"]], ["A1"])
        blockers = {
            row["task_id"]: row["operator_gate_blockers"]
            for row in report["operator_gate_blocked"]
        }
        self.assertEqual(blockers["A2"], [{"gate": "OP-B", "reason": "not_granted"}])
        self.assertEqual(
            blockers["A3"], [{"gate": "OP-MISSING", "reason": "missing_from_op_bundle"}]
        )

    def test_load_operator_gate_registry(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "op-bundle.md"
            p.write_text(
                "\n".join(
                    [
                        "- [x] **OP-A — approved gate**: GRANTED 2026-07-20",
                        "- [ ] **OP-B — pending gate**: waiting",
                        "- [x] **OP-C — denied gate**: DENIED 2026-07-20",
                    ]
                )
            )
            registry = bsr.load_operator_gate_registry(p)
        self.assertTrue(registry["OP-A"]["granted"])
        self.assertFalse(registry["OP-B"]["granted"])
        self.assertFalse(registry["OP-C"]["granted"])


class TestOpBundleFormatter(unittest.TestCase):
    def test_format_from_entry_dict(self):
        block = bsr.format_op_bundle_row(
            {"task_id": "EV-11", "title": "math-verify flip"},
            "Did math-verify agree with the stored ledger?",
            "safety_gate=reject | sequential=confirmed",
            ["Revert flag", "Accept override", "Re-run"],
        )
        self.assertIn("### EV-11 — math-verify flip", block)
        self.assertIn("- **Gate**: Did math-verify agree", block)
        self.assertIn("- **Evidence**: safety_gate=reject", block)
        self.assertIn("  1. Revert flag", block)
        self.assertIn("  3. Re-run", block)

    def test_format_from_string_id(self):
        block = bsr.format_op_bundle_row("X1", "g", "e", None)
        self.assertIn("### X1 — X1", block)
        self.assertIn("no pre-formed options", block)

    def test_append_dry_run_no_write(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "op-bundle.md"
            block = bsr.append_op_bundle_row(p, "X1", "g", "e", ["opt"])
            self.assertFalse(p.exists())
            self.assertIn("### X1", block)

    def test_append_writes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "op-bundle.md"
            bsr.append_op_bundle_row(p, "X1", "g", "e", ["opt"], dry_run=False)
            bsr.append_op_bundle_row(p, "X2", "g2", "e2", ["opt2"], dry_run=False)
            text = p.read_text()
            self.assertIn("### X1", text)
            self.assertIn("### X2", text)


class TestJsonLoader(unittest.TestCase):
    def test_load_json_manifest_and_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            mpath = Path(d) / "manifest.json"
            lpath = Path(d) / "ledger.jsonl"
            mpath.write_text(json.dumps(MANIFEST))
            lpath.write_text("\n".join(json.dumps(r) for r in LEDGER))
            manifest = bsr.load_manifest(mpath)
            ledger = bsr.load_ledger(lpath)
            report = bsr.build_report(manifest, ledger)
            self.assertEqual(report["summary"]["entries_total"], 5)
            self.assertEqual(report["summary"]["done_pass"], 1)

    def test_missing_ledger_fails_closed(self):
        with self.assertRaisesRegex(bsr.StatusReportError, "ledger not found"):
            bsr.load_ledger(Path("/nonexistent/ledger.jsonl"))


if __name__ == "__main__":
    unittest.main()
