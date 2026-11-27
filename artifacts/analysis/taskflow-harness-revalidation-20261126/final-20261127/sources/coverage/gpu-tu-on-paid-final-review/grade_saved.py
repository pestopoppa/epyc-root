"""Check the exact terminal GPU TU ON paid2 and run the qualified contained V4 grade."""
import argparse
from hashlib import file_digest
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
COVERAGE = HERE.parent
ROOT = COVERAGE.parent
PACKAGE = COVERAGE / "legacy-comparison"
CASE = PACKAGE / "cases/TU-GR-1/case.json"
SOURCE = COVERAGE / "persistent-callback-admission-v2"
NATIVE = SOURCE / "runs/tu-on-paid-01"
ID = "gpu-TU-GR-1-on-coding-paid-2"
UNIT = NATIVE / "units" / ID
WORKER = UNIT / "worker"
V4 = ROOT / "tu-oracle-v4-qualification-v2"
ORACLE = V4 / "oracle.py"
CHECKER = V4 / "tu_grader_isolation.py"
QUALIFIED = "e1f66b12bc1c5c5690486446ee23bdf5baf0b49144b9c487b679b6e176215ee8"
BIND = {
    NATIVE / "PLAN.json": "8254540ad378886041d9bd5f455a7c6bc99aba03a828a01bf7df53d43892c350",
    NATIVE / "APPROVAL.json": "76a8920567c4e367954061d3c6dd16abb3ce83a75f73121198670f5e6ba1c396",
    SOURCE / "RUNNER-SEAL.json": "652ea6d728c0c9ee274d74dca77ba2f7e2c52acfde3225df4fe0b566e4aa753f",
    V4 / "SOURCE-CONTROL.sha256": "6e1f09e36fb540f09f7d357c0de0b14cf186fc6d24f4ec85db4102d51ae9a875",
    V4 / "CONTROL.json": QUALIFIED,
    CASE: "d7a455b74aa99393979341d60bae2d5f62a2b2edfd623425c952561dfe4f2aba",
    PACKAGE / "prepare.py": "9bd8e09ab2d3adb4cf44f1ed0a9c68eaacfa8dee6cbeb3d713266fc8b3b5b341",
}
CANDIDATE = HERE / "CANDIDATE.json"
SAFETY_TEMPLATE = HERE / "SOURCE-SAFETY-TEMPLATE.json"
GRADE = HERE / "grade-v4/RESULT.json"


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"unexpected sealed source kind: {path}")
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def write_new(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def bound():
    sources = {}

    def add(path, expected=None):
        actual = digest(path)
        if expected is not None and actual != expected:
            raise RuntimeError(f"sealed source changed: {path}")
        sources[str(path)] = actual
        return actual

    for path, expected in BIND.items():
        add(path, expected)
    for name, expected in read(SOURCE / "RUNNER-SEAL.json")["sha256"].items():
        add(SOURCE / name, expected)
    for line in (V4 / "SOURCE-CONTROL.sha256").read_text().splitlines():
        checksum, name = line.split(maxsplit=1)
        add(V4 / name, checksum)
    qualified = read(V4 / "CONTROL.json")
    if len(qualified["rows"]) != 14 or qualified["model_calls"] != 0:
        raise RuntimeError("V4 owner qualification missing")
    return sources, add


def check():
    sources, bind = bound()
    job, = read(NATIVE / "PLAN.json")["jobs"]
    if job["id"] != ID or job["row"]["backend"] != "gpu" or job["row"]["slot"] != 0:
        raise RuntimeError("unexpected paid native plan")
    terminal_path = UNIT / "CALLBACK-RESULT.json"
    outer_path = NATIVE / "RESULTS.json"
    if not terminal_path.is_file() or not outer_path.is_file():
        raise RuntimeError("waiting for exact native terminal and cleanup receipt")
    terminal = read(terminal_path)
    if read(outer_path)["terminal"] != [terminal]:
        raise RuntimeError("terminal per-unit and owner epoch records disagree")
    receipt_path = WORKER / "receipt.json"
    job_path = UNIT / "JOB.json"
    receipt = read(receipt_path)
    native = read(job_path)
    case = read(CASE)
    lane = UNIT / "grade-lane"
    patch = WORKER / "candidate/candidate.patch"
    if (terminal["id"] != ID or terminal["status"] != "awaiting_source_review"
            or not terminal["terminal_at"] or not terminal["same_session"]
            or not terminal["cleanup"]["removed_verified"] or terminal["supervision"]["returncode"] != 0
            or terminal["lane"] != str(lane) or lane.is_symlink() or not lane.is_dir()
            or receipt["status"] != "review" or receipt["case"] != case["id"]
            or receipt["repo_base_sha"] != case["repo_base_sha"]
            or receipt["task_packet_sha256"] != case["task_packet_sha256"]
            or receipt["session"] != job["prior_session"] or receipt["resume"] != native["resume"]
            or receipt["outside_scope"] or receipt["unsafe_paths"] or not receipt["patch_sha256"]
            or not receipt["changed_files"]
            or not set(receipt["changed_files"]) <= set(case["editable_paths"])
            or native["generated_ceiling"] != job["generated_chain_budget"]["remaining_before_admission"]
            or receipt["reserved_at_terminal"] != 0):
        raise RuntimeError("terminal candidate lacks intact identity, scope, or custody")
    charged = receipt["charged_toward_ceiling"]
    previous = job["generated_chain_budget"]["previous_charged"]
    if (type(charged) is not int or not 0 <= receipt["generated_observed"] <= charged
            or charged + previous > job["generated_chain_budget"]["ceiling"]):
        raise RuntimeError("native cumulative generated debit is invalid")
    for path in (terminal_path, outer_path, WORKER / "session.json"):
        bind(path)
    bind(receipt_path, terminal["worker_receipt_sha256"])
    bind(job_path, receipt["job_sha256"])
    bind(patch, receipt["patch_sha256"])
    for name, expected in job["sha256"].items():
        bind(Path(name), expected)
    for prior in job["previous_attempts"]:
        bind(Path(prior["path"]) / "worker/receipt.json", prior["receipt_sha256"])
    bind(Path(native["prompt"]), receipt["prompt_sha256"])
    if native["prompt_sha256"] != receipt["prompt_sha256"]:
        raise RuntimeError("actual native paid prompt hash differs")
    sys.path.insert(0, str(PACKAGE))
    from prepare import file_map
    sys.path.pop(0)
    expected = dict(case["baseline_files"])
    for name, change in receipt["changed_files"].items():
        if change is None:
            expected.pop(name)
        else:
            expected[name] = change
    if file_map(lane) != expected:
        raise RuntimeError("exact candidate lane differs from baseline plus allowlisted edits")
    candidate = {"id": ID, "case": case["id"], "candidate_patch_sha256": receipt["patch_sha256"],
                 "patch": str(patch), "lane": str(lane), "files": len(expected), "input_sha256": sources,
                 "changed_files": receipt["changed_files"], "generated_observed": receipt["generated_observed"],
                 "charged_toward_ceiling": charged, "combined_generated_charge": charged + previous,
                 "unreported_generation_requests": receipt["generation_unknown"],
                 "verifier_sha256": digest(ORACLE), "v4_checker_sha256": digest(CHECKER),
                 "v4_qualification_sha256": QUALIFIED}
    return candidate, lane, expected, file_map


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_subparsers(dest="mode", required=True)
    action.add_parser("preflight")
    action.add_parser("inspect")
    execute = action.add_parser("execute")
    execute.add_argument("--safety", required=True, type=Path)
    execute.add_argument("--safety-sha", required=True)
    args = parser.parse_args()
    if args.mode == "preflight":
        sources, _ = bound()
        print(json.dumps({"pinned": len(sources), "candidate_executed": False, "model_calls": 0}))
        return 0
    candidate, lane, expected, file_map = check()
    if args.mode == "inspect":
        write_new(CANDIDATE, candidate)
        write_new(SAFETY_TEMPLATE, {"reviewed_by": None, "safe_for_contained_grade": False,
                                   "candidate_json_sha256": digest(CANDIDATE),
                                   "candidate_patch_sha256": candidate["candidate_patch_sha256"],
                                   "scope_findings": []})
        print(json.dumps({k: candidate[k] for k in ("id", "patch", "candidate_patch_sha256", "files",
                                                     "generated_observed", "combined_generated_charge")}))
        return 0
    if digest(args.safety) != args.safety_sha or read(CANDIDATE) != candidate:
        raise RuntimeError("source review or candidate scope binding changed")
    safety = read(args.safety)
    if (safety["reviewed_by"] != "main" or safety["safe_for_contained_grade"] is not True
            or safety["candidate_json_sha256"] != digest(CANDIDATE)
            or safety["candidate_patch_sha256"] != candidate["candidate_patch_sha256"]):
        raise RuntimeError("main must source-review this exact candidate before execution")
    GRADE.parent.mkdir()
    proc = subprocess.run([sys.executable, "-IB", str(ORACLE), str(lane)], timeout=185, capture_output=True)
    for name, data in (("stdout", proc.stdout), ("stderr", proc.stderr)):
        (GRADE.parent / (name + ".log")).write_bytes(data)
    if file_map(lane) != expected:
        raise RuntimeError("contained oracle changed exact candidate inputs")
    record = {"id": ID, "candidate_patch_sha256": candidate["candidate_patch_sha256"],
              "rc": proc.returncode, "candidate_json_sha256": digest(CANDIDATE),
              "source_safety": str(args.safety.resolve()), "source_safety_sha256": args.safety_sha,
              "oracle_sha256": digest(ORACLE), "checker_sha256": digest(CHECKER),
              "v4_qualification_sha256": QUALIFIED,
              "stdout_sha256": digest(GRADE.parent / "stdout.log"),
              "stderr_sha256": digest(GRADE.parent / "stderr.log"),
              "first_diagnostic": (proc.stdout or proc.stderr).decode(errors="replace").splitlines()[:1],
              "model_calls": 0}
    write_new(GRADE, record)
    print(json.dumps(record))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
