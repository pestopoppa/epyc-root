"""Structural fixtures only; main reviews opportunity premises and actual verdicts."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "validate_intake", Path(__file__).resolve().parents[1] / "validate_intake.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
REVIEW_FIELDS = (
    "project_objective", "implementation_ref", "gap", "operational_change",
    "benefit_direction", "owner", "execution_conditions", "closure_basis")


class ValidateIntakePlanTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.categories = {"tool_implementation"}
        owner = self.root / "handoffs/active/owner.md"
        owner.parent.mkdir(parents=True)
        owner.write_text("# Synthetic current owner\n\n"
                         "- [ ] **WIRE-1 — Bind existing outputs.**\n"
                         "- [ ] **PE-USE — Exercise the ParEval consumer.**\n"
                         "- [ ] **PE-SCREEN — Compare retained outcomes.**\n"
                         "- [x] **TD-21 — Repair the existing artifact path.**\n",
                         encoding="utf-8")
        source = self.root / "synthetic-current.py"
        source.write_text("# Synthetic fulfilled GEPA path; PAW artifacts present.\n",
                          encoding="utf-8")
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        self.entries = [dict(
            id="intake-001", arxiv_id=None, url="https://example.invalid/fixture",
            source_type="repo", title="Synthetic fixture", categories=list(self.categories),
            novelty="medium", relevance="high", discovered_via="input",
            verdict="worth_investigating", ingested_date="2026-10-04",
            verification="dive-verified", handoffs_updated=[], handoffs_created=[],
            key_claims=["Synthetic fixture, no factual research warrant."],
            claim_corrections=[dict(claim_index=0, effect="unaffected", note="Retain.")],
            future_field={"nested": ["preserve"]})]
        self.patch = dict(
            id="intake-001", integration_disposition="integrated",
            handoffs_updated=["owner.md"], handoffs_created=[],
            disposition_evidence=["P1 / WIRE-1; PE-USE; PE-SCREEN in owner.md"])
        self.review = dict(
            project_objective="Exercise the operational consumer with current artifacts.",
            implementation_ref=f"synthetic-current.py sha256:{source_hash}",
            gap="Synthetic operational comparison remains after enabling wiring.",
            operational_change="Wire outputs, exercise the consumer, compare outcomes.",
            benefit_direction="Lower avoidable cost; preserve correctness.", owner="owner.md",
            execution_conditions="Isolated sidecar allowed; native inference needs its window.",
            closure_basis="No closure: operational and enabling actions remain distinct.")
        self.rows = [
            dict(ledger_id="PE-WIRING", source="intake-001",
                 action="Bind outputs", terminal_mapping="primitive-now → P1 / WIRE-1"),
            dict(ledger_id="PE-USE", source="intake-001",
                 action="Exercise consumer", terminal_mapping="cheap-screen → P1 / PE-USE"),
            dict(ledger_id="PE-SCREEN", source="intake-001",
                 action="Compare outcomes", terminal_mapping="cheap-screen → P1 / PE-SCREEN")]
        self.plan = self.root / "plan.md"
        self.session = dict(
            stage="stage4-complete", stage4={"status": "complete", "reconciled": True},
            entries_remaining=[], entries_processed=["intake-001"], steering_ledger=[],
            actionable_ledger=copy.deepcopy(self.rows),
            stage3_filing=dict(entry_updates=[self.patch], opportunity_reviews={"P1": self.review}))
        self.write_plan()
        self.checkpoint = self.root / ".research-session.json"
        self.checkpoint.write_text(json.dumps(self.session), encoding="utf-8")

    def write_plan(self, fence=False):
        table = "\n".join(
            f"| {r['ledger_id']} | {r['source']}#record | {r['action']} | {r['terminal_mapping']} |"
            for r in self.rows)
        text = ("# Synthetic approved plan\n\n"
                "| Packet | Objective | Existing owners |\n|---|---|---|\n"
                "| P1 | Exercise the operational consumer | owner.md |\n\n"
                "### P1 — Operational consumer\n"
                "- [ ] **WIRE-1 — Bind existing outputs.**\n"
                "- [ ] **PE-USE — Exercise the ParEval consumer.**\n"
                "- [ ] **PE-SCREEN — Compare retained outcomes.**\n\n"
                "## Complete recommendation mapping\n"
                "| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |\n"
                "|---|---|---|---|\n" + table + "\n")
        if fence:
            payload = dict(entry_updates=[self.patch], opportunity_reviews={"P1": self.review})
            text += "\n## Stage-3 filing payload\n\n```json\n" + json.dumps(payload) + "\n```\n"
        self.plan.write_text(text, encoding="utf-8")
        if "stage3_filing" in self.session:
            self.session["stage3_filing"]["plan_sha256"] = hashlib.sha256(
                self.plan.read_bytes()).hexdigest()

    def errors(self):
        before = copy.deepcopy((self.session, self.entries, self.categories))
        files = {p.relative_to(self.root): (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.root.rglob("*") if p.is_file()}
        errors = validator.validate_plan_payload(
            self.session, self.plan, self.entries, self.categories, self.root)
        self.assertEqual((self.session, self.entries, self.categories), before)
        self.assertEqual(
            {p.relative_to(self.root): (p.read_bytes(), p.stat().st_mtime_ns)
             for p in self.root.rglob("*") if p.is_file()}, files)
        self.assertIsInstance(errors, list)
        self.assertTrue(all(isinstance(error, str) and error.strip() for error in errors))
        return errors

    def test_valid_payload_and_legacy_index(self):
        self.assertEqual(validator.validate_index(self.entries, self.categories), [])
        self.assertEqual(self.errors(), [])

    def test_invalid_proposed_enum_with_valid_persisted_index(self):
        self.patch["integration_disposition"] = "integrated_existing"
        self.assertEqual(validator.validate_index(self.entries, self.categories), [])
        self.assertRegex("\n".join(self.errors()), "invalid integration_disposition")

    def test_nonexistent_integrated_owner(self):
        self.patch["handoffs_updated"] = ["missing-owner.md"]
        self.review["owner"] = "missing-owner.md"
        self.assertRegex("\n".join(self.errors()), "missing-owner")

    def test_duplicate_or_missing_recommendations(self):
        original = copy.deepcopy(self.rows)
        for location in ("plan", "ledger"):
            for mutation in ("duplicate", "missing"):
                with self.subTest(location=location, mutation=mutation):
                    rows = copy.deepcopy(original)
                    if mutation == "duplicate":
                        rows.append(copy.deepcopy(rows[0]))
                    else:
                        rows = rows[:1]  # Wiring cannot replace both operational rows.
                    self.rows = rows if location == "plan" else copy.deepcopy(original)
                    self.session["actionable_ledger"] = (
                        rows if location == "ledger" else copy.deepcopy(original))
                    self.write_plan()
                    self.assertTrue(self.errors())

    def test_owner_task_and_dangling_plan_or_task_references(self):
        for target, valid in (
                ("P1 / TD-21", True), ("P404 / PE-USE", False), ("P1 / MISSING-TASK", False)):
            with self.subTest(target=target):
                for rows in (self.rows, self.session["actionable_ledger"]):
                    rows[1]["terminal_mapping"] = f"cheap-screen → {target}"
                self.write_plan()
                errors = self.errors()
                if valid:
                    self.assertEqual(errors, [])
                else:
                    self.assertTrue(errors)

    def test_stale_plan_hash(self):
        self.plan.write_bytes(self.plan.read_bytes() + b"\nChanged scope.\n")
        self.assertRegex("\n".join(self.errors()), "(?i)hash|sha256|digest")

    def test_packaged_new_owner_and_index_link(self):
        index = self.root / "handoffs/active/research-evaluation-index.md"
        index.write_text("# Synthetic index\n", encoding="utf-8")
        stub = dict(path="handoffs/active/new-owner.md",
                    content="# New owner\n\n- [ ] **NEW-1 — Bounded task.**\n",
                    index_file="handoffs/active/research-evaluation-index.md",
                    index_row="| RE-1 | Evaluation | [New](new-owner.md) | Run bounded task | — |")
        self.session["stage3_filing"]["proposed_stubs"] = [stub]
        self.patch["handoffs_updated"] = ["new-owner.md"]
        self.review["owner"] = "new-owner.md"
        for rows in (self.rows, self.session["actionable_ledger"]):
            rows[1]["terminal_mapping"] = "cheap-screen → P1 / NEW-1"
        self.write_plan()
        self.assertEqual(self.errors(), [])
        stub["index_row"] = "| RE-1 | Evaluation | [Wrong](wrong.md) | Run bounded task | — |"
        self.assertRegex("\n".join(self.errors()), "packaged handoff")

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            json.loads('{"entry_updates": [], "entry_updates": []}',
                       object_pairs_hook=validator._unique_json_object)

    def test_unsupported_or_malformed_payload_shapes(self):
        original = copy.deepcopy(self.session)
        cases = (
            ("stage3_filing", []),
            ("entry_updates", {"intake-001": self.patch}),
            ("entry_updates", [dict(id="intake-001", updates=self.patch)]),
            ("opportunity_reviews", [self.review]),
            ("actionable_ledger", {"PE-WIRING": self.rows[0]}))
        for field, value in cases:
            with self.subTest(field=field, value=value):
                self.session = copy.deepcopy(original)
                target = (self.session if field in {"stage3_filing", "actionable_ledger"}
                          else self.session["stage3_filing"])
                target[field] = copy.deepcopy(value)
                self.assertRegex("\n".join(self.errors()), "unsupported format")
        self.session = copy.deepcopy(original)
        self.plan.write_text("# Unsupported inventory\n", encoding="utf-8")
        self.session["stage3_filing"]["plan_sha256"] = hashlib.sha256(self.plan.read_bytes()).hexdigest()
        self.assertRegex("\n".join(self.errors()), "unsupported format")

    def test_review_fields_are_required_not_keyword_graded(self):
        for field in REVIEW_FIELDS:
            with self.subTest(field=field):
                saved = self.review.pop(field)
                self.assertRegex("\n".join(self.errors()), "opportunity review requires")
                self.review[field] = saved

    def test_preapproval_fence_allows_old_mappings_but_requires_ledger_ids(self):
        self.write_plan(fence=True)
        self.session.pop("stage3_filing")
        self.session.update(stage=3, stage4={"status": "pending", "reconciled": False})
        for mapping in (None, "stale checkpoint mapping"):
            for row in self.session["actionable_ledger"]:
                row.pop("terminal_mapping", None)
                if mapping is not None:
                    row["terminal_mapping"] = mapping
            self.checkpoint.write_text(json.dumps(self.session), encoding="utf-8")
            self.assertEqual(self.errors(), [])
            self.assertNotIn("stage3_filing", self.session)
        self.assertFalse(validator.session_cleanup_eligible(self.session))
        self.session["actionable_ledger"].pop()
        self.assertRegex("\n".join(self.errors()), "coverage mismatch")
        self.session["actionable_ledger"][0].pop("ledger_id")
        self.assertRegex("\n".join(self.errors()), "ledger_id")

    def test_gepa_and_paw_context_fixtures_preserve_reviews(self):
        contexts = (
            ("GEPA-historical", "Historical defect; current synthetic path is fulfilled."),
            ("GEPA-current", "Current behavior fulfilled; synthetic consumer work remains."),
            ("PAW-current", "Stale availability versus current artifacts and completed TD-21."))
        for name, gap in contexts:
            with self.subTest(fixture=name):
                self.review.update(gap=gap, operational_change=f"Review current {name} opportunity.")
                self.assertEqual(self.errors(), [])
                self.assertEqual(self.review["gap"], gap)

    def test_risk_only_and_nondeployment_closures_require_main_review(self):
        self.patch.update(integration_disposition="knowledge_only", handoffs_updated=[])
        for basis in ("Nondeployment alone", "HIGH/CRITICAL graph risk alone"):
            with self.subTest(basis=basis):
                self.review["closure_basis"] = basis
                self.assertEqual(self.errors(), [])  # Presence is not semantic approval.
                self.assertEqual(self.review["closure_basis"], basis)

    def test_sidecar_permission_and_inference_gate_remain_distinct(self):
        conditions = "Isolated sidecar permitted now; native inference needs an owned window."
        self.review["execution_conditions"] = conditions
        self.assertEqual(self.errors(), [])
        self.assertEqual(self.review["execution_conditions"], conditions)
        self.assertEqual(len(self.session["actionable_ledger"]), 3)

    def test_cleanup_requires_reconciled_completed_stage4(self):
        for stage in (1, 3, "stage1-complete", "stage4-in-progress"):
            with self.subTest(stage=stage):
                self.assertFalse(validator.session_cleanup_eligible(dict(self.session, stage=stage)))
        for reconciled in (None, False, "true"):
            session = dict(self.session, stage4={"status": "complete", "reconciled": reconciled})
            self.assertFalse(validator.session_cleanup_eligible(session))
        self.assertFalse(validator.session_cleanup_eligible(
            dict(self.session, stage4={"status": "complete"})))
        self.assertFalse(validator.session_cleanup_eligible(
            dict(self.session, stage=4, stage4={"status": "pending", "reconciled": True})))
        before = copy.deepcopy(self.session)
        self.assertTrue(validator.session_cleanup_eligible(self.session))
        self.assertTrue(validator.session_cleanup_eligible(dict(self.session, stage=4)))
        self.assertEqual(self.session, before)
