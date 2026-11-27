"""Verify TU's file binding with real pytest ran under the sealed offline wrapper."""
import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import textwrap
import xml.etree.ElementTree as ET

from tu_grader_isolation import _CONTROL, _ISOLATED, _WORK_PATH, _outcomes

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LEGACY = ROOT / "coverage/legacy-comparison"
CASE = LEGACY / "cases/TU-GR-1"
SEALED_POSITIVE = LEGACY / "controls/TU-GR-1/positive"
BASELINE = LEGACY / "controls/TU-GR-1/baseline"
MAIN = ROOT / "coverage/legacy-direct-repair/runs/TU-GR-1/direct-repair-1"
HARNESS = "scripts/autopilot/evals/dtap/harness/isolation.py"
CORE_SHA = "6da203e37f636fe2d094f4742bbef5816daf2af04add8b5bf150fa3843891de5"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def quantify_oracle_diff():
    """Verify original behavior and pytest command differ only in report binding."""
    original = CASE / "evaluator-support/tu_grader_isolation.py"
    assert digest(original) == CORE_SHA
    old = ast.parse(original.read_text())
    new = ast.parse((HERE / "tu_grader_isolation.py").read_text())
    module_old = [node for node in old.body if isinstance(node, ast.FunctionDef) and node.name == "validate"]
    module_new = [node for node in new.body if isinstance(node, ast.FunctionDef) and node.name == "validate"]
    validator = module_new[0]
    cmd = next(node for node in ast.walk(validator) if isinstance(node, ast.Assign)
               and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "cmd")
    command_suffixes = [value for value in ast.walk(cmd.value)
                        if isinstance(value, ast.Constant) and str(value.value).endswith(" -o junit_family=xunit1")]
    assert len(command_suffixes) == 1
    command_suffixes[0].value = command_suffixes[0].value.removesuffix(" -o junit_family=xunit1")
    assert ast.dump(module_new[0]).count("id='ValueError'") == 1
    stage_handler = next(node for node in ast.walk(validator)
                         if isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Tuple)
                         and any(isinstance(term, ast.Name) and term.id == "ValueError" for term in node.type.elts))
    stage_handler.type.elts.pop()
    cmd_old = next(node for node in ast.walk(module_old[0]) if isinstance(node, ast.Assign)
                   and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "cmd")
    # Adjacent fstrings can split constants differently without changing the arguments.
    assert ast.unparse(cmd.value) == ast.unparse(cmd_old.value)
    cmd.value = cmd_old.value
    assert ast.dump(module_old[0]) == ast.dump(module_new[0])
    same_remaining = []
    for module in (old, new):
        same_remaining.append([ast.dump(node) for node in module.body
                               if not (isinstance(node, ast.FunctionDef) and node.name in {"validate", "_outcomes"})
                               and not (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                                        and node.targets[0].id == "_WORK_PATH")])
    assert same_remaining[0] == same_remaining[1]


def qualified_class(source):
    before = ast.parse(source)
    functions = before.body[-2:]
    assert [node.name for node in functions] == [_CONTROL, _ISOLATED]
    lines = source.splitlines(keepends=True)
    split = functions[0].lineno - 1
    methods = "".join(lines[split:])
    for name in (_CONTROL, _ISOLATED):
        needle = f"def {name}("
        assert methods.count(needle) == 1
        methods = methods.replace(needle, needle + "self, ")
    candidate = "".join(lines[:split]) + "class TestGraderIsolation:\n" + textwrap.indent(methods, "    ")
    changed = ast.parse(candidate)
    assert isinstance(changed.body[-1], ast.ClassDef)
    restored = changed.body[:-1] + changed.body[-1].body
    for method in restored[-2:]:
        assert method.args.args.pop(0).arg == "self"
    assert ast.dump(ast.Module(body=restored, type_ignores=[])) == ast.dump(before)
    return candidate


def parser_controls(directory):
    report = directory / "fixture.xml"
    good_class = "scripts.autopilot.evals.dtap.tests.test_grader_isolation.TestGraderIsolation"

    def write(file, names):
        tests = ET.Element("testsuite")
        for name in names:
            ET.SubElement(tests, "testcase", {"file": file, "classname": good_class, "name": name})
        ET.ElementTree(tests).write(report, encoding="utf-8")

    write("foreign/test_grader_isolation.py", (_CONTROL, _ISOLATED))
    assert _outcomes(report) == {}
    write("scripts/autopilot/evals/dtap/tests/test_grader_isolation/foreign.py", (_CONTROL, _ISOLATED))
    assert _outcomes(report) == {}
    write(_WORK_PATH, ())
    assert _outcomes(report) == {}
    write(_WORK_PATH, (_CONTROL, _ISOLATED, _ISOLATED))
    try:
        _outcomes(report)
    except ValueError as exc:
        assert "duplicate results" in str(exc)
    else:
        raise AssertionError("duplicate result was accepted")
    return {"foreign_same_basename": "rejected", "foreign_module_with_same_prefix": "rejected",
            "empty_class_report": "rejected", "duplicate_named_result": "rejected"}


def run(name, lane, expected, witness=None):
    proc = subprocess.run([sys.executable, "-IB", str(HERE / "oracle.py"), str(lane)],
                          timeout=185, capture_output=True)
    directory = HERE / "controls" / name
    directory.mkdir(parents=True)
    (directory / "stdout.log").write_bytes(proc.stdout)
    (directory / "stderr.log").write_bytes(proc.stderr)
    diagnostic = (proc.stdout or proc.stderr).decode().splitlines()[0]
    assert proc.returncode == expected and (witness is None or witness in diagnostic), (name, proc.returncode, diagnostic)
    return {"id": name, "rc": proc.returncode, "diagnostic": diagnostic,
            "stdout_sha256": digest(directory / "stdout.log"), "stderr_sha256": digest(directory / "stderr.log")}


def reviewed_grades(run):
    old = load(run / "oracle-result.json")
    assert old["rc"] == 0
    assert old["oracle_sha256"] == digest(CASE / "oracle.py")
    for name, entry in old["checked_candidate_files"].items():
        assert digest(run / "lane" / name) == entry["sha256"]
    return {"path": str(run / "oracle-result.json"), "sha256": digest(run / "oracle-result.json")}


def main():
    quantify_oracle_diff()
    sys.path.insert(0, str(LEGACY))
    from prepare import candidate_state, file_map
    case = load(CASE / "case.json")
    baseline = case["baseline_files"]
    previous = {"main_repair": reviewed_grades(MAIN), "sealed_positive": reviewed_grades(SEALED_POSITIVE)}
    for run_dir in (MAIN, SEALED_POSITIVE):
        candidate, _runtime = candidate_state(baseline, file_map(run_dir / "lane"))
        changed = {name for name in candidate.keys() | baseline.keys() if candidate.get(name) != baseline.get(name)}
        assert changed == {_WORK_PATH, HARNESS}

    negative_path = ROOT / "source-review-legacy-boundary/REVIEW.json"
    negative = load(negative_path)["rows"]["gpu-TU-GR-1-off-common-on-sampling"]
    for path, sha in negative["input_sha256"].items():
        assert digest(Path(path)) == sha
    negative_lane = Path(negative["lane"])
    assert file_map(negative_lane) == baseline | negative["changed_files"]
    with TemporaryDirectory(prefix="private-tu-controls-", dir=HERE) as scratch:
        work = Path(scratch)
        parser = parser_controls(work)
        class_lane, empty_lane = work / "class-lane", work / "empty-lane"
        for lane in (class_lane, empty_lane):
            shutil.copytree(MAIN / "lane", lane, ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__"))
        function_source = (MAIN / "lane" / _WORK_PATH).read_text()
        (class_lane / _WORK_PATH).write_text(qualified_class(function_source))
        (empty_lane / _WORK_PATH).write_text(function_source[:function_source.index(f"def {_CONTROL}(")]
                                             + "class TestGraderIsolation:\n    pass\n")
        class_sha = digest(class_lane / _WORK_PATH)
        evidence = [
            ("main-repair-functions", MAIN / "lane", 0),
            ("same-main-repair-class-methods", class_lane, 0),
            ("sealed-positive", SEALED_POSITIVE / "lane", 0),
            ("empty-class", empty_lane, 1, "got rc=5 and {}"),
            ("missing-test-file-baseline", BASELINE / "lane", 1, "file or directory not found"),
        ]
        # Keep bounded evaluator work on shared control affinity. Negative old content
        # may fail earlier than mount handling due to its namespace-skip behavior.
        with ThreadPoolExecutor(max_workers=2) as pool:
            runs = list(pool.map(lambda row: run(*row), evidence))
        runs.append(run("previous-rejected-gpu-off", negative_lane, 1, "simulated namespace"))
    assert previous == {"main_repair": reviewed_grades(MAIN), "sealed_positive": reviewed_grades(SEALED_POSITIVE)}
    document = {
        "case": "TU-GR-1", "schema": "tu-grader-isolation.v2.controls",
        "controls": runs, "junit_parser_controls": parser, "prior_passing_controls": previous,
        "class_fixture_source_sha256": class_sha, "class_fixture_body_ast_equivalent": True,
        "original_support_sha256": CORE_SHA, "only_outcome_file_binding_and_junit_metadata_changed": True,
        "original_grades_preserved": True, "model_calls": 0,
    }
    (HERE / "CONTROL.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(json.dumps({row["id"]: row["rc"] for row in runs}))


if __name__ == "__main__":
    main()
