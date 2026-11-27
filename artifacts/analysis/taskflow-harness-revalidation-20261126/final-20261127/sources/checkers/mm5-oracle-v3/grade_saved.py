"""Run the additive V3 checker on one already-reviewed GPU MM candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REVIEW_DIR = HERE.parent / "source-review-objective-followup"
REVIEW_SHA = "a7b3bda0b919f799ed4a562f97311f67e45e1e256c43425700afef02ddcc7396"


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify(path, expected):
    if digest(path) != expected:
        raise RuntimeError(f"reviewed input changed: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    subprocess.run(["sha256sum", "-c", "--quiet", "SOURCE-CONTROL.sha256"], cwd=HERE, check=True)
    review_path = REVIEW_DIR / "REVIEW.json"
    verify(review_path, REVIEW_SHA)
    review = json.loads(review_path.read_bytes())
    row = review["rows"][args.id]
    if row["case_id"] != "MM-5" or not row["safe_for_contained_model_free_oracle"]:
        raise ValueError("candidate is outside reviewed MM-5 scope")
    for path, expected in row["input_sha256"].items():
        verify(Path(path), expected)
    sys.path.insert(0, review["legacy_package"])
    from prepare import file_map

    lane = Path(row["lane"])
    expected = json.loads(Path(row["case"]).read_bytes())["baseline_files"] | row["changed_files"]
    if file_map(lane) != expected:
        raise RuntimeError("complete grade lane differs from the reviewed baseline plus changes")
    if not args.execute:
        print(json.dumps({"id": args.id, "verified_files": len(expected), "model_calls": 0}))
        return

    prior = {}
    for version, directory in (("v1", "grades"), ("v2", "grades-v2")):
        path = REVIEW_DIR / directory / args.id / "RESULT.json"
        if path.is_file():
            previous = json.loads(path.read_bytes())
            if previous["candidate_patch_sha256"] != row["candidate_patch_sha256"]:
                raise RuntimeError(f"{version} score belongs to a different patch")
            prior[version] = {"path": str(path), "sha256": digest(path), "rc": previous["rc"]}

    output = HERE / "owner-assessments" / args.id
    output.mkdir(parents=True)
    oracle = HERE / "oracle.py"
    checker = HERE / "vision_contract_v3.py"
    proc = subprocess.run([sys.executable, "-IB", str(oracle), str(lane)], timeout=185, capture_output=True)
    for name, content in (("stdout", proc.stdout), ("stderr", proc.stderr)):
        (output / f"{name}.log").write_bytes(content)
    if file_map(lane) != expected:
        raise RuntimeError("contained scoring changed candidate bytes")
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"evaluation environment exited {proc.returncode}")
    outcome = json.loads(proc.stdout)
    if outcome["schema"] != "mm5.capped-encoding.v3" or proc.returncode != int(
        any(item["status"] != "pass" for item in outcome["checks"].values())
    ):
        raise RuntimeError("versioned acceptance result is inconsistent")
    result = {
        "id": args.id, "rc": proc.returncode, "checks": outcome["checks"],
        "candidate_patch_sha256": row["candidate_patch_sha256"],
        "oracle_sha256": digest(oracle), "check_module_sha256": digest(checker),
        "prior_grades_preserved": prior, "source_review_sha256": REVIEW_SHA,
        "stdout_sha256": digest(output / "stdout.log"), "stderr_sha256": digest(output / "stderr.log"),
        "raw_results_preserved": True, "model_calls": 0,
    }
    (output / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result))
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
