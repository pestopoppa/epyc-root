"""Stage a fresh Light V2 W66 semantic review with in-lane comparison evidence."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREVIOUS = HERE.parent / "w66-light-acceptance"
CASE_ROOT = HERE.parent / "w66-light-brief-v2/cases"
ORIGINAL = ROOT / "main-comparison"
CASE = "DS41-W-66"
SOURCE = "scripts/kernel_rnd/autokernel/loop/test_runtime_keep_source_continuity.py"
ARTIFACTS = {
    "baseline": f".review-evidence/original/{SOURCE}",
    "patch": ".review-evidence/candidate.patch",
    "manifest": ".review-evidence/SOURCE-COMPARISON.json",
}
OLD_SEAL = "89c009474ce5bd761068fb488e17480759bd7fc13c672ad21411d86cb1bb1abc"
PREPARE_SHA = "864bdad1512fc223469a372b78f779e47e00c6432d7515cba0884a753172ce0c"
MEASURE_SHA = "3175392d9b99143501a3b3e385d549234bc7ef4c2d50a802b72bf9a42f251488"
MODES = ("gpu-OFF-off-common-light", "gpu-ON-on-common-light")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_hash(path, expected):
    if sha(path) != expected:
        raise ValueError(f"pinned input changed: {path}")


def load(path):
    return json.loads(path.read_bytes())


def write(path, content):
    with path.open("x") as stream:
        json.dump(content, stream, indent=2, sort_keys=True)
        stream.write("\n")


def load_module(name, path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"pinned comparator code changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def modules(root, evidence=None):
    prepare = load_module("prepare", ORIGINAL / "prepare.py", PREPARE_SHA)
    prepare.HERE = root
    measure = load_module("w66_reviewer_measure", ORIGINAL / "measure.py", MEASURE_SHA)
    if evidence is not None:
        base_load = measure.load
        case_path = root / "cases" / CASE / "case.json"

        def with_readonly_review_evidence(path):
            record = base_load(path)
            if path == case_path:
                # Treat the review-only files as fixed inputs in the existing
                # report comparison. Any reviewer edit still fails guidance scope.
                record["baseline_files"] |= evidence
            return record

        measure.load = with_readonly_review_evidence
    return prepare, measure


def review_root(mode):
    return HERE / "reviews" / CASE / mode / "final-acceptance"


def comparison_evidence(lane, expected):
    for key, relative in ARTIFACTS.items():
        file = lane / relative
        if not file.is_file() or file.is_symlink():
            raise ValueError(f"missing or non-regular staged comparison evidence: {relative}")
        verify_hash(file, expected[relative]["sha256"])
        if file.stat().st_mode & 0o222:
            raise ValueError(f"staged comparison evidence has write permission: {relative}")
    manifest = load(lane / ARTIFACTS["manifest"])
    if manifest["candidate"]["path"] != SOURCE:
        raise ValueError("unexpected candidate path in evidence manifest")
    verify_hash(lane / SOURCE, manifest["candidate"]["sha256"])
    for key in ("baseline", "patch"):
        entry = manifest[key]
        if entry["path"] != ARTIFACTS[key] or entry["sha256"] != expected[ARTIFACTS[key]]["sha256"]:
            raise ValueError("comparison manifest differs from sealed paths")


def first_review(mode, prepare):
    root = PREVIOUS / "reviews" / CASE / mode / "final-acceptance"
    path = root / "SEAL.json"
    package = load(PREVIOUS / "ADAPTER-SEAL.json")
    verify_hash(path, package["review_seals"][mode])
    seal = load(path)
    for name, expected in seal["immutable"].items():
        verify_hash(root / name, expected)
    for name, expected in (seal["external"] | seal["source_native_files"]).items():
        verify_hash(Path(name), expected)
    run = Path(seal["run"])
    plan = load(run / "plan.json")
    feedback = load(root / "feedback.json")
    assert not feedback["actual_prior_help"] and feedback["native_ordinal"] == 0
    receipt = feedback["structural_reassessment"]
    assert receipt["two_listed_tests_passed"] and receipt["rc"] == 0
    assert not receipt["semantic_acceptance_inferred"]
    observed, _ = prepare.candidate_state(plan["before_files"], prepare.file_map(run / "lane"))
    assert observed == plan["before_files"] and not (run / "lane/.git").exists()
    raw = load(run / "assistance-accounting.json")
    verify_hash(run / "events.jsonl", raw["events_sha256"])
    verify_hash(run / "measurement.json", raw["measurement_sha256"])
    assert load(run / "execution.json") == raw["execution"]
    expected_patch = feedback["candidate_patch_sha256"]
    paths = [Path(name) for name in seal["source_native_files"] if name.endswith("/independent/candidate.patch")]
    patch, = paths
    verify_hash(patch, expected_patch)
    case = load(CASE_ROOT / CASE / "case.json")
    original = CASE_ROOT / CASE / "baseline" / SOURCE
    baseline_sha = case["baseline_files"][SOURCE]["sha256"]
    verify_hash(original, baseline_sha)
    assert all(row["sha256"] not in {expected_patch, baseline_sha} for row in observed.values())
    assert expected_patch in (run / "prompt.md").read_text()
    assert "--- a/" + SOURCE not in (run / "prompt.md").read_text()
    commands = [event["item"] for line in (run / "events.jsonl").read_text().splitlines()
                if (event := json.loads(line)).get("type") == "item.completed"
                and event.get("item", {}).get("type") == "command_execution"]
    diff_attempt = next(item for item in commands if "git diff" in item["command"])
    assert "not a git repository" in diff_attempt["aggregated_output"].lower()
    historical = {
        "review_seal": {"path": str(path), "sha256": sha(path)},
        "source_comparison_available_in_worker_lane": False,
        "git_diff_command_id": diff_attempt["id"], "git_diff_diagnostic": "Not a git repository",
        "prior_execution": raw["execution"], "prior_usage": raw["usage"],
        "original_advisory": raw["semantic_review_advisory"],
        "retained": {name: sha(run / name) for name in ("execution.json", "events.jsonl", "measurement.json",
                                                       "assistance-accounting.json", "prompt.md", "plan.json")},
    }
    return run, plan, feedback, patch, original, case, historical


def stage(mode):
    root = review_root(mode)
    run = root / "runs" / CASE / "guidance-1"
    lane = run / "lane"
    prepare, _ = modules(root)
    before, plan, feedback, patch, original, case, history = first_review(mode, prepare)
    baseline = CASE_ROOT / CASE / "baseline"
    assert prepare.file_map(baseline) == case["baseline_files"]
    run.mkdir(parents=True)
    (root / "cases").symlink_to(CASE_ROOT, target_is_directory=True)
    shutil.copytree(baseline, lane)
    common = ["git", "-c", "core.hooksPath=/dev/null", "apply", "--whitespace=nowarn"]
    subprocess.run([*common, "--check", str(patch)], cwd=lane, check=True, capture_output=True, timeout=15)
    subprocess.run([*common, str(patch)], cwd=lane, check=True, capture_output=True, timeout=15)
    assert prepare.file_map(lane) == plan["before_files"]
    for label, artifact in (("baseline", original), ("patch", patch)):
        target = lane / ARTIFACTS[label]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, target)
        target.chmod(0o444)
    metadata = {
        "repo_base_sha": case["repo_base_sha"],
        "baseline": {"path": ARTIFACTS["baseline"], "sha256": sha(original)},
        "patch": {"path": ARTIFACTS["patch"], "sha256": sha(patch)},
        "candidate": {"path": SOURCE, "sha256": sha(lane / SOURCE)},
        "original_oracle_sha256": case["oracle_sha256"],
    }
    write(lane / ARTIFACTS["manifest"], metadata)
    (lane / ARTIFACTS["manifest"]).chmod(0o444)
    staged = prepare.file_map(lane)
    evidence = {relative: staged[relative] for relative in ARTIFACTS.values()}
    assert staged == plan["before_files"] | evidence
    comparison_evidence(lane, evidence)
    prompt = (before / "prompt.md").read_text() + f"""
Source comparison files are available in this snapshot. Read the original file at
`{ARTIFACTS['baseline']}` and the exact submitted patch at `{ARTIFACTS['patch']}`.
The current candidate is at its original path `{SOURCE}`.
The hashes and pinned revision are recorded in `{ARTIFACTS['manifest']}`.
Compare the original and revised assertions before giving your independent decision.
Use the supplied original task criterion and test receipt. Leave all files unmodified.
"""
    (run / "prompt.md").write_text(prompt)
    (root / "feedback.json").write_bytes((before.parents[2] / "feedback.json").read_bytes())
    assert load(root / "feedback.json") == feedback
    plan["argv"][plan["argv"].index("-C") + 1] = str(lane)
    plan.update(before_files=staged, prompt_sha256=sha(run / "prompt.md"),
                review_comparison_evidence=evidence, evidence_version="source-comparison-v2",
                outside_worker_oracle=[str(CASE_ROOT / CASE / "oracle.py"), str(lane)])
    write(run / "plan.json", plan)
    fixed = {str(path.relative_to(root)): sha(path) for path in (run / "plan.json", run / "prompt.md", root / "feedback.json")}
    original_inputs = {
        str(original): sha(original), str(patch): sha(patch),
        str(CASE_ROOT / CASE / "case.json"): sha(CASE_ROOT / CASE / "case.json"),
        str(CASE_ROOT / CASE / "oracle.py"): case["oracle_sha256"],
    }
    seal = {"schema": "taskflow.w66.review.compare.v2", "mode": mode, "run": str(run),
            "code_sha256": sha(Path(__file__)), "fixed": fixed, "evidence": evidence,
            "original_inputs": original_inputs,
            "candidate_input_patch_sha256": feedback["candidate_patch_sha256"]}
    write(root / "SEAL.json", seal)
    write(root / "APPROVAL-TEMPLATE.json", {
        "approved_by": None, "native_harness_qualified": False,
        "review_seal_sha256": sha(root / "SEAL.json"), "plans": {str(run / "plan.json"): sha(run / "plan.json")},
        "paid_role": "paid-independent-final-acceptance", "instruction": "Template authorizes no model call.",
    })
    return history


def verify(mode, *, prelaunch=True):
    root = review_root(mode)
    seal = load(root / "SEAL.json")
    if seal["mode"] != mode or seal["code_sha256"] != sha(Path(__file__)):
        raise ValueError("review identity or code changed")
    for name, expected in seal["fixed"].items():
        verify_hash(root / name, expected)
    for name, expected in seal["original_inputs"].items():
        verify_hash(Path(name), expected)
    if (root / "cases").resolve() != CASE_ROOT.resolve():
        raise ValueError("private case binding changed")
    run = Path(seal["run"])
    plan = load(run / "plan.json")
    assert plan["review_comparison_evidence"] == seal["evidence"]
    if prelaunch:
        comparison_evidence(run / "lane", seal["evidence"])
        prepare, _ = modules(root)
        if prepare.file_map(run / "lane") != plan["before_files"]:
            raise ValueError("staged review lane differs from approved input")
    return seal, run


def controls():
    histories = {}
    verify_hash(PREVIOUS / "ADAPTER-SEAL.json", OLD_SEAL)
    for mode in MODES:
        histories[mode] = stage(mode)
        seal, run = verify(mode)
        # Exercise the actual evidence gate on a separate private copy.
        with TemporaryDirectory(prefix="evidence-tamper-controls-", dir=HERE) as scratch:
            lane = Path(scratch)
            shutil.copytree(run / "lane/.review-evidence", lane / ".review-evidence")
            candidate = lane / SOURCE
            candidate.parent.mkdir(parents=True)
            shutil.copy2(run / "lane" / SOURCE, candidate)
            comparison_evidence(lane, seal["evidence"])
            for relative in (*ARTIFACTS.values(), SOURCE):
                file = lane / relative
                raw, mode_bits = file.read_bytes(), file.stat().st_mode & 0o777
                file.chmod(0o644)
                file.write_bytes(raw + b"\n")
                file.chmod(mode_bits)
                try:
                    comparison_evidence(lane, seal["evidence"])
                except ValueError:
                    pass
                else:
                    raise ValueError(f"altered evidence passed: {relative}")
                file.chmod(0o644)
                file.write_bytes(raw)
                file.chmod(mode_bits)
            missing = lane / ARTIFACTS["patch"]
            missing.unlink()
            try:
                comparison_evidence(lane, seal["evidence"])
            except ValueError:
                pass
            else:
                raise ValueError("missing patch passed")
    write(HERE / "CONTROL.json", {
        "prior_adapter_sha256": OLD_SEAL, "previous_reviews_preserved": histories,
        "required_in_lane_comparison_evidence": ARTIFACTS,
        "exact_comparison_inputs_verified": True, "tampered_and_missing_evidence_rejected": True,
        "old_advisories_and_costs_retained": True, "model_calls": 0,
    })


def report(mode):
    seal, run = verify(mode, prelaunch=False)
    _, measure = modules(review_root(mode), seal["evidence"])
    result = measure.report(run)
    messages = []
    for line in (run / "events.jsonl").read_text().splitlines():
        event = json.loads(line)
        if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "agent_message":
            messages.append(event["item"].get("text", ""))
    match = re.match(r"\s*(ACCEPT|REJECT)\b", messages[-1]) if messages else None
    record = {
        "case": CASE, "mode": mode, "review_kind": "final-acceptance", "evidence_version": "source-comparison-v2",
        "candidate_input_patch_sha256": seal["candidate_input_patch_sha256"], "execution": result["execution"],
        "usage": result["jsonl"]["usage"], "path_scope_pass": result["path_scope_pass"],
        "candidate_unmodified_by_review": not result["changed_by_strong_turn"],
        "semantic_review_advisory": match.group(1) if match and result["path_scope_pass"] else "UNAVAILABLE",
        "previous_review_retained_separately": True, "events_sha256": sha(run / "events.jsonl"),
    }
    write(run / "assistance-accounting.json", record)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("stage")
    for name in ("verify", "launch", "report"):
        command = commands.add_parser(name)
        command.add_argument("mode", choices=MODES)
        if name == "launch":
            command.add_argument("--approval", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "stage":
        controls()
    elif args.command == "verify":
        seal, _ = verify(args.mode)
        print(json.dumps(seal))
    elif args.command == "launch":
        seal, run = verify(args.mode)
        root = review_root(args.mode)
        assert load(args.approval)["review_seal_sha256"] == sha(root / "SEAL.json")
        _, measure = modules(root)
        raise SystemExit(measure.launch(run, args.approval.resolve()))
    else:
        print(json.dumps(report(args.mode)))
