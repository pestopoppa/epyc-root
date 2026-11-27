"""Bind owner-only W66 adjudication to immutable source and control evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ADAPTER = ROOT / "coverage/w66-light-acceptance"
NATIVE = ROOT / "coverage/persistent-w66-light-12/runs/light-01/units"
LIGHT = ROOT / "coverage/w66-light-brief-v2/cases/DS41-W-66"
CONTROL = ROOT / "w66-receipt-identity-control"
SOURCE = "scripts/kernel_rnd/autokernel/loop/test_runtime_keep_source_continuity.py"
ORACLE = "54968138d7f0005acbe2f1c9ad07706015cab7baebb1e73f4d114ec84d9b8d5a"
ADAPTER_SHA = "89c009474ce5bd761068fb488e17480759bd7fc13c672ad21411d86cb1bb1abc"
CONTROL_SHA = "85075d9e8199128edec575e55eae65fb0bf0b3fa0b9141e44ed87000fe39ee6c"


def ref(path, sha=None):
    with path.open("rb") as stream:
        observed = hashlib.file_digest(stream, "sha256").hexdigest()
    if sha is not None and observed != sha:
        raise ValueError(f"pinned input changed: {path}")
    return {"path": str(path), "sha256": observed}


def load(path):
    return json.loads(path.read_bytes())


def write(name, report):
    with (HERE / name).open("x") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True) + "\n")


def prior_controls():
    seal = ref(CONTROL / "SOURCE-CONTROL.sha256", CONTROL_SHA)
    subprocess.run(["sha256sum", "-c", "--quiet", "SOURCE-CONTROL.sha256"],
                   cwd=CONTROL, check=True, timeout=15)
    selected = {}
    for name in ("full", "extra"):
        path = CONTROL / f"REPORT-{name}.json"
        selected[name] = ref(path)
    return {"seal": seal, **selected}


def check_evidence(row):
    for item in ("candidate_source", "evidence", "stdout", "stderr"):
        source = row[item]
        ref(Path(source["path"]), source["sha256"])
    return load(Path(row["evidence"]["path"]))


def bind_adjudication():
    scope = "preserving existing private-lock isolation and assertions"
    brief = LIGHT / "prompt.md"
    assert scope in brief.read_text()
    brief_ref = ref(brief, "c948ae10c650ec8f939b4bb4b0e6b39867db21538df009b405a4106d6e71faaf")
    source_before = LIGHT / "baseline" / SOURCE
    assert 'assert continuation["runtime_recipe_reference"] == {' in source_before.read_text()
    original_file = ref(source_before, "ec49d2f0607335d2a68c2522a9eee81fa379eb2e9d1d3f522af4e30c35096d83")
    original_oracle = ref(LIGHT / "oracle.py", ORACLE)

    unit = NATIVE / "gpu-DS41-W-66-off-common-light-v2"
    result_file = unit / "RESULT.json"
    result = load(result_file)
    oracle = result["oracle"]
    patch = ref(unit / "independent/candidate.patch", result["patch_sha256"])
    assert patch["sha256"] == "fc3c95b7d1a1ba2ec5239e78318ae29df9e85b700c0364906493f08c99283841"
    source = ref(unit / "independent/work" / SOURCE, result["changed_files"][SOURCE]["sha256"])
    assert result["status"] == "oracle_pass" and oracle["oracle_sha256"] == ORACLE and oracle["rc"] == 0
    assert oracle["semantic_review_required"]
    stdout = ref(unit / "ORACLE.stdout.log", oracle["stdout_sha256"])
    stderr = ref(unit / "ORACLE.stderr.log", oracle["stderr_sha256"])
    assert "2 passed in " in (unit / "ORACLE.stdout.log").read_text()

    controls = prior_controls()
    full = load(Path(controls["full"]["path"]))["rows"]
    cases = {}
    for name in ("gpu-off-light", "gpu-on-light", "main-light"):
        normal, mutated = (next(row for row in full if row["id"] == name and row["mode"] == mode)
                           for mode in ("original", "mutated"))
        assert normal["rc"] == 0 and normal["candidate_source"] == mutated["candidate_source"]
        initial = check_evidence(normal)
        replacement = check_evidence(mutated)
        assert initial["oracle_claim_observations"] == replacement["oracle_claim_observations"] == 2
        assert replacement["routing"]["phase_verified_before_change"]
        assert replacement["routing"]["original_read_proof_verified"]
        assert replacement["routing"]["same_content"]
        assert replacement["routing"]["replacement"] != replacement["routing"]["original"]
        catches = name != "gpu-off-light"
        assert mutated["rc"] == int(catches) and mutated["serial_receives_replacement"] is not catches
        assert not catches or mutated["failure_locations"]
        cases[name] = {"normal": normal, "mutated": mutated}
    assert cases["gpu-off-light"]["normal"]["candidate_source"] == source

    history = load(Path(controls["extra"]["path"]))["rows"]
    assert all(row["rc"] == 0 for row in history)
    assert all(row["serial_receives_replacement"] for row in history if row["mode"] == "mutated")
    review = {
        "schema": "taskflow.w66.light-v2.owner-adjudication.v1", "id": result["id"],
        "owner_decision": "reject_semantic_light_assertion_preservation",
        "raw_oracle": {"status": result["status"], "rc": oracle["rc"], "result": ref(result_file),
                       "oracle": original_oracle, "stdout": stdout, "stderr": stderr},
        "candidate": {"patch": patch, "edited_file": source},
        "actual_light_brief": {"source": brief_ref, "criterion": scope, "baseline_assertion_file": original_file},
        "existing_test_property": "The baseline continuation asserts exact equality to the fixture provider's expected runtime reference.",
        "observed_loss": "The Light OFF candidate can route a different valid receipt with the same payload through the real serial path, while both tests continue to pass. The Light ON and main variants catch that substitution at the original fixture-to-continuation identity assertion.",
        "distinction": "The separate continuation-to-child equality holds because both routing records carry the replacement. The historical detailed brief explicitly required this latter equality, so its scoped accepts remain.",
        "qualified_control": {"bindings": controls, "cases": cases, "historical_rows_preserved": True},
        "preserve_original_verdicts": True, "owner_use_only": True, "include_in_expert_prompt": False,
        "model_calls": 0,
    }
    return review


def expert_inputs():
    adapter_seal_path = ADAPTER / "ADAPTER-SEAL.json"
    adapter_seal = ref(adapter_seal_path, ADAPTER_SHA)
    sealed = load(adapter_seal_path)
    adapter_files = [ref(ADAPTER / path, sha) for path, sha in sealed["sha256"].items()]
    code_lock = load(ADAPTER / "CODE-LOCK.json")["sha256"]
    for path, sha in code_lock.items():
        ref(Path(path), sha)
    prepare_path = ADAPTER / "import-view/prepare.py"
    spec = importlib.util.spec_from_file_location("bound_w66_prepare", prepare_path)
    prepare = importlib.util.module_from_spec(spec)
    exec(compile(prepare_path.read_bytes(), str(prepare_path), "exec"), prepare.__dict__)
    cli = subprocess.check_output(["codex", "--version"], text=True, timeout=10).strip()
    summaries = {}
    for name, sha in sealed["review_seals"].items():
        side = "off" if "OFF" in name else "on"
        root = ADAPTER / "reviews/DS41-W-66" / name / "final-acceptance"
        seal_path = root / "SEAL.json"
        seal_ref = ref(seal_path, sha)
        verified = subprocess.check_output([sys.executable, "-B", str(ADAPTER / "review.py"),
                                            "verify", str(root)], timeout=15)
        seal = json.loads(verified)
        assert seal == load(seal_path) and seal["native_ordinal"] == 0
        run = Path(seal["run"])
        plan_path = run / "plan.json"
        plan = load(plan_path)
        assert plan["fresh_session"] and plan["model"] == "gpt-6.1-sol" and plan["reasoning_effort"] == "low"
        assert plan["command_affinity"] == "180-183" and plan["expected_cli_version"] == cli
        assert plan["max_wall_s"] == 900 and plan["task_scope"] == "Inspect and provide feedback only"
        assert "--ephemeral" in plan["argv"]
        assert plan["candidate_scope"] == "read-only exact staged proposal"
        case = load(LIGHT / "case.json")
        assert plan["before_files"] == case["baseline_files"] | seal["candidate_input_files"]
        raw_lane = prepare.file_map(run / "lane")
        lane, runtime = prepare.candidate_state(plan["before_files"], raw_lane)
        assert lane == plan["before_files"]

        prompt = (run / "prompt.md").read_text()
        assert "preserving existing private-lock isolation and assertions" in prompt
        assert "Return ACCEPT or REJECT" in prompt and "Leave the candidate unmodified" in prompt
        forbidden = ("receipt-identity-control", "w66-substituted-selection-receipt", "reject_assertion_weakening",
                     "ADJUDICATION.json", "REPORT-full.json", "REPORT-extra.json", "fixture-produced")
        assert not any(term in prompt for term in forbidden)
        feedback = load(root / "feedback.json")
        assert not feedback["actual_prior_help"]
        assert feedback["allowed_next_native_correction"] is None
        assert feedback["structural_pass_implies_semantic_acceptance"] is False
        structural = feedback["structural_reassessment"]
        assert structural["rc"] == 0 and structural["two_listed_tests_passed"] is True
        assert structural["semantic_acceptance_inferred"] is False
        assert structural["oracle_sha256"] == ORACLE
        unit = NATIVE / f"gpu-DS41-W-66-{side}-common-light-v2"
        actual = load(unit / "RESULT.json")
        assert structural["candidate_patch_sha256"] == plan["candidate_input_patch_sha256"] == actual["patch_sha256"]
        assert structural["checked_candidate_files"] == actual["changed_files"]
        assert structural["source_result_sha256"] == plan["source_native_result_sha256"]
        for path, expected in structural["source_files"].items():
            ref(Path(path), expected)
        receipt = ADAPTER / "test-pass-receipts" / f"gpu-DS41-W-66-{side}-common-light-v2.json"
        assert structural == load(receipt)
        template_path = root / "APPROVAL-TEMPLATE.json"
        template = load(template_path)
        assert template["approved_by"] is None and template["native_harness_qualified"] is False
        assert template["review_seal_sha256"] == sha
        assert template["plans"] == {str(plan_path): ref(plan_path)["sha256"]}
        launch = run / "launch-start.json"
        owner_approval = root / "MAIN-APPROVAL.json"
        launch_evidence = {}
        if launch.exists():
            started = load(launch)
            approval = load(owner_approval)
            assert approval["approved_by"] == "main" and approval["native_harness_qualified"] is True
            assert approval["review_seal_sha256"] == sha and approval["plans"] == template["plans"]
            assert started["argv"] == plan["argv"] and started["version"] == cli
            launch_evidence = {"start": ref(launch), "approval": ref(owner_approval, started["approval_sha256"])}
        else:
            assert not runtime
        summaries[name] = {
            "review_root": str(root), "seal": seal_ref,
            "plan": ref(plan_path), "prompt": ref(run / "prompt.md", plan["prompt_sha256"]),
            "approval_template": ref(template_path), "oracle_receipt": ref(receipt),
            "candidate_patch_sha256": actual["patch_sha256"], "verified_candidate_files": len(plan["before_files"]),
            "scope": plan["task_scope"], "launch_state": "owner-approved launch observed" if launch_evidence
                else "unlaunched; template ready for owner approval",
            "observed_launch": launch_evidence,
        }
    return {
        "schema": "taskflow.w66.light-v2.expert-readiness.v1", "adapter": adapter_seal,
        "adapter_files": adapter_files, "reviews": summaries, "cli": cli,
        "evidence_scope": "Exact Light V2 preservation wording, staged candidate and original two-test receipt. No prior help, expected decision, substitution witness or other mode solution.",
        "blinding": "Answer- and outcome-blinded. Native mode and execution metadata remain visible in the quoted terminal record.",
        "approval_changed": False, "model_calls": 0,
    }


if __name__ == "__main__":
    adjudication, readiness = bind_adjudication(), expert_inputs()
    write("ADJUDICATION.json", adjudication)
    write("EXPERT-READINESS.json", readiness)
    print(json.dumps({"adjudication": adjudication["owner_decision"], "templates_ready": len(readiness["reviews"])}))
