from __future__ import annotations

import importlib.util
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
