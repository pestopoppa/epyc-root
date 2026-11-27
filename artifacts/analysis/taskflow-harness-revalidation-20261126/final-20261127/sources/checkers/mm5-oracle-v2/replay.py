"""Model-free controls for the MM-5 additive oracle."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from vision_contract_v2 import check_resized_geometry

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = "src/vision/analyzers/vl_describe.py"
LEGACY = ROOT / "coverage/legacy-comparison"
CASE = LEGACY / "cases/MM-5"
REVIEW = ROOT / "source-review-legacy-boundary/REVIEW.json"
CPU = "cpu-MM-5-off-recommended"
GPU = "gpu-MM-5-off-common-on-sampling"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def synthetic_geometry():
    passing = [
        ((641, 913), 200_000, (364, 532)),
        ((641, 913), 200_000, (336, 476)),
        ((913, 641), 200_000, (532, 364)),
        ((100, 4000), 7840, (28, 280)),
        ((100, 4000), 7840, (28, 252)),
        ((4000, 100), 7840, (280, 28)),
        ((100, 4000), 784, (28, 28)),
    ]
    failing = [
        ((100, 4000), 7840, (28, 28), "lose source orientation"),
        ((4000, 100), 7840, (28, 28), "lose source orientation"),
        ((641, 913), 200_000, (532, 364), "inconsistent with aspect-preserving grid rounding"),
    ]
    for source, cap, shape in passing:
        check_resized_geometry(source, cap, shape)
    for source, cap, shape, witness in failing:
        try:
            check_resized_geometry(source, cap, shape)
        except AssertionError as exc:
            assert witness in str(exc)
        else:
            raise AssertionError(f"accepted bad geometry: {source, cap, shape}")
    return {"valid_geometry_cases": passing, "rejected_geometry_cases": failing}


def main():
    controls = synthetic_geometry()
    sys.path.insert(0, str(LEGACY))
    from prepare import candidate_state, file_map
    case = load(CASE / "case.json")
    review = load(REVIEW)["rows"]
    direct = LEGACY / "runs/MM-5/direct-1"
    main = load(direct / "measurement.json")
    if not main["path_scope_pass"]:
        raise RuntimeError("main candidate scope is not closed")
    candidates = [
        ("original-baseline", CASE / "baseline", 1, "ImportError"),
        ("reviewed-main-direct", direct / "lane", 0, ""),
        (CPU, Path(review[CPU]["lane"]), 1, "encoded bytes differ from the original"),
        (GPU, Path(review[GPU]["lane"]), 1, "encoded dimensions (28, 28) lose source orientation"),
    ]
    original_oracle = CASE / "oracle.py"
    original_sha = case["oracle_sha256"]
    assert digest(original_oracle) == original_sha
    for name in (CPU, GPU):
        details = review[name]
        for source, expected in details["input_sha256"].items():
            assert digest(Path(source)) == expected, source
    rows = []
    for name, lane, expected_rc, witness in candidates:
        raw_before = file_map(lane)
        before, runtime = candidate_state(case["baseline_files"], raw_before)
        changes = {path for path in before.keys() | case["baseline_files"].keys()
                   if before.get(path) != case["baseline_files"].get(path)}
        assert not changes - set(case["editable_paths"])
        if name in (CPU, GPU):
            assert changes == set(review[name]["changed_files"])
            assert all(before[path] == review[name]["changed_files"][path] for path in changes)
        elif name == "reviewed-main-direct":
            assert sorted(changes) == main["final_changes"]
            assert digest(direct / "delta.patch") == main["patch_sha256"]
        elif changes:
            raise ValueError("frozen baseline changed")
        if name in (CPU, GPU):
            old = RootGrade(name)
        elif name == "original-baseline":
            old = load(LEGACY / "controls/MM-5/baseline/oracle-result.json")
        else:
            old = main.get("oracle")
        out = HERE / "controls" / name
        out.mkdir(parents=True)
        proc = subprocess.run([sys.executable, "-IB", str(HERE / "oracle.py"), str(lane)],
                              capture_output=True, timeout=185)
        for label, payload in (("stdout", proc.stdout), ("stderr", proc.stderr)):
            (out / f"{label}.log").write_bytes(payload)
        assert proc.returncode == expected_rc and witness in proc.stderr.decode(), (
            name, proc.returncode, proc.stderr.decode())
        assert file_map(lane) == raw_before, "candidate changed during read-only verification"
        row = {"id": name, "lane": str(lane), "v2_rc": proc.returncode,
               "source_sha256": digest(lane / SOURCE), "original_oracle_rc_retained": None if old is None else old["rc"],
               "preserved_runtime_artifacts": sorted(runtime),
               "stdout_sha256": digest(out / "stdout.log"), "stderr_sha256": digest(out / "stderr.log"),
               "diagnostic": proc.stderr.decode().strip().splitlines()[-1:] or None}
        write(out / "RESULT.json", row)
        rows.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)
    assert digest(original_oracle) == original_sha
    write(HERE / "CONTROL.json", {
        "case": "MM-5", "version": "mm5.capped-encoding.v2",
        "pinned_original_oracle_sha256": original_sha,
        "unchanged_original_checker_called": True, "synthetic_geometry": controls,
        "saved_control_candidates": rows, "new_checks": ["already-within-cap byte identity",
            "capped PNG/decoded size/grid", "orientation when a minimum side binds and multiple tiles fit",
            "common-scale grid rounding for ordinary aspect ratios"],
        "fixed_question_excludes_cap_below_one_patch": True,
        "review_scope": "controls only; owning session grades and records final assessments",
        "candidate_bytes_preserved": True, "native_model_calls": 0,
    })


def RootGrade(name):
    return load(ROOT / "source-review-legacy-boundary/grades" / name / "RESULT.json")


if __name__ == "__main__":
    main()
