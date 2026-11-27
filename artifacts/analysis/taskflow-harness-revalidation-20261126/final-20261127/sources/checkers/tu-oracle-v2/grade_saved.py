"""Regrade the exact previously reviewed GPU TU ON patch in the V2 evaluator."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "source-review-legacy-boundary-tu-on"
REVIEW_SHA = "f84cfd6bb451b775957b41dfb8c27b037df8ec2490791765506d9e7500401760"
UNIT = "gpu-TU-GR-1-on-coding"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(path, expected):
    if digest(path) != expected:
        raise RuntimeError(f"reviewed input changed: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    subprocess.run(["sha256sum", "-c", "--quiet", "SOURCE-CONTROL.sha256"], cwd=HERE, check=True)
    review_path = ORIGINAL / "REVIEW.json"
    verify(review_path, REVIEW_SHA)
    review = json.loads(review_path.read_bytes())
    row = review["rows"][UNIT]
    if not row["safe_for_contained_model_free_oracle"]:
        raise RuntimeError("candidate lacks source-safety review")
    for path, expected in row["input_sha256"].items():
        verify(Path(path), expected)
    prior_result = ORIGINAL / "grades" / UNIT / "RESULT.json"
    prior = json.loads(prior_result.read_bytes())
    if prior["candidate_patch_sha256"] != row["candidate_patch_sha256"]:
        raise RuntimeError("prior grade belongs to different bytes")
    for stream in ("stdout", "stderr"):
        verify(prior_result.parent / f"{stream}.log", prior[f"{stream}_sha256"])
    sys.path.insert(0, review["legacy_package"])
    from prepare import file_map
    expected = json.loads(Path(row["case"]).read_bytes())["baseline_files"] | row["changed_files"]
    lane = Path(row["lane"])
    if file_map(lane) != expected:
        raise RuntimeError("grade lane differs from the reviewed baseline and exact patch")
    if not args.execute:
        print(json.dumps({"id": UNIT, "verified_files": len(expected), "model_calls": 0}))
        return

    output = HERE / "owner-assessments" / UNIT
    output.mkdir(parents=True)
    oracle = HERE / "oracle.py"
    proc = subprocess.run([sys.executable, "-IB", str(oracle), str(lane)], timeout=185, capture_output=True)
    for name, content in (("stdout", proc.stdout), ("stderr", proc.stderr)):
        (output / f"{name}.log").write_bytes(content)
    if file_map(lane) != expected:
        raise RuntimeError("contained grading changed candidate bytes")
    result = {
        "id": UNIT, "rc": proc.returncode, "candidate_patch_sha256": row["candidate_patch_sha256"],
        "oracle_sha256": digest(oracle), "checker_sha256": digest(HERE / "tu_grader_isolation.py"),
        "source_review_sha256": REVIEW_SHA, "v1_raw_score": {"path": str(prior_result),
            "sha256": digest(prior_result), "rc": prior["rc"], "obsolete_diagnostic": "class-based JUnit omission"},
        "stdout_sha256": digest(output / "stdout.log"), "stderr_sha256": digest(output / "stderr.log"),
        "diagnostic": (proc.stdout or proc.stderr).decode().splitlines()[:1], "model_calls": 0,
        "raw_results_preserved": True,
    }
    (output / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result))
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
