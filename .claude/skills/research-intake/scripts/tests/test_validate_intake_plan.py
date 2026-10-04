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
TASK_LINES = {
    "WIRE-1": "- [ ] **WIRE-1 — Bind existing outputs.**",
    "PE-USE": "- [ ] **PE-USE — Exercise the ParEval consumer.**",
    "PE-SCREEN": "- [ ] **PE-SCREEN — Compare retained outcomes.**",
}

# Independent-main review fixtures derived from the practical-applications review.
# These are recorded judgments about operational purpose, never classifier inputs.
# Both variants can be structurally valid when a record falsely asserts preservation.
OPERATIONAL_CASES = (
    dict(name="monty-containment", task_id="D-RI-CONTAIN",
         required_outcome="Reclaim over-budget computation and contain callbacks and output.",
         bad_task="Poison the persistent namespace after a timeout.",
         bad_acceptance="Prove the timed-out namespace cannot be persisted or reused.",
         bad_review="Poisoning does not terminate the running thread or bound callbacks/output.",
         preserved_task="Add a killable, resource-limited CPython execution lane.",
         preserved_acceptance="Terminate and reap the captured worker on timeout; revoke callbacks, "
                              "bound output, reject late replies and restore completed state.",
         preserved_review="Worker lifetime and resource limits address the remaining containment gap."),
    dict(name="monty-runtime-slice", task_id="D-RI-MONTY-SLICE",
         required_outcome="Exercise admitted REPL operations in a persistent Monty adapter.",
         bad_task="Write a Monty compatibility and sandbox requirements matrix.",
         bad_acceptance="Retain the compatibility document and publisher startup comparisons.",
         bad_review="A requirements matrix does not execute current cells or prove state/callback parity.",
         preserved_task="Implement and run the restricted Monty adapter on twelve existing REPL cases.",
         preserved_acceptance="Retain actual feeds, state continuity, FINAL/artifact outputs, callback "
                              "refusals and worker disposal against warm and contained CPython.",
         preserved_review="The bounded runnable adapter tests admitted current operations."),
    dict(name="sdm-runtime-scorer", task_id="LRC-SDM-ACTION-SCORER",
         required_outcome="Score changing runtime actions from supported decision outcomes.",
         bad_task="Repair extraction provenance and bind the selected routing snapshot.",
         bad_acceptance="Retain a correctly attributed snapshot and its extraction receipt.",
         bad_review="Correct provenance does not implement the runtime action scorer or test alternatives.",
         preserved_task="Implement the bounded SDM runtime action scorer and cached comparison.",
         preserved_acceptance="Score admitted role menus against the incumbent with retained per-action "
                              "outcomes; keep unobserved alternatives unlabeled and failures counted.",
         preserved_review="Runtime scoring and the cached comparison preserve the changed-menu opportunity."),
    dict(name="cross-harness-execution", task_id="TU-MH-1",
         required_outcome="Compare actual tool execution across current harnesses.",
         bad_task="Add a carrier that captures cross-harness receipts.",
         bad_acceptance="Verify receipt schema and provenance bindings.",
         bad_review="Capture wiring alone does not run harnesses or produce comparable execution outcomes.",
         preserved_task="Run the current cross-harness execution comparison on frozen cases.",
         preserved_acceptance="Retain proposed and executed actions, outputs, invalids and refusals "
                              "per harness under the same inputs and predeclared rule.",
         preserved_review="Actual harness executions supply the findings the existing carrier records."),
    dict(name="sft-execution-selection", task_id="S2-CGE-1",
         required_outcome="Select SFT candidates using actual execution outcomes.",
         bad_task="Project SFT candidate capture receipts into the existing carrier.",
         bad_acceptance="Retain provenance-complete candidate receipts.",
         bad_review="Candidate receipts do not execute candidates or establish execution-based selection.",
         preserved_task="Execute the bounded SFT candidate comparison and select from retained outcomes.",
         preserved_acceptance="Keep frozen candidate/input identities, actual successes and failures, "
                              "untouched evaluation cases and the predeclared selection rule.",
         preserved_review="The execution comparison supplies the operational selection evidence."),
    dict(name="looped-native-feasibility", task_id="RC-XLLM-PREFILL-1",
         required_outcome="Determine bounded native looped-model feasibility on the selected runtime.",
         bad_task="Check for a production-ready GGUF and review production admission.",
         bad_acceptance="Record that no admitted production artifact is available.",
         bad_review="GGUF/admission availability does not settle native-runtime feasibility.",
         preserved_task="Run a bounded native looped prefill feasibility probe under its actual window.",
         preserved_acceptance="Retain native artifact/runtime identity, outputs, failures and resource "
                              "requirements; keep feasibility separate from production admission.",
         preserved_review="A coordinated native probe addresses feasibility without implying cutover."),
    dict(name="risk-freeze-only-closure", task_id="SAFE-PROBE",
         required_outcome="Retain useful isolated implementation or probing before production activation.",
         bad_task="Close the opportunity because activation is frozen and graph risk is HIGH/CRITICAL.",
         bad_acceptance="Record only the activation freeze and graph risk flag.",
         bad_review="Activation freeze and graph risk alone do not establish that no useful immediate step remains.",
         preserved_task="Preserve the bounded isolated probe with safeguards and a separate activation gate.",
         preserved_acceptance="Record the actual probe conditions, conformance outputs and rollback "
                              "safeguards; require cutover approval only for activation.",
         preserved_review="Separately reviewed execution conditions preserve the permitted immediate opportunity."),
)


def v2_payload(rows, patch, review, steering=()):
    """Valid synthetic defaults; no inference about operational equivalence."""
    return dict(
        format_version=2, entry_updates=[copy.deepcopy(patch)],
        opportunity_reviews={"P1": copy.deepcopy(review)},
        actionable_additions=[], steering_reconciliation=copy.deepcopy(list(steering)),
        proposed_tasks=[],
        opportunity_scan=[dict(
            scan_id=f"SCAN-{i}", source_ref="intake-001#00 synthetic passage",
            implementation_ref=review["implementation_ref"],
            mechanism=row["action"], consumer="Synthetic operational consumer",
            application=row["action"], disposition="actionable",
            ledger_ids=[row["ledger_id"]], basis="Selected passage and current consumer read.")
            for i, row in enumerate(rows, 1)],
        outcome_reviews={row["ledger_id"]: dict(
            required_outcome=row["action"], review_status="preserved",
            review_basis="Main-reviewed synthetic task and operational acceptance.",
            task_refs=[dict(
                owner="owner.md", task_id=row["terminal_mapping"].split(" / ")[-1],
                task_text=TASK_LINES[row["terminal_mapping"].split(" / ")[-1]],
                acceptance=f"Verify the consumer outcome: {row['action']}.")])
            for row in rows})


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
            payload = v2_payload(self.rows, self.patch, self.review,
                                 self.session["steering_ledger"])
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

    def test_explicit_version_one_preserves_completed_stage4_legacy_validation(self):
        self.session["stage3_filing"]["format_version"] = 1
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


class ValidateIntakePlanV2Tests(unittest.TestCase):
    """Exercise the public API; successful structure never certifies semantics."""

    # Keep the completed, unversioned Stage-4 fixtures in the class above intact.
    write_plan = ValidateIntakePlanTests.write_plan
    errors = ValidateIntakePlanTests.errors

    def setUp(self):
        ValidateIntakePlanTests.setUp(self)
        self.payload = v2_payload(self.rows, self.patch, self.review)
        self.session.pop("stage3_filing")
        self.session.update(stage=3, stage4={"status": "pending", "reconciled": False})
        self.packet_rows = ""
        self.render()

    def render(self):
        self.write_plan()
        text = self.plan.read_text(encoding="utf-8")
        if self.packet_rows:
            text = text.replace("### P1 — Operational consumer",
                                self.packet_rows + "\n### P1 — Operational consumer")
        text += ("\n## Stage-3 filing payload\n\n```json\n"
                 + json.dumps(self.payload, ensure_ascii=False) + "\n```\n")
        self.plan.write_text(text, encoding="utf-8")
        if "stage3_filing" in self.session:
            self.session["stage3_filing"]["plan_sha256"] = hashlib.sha256(
                self.plan.read_bytes()).hexdigest()

    def assert_valid(self):
        self.render()
        self.assertEqual(self.errors(), [])

    def assert_invalid(self, diagnostic):
        self.render()
        self.assertRegex("\n".join(self.errors()), diagnostic)

    def reconcile_stage4(self):
        self.session.update(stage="stage4-complete",
                            stage4={"status": "complete", "reconciled": True})
        self.session["actionable_ledger"] = copy.deepcopy(self.rows)
        self.session["steering_ledger"] = copy.deepcopy(
            self.payload["steering_reconciliation"])
        self.session["stage3_filing"] = self.payload
        self.render()

    def add_delta(self):
        row = dict(ledger_id="PE-RUNTIME", source="intake-001",
                   action="Run the current consumer beyond output wiring",
                   terminal_mapping="cheap-screen → P1 / PE-RUNTIME")
        self.rows.append(row)
        self.payload["actionable_additions"] = [copy.deepcopy(row)]
        line = "- [ ] **PE-RUNTIME — Run the operational consumer.**"
        self.payload["proposed_tasks"] = [dict(owner="owner.md", task_text=line)]
        self.payload["outcome_reviews"][row["ledger_id"]] = dict(
            required_outcome=row["action"], review_status="preserved",
            review_basis="Main reviewed the distinct operational follow-through.",
            task_refs=[dict(owner="owner.md", task_id="PE-RUNTIME", task_text=line,
                            acceptance="Retain actual execution outputs and failures.")])
        self.payload["opportunity_scan"].append(dict(
            scan_id="SCAN-RUNTIME", source_ref="intake-001#00 selected runtime passage",
            implementation_ref=self.review["implementation_ref"],
            mechanism="Execution beyond enabling wiring", consumer="Current consumer",
            application=row["action"], disposition="actionable",
            ledger_ids=[row["ledger_id"]], basis="Selected passage requires actual execution."))
        return row, line

    def steering_row(self, seq=1, **updates):
        row = dict(seq=seq, stage=2, verbatim="Keep actual consumer execution in the plan.",
                   disposition="planned", plan_ref="P1",
                   reason="The operational consumer is covered by P1.")
        row.update(updates)
        return row

    def test_valid_stage3_and_stage4_do_not_mutate_inputs_or_files(self):
        self.assert_valid()
        self.assertNotIn("stage3_filing", self.session)
        self.reconcile_stage4()
        self.assert_valid()

    def test_stage3_requires_integer_version_two(self):
        self.assert_valid()
        for value in (None, 1, 3, "2", True, 2.0, [], {}):
            with self.subTest(version=value):
                if value is None:
                    self.payload.pop("format_version", None)
                else:
                    self.payload["format_version"] = value
                self.assert_invalid("(?i)version|format")

    def test_stage4_does_not_fall_back_to_a_valid_fence(self):
        self.assert_valid()
        self.session.update(stage="stage4-complete")
        self.assert_invalid("(?i)persist|stage.?4|format")

    def test_required_v2_fields_have_explicit_shape_errors(self):
        self.assert_valid()
        original = copy.deepcopy(self.payload)
        shapes = {
            "actionable_additions": ({}, None, [None]),
            "steering_reconciliation": ({}, None, [None]),
            "opportunity_scan": ({}, None, [], [None]),
            "outcome_reviews": ([], None, {"PE-WIRING": None}),
            "proposed_tasks": ({}, None, [None]),
        }
        for field, values in shapes.items():
            for value in ("missing", *values):
                with self.subTest(field=field, value=value):
                    self.payload = copy.deepcopy(original)
                    if value == "missing":
                        self.payload.pop(field)
                    else:
                        self.payload[field] = value
                    self.assert_invalid("(?i)" + field + "|unsupported format")

    def test_stage3_delta_is_a_plan_only_union_and_stage4_requires_reconciliation(self):
        retained = copy.deepcopy(self.session["actionable_ledger"])
        _, line = self.add_delta()
        self.assert_valid()
        self.assertEqual(self.session["actionable_ledger"], retained)
        self.assertNotIn("PE-RUNTIME", (self.root / "handoffs/active/owner.md").read_text())
        self.session.update(stage="stage4-complete")
        self.session["stage3_filing"] = self.payload
        self.assert_invalid("(?i)addition|reconcil|coverage|applied|task")
        self.reconcile_stage4()
        self.assert_invalid("(?i)task|owner|applied")  # The proposed task is still unlanded.
        owner = self.root / "handoffs/active/owner.md"
        owner.write_text(owner.read_text() + line + "\n", encoding="utf-8")
        self.assert_valid()  # Addition occurs once in the reconciled retained ledger.
        self.assertEqual(len(self.session["actionable_ledger"]), 4)

    def test_addition_ids_cannot_duplicate_or_shadow_retained_rows(self):
        self.add_delta()
        self.assert_valid()
        original = copy.deepcopy(self.payload["actionable_additions"])
        for rows in (original + original, [copy.deepcopy(self.rows[0])]):
            with self.subTest(additions=rows):
                self.payload["actionable_additions"] = rows
                self.assert_invalid("(?i)addition|duplicate|shadow|retained")

    def test_additions_require_full_nonempty_records(self):
        self.add_delta()
        self.assert_valid()
        original = copy.deepcopy(self.payload["actionable_additions"][0])
        for field in ("ledger_id", "source", "action", "terminal_mapping"):
            for value in (None, "", "  ", [], 7):
                with self.subTest(field=field, value=value):
                    row = copy.deepcopy(original)
                    if value is None:
                        row.pop(field)
                    else:
                        row[field] = value
                    self.payload["actionable_additions"] = [row]
                    self.assert_invalid("(?i)addition|" + field + "|format")

    def test_retained_source_and_action_cannot_be_reworded_in_table(self):
        self.assert_valid()
        for field in ("source", "action"):
            with self.subTest(field=field):
                saved = self.rows[0][field]
                self.rows[0][field] = "Reworded retained value"
                self.assert_invalid("(?i)source|action|immutable|match|retained")
                self.rows[0][field] = saved

    def test_stage4_addition_record_must_match_reconciled_retained_row(self):
        _, line = self.add_delta()
        owner = self.root / "handoffs/active/owner.md"
        owner.write_text(owner.read_text() + line + "\n", encoding="utf-8")
        self.reconcile_stage4()
        self.assert_valid()
        original = copy.deepcopy(self.session["actionable_ledger"][-1])
        for field in ("source", "action", "terminal_mapping"):
            with self.subTest(field=field):
                self.session["actionable_ledger"][-1] = dict(original, **{field: "Changed"})
                self.assert_invalid("(?i)addition|reconcil|match|source|action|terminal")

    def test_steering_retained_and_new_rows_are_reconciled_without_checkpoint_write(self):
        retained = self.steering_row(ts="2026-10-04T08:00:00Z")
        self.session["steering_ledger"] = [copy.deepcopy(retained)]
        self.payload["steering_reconciliation"] = [retained, self.steering_row(2, stage=3)]
        self.assert_valid()
        self.assertEqual(len(self.session["steering_ledger"]), 1)
        self.reconcile_stage4()
        self.assert_valid()
        self.session["steering_ledger"].pop()
        self.assert_invalid("(?i)steering|reconcil")

    def test_steering_cannot_drop_reword_renumber_or_restage_retained_rows(self):
        retained = self.steering_row(ts="2026-10-04T08:00:00Z")
        self.session["steering_ledger"] = [copy.deepcopy(retained)]
        self.payload["steering_reconciliation"] = [copy.deepcopy(retained)]
        self.assert_valid()
        for field, value in (("seq", 2), ("stage", 1), ("verbatim", "Paraphrase"),
                             ("ts", "2026-10-04T09:00:00Z"), ("drop", None)):
            with self.subTest(field=field):
                row = dict(retained, **{field: value})
                self.payload["steering_reconciliation"] = [] if field == "drop" else [row]
                self.assert_invalid("(?i)steering|retained|verbatim")

    def test_steering_sequences_are_unique_increasing_and_typed(self):
        self.payload["steering_reconciliation"] = [self.steering_row(), self.steering_row(2)]
        self.assert_valid()
        for seqs in ((1, 1), (2, 1), (0, 1), (True, 2), ("1", 2), (1.0, 2)):
            with self.subTest(seqs=seqs):
                self.payload["steering_reconciliation"] = [self.steering_row(s) for s in seqs]
                self.assert_invalid("(?i)steering|seq")

    def test_steering_dispositions_and_references_require_grounded_records(self):
        for disposition in ("context-only", "declined"):
            with self.subTest(disposition=disposition):
                row = self.steering_row(disposition=disposition, plan_ref=None,
                                        reason="Current consumer already supplies this bounded behavior.")
                self.payload["steering_reconciliation"] = [row]
                self.assert_valid()
                for field, value in (("plan_ref", "P1"), ("reason", "")):
                    self.payload["steering_reconciliation"] = [dict(row, **{field: value})]
                    self.assert_invalid("(?i)steering|reason|plan_ref")
        for changes in (dict(plan_ref=None), dict(plan_ref="P404"),
                        dict(disposition="pending"), dict(verbatim=""), dict(stage=[])):
            with self.subTest(changes=changes):
                self.payload["steering_reconciliation"] = [self.steering_row(**changes)]
                self.assert_invalid("(?i)steering|reference|format")

    def test_malformed_retained_steering_is_not_hidden_by_reconciliation(self):
        valid = self.steering_row()
        self.payload["steering_reconciliation"] = [copy.deepcopy(valid)]
        for retained in ({}, [None], [dict(valid, seq="1")], [dict(valid, verbatim=[])],
                         [valid, valid]):
            with self.subTest(retained=retained):
                self.session["steering_ledger"] = copy.deepcopy(retained)
                self.assert_invalid("(?i)steering|retained|format")

    def test_scan_catches_an_application_missing_from_both_inventories(self):
        self.assert_valid()
        # Keep the independent source scan while removing both ID inventories and the review.
        rid = self.rows.pop()["ledger_id"]
        self.session["actionable_ledger"].pop()
        self.payload["outcome_reviews"].pop(rid)
        self.assert_invalid("(?i)scan|" + rid)

    def test_every_recommendation_requires_scan_coverage(self):
        self.assert_valid()
        self.payload["opportunity_scan"].pop()
        self.assert_invalid("(?i)scan|coverage")

    def test_scan_ids_records_and_actionable_references_are_validated(self):
        self.assert_valid()
        original = copy.deepcopy(self.payload["opportunity_scan"])
        mutations = [(field, "") for field in (
            "scan_id", "source_ref", "implementation_ref", "mechanism", "consumer", "application")]
        mutations += [("disposition", "pending"), ("ledger_ids", []),
                      ("ledger_ids", "PE-WIRING"), ("ledger_ids", ["ABSENT-ID"])]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                self.payload["opportunity_scan"] = copy.deepcopy(original)
                self.payload["opportunity_scan"][0][field] = value
                self.assert_invalid("(?i)scan|" + field + "|ABSENT-ID")
        self.payload["opportunity_scan"] = original + [copy.deepcopy(original[0])]
        self.assert_invalid("(?i)scan|duplicate")

    def test_scan_nonactionable_dispositions_need_basis_and_may_cover_existing_action(self):
        original = copy.deepcopy(self.payload["opportunity_scan"])
        for disposition in ("covered", "context-only", "declined"):
            with self.subTest(disposition=disposition):
                self.payload["opportunity_scan"] = copy.deepcopy(original)
                row = self.payload["opportunity_scan"][0]
                row.update(disposition=disposition, basis="Explicit selected-source review basis.")
                self.assert_valid()  # Its existing ledger reference remains covered.
                extra = dict(row, scan_id="SCAN-CONTEXT", ledger_ids=[])
                self.payload["opportunity_scan"].append(extra)
                self.assert_valid()
                extra["basis"] = ""
                self.assert_invalid("(?i)scan|basis")

    def test_outcome_review_keys_match_every_recommendation_exactly(self):
        self.assert_valid()
        original = copy.deepcopy(self.payload["outcome_reviews"])
        for mutation in ("missing", "extra"):
            with self.subTest(mutation=mutation):
                self.payload["outcome_reviews"] = copy.deepcopy(original)
                if mutation == "missing":
                    self.payload["outcome_reviews"].pop("PE-USE")
                else:
                    self.payload["outcome_reviews"]["UNDECLARED-RID"] = copy.deepcopy(original["PE-USE"])
                self.assert_invalid("(?i)outcome|review|recommendation")

    def test_unresolved_or_malformed_outcome_reviews_fail_explicitly(self):
        self.assert_valid()
        original = copy.deepcopy(self.payload["outcome_reviews"]["PE-USE"])
        for field, values in {
            "required_outcome": ("", None, []), "review_basis": ("", None, []),
            "review_status": ("unresolved", "pending", "approved", None),
            "task_refs": ([], {}, [None]),
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.payload["outcome_reviews"]["PE-USE"] = dict(original, **{field: value})
                    self.assert_invalid("(?i)outcome|review|task|" + field)
        self.payload["outcome_reviews"]["PE-USE"] = dict(original, review_status="closed-with-basis")
        self.assert_invalid("(?i)immediate|preserved|outcome|review")

    def test_task_ref_requires_nonempty_text_and_exact_checkbox_id(self):
        self.assert_valid()
        original = copy.deepcopy(self.payload["outcome_reviews"]["PE-USE"]["task_refs"][0])
        for field in ("owner", "task_id", "task_text", "acceptance"):
            for value in (None, "", [], 12):
                with self.subTest(field=field, value=value):
                    ref = dict(original)
                    if value is None:
                        ref.pop(field)
                    else:
                        ref[field] = value
                    self.payload["outcome_reviews"]["PE-USE"]["task_refs"] = [ref]
                    self.assert_invalid("(?i)task|owner|acceptance|outcome|format")
        self.payload["outcome_reviews"]["PE-USE"]["task_refs"] = [dict(original, task_id="WIRE-1")]
        self.assert_invalid("(?i)task|match|id")

    def test_task_in_another_owner_cannot_satisfy_the_reference(self):
        other = self.root / "handoffs/active/other.md"
        other.write_text("# Other owner\n\n" + TASK_LINES["PE-USE"] + "\n", encoding="utf-8")
        self.payload["entry_updates"][0]["handoffs_updated"].append("other.md")
        self.assert_valid()
        ref = self.payload["outcome_reviews"]["PE-WIRING"]["task_refs"][0]
        ref["owner"] = "other.md"
        self.assert_invalid("(?i)task|owner|WIRE-1")

    def test_task_text_must_match_exact_current_checkbox_line(self):
        self.assert_valid()
        ref = self.payload["outcome_reviews"]["PE-USE"]["task_refs"][0]
        ref["task_text"] = "- [ ] **PE-USE — Merely wire an output receipt.**"
        self.assert_invalid("(?i)task|match|owner")

    def test_plan_table_json_and_owner_mentions_do_not_define_a_task(self):
        self.assert_valid()
        owner = self.root / "handoffs/active/owner.md"
        original = owner.read_text()
        for mention in ("**PE-USE — Exercise the ParEval consumer.**",
                        "| PE-USE | Mention in a table |", '{"task_id": "PE-USE"}'):
            with self.subTest(mention=mention):
                owner.write_text(original.replace(TASK_LINES["PE-USE"], mention), encoding="utf-8")
                self.assert_invalid("(?i)task|owner|PE-USE")

    def test_undefined_task_is_not_rescued_by_a_terminal_mention(self):
        self.rows[1]["terminal_mapping"] = "cheap-screen → P1 / NO-TASK"
        ref = self.payload["outcome_reviews"]["PE-USE"]["task_refs"][0]
        ref.update(task_id="NO-TASK", task_text="- [ ] **NO-TASK — Undefined task.**")
        self.assert_invalid("(?i)task|undefined|NO-TASK")

    def test_proposed_tasks_bind_exact_owner_line_and_unique_owner_id(self):
        self.add_delta()
        self.assert_valid()
        original = copy.deepcopy(self.payload["proposed_tasks"])
        other = self.root / "handoffs/active/other.md"
        other.write_text("# Other owner\n", encoding="utf-8")
        cases = [original + original, [dict(original[0], owner="other.md")],
                 [dict(original[0], task_text="- [ ] **PE-RUNTIME — Reworded task.**")],
                 [dict(original[0], owner="missing.md")],
                 [dict(original[0], task_text="PE-RUNTIME appears in prose")]]
        for tasks in cases:
            with self.subTest(tasks=tasks):
                self.payload["proposed_tasks"] = tasks
                self.assert_invalid("(?i)task|owner|duplicate|match|format")

    def test_proposed_task_ids_can_repeat_in_distinct_owners(self):
        _, line = self.add_delta()
        other = self.root / "handoffs/active/other.md"
        other.write_text("# Other owner\n", encoding="utf-8")
        self.payload["proposed_tasks"].append(dict(owner="other.md", task_text=line))
        self.payload["outcome_reviews"]["PE-RUNTIME"]["task_refs"].append(dict(
            owner="handoffs/active/other.md", task_id="PE-RUNTIME", task_text=line,
            acceptance="Exercise the distinct consumer adoption under this owner."))
        self.assert_valid()  # Identity is (resolved owner, ID), not a corpus-wide ID.

    def test_stage3_proposed_task_resolves_against_packaged_stub(self):
        row, line = self.add_delta()
        index = self.root / "handoffs/active/research-evaluation-index.md"
        index.write_text("# Synthetic domain index\n", encoding="utf-8")
        self.payload["proposed_stubs"] = [dict(
            path="handoffs/active/new-owner.md", content="# New owner\n\n" + line + "\n",
            index_file="handoffs/active/research-evaluation-index.md",
            index_row="| RE-1 | Evaluation | [New](new-owner.md) | Run bounded task | — |")]
        self.payload["entry_updates"][0]["handoffs_created"] = ["new-owner.md"]
        self.payload["proposed_tasks"][0]["owner"] = "new-owner.md"
        ref = self.payload["outcome_reviews"][row["ledger_id"]]["task_refs"][0]
        ref["owner"] = "new-owner.md"
        self.assert_valid()
        self.payload["proposed_tasks"][0]["owner"] = "owner.md"
        self.payload["proposed_stubs"][0]["content"] = "# New owner\n\nOnly mentions PE-RUNTIME.\n"
        self.assert_invalid("(?i)task|owner|stub|match")

    def test_monitor_and_knowledge_packets_require_full_opportunity_reviews(self):
        for packet, disposition in (("K1", "knowledge-only"), ("M1", "monitor")):
            with self.subTest(packet=packet):
                self.packet_rows = f"| {packet} | Grounded contextual closure | owner.md |\n"
                self.rows[1]["terminal_mapping"] = f"{disposition} → {packet}"
                outcome = self.payload["outcome_reviews"]["PE-USE"]
                outcome.update(review_status="closed-with-basis", task_refs=[],
                               review_basis="Reviewed immediate behavior; retained named future trigger.")
                self.payload["opportunity_reviews"][packet] = copy.deepcopy(self.review)
                self.assert_valid()
                for field in REVIEW_FIELDS:
                    saved = self.payload["opportunity_reviews"][packet].pop(field)
                    self.assert_invalid("(?i)opportunity|review|" + field)
                    self.payload["opportunity_reviews"][packet][field] = saved
                self.payload["opportunity_reviews"].pop(packet)
                self.assert_invalid("(?i)opportunity|review|" + packet)
                self.packet_rows = ""

    def test_decline_without_packet_requires_explicit_closed_review(self):
        self.rows[1]["terminal_mapping"] = "decline: Reviewed bounded opportunity and closed it."
        outcome = self.payload["outcome_reviews"]["PE-USE"]
        outcome.update(review_status="closed-with-basis", task_refs=[],
                       review_basis="Main reviewed the selected source and current consumer.")
        self.assert_valid()
        outcome["review_basis"] = ""
        self.assert_invalid("(?i)review|basis|outcome")

    def test_duplicate_json_keys_are_rejected_through_the_public_api(self):
        self.assert_valid()
        text = self.plan.read_text()
        text = text.replace('"format_version": 2', '"format_version": 2, "format_version": 2', 1)
        self.plan.write_text(text, encoding="utf-8")
        self.assertRegex("\n".join(self.errors()), "(?i)duplicate JSON key")

    def test_stage4_explicit_unsupported_versions_do_not_use_legacy_path(self):
        self.reconcile_stage4()
        self.assert_valid()
        for value in (True, 3, "2", 2.0, None):
            with self.subTest(version=value):
                self.payload["format_version"] = value
                self.assert_invalid("(?i)version|format")

    def test_stage3_existing_checkpoint_filing_cannot_bypass_version_two(self):
        self.assert_valid()
        legacy = dict(entry_updates=copy.deepcopy(self.payload["entry_updates"]),
                      opportunity_reviews=copy.deepcopy(self.payload["opportunity_reviews"]))
        for version in (None, 1):
            with self.subTest(version=version):
                self.session["stage3_filing"] = copy.deepcopy(legacy)
                if version is not None:
                    self.session["stage3_filing"]["format_version"] = version
                self.assert_invalid("(?i)version|stage.?3|format")

    def test_retained_actionable_rows_require_nonempty_immutable_fields(self):
        self.assert_valid()
        original = copy.deepcopy(self.session["actionable_ledger"])
        for field in ("ledger_id", "source", "action"):
            for value in (None, "", [], 12):
                with self.subTest(field=field, value=value):
                    self.session["actionable_ledger"] = copy.deepcopy(original)
                    row = self.session["actionable_ledger"][0]
                    if value is None:
                        row.pop(field)
                    else:
                        row[field] = value
                    self.assert_invalid("(?i)ledger|retained|" + field + "|format")

    def test_steering_stage4_matches_full_reconciliation_not_only_identity(self):
        self.payload["steering_reconciliation"] = [self.steering_row()]
        self.reconcile_stage4()
        self.assert_valid()
        original = copy.deepcopy(self.session["steering_ledger"][0])
        for field, value in (("disposition", "context-only"), ("plan_ref", None),
                             ("reason", "Different review rationale.")):
            with self.subTest(field=field):
                self.session["steering_ledger"] = [dict(original, **{field: value})]
                self.assert_invalid("(?i)steering|reconcil")

    def test_nonactionable_scan_references_must_resolve_when_present(self):
        self.assert_valid()
        original = copy.deepcopy(self.payload["opportunity_scan"][0])
        for disposition in ("covered", "context-only", "declined"):
            with self.subTest(disposition=disposition):
                row = dict(original, scan_id="SCAN-CLOSED", disposition=disposition,
                           ledger_ids=["NEVER-INVENTORIED"], basis="Grounded selected-source rationale.")
                self.payload["opportunity_scan"] = [*copy.deepcopy(
                    v2_payload(self.rows, self.patch, self.review)["opportunity_scan"]), row]
                self.assert_invalid("(?i)scan|NEVER-INVENTORIED")

    def test_stage3_unmapped_proposed_tasks_fail_even_with_valid_shape_and_owner_text(self):
        self.assert_valid()
        valid = dict(owner="owner.md", task_text="- [ ] **EXTRA-1 — Bounded optional task.**")
        self.payload["proposed_tasks"] = [valid]
        association_error = "(?i)unmapped|(?:outcome|recommendation).*task|task.*(?:outcome|associat|referenced)"
        self.assert_invalid(association_error)
        owner = self.root / "handoffs/active/owner.md"
        owner.write_text(owner.read_text() + valid["task_text"] + "\n", encoding="utf-8")
        self.assert_invalid(association_error)
        for field in ("owner", "task_text"):
            for value in (None, "", [], 12):
                with self.subTest(field=field, value=value):
                    task = dict(valid)
                    if value is None:
                        task.pop(field)
                    else:
                        task[field] = value
                    self.payload["proposed_tasks"] = [task]
                    self.assert_invalid("(?i)task|owner|format")

    def test_stage4_unmapped_proposed_tasks_fail_even_after_owner_line_is_applied(self):
        line = "- [ ] **EXTRA-1 — Bounded optional task.**"
        self.payload["proposed_tasks"] = [dict(owner="owner.md", task_text=line)]
        association_error = "(?i)unmapped|(?:outcome|recommendation).*task|task.*(?:outcome|associat|referenced)"
        self.assert_invalid(association_error)
        self.reconcile_stage4()
        self.assert_invalid(association_error)
        owner = self.root / "handoffs/active/owner.md"
        owner.write_text(owner.read_text() + line + "\n", encoding="utf-8")
        self.assert_invalid(association_error)

    def test_owner_aliases_cannot_evade_proposed_task_uniqueness(self):
        _, line = self.add_delta()
        self.assert_valid()
        self.payload["proposed_tasks"].append(
            dict(owner="handoffs/active/owner.md", task_text=line))
        self.assert_invalid("(?i)task|duplicate|owner")

    def test_stage3_refinement_requires_exact_previous_incumbent_line(self):
        previous = TASK_LINES["PE-USE"]
        replacement = "- [ ] **PE-USE — Execute the consumer and retain failures.**"
        self.payload["proposed_tasks"] = [dict(
            owner="owner.md", task_text=replacement, previous_task_text=previous)]
        ref = self.payload["outcome_reviews"]["PE-USE"]["task_refs"][0]
        ref["task_text"] = replacement
        self.assert_valid()
        task = self.payload["proposed_tasks"][0]
        for invalid in (None, "", "- [ ] **PE-USE — Stale incumbent wording.**",
                        TASK_LINES["WIRE-1"], [], 12):
            with self.subTest(previous_task_text=invalid):
                if invalid is None:
                    task.pop("previous_task_text", None)
                else:
                    task["previous_task_text"] = invalid
                self.assert_invalid("(?i)previous|incumbent|refin|task|match")

    def test_stage4_refinement_requires_replacement_applied_and_not_old_line(self):
        previous = TASK_LINES["PE-USE"]
        replacement = "- [ ] **PE-USE — Execute the consumer and retain failures.**"
        self.payload["proposed_tasks"] = [dict(
            owner="handoffs/active/owner.md", task_text=replacement,
            previous_task_text=previous)]
        ref = self.payload["outcome_reviews"]["PE-USE"]["task_refs"][0]
        ref.update(owner="owner.md", task_text=replacement)
        self.assert_valid()  # Canonical owner aliases bind the same refinement.
        self.reconcile_stage4()
        self.assert_invalid("(?i)task|owner|applied|match")
        owner = self.root / "handoffs/active/owner.md"
        original = owner.read_text()
        self.assertEqual(original.count(previous), 1)
        owner.write_text(original.replace(previous, replacement), encoding="utf-8")
        self.assert_valid()
        owner.write_text(original, encoding="utf-8")
        self.assert_invalid("(?i)task|owner|applied|match")

    def test_refinement_owner_aliases_cannot_duplicate_the_same_task_id(self):
        replacement = "- [ ] **PE-USE — Execute the consumer and retain failures.**"
        task = dict(owner="owner.md", task_text=replacement,
                    previous_task_text=TASK_LINES["PE-USE"])
        self.payload["proposed_tasks"] = [task]
        self.payload["outcome_reviews"]["PE-USE"]["task_refs"][0]["task_text"] = replacement
        self.assert_valid()
        self.payload["proposed_tasks"].append(dict(task, owner="handoffs/active/owner.md"))
        self.assert_invalid("(?i)duplicate|task|owner")

    def test_stage4_new_stub_and_index_row_must_match_the_applied_package(self):
        row, line = self.add_delta()
        index = self.root / "handoffs/active/research-evaluation-index.md"
        index.write_text("# Synthetic domain index\n", encoding="utf-8")
        stub = dict(
            path="handoffs/active/new-owner.md", content="# New owner\n\n" + line + "\n",
            index_file="handoffs/active/research-evaluation-index.md",
            index_row="| RE-1 | Evaluation | [New](new-owner.md) | Run bounded task | — |")
        self.payload["proposed_stubs"] = [stub]
        self.payload["entry_updates"][0]["handoffs_created"] = ["new-owner.md"]
        self.payload["proposed_tasks"][0]["owner"] = "new-owner.md"
        self.payload["outcome_reviews"][row["ledger_id"]]["task_refs"][0]["owner"] = "new-owner.md"
        self.assert_valid()
        self.reconcile_stage4()
        self.assert_invalid("(?i)stub|package|applied|task|owner")
        target = self.root / stub["path"]
        target.write_text(stub["content"], encoding="utf-8")
        index_text = "# Synthetic domain index\n\n" + stub["index_row"] + "\n"
        index.write_text(index_text, encoding="utf-8")
        self.assert_valid()
        target.write_text(stub["content"] + "\nUnapproved extra scope.\n", encoding="utf-8")
        self.assert_invalid("(?i)stub|content|package|match|applied")
        target.write_text(stub["content"], encoding="utf-8")
        index.write_text("# Synthetic domain index\n", encoding="utf-8")
        self.assert_invalid("(?i)stub|index|row|package|applied")
        index.write_text(index_text.replace("Run bounded task", "Run different task"), encoding="utf-8")
        self.assert_invalid("(?i)stub|index|row|package|match|applied")
        index.write_text(index_text, encoding="utf-8")
        self.assert_valid()

    def test_named_operational_cases_record_bad_and_preserved_semantic_expectations(self):
        """Main reviews the recorded judgments; the validator accepts honest structure only.

        A false assertion of preservation is intentionally structurally accepted.
        Absence/unresolved status is rejected for its missing review, not its wording.
        """
        owner = self.root / "handoffs/active/owner.md"
        owner_text = owner.read_text()
        original = copy.deepcopy(self.payload)
        for case in OPERATIONAL_CASES:
            for variant, expected_semantics in (("bad", "not-preserved"),
                                                 ("preserved", "preserved")):
                with self.subTest(case=case["name"], main_review=expected_semantics):
                    self.payload = copy.deepcopy(original)
                    self.rows[1]["terminal_mapping"] = f"cheap-screen → P1 / {case['task_id']}"
                    line = f"- [ ] **{case['task_id']} — {case[variant + '_task']}**"
                    owner.write_text(owner_text + line + "\n", encoding="utf-8")
                    semantic_expectation = dict(
                        case=case["name"], variant=variant, expected_outcome=expected_semantics,
                        rationale=case[variant + "_review"])
                    outcome = self.payload["outcome_reviews"]["PE-USE"]
                    outcome.update(
                        required_outcome=case["required_outcome"], review_status="preserved",
                        review_basis=semantic_expectation["rationale"],
                        task_refs=[dict(owner="owner.md", task_id=case["task_id"], task_text=line,
                                        acceptance=case[variant + "_acceptance"])])
                    scan = self.payload["opportunity_scan"][1]
                    scan.update(mechanism=case["required_outcome"], consumer=case["name"],
                                application=case["required_outcome"],
                                basis="Synthetic selected-source mechanism; independently reviewed purpose.")
                    self.payload["opportunity_reviews"]["P1"].update(
                        project_objective=case["required_outcome"],
                        operational_change=case[variant + "_task"],
                        closure_basis=case[variant + "_review"])
                    self.assert_valid()  # Presence/exact owner line cannot prove semantic equivalence.
                    self.assertEqual(outcome["review_basis"], semantic_expectation["rationale"])
                    self.assertEqual(outcome["required_outcome"], case["required_outcome"])
                    outcome["review_status"] = "unresolved"
                    self.assert_invalid("(?i)review|unresolved|status")

    def test_risk_and_freeze_only_closed_records_require_independent_main_review(self):
        self.packet_rows = "| M1 | Future activation trigger | owner.md |\n"
        self.rows[1]["terminal_mapping"] = "monitor → M1"
        self.payload["opportunity_reviews"]["M1"] = copy.deepcopy(self.review)
        outcome = self.payload["outcome_reviews"]["PE-USE"]
        outcome.update(review_status="closed-with-basis", task_refs=[])
        for basis, semantic_expectation in (
            ("Activation is frozen.", "not-closed: isolated work still requires review"),
            ("Graph risk is HIGH/CRITICAL.", "not-closed: safeguards still require review"),
            ("Current consumer already implements the selected behavior; only the named future "
             "activation trigger remains.", "closed only if main independently verifies the premise"),
        ):
            with self.subTest(main_review=semantic_expectation):
                outcome["review_basis"] = basis
                self.payload["opportunity_reviews"]["M1"]["closure_basis"] = basis
                self.assert_valid()  # Structural success never endorses the closure premise.
                self.assertEqual(outcome["review_basis"], basis)
