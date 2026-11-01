import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rowflow_unit as U


def fixture(tmp_path):
    source = tmp_path / "source"
    build = tmp_path / "scratch" / "buildcpu"
    source.mkdir()
    build.mkdir(parents=True)
    source_file = source / U.CPU_SOURCE_REL
    source_file.parent.mkdir(parents=True)
    source_file.write_text("int gguf_unit() { return 1; }\n")
    recipe = tmp_path / "recipe.json"
    recipe.write_text(json.dumps({"cpu": {"configure_definitions": {
        "BUILD_SHARED_LIBS": {"type": "BOOL", "value": "ON"},
        "CMAKE_BUILD_TYPE": {"type": "STRING", "value": "Release"},
    }}}))
    expected = {
        "BUILD_SHARED_LIBS": ("BOOL", "ON"),
        "CMAKE_BUILD_TYPE": ("STRING", "Release"),
        "CMAKE_HOME_DIRECTORY": ("INTERNAL", str(source.resolve())),
        "CMAKE_GENERATOR": ("INTERNAL", "Unix Makefiles"),
        "CMAKE_C_COMPILER": ("FILEPATH", "/usr/bin/cc"),
        "CMAKE_CXX_COMPILER": ("FILEPATH", "/usr/bin/c++"),
        "CMAKE_C_COMPILER_AR": ("FILEPATH", "/usr/bin/gcc-ar-15"),
        "CMAKE_CXX_COMPILER_AR": ("FILEPATH", "/usr/bin/gcc-ar-15"),
        "CMAKE_C_COMPILER_RANLIB": ("FILEPATH", "/usr/bin/gcc-ranlib-15"),
        "CMAKE_CXX_COMPILER_RANLIB": ("FILEPATH", "/usr/bin/gcc-ranlib-15"),
    }
    (build / "CMakeCache.txt").write_text("\n".join(f"{k}:{t}={v}" for k, (t, v) in expected.items()) + "\n")
    makefile = build / U.CPU_MAKEFILE_REL
    makefile.parent.mkdir(parents=True)
    makefile.write_text(f"{U.CPU_OBJECT_REL}: {source_file} other-dependency\n\t/usr/bin/c++ -o {U.CPU_OBJECT_REL} -c {source_file}\n")
    flags = build / U.CPU_FLAGS_REL
    flags.write_text("CXX_COMPILER = /usr/bin/c++\n")
    obj = build / U.CPU_OBJECT_REL
    obj.parent.mkdir(parents=True, exist_ok=True)
    obj.write_bytes(b"x" * 128)
    os.utime(obj, ns=(2_000_000_000, 2_000_000_000))
    return source, build, recipe, obj


def test_accepts_only_fresh_pinned_cpu_object(monkeypatch, tmp_path):
    source, build, recipe, obj = fixture(tmp_path)
    monkeypatch.setattr(U.subprocess, "check_output", lambda *a, **kw: "  Type: REL (Relocatable file)\n")
    command = ["/usr/bin/gmake", "-C", str(build.resolve()), "-f", str(U.CPU_MAKEFILE_REL), str(U.CPU_OBJECT_REL), "-j1"]
    record = U.cpu_compile_record(source=source, build=build, scratch_root=tmp_path / "scratch",
        recipe_path=recipe, source_commit="commit", source_tree="tree", compiler_path=Path("/usr/bin/c++"),
        started_ns=1_000_000_000, command=command, command_returncode=0, output_removed_before=True)
    assert record["schema"] == U.UNIT_SCHEMA
    assert record["kind"] == "cpu_translation_unit_compiled"
    assert record["object_sha256"] == hashlib.sha256(obj.read_bytes()).hexdigest()
    assert record["full_symbol_identity_complete"] is False


def test_rejects_bad_rc_stale_object_and_changed_rule(monkeypatch, tmp_path):
    source, build, recipe, obj = fixture(tmp_path)
    monkeypatch.setattr(U.subprocess, "check_output", lambda *a, **kw: "  Type: REL (Relocatable file)\n")
    command = ["/usr/bin/gmake", "-C", str(build.resolve()), "-f", str(U.CPU_MAKEFILE_REL), str(U.CPU_OBJECT_REL), "-j1"]
    kwargs = dict(source=source, build=build, scratch_root=tmp_path / "scratch", recipe_path=recipe,
        source_commit="commit", source_tree="tree", compiler_path=Path("/usr/bin/c++"), started_ns=1_000_000_000,
        command=command, command_returncode=0, output_removed_before=True)
    with pytest.raises(ValueError, match="successful command"):
        U.cpu_compile_record(**{**kwargs, "command_returncode": 1})
    with pytest.raises(ValueError, match="fresh"):
        U.cpu_compile_record(**{**kwargs, "started_ns": 3_000_000_000})
    makefile = build / U.CPU_MAKEFILE_REL
    makefile.write_text(makefile.read_text().replace("gguf.cpp", "wrong.cpp"))
    with pytest.raises(ValueError, match="does not bind"):
        U.cpu_compile_record(**kwargs)


def test_comparator_records_pass_fail_invalid_and_not_run(tmp_path):
    path = tmp_path / "comparison.json"
    assert U.comparison_outcome(path, None, None)["state"] == "not_run"
    path.write_text(json.dumps({"schema": "r18a.independent_symbol_identity.v1", "symbol_identity_pass": True, "comparisons": {}}))
    os.utime(path, ns=(2_000_000_000, 2_000_000_000))
    assert U.comparison_outcome(path, 1_000_000_000, 0)["state"] == "pass"
    path.write_text(json.dumps({"schema": "r18a.independent_symbol_identity.v1", "symbol_identity_pass": False, "comparisons": {}}))
    os.utime(path, ns=(2_000_000_000, 2_000_000_000))
    assert U.comparison_outcome(path, 1_000_000_000, 1)["state"] == "fail"
    assert U.comparison_outcome(path, 3_000_000_000, 1)["state"] == "invalid"
    assert U.comparison_outcome(path, 1_000_000_000, 2)["state"] == "invalid"


def test_completion_requires_successful_nonpartial_comparison():
    assert U.completion_eligible(exit_code=0, partial=False, comparison={"state": "pass"})
    for rc, partial, state in [(0, True, "pass"), (1, False, "pass"), (0, False, "fail"), (0, False, "invalid"), (75, True, "not_run")]:
        assert not U.completion_eligible(exit_code=rc, partial=partial, comparison={"state": state})


def test_jsonl_appender_isolates_and_refuses_symlinks(tmp_path):
    path = tmp_path / "ROWFLOW-UNITS.jsonl"
    unit = {"schema": U.UNIT_SCHEMA, "kind": "cpu_translation_unit_compiled"}
    U.append_jsonl(path, unit)
    assert json.loads(path.read_text()) == unit
    target = tmp_path / "target"
    target.write_text("")
    link = tmp_path / "link.jsonl"
    link.symlink_to(target)
    with pytest.raises(OSError):
        U.append_jsonl(link, unit)


def test_full_job_emits_real_cpu_unit_to_dryrun_dir_then_exits_before_full_build():
    source = (Path(__file__).resolve().parent / "full_build.py").read_text()
    configure_cpu = source.index("cpu=configure('cpu')")
    compile_unit = source.index("unit=compile_cpu_first_unit(cpu)")
    dryrun_append = source.index("rowflow_unit.append_jsonl(unit_path,unit)")
    dryrun_finish = source.index("finish(75,'rowflow_first_cpu_compile_unit_complete',True)")
    full_build = source.index("run([cmake,'--build',str(cpu),'--target','ggml-cpu'")
    assert configure_cpu < compile_unit < dryrun_append < dryrun_finish < full_build
    assert "rowflow_result_root/'dryrun'/run_id/'cpu-unit.jsonl'" in source
    assert "rowflow_result_root/'full'/run_id/'terminal.jsonl'" in source
    assert "R18_ROWFLOW_RESULT_ROOT missing" in source


def test_spec_and_completion_bind_full_terminal_comparator():
    root = Path(__file__).resolve().parent
    spec = json.loads((root / "rowflow-spec.proposed.json").read_text())
    assert spec["result_format"] == "jsonl"
    assert "/compute-flags/rowflow-results/" in spec["result_path"]
    assert spec["result_path"].endswith("/*/*/*.jsonl")
    assert "successful single-TU CPU compile" in spec["decision_rule"]
    assert "truthful" not in spec["decision_rule"].lower()
    completion = (root / "complete.py").read_text()
    for token in ("full-terminal.jsonl", "full_result_sha256", "symbol_identity_pass", "rowflow_result_file", "rowflow_result_filed"):
        assert token in completion


def test_source_manifest_and_launcher_pin_candidate_runtime_files():
    root = Path(__file__).resolve().parent
    manifest = root / "SOURCE-MANIFEST.sha256"
    launcher = (root / "launcher.v15.sh").read_text()
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    import re
    match = re.search(r"SOURCE_MANIFEST_SHA256=([0-9a-f]{64})", launcher)
    assert match and match.group(1) == digest
    pins = {path: value for value, path in (line.split("  ", 1) for line in manifest.read_text().splitlines())}
    canonical = "/mnt/raid0/llm/tmp/refactor-r18a-v10-independent-symbols-r3-20261101-candidate-b7"
    for name in ("full_build.py", "complete.py", "job.sh", "rowflow_unit.py", "test_rowflow_unit.py"):
        assert pins[f"{canonical}/{name}"] == hashlib.sha256((root / name).read_bytes()).hexdigest()


def test_rowflow_glob_counts_dryrun_and_full_terminal_but_not_legacy_qualification(tmp_path):
    import importlib.util
    rowflow_path = Path('/workspace/scripts/coordination/rowflow/rowflow.py')
    spec = importlib.util.spec_from_file_location('r18a_test_rowflow', rowflow_path)
    rowflow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rowflow)
    root = tmp_path / 'rowflow-results' / 'this-row'
    pattern = str(root / '*' / '*' / '*.jsonl')
    assert rowflow.count_units(pattern, 'jsonl') == 0
    dry = root / 'dryrun' / 'd1' / 'cpu-unit.jsonl'
    U.append_jsonl(dry, {'schema': U.UNIT_SCHEMA, 'kind': 'cpu_translation_unit_compiled'})
    after_dry = rowflow.count_units(pattern, 'jsonl')
    assert after_dry == 1
    full = root / 'full' / 'f1' / 'terminal.jsonl'
    U.append_jsonl(full, {'schema': U.FULL_TERMINAL_SCHEMA, 'run_id': 'f1', 'comparison': {'state': 'fail'}})
    assert rowflow.count_units(pattern, 'jsonl') - after_dry == 1
    (tmp_path / 'legacy-qualification.jsonl').write_text('{"schema":"old-qualification"}\n')
    assert rowflow.count_units(pattern, 'jsonl') == 2


def test_job_isolates_dryrun_build_scratch_from_production_full():
    job = (Path(__file__).resolve().parent / "job.sh").read_text()
    assert 'if [[ "${FILLER_DRYRUN:-0}" == 1 ]]' in job
    assert 'mktemp -d "$D/scratch/dryrun/run-XXXXXXXX"' in job
    assert 'SCRATCH="$D/scratch/full"' in job
    assert '--scratch "$SCRATCH" --mode full' in job
    assert job.index('SCRATCH=$(mktemp -d') < job.index('exec /usr/bin/python3 -B "$D/full_build.py"')
