#!/usr/bin/env python3
"""Tests for B5 entry_verdict.decide — fork coverage + autonomy revert-scope.

Stdlib unittest only (no pytest dependency); pytest also discovers it.
"""
import sys
import unittest
from pathlib import Path

_COORD = Path(__file__).resolve().parents[1]
if str(_COORD) not in sys.path:
    sys.path.insert(0, str(_COORD))

import entry_verdict as ev  # noqa: E402


def make_gate_table(fail_actions=None, ambiguous_next=None):
    return [
        {
            "gate": "Did quality improve without a regression?",
            "evidence": "SafetyGate verdict + sequential e-process",
            "fork": {
                "pass": {
                    "rule": "PASS and confirmed",
                    "action": ["keep change", "commit ledger DONE_PASS"],
                    "next": "DONE_PASS",
                },
                "marginal": {
                    "rule": "warn or accumulating",
                    "action": ["record observation only"],
                    "next": "DONE_MARGINAL_OBS",
                },
                "fail": {
                    "rule": "REJECT or refuted",
                    "action": fail_actions or ["reset_flag GGML_FOO"],
                    "next": "FAILED_REVERTED",
                },
                "infra": {
                    "classify": "run did not complete",
                    "action": ["retry after drop_caches"],
                },
                "ambiguous": {
                    "action": ["operator adjudicate"],
                    "next": ambiguous_next or "HELD_AMBIGUOUS",
                },
            },
        }
    ]


def make_entry(
    task_id="EV-11",
    concurrency_mode="paired_sequential",
    flags_required=None,
    stack_lineup=None,
    gate_table=None,
    operator_gates=None,
    fail_actions=None,
):
    pre = {"depends_on": []}
    if flags_required is not None:
        pre["flags_required"] = flags_required
    if stack_lineup is not None:
        pre["stack_lineup"] = stack_lineup
    if operator_gates is not None:
        pre["operator_gates"] = operator_gates
    return {
        "task_id": task_id,
        "title": f"{task_id} title",
        "provenance": {"owning_handoff": "handoffs/active/x.md", "checkbox": task_id},
        "phase": 1,
        "priority": "P1",
        "preconditions": pre,
        "execution": {"driver": "clean_window_entry", "concurrency_mode": concurrency_mode},
        "outcomes": {"gate_table": gate_table if gate_table is not None else make_gate_table(fail_actions)},
        "artifacts": {},
        "ledger": {},
    }


OK_EXEC = {"infra_ok": True, "status": "completed", "completed": True}


class TestForkCoverage(unittest.TestCase):
    def test_pass(self):
        v = ev.decide(make_entry(), OK_EXEC, {"safety_gate": "PASS", "sequential": "confirmed"})
        self.assertEqual(v.action, ev.CAT_PASS)
        self.assertEqual(v.ledger_status, ev.DONE_PASS)
        self.assertIsNone(v.revert_plan)
        self.assertIsNone(v.op_bundle_row)

    def test_marginal_warn_confirmed(self):
        v = ev.decide(make_entry(), OK_EXEC, {"safety_gate": "WARN", "sequential": "confirmed"})
        self.assertEqual(v.action, ev.CAT_MARGINAL)
        self.assertEqual(v.ledger_status, ev.DONE_MARGINAL_OBS)
        self.assertIsNone(v.revert_plan)

    def test_marginal_accumulating(self):
        v = ev.decide(make_entry(), OK_EXEC, {"safety_gate": "PASS", "sequential": "accumulating"})
        self.assertEqual(v.action, ev.CAT_MARGINAL)
        self.assertEqual(v.ledger_status, ev.DONE_MARGINAL_OBS)

    def test_marginal_observe_only(self):
        e = make_entry(concurrency_mode="observe_only")
        v = ev.decide(e, OK_EXEC, {})  # no signals; observe_only forces marginal
        self.assertEqual(v.action, ev.CAT_MARGINAL)
        self.assertEqual(v.ledger_status, ev.DONE_MARGINAL_OBS)

    def test_infra(self):
        v = ev.decide(make_entry(), {"infra_ok": False, "status": "timeout"}, {"safety_gate": "PASS"})
        self.assertEqual(v.action, ev.CAT_INFRA)
        self.assertEqual(v.ledger_status, ev.INFRA_BLOCKED)
        self.assertIsNone(v.next_task)  # infra re-queues the same task
        self.assertIsNone(v.revert_plan)
        self.assertIsNone(v.op_bundle_row)

    def test_infra_bad_status_string(self):
        v = ev.decide(make_entry(), {"status": "preflight_failed"}, {"safety_gate": "PASS", "sequential": "confirmed"})
        self.assertEqual(v.action, ev.CAT_INFRA)

    def test_fail_refuted_auto_revert_flags(self):
        e = make_entry(flags_required={"GGML_FOO": 1})
        v = ev.decide(e, OK_EXEC, {"safety_gate": "PASS", "sequential": "refuted"})
        self.assertEqual(v.action, ev.CAT_FAIL)
        self.assertEqual(v.ledger_status, ev.FAILED_REVERTED)
        self.assertIsNotNone(v.revert_plan)
        self.assertTrue(v.revert_plan.auto)
        self.assertIn("runtime_flags", v.revert_plan.kind)
        self.assertIn("GGML_FOO", v.revert_plan.flags_to_reset)
        self.assertIsNone(v.op_bundle_row)

    def test_fail_reject_auto_revert(self):
        e = make_entry(flags_required={"GGML_BAR": "on"})
        v = ev.decide(e, OK_EXEC, {"safety_gate": "REJECT", "sequential": "accumulating"})
        self.assertEqual(v.action, ev.CAT_FAIL)
        self.assertEqual(v.ledger_status, ev.FAILED_REVERTED)
        self.assertTrue(v.revert_plan.auto)

    def test_ambiguous_conflict(self):
        # REJECT but sequential CONFIRMED -> genuine conflict -> operator.
        v = ev.decide(make_entry(), OK_EXEC, {"safety_gate": "REJECT", "sequential": "confirmed"})
        self.assertEqual(v.action, ev.CAT_AMBIGUOUS)
        self.assertEqual(v.ledger_status, ev.HELD_AMBIGUOUS)
        self.assertIsNotNone(v.op_bundle_row)
        self.assertTrue(v.op_bundle_row.options)

    def test_ambiguous_missing_sequential(self):
        # paired_sequential requires a sequential verdict; absent -> ambiguous.
        v = ev.decide(make_entry(), OK_EXEC, {"safety_gate": "PASS"})
        self.assertEqual(v.action, ev.CAT_AMBIGUOUS)

    def test_ambiguous_operator_gate_becomes_op_gate(self):
        e = make_entry(operator_gates=["OP-6"])
        v = ev.decide(e, OK_EXEC, {"safety_gate": "REJECT", "sequential": "confirmed"})
        self.assertEqual(v.action, ev.CAT_AMBIGUOUS)
        self.assertEqual(v.ledger_status, ev.HELD_OP_GATE)
        self.assertTrue(any("OP-6" in o for o in v.op_bundle_row.options))

    def test_pass_rule_requires_metric_count_signal(self):
        gate_table = [
            {
                "gate": "Does EV-4 produce a complete calibration baseline?",
                "evidence": "6 metrics per role",
                "fork": {
                    "pass": {
                        "rule": "all 6 metrics recorded per role AND confidence distribution non-degenerate",
                        "action": ["flip EV-4"],
                        "next": "DONE_PASS",
                    },
                    "marginal": {
                        "rule": "all metrics recorded but confidence is the binary float(correct) proxy",
                        "action": ["record observation"],
                        "next": "DONE_MARGINAL_OBS",
                    },
                    "ambiguous": {
                        "action": ["operator adjudicate"],
                        "next": "HELD_AMBIGUOUS",
                    },
                },
            }
        ]
        e = make_entry(task_id="EV-4", gate_table=gate_table)
        v = ev.decide(e, OK_EXEC, {"safety_gate": "PASS", "sequential": "confirmed"})
        self.assertEqual(v.action, ev.CAT_AMBIGUOUS)
        self.assertEqual(v.ledger_status, ev.HELD_AMBIGUOUS)
        self.assertTrue(any("metric completeness" in r for r in v.reasons))

    def test_pass_rule_downgrades_degenerate_confidence_to_marginal(self):
        gate_table = [
            {
                "gate": "Does EV-4 produce a complete calibration baseline?",
                "evidence": "6 metrics per role",
                "fork": {
                    "pass": {
                        "rule": "all 6 metrics recorded per role AND confidence distribution non-degenerate",
                        "action": ["flip EV-4"],
                        "next": "DONE_PASS",
                    },
                    "marginal": {
                        "rule": "all metrics recorded but confidence is the binary float(correct) proxy",
                        "action": ["record observation"],
                        "next": "DONE_MARGINAL_OBS",
                    },
                    "ambiguous": {
                        "action": ["operator adjudicate"],
                        "next": "HELD_AMBIGUOUS",
                    },
                },
            }
        ]
        e = make_entry(task_id="EV-4", gate_table=gate_table)
        v = ev.decide(
            e,
            OK_EXEC,
            {
                "safety_gate": "PASS",
                "sequential": "confirmed",
                "metrics_complete": True,
                "confidence_source": "binary float(correct) proxy",
            },
        )
        self.assertEqual(v.action, ev.CAT_MARGINAL)
        self.assertEqual(v.ledger_status, ev.DONE_MARGINAL_OBS)
        self.assertTrue(any("downgraded PASS to MARGINAL" in r for r in v.reasons))

    def test_pass_rule_accepts_complete_nondegenerate_metrics(self):
        gate_table = [
            {
                "gate": "Does EV-4 produce a complete calibration baseline?",
                "evidence": "6 metrics per role",
                "fork": {
                    "pass": {
                        "rule": "all 6 metrics recorded per role AND confidence distribution non-degenerate",
                        "action": ["flip EV-4"],
                        "next": "DONE_PASS",
                    },
                    "ambiguous": {
                        "action": ["operator adjudicate"],
                        "next": "HELD_AMBIGUOUS",
                    },
                },
            }
        ]
        e = make_entry(task_id="EV-4", gate_table=gate_table)
        v = ev.decide(
            e,
            OK_EXEC,
            {
                "safety_gate": "PASS",
                "sequential": "confirmed",
                "metric_count": 6,
                "required_metric_count": 6,
                "confidence_nondegenerate": True,
            },
        )
        self.assertEqual(v.action, ev.CAT_PASS)
        self.assertEqual(v.ledger_status, ev.DONE_PASS)


class TestAutonomyPolicyRevertScope(unittest.TestCase):
    def test_reference_relaunch_auto(self):
        e = make_entry(flags_required=None, stack_lineup="reference-v6")
        v = ev.decide(e, OK_EXEC, {"safety_gate": "PASS", "sequential": "refuted"})
        self.assertEqual(v.ledger_status, ev.FAILED_REVERTED)
        self.assertIn("reference_relaunch", v.revert_plan.kind)
        self.assertEqual(v.revert_plan.reference_lineup, "reference-v6")

    def test_combined_flags_and_relaunch(self):
        e = make_entry(flags_required={"GGML_FOO": 1}, stack_lineup="reference-v6")
        v = ev.decide(e, OK_EXEC, {"safety_gate": "PASS", "sequential": "refuted"})
        self.assertEqual(v.revert_plan.kind, "runtime_flags+reference_relaunch")

    def test_file_edit_fail_never_auto(self):
        # Even WITH flags available, a file/config-edit revert goes to op-bundle.
        e = make_entry(
            flags_required={"GGML_FOO": 1},
            fail_actions=["edit_file src/foo.py to restore prior behavior"],
        )
        v = ev.decide(e, OK_EXEC, {"safety_gate": "PASS", "sequential": "refuted"})
        self.assertEqual(v.action, ev.CAT_FAIL)
        self.assertEqual(v.ledger_status, ev.HELD_OP_GATE)  # NOT FAILED_REVERTED
        self.assertIsNone(v.revert_plan)
        self.assertIsNotNone(v.op_bundle_row)

    def test_config_edit_marker_never_auto(self):
        e = make_entry(
            flags_required={"GGML_FOO": 1},
            fail_actions=["revert_config orchestration/model_registry.yaml"],
        )
        v = ev.decide(e, OK_EXEC, {"safety_gate": "REJECT", "sequential": "accumulating"})
        self.assertEqual(v.ledger_status, ev.HELD_OP_GATE)

    def test_fail_no_mechanism_goes_to_op_bundle(self):
        # refuted, but no flags, no lineup, no recognized revert action -> operator.
        e = make_entry(fail_actions=["think about it"])
        v = ev.decide(e, OK_EXEC, {"safety_gate": "PASS", "sequential": "refuted"})
        self.assertEqual(v.action, ev.CAT_FAIL)
        self.assertEqual(v.ledger_status, ev.HELD_OP_GATE)
        self.assertIsNone(v.revert_plan)
        self.assertIsNotNone(v.op_bundle_row)


class TestNextAndNormalizers(unittest.TestCase):
    def test_next_task_scheduling(self):
        gt = make_gate_table()
        gt[0]["fork"]["pass"]["next"] = "EV-12"  # a task id, not a terminal status
        e = make_entry(gate_table=gt)
        v = ev.decide(e, OK_EXEC, {"safety_gate": "PASS", "sequential": "confirmed"})
        self.assertEqual(v.ledger_status, ev.DONE_PASS)  # default, since next is a task id
        self.assertEqual(v.next_task, "EV-12")

    def test_normalizers_accept_objects(self):
        class FakeGateVerdict:
            verdict = "reject"

        class FakeSeqView:
            state = "refuted"

        e = make_entry(flags_required={"GGML_FOO": 1})
        v = ev.decide(e, OK_EXEC, {"safety_gate": FakeGateVerdict(), "sequential": FakeSeqView()})
        self.assertEqual(v.action, ev.CAT_FAIL)

    def test_forced_category(self):
        v = ev.decide(make_entry(), OK_EXEC, {"category": "pass"})
        self.assertEqual(v.action, ev.CAT_PASS)

    def test_to_dict_shape(self):
        v = ev.decide(make_entry(), OK_EXEC, {"safety_gate": "PASS", "sequential": "confirmed"})
        d = v.to_dict()
        for key in ("action", "ledger_status", "reasons", "revert_plan", "op_bundle_row"):
            self.assertIn(key, d)


if __name__ == "__main__":
    unittest.main()
