from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "granite_embedder_conversion_preflight.py"
SPEC = importlib.util.spec_from_file_location("granite_embedder_conversion_preflight", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
preflight = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preflight
SPEC.loader.exec_module(preflight)


def _write(path: Path, content: str = "{}") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _tiny_artifacts():
    return (
        preflight.EmbedderArtifact(
            name="granite-test",
            source_dir="granite",
            weight_file="model.safetensors",
            expected_weight_bytes=7,
            q8_target="granite-Q8_0.gguf",
            q4_target="granite-Q4_K_M.gguf",
            context_tokens=32768,
            pooling="cls",
        ),
        preflight.EmbedderArtifact(
            name="e5-test",
            source_dir="e5",
            weight_file="model.safetensors",
            expected_weight_bytes=5,
            q8_target="e5-Q8_0.gguf",
            context_tokens=512,
            pooling="mean",
        ),
    )


def _stage_model(root: Path, artifact) -> None:  # noqa: ANN001
    source = root / artifact.source_dir
    _write(source / "config.json")
    _write(source / "tokenizer.json")
    _write(source / "tokenizer_config.json")
    weight = source / artifact.weight_file
    weight.parent.mkdir(parents=True, exist_ok=True)
    weight.write_bytes(b"0" * artifact.expected_weight_bytes)


def test_build_report_ready_without_running_conversion(tmp_path: Path, monkeypatch) -> None:
    hf_root = tmp_path / "hf"
    llama_root = tmp_path / "llama.cpp"
    models_dir = tmp_path / "models"
    convert_python = tmp_path / "venv" / "bin" / "python"

    artifacts = _tiny_artifacts()
    monkeypatch.setattr(preflight, "ARTIFACTS", artifacts)
    for artifact in artifacts:
        _stage_model(hf_root, artifact)
    _write(llama_root / "convert_hf_to_gguf.py", "#!/usr/bin/env python\n")
    _write(llama_root / "build" / "bin" / "llama-quantize", "#!/bin/sh\n")
    _write(convert_python, "#!/bin/sh\n")
    (llama_root / "convert_hf_to_gguf.py").chmod(0o755)
    (llama_root / "build" / "bin" / "llama-quantize").chmod(0o755)
    convert_python.chmod(0o755)
    models_dir.mkdir()

    report = preflight.build_report(
        hf_root=hf_root,
        llama_root=llama_root,
        models_dir=models_dir,
        convert_python=convert_python,
    )

    assert report["status"] == "ready_for_conversion"
    assert report["failures"] == []
    assert "does not run conversion" in report["note"]
    granite = report["artifacts"][0]
    assert granite["ready_to_convert"] is True
    assert granite["targets"]["q8_0"]["exists"] is False
    assert "convert_hf_to_gguf.py" in granite["commands"]["convert_f16"]
    assert "Q8_0" in granite["commands"]["quantize_q8"]
    assert "Q4_K_M" in granite["commands"]["quantize_q4_k_m"]


def test_build_report_blocks_on_weight_size_mismatch(tmp_path: Path, monkeypatch) -> None:
    hf_root = tmp_path / "hf"
    llama_root = tmp_path / "llama.cpp"
    models_dir = tmp_path / "models"
    convert_python = tmp_path / "venv" / "bin" / "python"

    artifacts = _tiny_artifacts()
    monkeypatch.setattr(preflight, "ARTIFACTS", artifacts)
    for artifact in artifacts:
        _stage_model(hf_root, artifact)
    first = artifacts[0]
    (hf_root / first.source_dir / first.weight_file).write_bytes(b"bad")
    _write(llama_root / "convert_hf_to_gguf.py", "#!/usr/bin/env python\n")
    _write(llama_root / "build" / "bin" / "llama-quantize", "#!/bin/sh\n")
    _write(convert_python, "#!/bin/sh\n")
    (llama_root / "convert_hf_to_gguf.py").chmod(0o755)
    (llama_root / "build" / "bin" / "llama-quantize").chmod(0o755)
    convert_python.chmod(0o755)
    models_dir.mkdir()

    report = preflight.build_report(
        hf_root=hf_root,
        llama_root=llama_root,
        models_dir=models_dir,
        convert_python=convert_python,
    )

    assert report["status"] == "blocked"
    assert any("weight size mismatch" in failure for failure in report["failures"])


# --------------------------------------------------------------------------- #
# CJ-8 — the preflight verdict is three-valued (2026-09-07)
#
# Pre-fix behaviour, and the bite: "the HF tree has not been downloaded yet" and
# "the staged weight file is the wrong size" both appended to one `failures`
# list, both reported `status: blocked`, and both exited 1. An operator reading
# that could not tell "stage the tree" from "the artifact you staged is corrupt".
# Every positive below is paired with a mutation that removes exactly the signal
# under test.
# --------------------------------------------------------------------------- #
def _full_env(tmp_path: Path, monkeypatch, *, stage_models=True, stage_tools=True):
    hf_root = tmp_path / "hf"
    llama_root = tmp_path / "llama.cpp"
    models_dir = tmp_path / "models"
    convert_python = tmp_path / "venv" / "bin" / "python"
    artifacts = _tiny_artifacts()
    monkeypatch.setattr(preflight, "ARTIFACTS", artifacts)
    if stage_models:
        for artifact in artifacts:
            _stage_model(hf_root, artifact)
    if stage_tools:
        _write(llama_root / "convert_hf_to_gguf.py", "#!/usr/bin/env python\n")
        _write(llama_root / "build" / "bin" / "llama-quantize", "#!/bin/sh\n")
        _write(convert_python, "#!/bin/sh\n")
        (llama_root / "convert_hf_to_gguf.py").chmod(0o755)
        (llama_root / "build" / "bin" / "llama-quantize").chmod(0o755)
        convert_python.chmod(0o755)
        models_dir.mkdir()
    return dict(hf_root=hf_root, llama_root=llama_root, models_dir=models_dir,
                convert_python=convert_python), artifacts


def test_unstaged_tree_is_out_of_coverage_not_blocked(tmp_path: Path, monkeypatch) -> None:
    """CATCHES the conflation this row exists to end: an absent input reported as
    a failed check.

    Nothing is staged, so no check ran against any artifact. The verdict must be
    `out-of-coverage` with a cause code, the `failures` list must be EMPTY (no
    check decided against anything), and the status must not be `blocked`.
    """
    env, _ = _full_env(tmp_path, monkeypatch, stage_models=False, stage_tools=False)
    report = preflight.build_report(**env)

    assert report["verdict"] == "out-of-coverage"
    assert report["status"] == "not_assessable"
    assert report["failures"] == []
    assert report["out_of_coverage"], "nothing was staged; something must be undecided"
    assert set(report["out_of_coverage_by_cause"]) == {"absent"}
    for entry in report["out_of_coverage"]:
        assert entry["cause"] == "absent"
        assert entry["cause_means"]


def test_mutation_staging_everything_flips_the_same_run_to_pass(
        tmp_path: Path, monkeypatch) -> None:
    """MUTATION: adds back exactly the staged files, changing nothing else.

    Proves the `out-of-coverage` verdict above is produced by the ABSENT INPUTS
    and not by some unrelated property of the fixture (the tmp paths, the tiny
    artifact table, the absence of a models dir). Without this pairing the test
    above would also pass against a preflight that returned `out-of-coverage`
    unconditionally.
    """
    env, _ = _full_env(tmp_path, monkeypatch)
    report = preflight.build_report(**env)
    assert report["verdict"] == "pass"
    assert report["status"] == "ready_for_conversion"
    assert report["out_of_coverage"] == []


def test_a_corrupt_weight_is_still_a_decided_fail(tmp_path: Path, monkeypatch) -> None:
    """The three-valued split must not swallow real findings. A staged-but-wrong
    weight WAS checked and WAS rejected, so it stays `fail`/`blocked` — the
    original behaviour, which the fix must preserve exactly."""
    env, artifacts = _full_env(tmp_path, monkeypatch)
    first = artifacts[0]
    (env["hf_root"] / first.source_dir / first.weight_file).write_bytes(b"bad")
    report = preflight.build_report(**env)

    assert report["verdict"] == "fail"
    assert report["status"] == "blocked"
    assert any("weight size mismatch" in f for f in report["failures"])
    assert report["out_of_coverage"] == []


def test_a_decided_fail_outranks_an_undecided_remainder(
        tmp_path: Path, monkeypatch) -> None:
    """When a check ran and rejected the artifact, THAT is the finding — the
    unstaged remainder must not demote a real failure to 'we could not tell'.
    This is the direction that would hide a defect, so it is pinned."""
    env, artifacts = _full_env(tmp_path, monkeypatch)
    first = artifacts[0]
    (env["hf_root"] / first.source_dir / first.weight_file).write_bytes(b"bad")
    # ...and remove an unrelated staged file, producing undecided items too.
    (env["hf_root"] / artifacts[1].source_dir / "config.json").unlink()

    report = preflight.build_report(**env)
    assert report["out_of_coverage"], "fixture failed to produce an undecided item"
    assert report["verdict"] == "fail"
    assert report["status"] == "blocked"


def test_exit_codes_are_three_valued(tmp_path: Path, monkeypatch, capsys) -> None:
    """0 pass / 1 fail / 2 could-not-check, the contract already ratified in
    scripts/validate/check_ratification_receipts.py. A wrapper testing `!= 0` is
    unaffected; one that wants the distinction can now have it."""
    env, artifacts = _full_env(tmp_path, monkeypatch)
    argv = ["--hf-root", str(env["hf_root"]), "--llama-root", str(env["llama_root"]),
            "--models-dir", str(env["models_dir"]),
            "--convert-python", str(env["convert_python"])]

    assert preflight.main(argv) == 0
    (env["hf_root"] / artifacts[0].source_dir / artifacts[0].weight_file).write_bytes(b"bad")
    assert preflight.main(argv) == 1
    for artifact in artifacts:
        shutil.rmtree(env["hf_root"] / artifact.source_dir)
    assert preflight.main(argv) == 2
    capsys.readouterr()


def test_mutation_a_two_valued_exit_cannot_separate_those_three_runs(
        tmp_path: Path, monkeypatch, capsys) -> None:
    """MUTATION: collapses exactly the third exit code, keeping the three runs.

    Reproduces the pre-fix mapping (`0 if ready else 1`) over the SAME three
    fixtures the test above distinguishes, and shows the corrupt-artifact run
    and the nothing-staged run become one value. Without the third code, the
    only two remedies an operator could choose between are indistinguishable.
    """
    env, artifacts = _full_env(tmp_path, monkeypatch)
    argv = ["--hf-root", str(env["hf_root"]), "--llama-root", str(env["llama_root"]),
            "--models-dir", str(env["models_dir"]),
            "--convert-python", str(env["convert_python"])]

    def pre_fix_exit(code: int) -> int:
        return 0 if code == 0 else 1          # the two-valued mapping

    (env["hf_root"] / artifacts[0].source_dir / artifacts[0].weight_file).write_bytes(b"bad")
    corrupt = preflight.main(argv)
    for artifact in artifacts:
        shutil.rmtree(env["hf_root"] / artifact.source_dir)
    unstaged = preflight.main(argv)
    capsys.readouterr()

    assert corrupt != unstaged
    assert pre_fix_exit(corrupt) == pre_fix_exit(unstaged) == 1
