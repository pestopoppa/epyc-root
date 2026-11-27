"""Exercise the missing-launcher contract in the same offline evaluator."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
V2 = HERE.parent / "tu-oracle-v2"
MAIN = HERE.parent / "coverage/legacy-direct-repair/runs/TU-GR-1/direct-repair-1"
TEST = Path("scripts/autopilot/evals/dtap/tests/test_grader_isolation.py")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def controls_v2():
    assert digest(V2 / "SOURCE-CONTROL.sha256") == "75745276e36e01cc279da123094036228ba187dc707f82ce0769b6b50345bca8"
    subprocess.run(["sha256sum", "-c", "--quiet", "SOURCE-CONTROL.sha256"], cwd=V2, check=True)
    spec = importlib.util.spec_from_file_location("sealed_v2_controls", V2 / "controls.py")
    controls = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controls)
    return controls


def run(name, oracle, lane, rc, witness):
    proc = subprocess.run([sys.executable, "-IB", str(oracle), str(lane)],
                          timeout=185, capture_output=True)
    directory = HERE / "controls" / name
    directory.mkdir(parents=True)
    (directory / "stdout.log").write_bytes(proc.stdout)
    (directory / "stderr.log").write_bytes(proc.stderr)
    first = (proc.stdout or proc.stderr).decode().splitlines()[:1]
    assert proc.returncode == rc and first and witness in first[0], (name, proc.returncode, first)
    return {
        "id": name, "rc": rc, "diagnostic": first[0], "oracle_sha256": digest(oracle),
        "test_sha256": digest(lane / TEST),
        "stdout_sha256": digest(directory / "stdout.log"), "stderr_sha256": digest(directory / "stderr.log"),
    }


def main():
    old = controls_v2()
    raw = old.reviewed_grades(MAIN)
    core_v2 = (V2 / "tu_grader_isolation.py").read_text()
    core_v3 = (HERE / "tu_grader_isolation.py").read_text()
    start = "def validate("
    assert core_v2.split(start, 1)[0] == core_v3.split(start, 1)[0]
    original_test = (MAIN / "lane" / TEST).read_text()
    with TemporaryDirectory(prefix="tu-missing-launcher-controls-", dir=HERE) as tmp:
        scratch = Path(tmp)
        parser_checks = old.parser_controls(scratch)
        class_lane, skip_lane = scratch / "class", scratch / "missing-skip"
        for lane in (class_lane, skip_lane):
            shutil.copytree(MAIN / "lane", lane, ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__"))
        (class_lane / TEST).write_text(old.qualified_class(original_test))
        marker = "def test_isolated_launch_denies(tmp_path: Path) -> None:\n"
        assert original_test.count(marker) == 1
        control = original_test.replace(marker, marker +
            '    if subprocess.run(["which", "unshare"], capture_output=True).returncode:\n'
            '        pytest.skip("unshare binary is unavailable")\n')
        control = control.replace("import secrets\n", "import secrets\nimport subprocess\n")
        (skip_lane / TEST).write_text(control)
        v2, v3 = V2 / "oracle.py", HERE / "oracle.py"
        tests = [
            ("accepted-main-functions-v3", v3, MAIN / "lane", 0, "TU-GR-1 contract passed"),
            ("accepted-main-classes-v3", v3, class_lane, 0, "TU-GR-1 contract passed"),
            ("missing-launcher-skip-v2", v2, skip_lane, 0, "TU-GR-1 contract passed"),
            ("missing-launcher-skip-v3", v3, skip_lane, 1, "simulated namespace missing-launcher:"),
        ]
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(lambda test: run(*test), tests))
        assert "isolated failure, got rc=0" in rows[-1]["diagnostic"]
        assert "('skipped', 'unshare binary is unavailable')" in rows[-1]["diagnostic"]
        assert rows[-2]["test_sha256"] == rows[-1]["test_sha256"]
    assert raw == old.reviewed_grades(MAIN)
    report = {
        "schema": "tu-grader-isolation.v3.controls", "prior_accepted_main_grade": raw,
        "rows": rows, "unchanged_parser_controls": parser_checks,
        "class_fixture_body_ast_equivalent": True, "preserved_prior_sources_and_grades": True,
        "model_calls": 0,
    }
    (HERE / "CONTROL.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({row["id"]: row["rc"] for row in rows}))


if __name__ == "__main__":
    main()
