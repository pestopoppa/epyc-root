"""Bind the four terminal candidates reviewed for this offline source assessment."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CPU = ROOT / "coverage/cpu-numa-repair/runs/cpu-02/jobs/measured-01/units"
GPU = ROOT / "coverage/legacy-boundary-v3/runs/boundary-01/units"
LEGACY = ROOT / "coverage/legacy-comparison"
QUALITY = ROOT.parent / "ws58-a3b-frozen-revalidation-20261126/quality-v4"
PAW = "cpu-PAW-5-off-recommended-numa-resume-1"

items = [
    (CPU, "cpu-MM-5-off-recommended", [
        "Reject. The brief conditions resizing on w*h exceeding max_pixels and requires raw bytes otherwise. Candidate encode_image_for_vl enters its resize path for every non-None cap at src/vision/analyzers/vl_describe.py:96–103. Its test for an already-under-cap image checks decoded grid/dimensions and never compares original bytes.",
        "If caps below one 28x28 patch are supported by the API, the final loop cannot satisfy such a cap because both sides are clamped to 28. This is an additional input-validation concern and does not determine the review.",
    ]),
    (GPU, "gpu-MM-5-off-common-on-sampling", [
        "Reject the aspect-ratio handling for feasible tall inputs. The brief requires PIL resizing while keeping aspect ratio, rounding to the 28-pixel grid, and re-enforcing the cap for both orientations. For 100x4000 at cap 7840 the candidate clamps to 28x560, then its width-only loop and height fallback produce 28x28 at src/vision/analyzers/vl_describe.py:90–115. The feasible 28x280 preserves substantially more of the original portrait geometry while meeting the exact same cap and patch grid.",
        "Default and already-under-cap paths preserve raw bytes, and the recorder uses its existing notes parameter. The verifier's tighter cap=784 requires a square, so its acceptance alone cannot establish aspect-ratio handling at other feasible budgets.",
        "Caps below 784 cannot be fulfilled by a resized image on this grid. The code emits a 784-pixel image in such cases, but the intended supported input domain for smaller caps was not explicitly pinned. The source rejection uses the feasible 7840-pixel case.",
    ]),
    (GPU, "gpu-TU-GR-1-off-common-on-sampling", [
        "Reject. The brief permits a skip only for explicit permission refusal setting up the user namespace. tests/test_grader_isolation.py:112–122 skips any failed child's permission text, including mount-stage permission failure, which the trusted mount-permission-refusal control explicitly requires to fail.",
        "The brief requires failure for missing or malformed child stdout and preserves launcher/probe failure separately from inaccessible grader material. harness/isolation.py:120–143 returns a false-access dict with None errno for rc0 empty stdout and accepts parseable JSON without checking a nonzero child rc. assert_grader_unreachable only examines open_ok/listdir_ok, so the no-output dict can pass for denial.",
    ]),
    (CPU, PAW, [
        "Reject on source fidelity and semantic scope. Raw v3 failed Comparison because its three labels introduce bullet bodies. A scratch-only layout normalization moved each existing first bullet onto its label line and the exact same checker passed, establishing a layout confound separate from the substantive review.",
        "Candidate 1 describes six known error categories and the FW-1 F1 fallback as current. At APP 332ceb2e14d16f2031bd17b1f7c839ce8276a24b, src/graph/error_classifier.py:12–36 branches across seven named categories before UNKNOWN, and src/graph/nodes.py uses seven _classify_error call sites. FW-1 is historical design context under the owner brief.",
        "Candidate 2's pruning seam matches the staged context_arm_ab.py:162–172. Candidate 3 hands explicit deterministic routing policy, including the final_schema_validation feature gate in repl_executor.py:711, to a learned predicate. The brief requires identifying a semantic decision separately from deterministic behavior.",
    ]),
]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def row(root, name, reasons):
    source = root / name
    result = load(source / "RESULT.json")
    assert result["terminal_at"] > 0 and result["id"] == name
    hashes = {}
    def bind(path, expected=None):
        seen = sha(path)
        assert expected is None or seen == expected, path
        hashes[str(path)] = seen

    bind(source / "RESULT.json")
    if name == PAW:
        kind, case_dir = "markdown", QUALITY / "packets/PAW-5"
        lane, patch = source / "independent/work", source / "independent/candidate.patch"
        oracle = case_dir / "oracle-format-v3.py"
        patch_sha = result["patch_sha256"]
        expected_oracle = result["oracle"]["oracle_sha256"]
        changes = result["changed_files"]
        bind(lane / next(iter(changes)), next(iter(changes.values()))["sha256"])
        bind(source / "ORACLE.stderr.log", result["oracle"]["stderr_sha256"])
    else:
        kind, case_dir = "python", LEGACY / "cases" / result["case"]
        job, receipt = source / "JOB.json", source / "worker/receipt.json"
        bind(job, result["job_sha256"])
        bind(receipt, result["worker_receipt_sha256"])
        data = load(receipt)
        assert not data["outside_scope"] and not data["unsafe_paths"]
        lane = Path(result["lane"])
        assert lane == source / "grade-lane"
        patch, patch_sha = source / "worker/candidate/candidate.patch", result["candidate_patch_sha256"]
        assert data["patch_sha256"] == patch_sha
        oracle = case_dir / "oracle.py"
        expected_oracle = load(case_dir / "case.json")["oracle_sha256"]
        changes = data["changed_files"]
        bind(case_dir / "case.json", load(job)["case_sha256"])
        for name_, record in changes.items():
            bind(lane / name_, record["sha256"])
        for fixed in ("task-env.json", "evaluator-support/vision_contract.py", "evaluator-support/tu_grader_isolation.py"):
            bind(case_dir / fixed)
    bind(case_dir/"case.json")
    bind(oracle, expected_oracle)
    bind(patch, patch_sha)
    return {"id": name, "kind": kind, "lane": str(lane), "oracle": str(oracle), "case": str(case_dir/"case.json"),
            "input_sha256": hashes, "candidate_patch_sha256": patch_sha, "changed_files": changes,
            "raw_status": result["status"], "source_recommendation": "reject", "reasons": reasons}


if __name__ == "__main__":
    rows = {name: row(root, name, reasons) for root, name, reasons in items}
    value = {"legacy_package": str(LEGACY), "purpose": "source-only review and commands for the owning session",
             "model_calls": 0, "original_scores_preserved": True, "rows": rows}
    (HERE/"REVIEW.json").write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)+"\n")
